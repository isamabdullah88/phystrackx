"""
physics.py

What the ball's motion allows, applied to a whole track after it is found (cliptrack.py):

- refine: drops sightings that fit neither the motion before them nor the motion after them (a
  jump to something else for a frame or two), fills the frames between sightings with one
  parabola through both sides when the ball flew freely across them (constant acceleration), and
  smooths the jitter of the sightings with a small local fit, except at kinks (a bounce, the
  release).
- quality: label-free checks of a track, for real clips with no known path: how much was seen,
  filled or lost, how much the sightings jitter about a smooth path, the longest gap, outliers.
- fit_damped_oscillation, fit_free_fall: the experiment's own motion, as a check on real clips
  (how well a damped oscillation or a free fall fits the track, and its parameters).

Positions are pixels and times frames. No GUI here. Author: Isam Balghari
"""

from dataclasses import asdict, dataclass, fields

import numpy as np

LOST, MEASURED, FILLED = 0, 1, 2


@dataclass
class PhysicsSettings:
    side: int = 5                 # Sightings on each side used to judge one (and to bridge a gap)
    outlier: float = 0.7          # A sighting this far from both sides' motion is dropped (ball radii),
    outlier_px: float = 2.5       # ...but at least this many pixels
    bridge: float = 0.35          # A gap is one parabola when it fits both sides within this (radii, RMS)
    smooth: int = 2               # Half-width of the smoothing fit (frames; 0: no smoothing)
    kink: float = 0.25            # ...not where that fit misses the sightings by more than this (radii, RMS)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict) -> "PhysicsSettings":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in values.items() if k in names})


def _quadratic(t, p, at):
    """Least-squares quadratic (or lower, with few points) of p over t, evaluated at `at`, and the
    RMS of its residuals."""
    deg = min(2, len(t) - 1)
    if deg < 0:
        return None, np.inf
    c = np.polyfit(t, p, deg)
    fit = np.stack([np.polyval(c[:, k], at) for k in range(p.shape[1])], axis=-1)
    res = p - np.stack([np.polyval(c[:, k], t) for k in range(p.shape[1])], axis=-1)
    return fit, float(np.sqrt((res ** 2).sum(axis=1).mean())) if deg < len(t) - 1 else 0.0


def refine(centre, status, radius: float, settings: PhysicsSettings | None = None):
    """The track with outliers dropped, gaps bridged and jitter smoothed: (centre, status), new
    arrays. Only MEASURED and FILLED frames between the first and last sighting change."""
    s = settings or PhysicsSettings()
    centre, status = np.array(centre, float), np.array(status, int)
    n = len(centre)
    seen = np.nonzero(status == MEASURED)[0]
    if len(seen) < 2 * s.side + 1:
        return centre, status
    limit = max(s.outlier * radius, s.outlier_px)
    # 1. Outliers: a sighting that neither side's motion reaches (one-sided quadratic predictions,
    # from the nearest sightings before and after it; a bounce fits one side)
    drop = []
    for j in range(1, len(seen) - 1):
        i = seen[j]
        before, after = seen[max(0, j - s.side):j], seen[j + 1:j + 1 + s.side]
        miss = []
        for side in (before, after):
            if len(side) >= 3:
                pred, _ = _quadratic(side.astype(float), centre[side], np.array([float(i)]))
                miss.append(float(np.hypot(*(pred[0] - centre[i]))))
        if len(miss) == 2 and min(miss) > limit:
            drop.append(i)
    status[drop] = FILLED
    seen = np.nonzero(status == MEASURED)[0]
    # 2. Gaps: one parabola through both sides when it fits them
    for a, b in zip(seen, seen[1:]):
        if b - a < 2:
            continue
        sides = np.concatenate([seen[(seen <= a)][-s.side:], seen[(seen >= b)][:s.side]])
        inside = np.arange(a + 1, b, dtype=float)
        fit, rms = _quadratic(sides.astype(float), centre[sides], inside)
        if fit is not None and len(sides) >= 4 and rms <= s.bridge * radius:
            centre[a + 1:b] = fit
            status[a + 1:b] = FILLED
    # 3. Smoothing: a local quadratic over the sightings within `smooth` frames, where it fits
    if s.smooth > 0:
        out = centre.copy()
        for i in seen:
            near = seen[np.abs(seen - i) <= s.smooth]
            if len(near) < 2 * s.smooth + 1:
                continue
            fit, rms = _quadratic(near.astype(float), centre[near], np.array([float(i)]))
            if rms <= s.kink * radius:
                out[i] = fit[0]
        centre = out
    return centre, status


