"""Two tracking engines: the fast tracker on every frame, Segment Anything on hard frames only
(no window needed).

A synthetic clip has a ball moving alone, plus a "hand" (a block) moving beside it for the first
frames. The pixel-change gate must stay quiet for the lone ball and fire for the hand; the hard
engine must respect its cooldown; and a tracking run with it must keep the points on the ball.
The loop tests use a stand-in segmenter that returns the ball's true outline, because the real
model takes seconds per frame; one check runs the real model on a single frame.
"""

import os
import shutil
import subprocess
import tempfile

import cv2
import numpy as np

from tests import harness as h
h.setup_env()

from core import NormalizedRect, PixelRect  # noqa: E402
from experiments.rigid.assist import AssistSettings, HardEngine, ring_change  # noqa: E402
from experiments.rigid.rigid import Rigid  # noqa: E402

W, H, N, R = 640, 480, 90, 12
HAND_FRAMES = range(1, 25)  # The hand is beside the ball for these frames


def truth(t: int) -> tuple[float, float]:
    """The ball falls down the middle (as down a tube), from y = 80."""
    return 320.0, 80.0 + 4.0 * t


def frame(t: int, with_hand: bool = True) -> np.ndarray:
    img = np.full((H, W, 3), 60, np.uint8)
    img[::8, ::8] = 110
    x, y = truth(t)
    cv2.circle(img, (int(round(x)), int(round(y))), R, (255, 255, 255), -1)
    if with_hand and t in HAND_FRAMES:
        hx = int(x + R + 4 + 5 * t)  # Moves away to the right
        cv2.rectangle(img, (hx, int(y - 3 * R)), (hx + 4 * R, int(y + 3 * R)), (150, 180, 220), -1)
    return img


def make_clip() -> str:
    path = os.path.join(h.WORK_DIR, f"assist_ball_{W}x{H}_{N}.mp4")
    if os.path.isfile(path):
        return path
    p = subprocess.Popen([shutil.which("ffmpeg"), "-loglevel", "error", "-y", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for t in range(N):
        p.stdin.write(frame(t).tobytes())
    p.stdin.close()
    p.wait()
    return path


class TruthSegmenter:
    """Stands in for Segment Anything: returns the ball's true outline on the frame it is shown.
    The frame is recognised by the ball's position (the brightest blob)."""

    def __init__(self):
        self.calls = 0

    def set_image(self, rgb):
        self._mask = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) > 240

    def predict(self, points=None, labels=None, box=None):
        self.calls += 1
        return self._mask, 0.99


def _box(t):
    x, y = truth(t)
    return PixelRect(int(x - R), int(y - R), 2 * R, 2 * R)


def test_gate_is_quiet_alone_and_fires_for_the_hand():
    gray = lambda t, hand: cv2.cvtColor(frame(t, hand), cv2.COLOR_BGR2GRAY)  # noqa: E731
    alone = [ring_change(gray(t - 1, False), gray(t, False), _box(t), _box(t - 1))
             for t in range(1, 40)]
    # Frames 2 and 3: the hand is still inside the ring (it then moves out of it to the right)
    hand = [ring_change(gray(t - 1, True), gray(t, True), _box(t), _box(t - 1))
            for t in range(2, 4)]
    limit = AssistSettings().ring_change
    h.check("a ball moving alone stays under the gate", max(alone) < limit,
            f"max {max(alone):.2f} vs {limit}")
    h.check("a hand moving beside the ball goes over the gate", min(hand) > limit,
            f"min {min(hand):.2f} vs {limit}")


def test_hard_engine_respects_its_cooldown():
    engine = HardEngine(TruthSegmenter(), AssistSettings(cooldown=10))
    g0 = cv2.cvtColor(frame(1), cv2.COLOR_BGR2GRAY)
    g1 = cv2.cvtColor(frame(2), cv2.COLOR_BGR2GRAY)
    h.check("a hand frame is hard", engine.is_hard(g0, g1, _box(2), _box(1), 0.9, 2))
    found = engine.redetect(frame(2), truth(1), _box(1), 2)
    h.check("the hard engine finds the ball's box", found is not None and
            abs(found.tocenter()[0] - truth(2)[0]) <= 1 and abs(found.tocenter()[1] - truth(2)[1]) <= 1,
            str(found))
    h.check("right after, the engine is cooling down", not engine.is_hard(g0, g1, _box(2), _box(1), 0.0, 5))
    h.check("after the cooldown it may run again", engine.ready(12))


def test_tracking_with_assist_stays_on_the_ball():
    clip = make_clip()
    work = tempfile.mkdtemp(dir=h.WORK_DIR)
    r = Rigid(trimpath=os.path.join(work, "trim.mp4"), vwidth=W, vheight=H)
    r.addvideo(clip)
    from tests.test_tracker_accuracy import _Crop, _NoFilter
    seg = TruthSegmenter()
    engine = HardEngine(seg)
    x0, y0 = truth(0)
    rect = NormalizedRect((x0 - R) / W, (y0 - R) / H, 2 * R / W, 2 * R / H)
    r.track(0, [rect], [], _NoFilter(), _Crop(r.fwidth, r.fheight), None, assist=engine)
    scale = r.fwidth / W
    errs = [np.hypot(p[0] / scale - truth(t)[0], p[1] / scale - truth(t)[1])
            for t, p in enumerate(r.trackpts[0]) if len(p) == 2]
    h.check("the hard engine ran while the hand was there", 1 <= engine.uses <= 4, str(engine.uses))
    h.check("it ran far less often than once a frame", engine.uses < N // 10, str(engine.uses))
    h.check("every point stays on the ball", max(errs) < 3 * R * scale + 2,
            f"worst {max(errs):.1f} px")


def test_real_segment_anything_finds_the_ball():
    from core import abspath
    path = abspath("models/sam_vit_b_01ec64.pth")
    if not os.path.isfile(path):
        h.say("  (skipped: Segment Anything model not installed)")
        return
    from media.segmenter import default_segmenter
    engine = HardEngine(default_segmenter())
    found = engine.redetect(frame(3), truth(2), _box(2), 3)
    h.check("Segment Anything finds the ball, not the hand", found is not None and
            abs(found.tocenter()[0] - truth(3)[0]) <= 3 and abs(found.tocenter()[1] - truth(3)[1]) <= 3
            and found.width < 4 * R, str(found))


if __name__ == "__main__":
    h.run_tests([test_gate_is_quiet_alone_and_fires_for_the_hand, test_hard_engine_respects_its_cooldown,
                 test_tracking_with_assist_stays_on_the_ball, test_real_segment_anything_finds_the_ball])
