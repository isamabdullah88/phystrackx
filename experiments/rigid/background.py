"""
background.py

The still background of a clip from a fixed camera: everything that does not move (lens dirt, the
tube, the clamp stand, the ruler, the wall). A tracker can then look for what differs from it, so
static clutter that looks like a ball no longer competes with the ball.

- estimate_background: the per-pixel median of frames spread over the clip. A ball that sits still
  for less than half of the sampled frames does not get into it; one that rests longer leaves a
  ghost, so the background can be taken again without the ball where it is known (exclude).
- rested: whether a first track shows the ball resting long enough to leave a ghost.
- camera_moved: whether the background is any good (the camera shook or panned).

No GUI here. Author: Isam Balghari
"""

import warnings

import cv2
import numpy as np


def _gray(frame) -> np.ndarray:
    return (cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame).astype(np.float32)


def sample_frames(n: int, count: int = 30) -> np.ndarray:
    """The indices of the frames the background is taken from."""
    return np.unique(np.linspace(0, n - 1, min(count, n)).round().astype(int))


def estimate_background(frames, count: int = 30, max_shift: float = 1.5,
                        exclude=None, base: np.ndarray | None = None) -> np.ndarray | None:
    """The median of `count` frames spread over `frames` (any sequence of grey or BGR images), as
    float32 grey, each frame first scaled to the same mean brightness (flicker, auto exposure).
    None when the camera moved by more than `max_shift` pixels between the samples, as a median of a
    moving picture is a blur that matches nothing.

    `exclude` maps a frame index to a disc (x, y, radius) left out of that frame (where the ball
    was), so a ball that rested in one place for much of the clip does not stay in the background
    as a ghost. A pixel left out of every sample keeps the plain median. With `base` (this clip's
    plain background, from an earlier call), only the box around the discs is worked out again."""
    n = len(frames)
    if n < 3:
        return None
    picks = sample_frames(n, count)
    discs = [(j, exclude[i]) for j, i in enumerate(picks.tolist()) if exclude and exclude.get(i) is not None]
    if base is not None and discs:
        box = _box(discs, base.shape)
        if box is None:
            return base
        x0, y0, x1, y1 = box
        parts, means = [], []
        for i in picks:
            g = _gray(frames[i])
            means.append(float(g.mean()))
            parts.append(g[y0:y1, x0:x1])
        stack = np.stack(parts)
        means = np.array(means)[:, None, None]
        stack *= float(means.mean()) / np.maximum(means, 1e-3)
        return _without(base.copy(), stack, discs, box, (x0, y0))
    stack = np.stack([_gray(frames[i]) for i in picks])
    means = stack.mean(axis=(1, 2), keepdims=True)
    stack *= float(means.mean()) / np.maximum(means, 1e-3)
    background = np.median(stack, axis=0).astype(np.float32)
    if camera_moved(stack, background, max_shift):
        return None
    if discs:
        box = _box(discs, background.shape)
        if box is not None:
            x0, y0, x1, y1 = box
            background = _without(background, stack[:, y0:y1, x0:x1], discs, box, (x0, y0))
    return background


def _box(discs, shape):
    """The box (x0, y0, x1, y1) around the left-out discs, or None if it is empty."""
    h, w = shape
    x0 = max(0, int(min(x - rad for _, (x, y, rad) in discs)))
    y0 = max(0, int(min(y - rad for _, (x, y, rad) in discs)))
    x1 = min(w, int(max(x + rad for _, (x, y, rad) in discs)) + 2)
    y1 = min(h, int(max(y + rad for _, (x, y, rad) in discs)) + 2)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _without(background, part, discs, box, origin):
    """The background with the box's median taken again from `part` (the samples cut to the box),
    leaving the discs out (a NaN-aware median is slow, so only the box)."""
    x0, y0, x1, y1 = box
    part = part.copy()
    yy, xx = np.mgrid[y0:y1, x0:x1]
    for j, (x, y, rad) in discs:
        part[j][(xx - x) ** 2 + (yy - y) ** 2 <= rad * rad] = np.nan
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # Pixels left out of every sample
        again = np.nanmedian(part, axis=0)
    region = background[y0:y1, x0:x1]
    region[np.isfinite(again)] = again[np.isfinite(again)]
    return background


def rested(points, radius: float, share: float) -> bool:
    """True when one place holds at least `share` of the ball's positions `points` (at the sampled
    frames; NaN where unknown): the ball sat there long enough to be in the median."""
    pts = np.asarray(points, float)
    pts = pts[np.isfinite(pts).all(axis=1)]
    if not len(pts):
        return False
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    return bool(((d <= radius).sum(axis=1) >= share * len(points)).any())


def camera_moved(stack, background, max_shift: float = 1.5, checks: int = 5) -> bool:
    """True when any of a few sampled frames is shifted against the background by more than
    `max_shift` pixels (phase correlation, which looks at the whole picture, so a moving ball or
    hand does not count)."""
    # At half size (a quarter of the work; the shift found is halved, so is the limit)
    half = (lambda a: cv2.resize(a, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    small = half(background)
    window = cv2.createHanningWindow(small.shape[::-1], cv2.CV_32F)
    for i in np.linspace(0, len(stack) - 1, min(checks, len(stack))).round().astype(int):
        # OpenCV (4.11) multiplies its inputs by the window in place: half() gives fresh copies
        (dx, dy), _ = cv2.phaseCorrelate(half(background), half(stack[i]), window)
        if 2 * np.hypot(dx, dy) > max_shift:
            return True
    return False
