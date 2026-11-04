"""
Animated GIFs of a trial, for checking a tracking run by eye (outside the app).

- overview_gif: the whole video, with a timeline that marks the trim, a banner saying whether the
  frame is inside the trim, and the tracker's selection drawn on each tracked frame.
- selection_gif: a close-up around the tracked object over the trim (a quick look on the
  selection), to see how well the box stays on the ball.

Both read a Qt project file (.phystrack, format "phystrackx-qt"): its video, trim, and the object's
box on each frame. The boxes are in picture pixels: the video upright (its rotation flag applied)
and scaled to the project's "picture" size, so frames are read the same way here.

    python -m core.render "Trial 1.phystrack" out_dir/
"""

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

GREEN, RED, GREY, WHITE, BLACK = (60, 200, 60), (40, 40, 230), (150, 150, 150), (255, 255, 255), (0, 0, 0)


def load_project(path: str) -> dict:
    """The parts of a project file the renders need: video, picture size, trim, fps, and each
    object's {frame: [x, y, w, h]} boxes and marked frame."""
    with open(path) as f:
        data = json.load(f)
    video = data["video"]
    if not os.path.isfile(video):   # Moved with its project: look beside it
        video = os.path.join(os.path.dirname(os.path.abspath(path)), os.path.basename(video))
    objects = []
    for obj in data.get("objects", []):
        boxes = {int(k): v for k, v in (obj.get("boxes") or {}).items()}
        objects.append({"number": obj.get("number"), "boxes": boxes, "marked": obj.get("marked"),
                        "marked_frame": obj.get("marked_frame")})
    return {"video": video, "picture": tuple(data["picture"]), "trim": tuple(data["trim"]),
            "objects": objects, "fps": data.get("fps")}


def _frames(video: str, picture: tuple, indices):
    """Yields (index, BGR frame in picture pixels) for the sorted indices, reading forward."""
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    wanted = sorted(set(indices))
    i, k = 0, 0
    while k < len(wanted):
        if not cap.grab():
            break
        if i == wanted[k]:
            ok, frame = cap.retrieve()
            if ok:
                yield i, cv2.resize(frame, picture, interpolation=cv2.INTER_AREA)
            k += 1
        i += 1
    cap.release()


