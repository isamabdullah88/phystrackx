"""Can the tracker follow an object? Uses a synthetic clip where the ball's true path is known.

- The raw tracker must follow the ball closely on the clean clip.
- The tracking pipeline (proxy, preprocessing, frame bookkeeping) must keep its points on the
  same frame and the same spot, both at native size and when the viewer forces a downscale.

Errors are measured in the original clip's pixels. No window is needed.
"""

import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

from tests import harness as h
h.setup_env()

from core import NormalizedRect, PixelRect  # noqa: E402
from experiments.rigid.mltracker import MLTracker  # noqa: E402
from experiments.rigid.rigid import Rigid, FullResSource  # noqa: E402

W, H, N, R = 640, 480, 160, 12  # frame size, ball radius, frame count


def truth(t: int) -> tuple[float, float]:
    """The ball's centre on frame t (a smooth bouncing path)."""
    return (320 + 220 * np.sin(2 * np.pi * t / 80.0),
            240 + 160 * np.abs(np.sin(np.pi * t / 50.0)) - 60)


def frame(t: int) -> np.ndarray:
    img = np.full((H, W, 3), 60, np.uint8)
    img[::8, ::8] = 110  # light texture, so the tracker has something to lock onto
    x, y = truth(t)
    cv2.circle(img, (int(round(x)), int(round(y))), R, (255, 255, 255), -1)
    return img


def make_clip() -> str:
    path = os.path.join(h.WORK_DIR, f"ball_{W}x{H}_{N}.mp4")
    if os.path.isfile(path):
        return path
    ffmpeg = shutil.which("ffmpeg")
    p = subprocess.Popen([ffmpeg, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-s", f"{W}x{H}", "-r", "30", "-i", "-", "-c:v", "libx264",
                          "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", path],
                         stdin=subprocess.PIPE)
    for t in range(N):
        p.stdin.write(frame(t).tobytes())
    p.stdin.close()
    p.wait()
    return path


class _Crop:
    """Stands in for the GUI crop tool: no crop, the full frame."""
    def __init__(self, w, hgt):
        self.cropwidth, self.cropheight, self.cropx, self.cropy = w, hgt, 0, 0

    def apply_crop(self, f):
        return f


class _NoFilter:
    def apply_filter(self, f):
        return f


def _median_error(errs) -> tuple[float, float]:
    e = np.asarray(errs)
    return float(np.median(e)), float(e.max())


def test_raw_tracker_follows_the_ball():
    tr = MLTracker("nanotrack")
    x0, y0 = truth(0)
    tr.initialize_tracker(frame(0), PixelRect(int(x0) - R, int(y0) - R, 2 * R, 2 * R))
    errs, lost = [], 0
    for t in range(1, N):
        ok, box = tr.update_tracker(frame(t))
        if not ok:
            lost += 1
            continue
        x, y = truth(t)
        errs.append(np.hypot(box.xmin + box.width / 2 - x, box.ymin + box.height / 2 - y))
    med, worst = _median_error(errs)
    h.check("raw tracker loses the ball on no frames", lost == 0, f"lost {lost}")
    h.check("raw tracker median error is under 2 px", med < 2.0, f"median {med:.2f}")


def _run_pipeline(clip: str, viewer_height: int, fullres: bool = False):
    """Runs the tracking pipeline (proxy + preprocessing, or the full-resolution copy) on the clip,
    as the app does. Stored points are in on-screen (proxy) pixels either way."""
    work = tempfile.mkdtemp(dir=h.WORK_DIR)
    r = Rigid(trimpath=os.path.join(work, "trim.mp4"), vwidth=W, vheight=viewer_height)
    r.addvideo(clip)
    x0, y0 = truth(0)
    rect = NormalizedRect((x0 - R) / W, (y0 - R) / H, 2 * R / W, 2 * R / H)
    source = FullResSource(r.ensure_native()) if fullres else None
    r.track(0, [rect], [], _NoFilter(), _Crop(r.fwidth, r.fheight), None, fullres=source)
    return r, r.fwidth / W