@dataclass
class Quality:
    measured: float      # Share of frames with a sighting
    filled: float        # ...filled in between sightings
    lost: float          # ...with no position
    jitter: float        # RMS distance of the sightings from a smooth local path (px)
    longest_gap: int     # Longest run of frames without a sighting
    outliers: int        # Sightings that fit neither side's motion

    def to_dict(self) -> dict:
        return asdict(self)


def quality(centre, status, radius: float, settings: PhysicsSettings | None = None) -> Quality:
    """Label-free checks of a track (see the module's docstring)."""
    s = settings or PhysicsSettings()
    centre, status = np.asarray(centre, float), np.asarray(status, int)
    n = len(centre)
    seen = np.nonzero(status == MEASURED)[0]
    res = []
    for i in seen:
        near = seen[(np.abs(seen - i) <= 3) & (seen != i)]
        if len(near) >= 4:
            pred, _ = _quadratic(near.astype(float), centre[near], np.array([float(i)]))
            res.append(float(np.hypot(*(pred[0] - centre[i]))))
    res = np.array(res)
    limit = max(s.outlier * radius, s.outlier_px)
    gaps = np.diff(seen) - 1 if len(seen) > 1 else np.array([n])
    return Quality(measured=float((status == MEASURED).mean()), filled=float((status == FILLED).mean()),
                   lost=float((status == LOST).mean()),
                   jitter=float(np.sqrt(np.mean(np.minimum(res, limit) ** 2))) if len(res) else float("nan"),
                   longest_gap=int(gaps.max()) if len(gaps) else 0, outliers=int((res > limit).sum()))


def fit_damped_oscillation(t, y):
    """y(t) = c + a exp(-t / tau) cos(2 pi t / period + phase), least squares (scipy). Returns
    {c, a, tau, period, phase, rms} or None when it does not converge."""
    from scipy.optimize import curve_fit
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(y)
    t, y = t[ok], y[ok]
    if len(t) < 8:
        return None

    def model(t, c, a, tau, period, phase):
        return c + a * np.exp(-t / tau) * np.cos(2 * np.pi * t / period + phase)

    centre = float(np.median(y))
    crossings = np.nonzero(np.diff(np.sign(y - centre)))[0]
    period = 2 * float(np.median(np.diff(t[crossings]))) if len(crossings) > 2 else (t[-1] - t[0]) / 2
    best = None
    for phase in np.linspace(0, 2 * np.pi, 4, endpoint=False):
        try:
            p, _ = curve_fit(model, t, y, p0=[centre, float(np.ptp(y)) / 2, (t[-1] - t[0]), period, phase],
                             maxfev=4000)
        except (RuntimeError, ValueError):
            continue
        rms = float(np.sqrt(np.mean((model(t, *p) - y) ** 2)))
        if best is None or rms < best["rms"]:
            best = dict(zip(("c", "a", "tau", "period", "phase"), map(float, p)), rms=rms)
    return best


def fit_free_fall(t, y):
    """y(t) = y0 + v0 t + g t^2 / 2 (y down): {y0, v0, g, rms} (g in px per frame^2)."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(y)
    if ok.sum() < 4:
        return None
    c = np.polyfit(t[ok], y[ok], 2)
    rms = float(np.sqrt(np.mean((np.polyval(c, t[ok]) - y[ok]) ** 2)))
    return {"y0": float(c[2]), "v0": float(c[1]), "g": float(2 * c[0]), "rms": rms}