def frame_count(video: str) -> int:
    cap = cv2.VideoCapture(video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return n


def _save_gif(frames: list, out: str, ms: int) -> str:
    images = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in frames]
    # One shared palette keeps the file small and the colours steady between frames
    pal = images[len(images) // 2].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    images = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in images]
    images[0].save(out, save_all=True, append_images=images[1:], duration=ms, loop=0, optimize=True)
    return out


def overview_gif(project: str, out: str, width: int = 300, step: int = 4, fps: float = 120.0,
                 speed: float = 1.0, lead: float = 1.0) -> str:
    """
    The whole video as a GIF, every `step`-th frame, `width` pixels wide.

    A bar under the picture is the timeline: the trim is the green span, the playhead the white
    line. The banner says IN TRIM / OUTSIDE TRIM with the frame and time. Each tracked frame shows
    the selection box (green), and the marked frame its box in red. fps is the recording rate
    (time stamps); speed scales playback against real time (1 = real time at fps). The clip runs
    from `lead` seconds before the trim to the trim's end (lead=None: the whole video).
    """
    p = load_project(project)
    n = frame_count(p["video"])
    (t0, t1), (pw, ph) = p["trim"], p["picture"]
    scale = width / pw
    h = round(ph * scale)
    bar = 18
    frames = []
    first, last = (0, n - 1) if lead is None else (max(0, t0 - round(lead * fps)), min(t1, n - 1))
    for i, frame in _frames(p["video"], p["picture"], range(first, last + 1, step)):
        img = cv2.resize(frame, (width, h), interpolation=cv2.INTER_AREA)
        inside = t0 <= i <= t1
        for obj in p["objects"]:
            box = obj["boxes"].get(i)
            if box is None and obj["marked_frame"] == i:
                box = obj["marked"]
            if box is not None:
                x, y, w, hh = (v * scale for v in box)
                pad = 3
                colour = RED if obj["marked_frame"] == i else GREEN
                cv2.rectangle(img, (int(x - pad), int(y - pad)), (int(x + w + pad), int(y + hh + pad)),
                              colour, 2)
        canvas = np.full((h + bar + 22, width, 3), 30, np.uint8)
        canvas[22:22 + h] = img
        cv2.rectangle(canvas, (0, 0), (width, 21), GREEN if inside else (60, 60, 160), -1)
        cv2.putText(canvas, f"{'IN TRIM' if inside else 'OUTSIDE TRIM'}  f{i}  {i / fps:.2f}s",
                    (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, WHITE, 1, cv2.LINE_AA)
        y0 = 22 + h + 4
        cv2.rectangle(canvas, (0, y0), (width - 1, y0 + bar - 8), GREY, -1)
        cv2.rectangle(canvas, (int(t0 / n * width), y0), (int(t1 / n * width), y0 + bar - 8), GREEN, -1)
        x = int(i / n * width)
        cv2.line(canvas, (x, y0 - 2), (x, y0 + bar - 6), WHITE, 2)
        frames.append(canvas)
    return _save_gif(frames, out, max(20, round(1000 * step / fps / speed)))


def selection_gif(project: str, out: str, size: int = 160, half: int = 40, step: int = 2,
                  fps: float = 120.0, speed: float = 0.5, n: int = 0) -> str:
    """
    A close-up of object n's selection over the trim: a square of 2*half picture pixels around
    the box centre, enlarged to `size` pixels, with the box drawn and a crosshair on its centre.
    The crop follows the box, so a box that drifts off the ball shows as the ball moving away from
    the crosshair. Frames with no box (lost) are shown red-framed at the last known place.
    """
    p = load_project(project)
    obj = p["objects"][n]
    (t0, t1), (pw, ph) = p["trim"], p["picture"]
    tracked = sorted(obj["boxes"])
    start = tracked[0] if tracked else t0
    indices = range(start, (tracked[-1] if tracked else t1) + 1, step)
    k = size / (2 * half)
    frames, last = [], None
    for i, frame in _frames(p["video"], p["picture"], indices):
        box = obj["boxes"].get(i)
        lost = box is None
        box = box or last
        if box is None:
            continue
        last = box
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        # Pad the frame so a crop near the edge stays the same size
        padded = cv2.copyMakeBorder(frame, half, half, half, half, cv2.BORDER_CONSTANT, value=BLACK)
        ix, iy = int(round(cx)), int(round(cy))
        crop = padded[iy:iy + 2 * half, ix:ix + 2 * half]
        img = cv2.resize(crop, (size, size), interpolation=cv2.INTER_CUBIC)
        bx, by = (x - cx + half) * k, (y - cy + half) * k
        cv2.rectangle(img, (int(bx), int(by)), (int(bx + w * k), int(by + h * k)), RED if lost else GREEN, 1)
        c = size // 2
        cv2.line(img, (c - 6, c), (c + 6, c), WHITE, 1)
        cv2.line(img, (c, c - 6), (c, c + 6), WHITE, 1)
        canvas = np.full((size + 18, size, 3), 30, np.uint8)
        canvas[18:] = img
        cv2.putText(canvas, f"f{i} {i / fps:.2f}s{' LOST' if lost else ''}", (3, 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, RED if lost else WHITE, 1, cv2.LINE_AA)
        frames.append(canvas)
    return _save_gif(frames, out, max(20, round(1000 * step / fps / speed)))


if __name__ == "__main__":
    project, folder = sys.argv[1], sys.argv[2]
    os.makedirs(folder, exist_ok=True)
    name = os.path.splitext(os.path.basename(project))[0]
    print(overview_gif(project, os.path.join(folder, f"{name}_video.gif")))
    print(selection_gif(project, os.path.join(folder, f"{name}_selection.gif")))