def _pipeline_errors(r, scale):
    errs, lost = [], 0
    for t in range(1, N - 1):
        pt = r.trackpts[0][t]
        if len(pt) != 2:
            lost += 1
            continue
        x, y = truth(t)
        errs.append(np.hypot(pt[0] / scale - x, pt[1] / scale - y))
    return errs, lost


def test_pipeline_at_native_size():
    clip = make_clip()
    r, scale = _run_pipeline(clip, viewer_height=H)
    errs, lost = _pipeline_errors(r, scale)
    med, worst = _median_error(errs)
    h.check("pipeline (native size) keeps every frame", lost == 0, f"lost {lost}")
    h.check("pipeline (native size) points sit on the ball: median under 2 px",
            med < 2.0, f"median {med:.2f}, worst {worst:.2f}")


def test_pipeline_when_the_viewer_downscales():
    clip = make_clip()
    r, scale = _run_pipeline(clip, viewer_height=H // 2)
    errs, lost = _pipeline_errors(r, scale)
    med, worst = _median_error(errs)
    h.check("pipeline (half size) keeps every frame", lost == 0, f"lost {lost}")
    h.check("pipeline (half size) points sit on the ball: median under 3 px",
            med < 3.0, f"median {med:.2f}, worst {worst:.2f}")


def test_pipeline_full_resolution_when_the_viewer_downscales():
    clip = make_clip()
    r, scale = _run_pipeline(clip, viewer_height=H // 2, fullres=True)
    errs, lost = _pipeline_errors(r, scale)
    med, worst = _median_error(errs)
    h.check("pipeline (half size, full resolution) keeps every frame", lost == 0, f"lost {lost}")
    h.check("pipeline (half size, full resolution) points sit on the ball: median under 2 px",
            med < 2.0, f"median {med:.2f}, worst {worst:.2f}")


def test_fullres_region_maps_the_crop():
    """The clip's area in the full-size copy: a crop at (40, 20) in a 320x240 proxy of a 640x480
    copy, 100x80 on screen, is (80, 40) to (280, 200) in the copy."""
    from types import SimpleNamespace
    r = Rigid(trimpath=os.path.join(h.WORK_DIR, "unused.mp4"), vwidth=W, vheight=H)
    r.proxysize, r.proxyfcount = (320, 240), N
    native = SimpleNamespace(width=640, height=480, fcount=N)
    region = r._fullres_region(FullResSource("unused", 0, (40, 20)), native, 100, 80)
    h.check("full-size region follows the crop", region == (80, 40, 280, 200), str(region))
    region = r._fullres_region(FullResSource("unused", 0, (0, 0)), native, 320, 240)
    h.check("uncropped clip covers the whole copy", region == (0, 0, 640, 480), str(region))


def test_several_objects_track_the_same_as_one():
    """Several objects are tracked in parallel threads: each must get exactly the positions it gets
    when tracked alone."""
    clip = make_clip()
    work = tempfile.mkdtemp(dir=h.WORK_DIR)
    r = Rigid(trimpath=os.path.join(work, "trim.mp4"), vwidth=W, vheight=H)
    r.addvideo(clip)
    x0, y0 = truth(0)
    ball = NormalizedRect((x0 - R) / W, (y0 - R) / H, 2 * R / W, 2 * R / H)
    corner = NormalizedRect(0.05, 0.05, 0.1, 0.1)
    crop = _Crop(r.fwidth, r.fheight)
    r.track(0, [ball], [], _NoFilter(), crop, None)
    alone = [list(p) for p in r.trackpts[0]]
    r.track(0, [ball, corner], [], _NoFilter(), crop, None)
    together = [list(p) for p in r.trackpts[0]]
    h.check("two objects in threads: the ball's positions are unchanged", alone == together,
            f"first difference at {next((i for i, (a, b) in enumerate(zip(alone, together)) if a != b), None)}")
    h.check("the second object is tracked too", sum(len(p) == 2 for p in r.trackpts[1]) > 0.9 * len(alone))


if __name__ == "__main__":
    h.run_tests([test_raw_tracker_follows_the_ball, test_pipeline_at_native_size,
                 test_pipeline_when_the_viewer_downscales,
                 test_pipeline_full_resolution_when_the_viewer_downscales,
                 test_fullres_region_maps_the_crop, test_several_objects_track_the_same_as_one])
