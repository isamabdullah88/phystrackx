"""
ringfit.py

The ball's geometric centre from its round outline: a ring of the ball's radius is laid where the
picture's edges are strongest. A blob centre (blobtracker.py) is the middle of what stands out,
and a shiny ball's highlights pull it toward them, more so when motion blur smears them; the
outline is round whatever is inside it, and blur spreads it evenly both ways, so its centre stays
put.

With the clip's still background (background.py), the edges are those of what differs from it, so
a tube wall or a ruler line that runs along the ball's edge does not pull the ring onto itself.

- fit_radius: the ball's radius, from a few frames (a hand-drawn selection is rarely tight).
- ring_centre: the centre on one frame, near a first guess.
- ring_refine: every measured frame of a track moved to its ring centre (tracks from cliptrack).

No GUI here. Author: Isam Balghari
"""

import cv2
import numpy as np

STRONG = 2.0      # Least strength (edge along the ring over the window's mean edge) to trust a fit
REACH = 0.5       # A fit may move the centre this many radii from the first guess
_kernels: dict = {}


def _ring(r: float, width: float = 0.7) -> np.ndarray:
    """A ring of radius r (a Gaussian profile `width` px across), summing to 1."""
    key = round(r * 20)
    if key not in _kernels:
        k = int(np.ceil(r + 3 * width))
        yy, xx = np.mgrid[-k:k + 1, -k:k + 1].astype(np.float32)
        ring = np.exp(-((np.hypot(xx, yy) - r) ** 2) / (2 * width * width)).astype(np.float32)
        _kernels[key] = ring / ring.sum()
    return _kernels[key]


def edges(gray, background, p, half: int, scale: float = 1.0):
    """Edge strength (gradient magnitude) in the window of `half` px around p of the grey frame,
    or of its difference from the background (`scale`: the frame's brightness over the
    background's). Returns (edges, window origin) or None at the frame's border."""
    x0, y0 = int(round(p[0])) - half, int(round(p[1])) - half
    h, w = gray.shape[:2]
    if x0 < 0 or y0 < 0 or x0 + 2 * half + 1 > w or y0 + 2 * half + 1 > h:
        return None
    win = np.asarray(gray[y0:y0 + 2 * half + 1, x0:x0 + 2 * half + 1], np.float32)
    if background is not None:
        win = np.abs(win - background[y0:y0 + 2 * half + 1, x0:x0 + 2 * half + 1] * scale)
    win = cv2.GaussianBlur(win, (0, 0), 0.8)
    return cv2.magnitude(cv2.Sobel(win, cv2.CV_32F, 1, 0), cv2.Sobel(win, cv2.CV_32F, 0, 1)), (x0, y0)


def _peak(edge, origin, p, r, reach):
    """(centre, strength) of the best ring of radius r within `reach` px of p, sub-pixel."""
    score = cv2.filter2D(edge, -1, _ring(r), borderType=cv2.BORDER_CONSTANT)
    x0, y0 = origin
    yy, xx = np.mgrid[:score.shape[0], :score.shape[1]]
    far = (xx + x0 - p[0]) ** 2 + (yy + y0 - p[1]) ** 2 > reach * reach
    score[far] = -1
    y, x = np.unravel_index(int(np.argmax(score)), score.shape)
    best = float(score[y, x])
    dx = dy = 0.0
    if 0 < x < score.shape[1] - 1 and min(score[y, x - 1], score[y, x + 1]) >= 0:
        a, b, c = score[y, x - 1], best, score[y, x + 1]
        dx = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c < 0 else 0.0
    if 0 < y < score.shape[0] - 1 and min(score[y - 1, x], score[y + 1, x]) >= 0:
        a, b, c = score[y - 1, x], best, score[y + 1, x]
        dy = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c < 0 else 0.0
    return np.array([x + x0 + dx, y + y0 + dy]), best / max(float(edge.mean()), 1e-6)


def ring_centre(gray, background, p, r: float, reach: float | None = None, scale: float = 1.0):
    """(centre, strength) of the ball of radius r near p; strength about 1 means no ring there,
    STRONG or more a clear one. (p, 0) at the frame's border."""
    reach = REACH * r if reach is None else reach
    got = edges(gray, background, p, int(np.ceil(r + reach)) + 4, scale)
    if got is None:
        return np.asarray(p, float), 0.0
    return _peak(*got, p, r, reach)


def fit_radius(windows, r0: float) -> float:
    """The ball's radius from (edges, origin, p) of a few frames: the radius from 0.6 to 1.15 of
    the selection's `r0` whose ring is strongest on most of them (the median of each one's best)."""
    radii = r0 * np.arange(0.6, 1.151, 0.025)
    best = []
    for edge, origin, p in windows:
        strengths = [_peak(edge, origin, p, r, REACH * r0)[1] for r in radii]
        if max(strengths) >= STRONG:
            best.append(radii[int(np.argmax(strengths))])
    return float(np.median(best)) if best else r0


def ring_refine(frames, centre, status, r0: float, background=None, measured: int = 1, report=None):
    """Every frame whose status is `measured` moved to its ring centre where the ring is clear
    (STRONG) and within REACH radii; the others (and frames filled in between) move by the shift of
    the fits around them, so the track does not jump where a fit is missing. Reads those frames in
    order (`report(i, n)` as it goes). Returns (centres, radius found, share of frames fitted)."""
    centre = np.array(centre, float)
    n = len(centre)
    times = np.nonzero(np.asarray(status) == measured)[0]
    if not len(times):
        return centre, r0, 0.0
    half = int(np.ceil(1.15 * r0 + REACH * r0)) + 4
    bg_mean = float(background.mean()) if background is not None else 1.0
    windows = {}
    for i, t in enumerate(times):
        if report is not None:
            report(i, len(times))
        frame = np.asarray(frames[int(t)])
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        scale = float(gray.mean()) / max(bg_mean, 1e-3) if background is not None else 1.0
        got = edges(gray, background, centre[t], half, scale)
        if got is not None:
            windows[int(t)] = got
    picks = list(windows)[:: max(1, len(windows) // 15)]
    r = fit_radius([(*windows[t], centre[t]) for t in picks], r0)
    shift, fitted = np.full((n, 2), np.nan), 0
    for t, (edge, origin) in windows.items():
        c, strength = _peak(edge, origin, centre[t], r, REACH * r)
        if strength >= STRONG and np.hypot(*(c - centre[t])) <= REACH * r:
            shift[t], fitted = c - centre[t], fitted + 1
    known = np.nonzero(np.isfinite(shift[:, 0]))[0]
    if len(known):
        idx = np.arange(n)
        centre[:, 0] += np.interp(idx, known, shift[known, 0])
        centre[:, 1] += np.interp(idx, known, shift[known, 1])
    return centre, r, fitted / len(times)
