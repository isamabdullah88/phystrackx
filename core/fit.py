"""
fit.py

Fits of a time series with a damped oscillation, and period measurements. No GUI here, so the
maths can be tested on its own.

Models, with tt = t - t[0] (time from the start of the chosen range):

    "damped":        y = C + A * exp(-gamma * tt) * cos(omega * tt + phi)
    "damped_linear": y = C + m * tt + A * exp(-gamma * tt) * cos(omega * tt + phi)
    "damped_exp":    y = C + D * exp(-tt / ts) + A * exp(-gamma * tt) * cos(omega * tt + phi)
    "drag":          z'' = -omega^2 z - k |z'| z'   (quadratic drag), y = C + z
    "drag_linear":   y = C + m * tt + z, with z solving the same equation
    "both_exp":      z'' = -omega^2 z - 2 beta z' - k |z'| z'   (linear and quadratic damping),
                     y = C + D * exp(-tt / ts) + z
    "gas":           z'' = (omega^2 L / G) [(L / (L + z))^G - 1] - 2 beta z' - k |z'| z',
                     y = C + m * tt + z   (the air below compressed adiabatically, G = 1.4)
    "friction":      z'' = -omega^2 z - 2 beta z' - f sgn(z')   (sliding friction),
                     y = C + m * tt + z

The linear term lets the oscillation settle onto a sloped line rather than a flat one; the
exponential term onto a level that sinks quickly at first, then levels off (D, settling time ts).
The equation-of-motion models start from z(0) = z0 with speed z'(0) = v0, so the damping strengths
are fitted directly. Their period depends a little on the amplitude, so the fitted omega is the
small-swing value. The gas spring's L is the air column's length at rest, in the data's unit.

Period: T = 2*pi/omega from the fit, and the spacing of successive peaks and troughs in the data.

Author: Isam Balghari
"""

from dataclasses import dataclass, field
import math

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

MIN_POINTS = 8
GOOD_FIT_R2 = 0.9  # Above this the fit period is preferred over the peak spacing


def damped(tt, A, gamma, omega, phi, C):
    """Damped oscillation about a constant C. tt is time measured from the start of the range."""
    return C + A * np.exp(-gamma * tt) * np.cos(omega * tt + phi)


def damped_linear(tt, A, gamma, omega, phi, C, m):
    """Damped oscillation about a straight line C + m*tt."""
    return damped(tt, A, gamma, omega, phi, C) + m * tt


def _drag_path(tt, z0: float, v0: float, omega: float, k: float) -> np.ndarray:
    """
    Position of z'' = -omega^2 z - k |z'| z' at the times tt (starting at tt[0] = 0), from
    z(0) = z0 and z'(0) = v0. Each step is one Runge-Kutta (RK4) step over the sample interval.
    Written out in plain floats (no calls per step): a fit integrates it thousands of times.
    """
    w2, k = float(omega) * float(omega), float(k)
    z, v = float(z0), float(v0)
    out = [z]
    with np.errstate(all="ignore"):
        for h in np.diff(np.asarray(tt, dtype=float)).tolist():
            a1 = -w2 * z - k * abs(v) * v
            v2 = v + 0.5 * h * a1
            a2 = -w2 * (z + 0.5 * h * v) - k * abs(v2) * v2
            v3 = v + 0.5 * h * a2
            a3 = -w2 * (z + 0.5 * h * v2) - k * abs(v3) * v3
            v4 = v + h * a3
            a4 = -w2 * (z + h * v3) - k * abs(v4) * v4
            z += h / 6 * (v + 2 * v2 + 2 * v3 + v4)
            v += h / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
            if not abs(z) < 1e12:   # Blown up (a wild trial): far off, so the fit steps back
                out += [1e12] * (len(tt) - len(out))
                break
            out.append(z)
    return np.array(out)


def drag(tt, z0, v0, omega, k, C):
    """Quadratic-drag oscillation about a constant C."""
    return C + _drag_path(tt, z0, v0, omega, k)


def drag_linear(tt, z0, v0, omega, k, C, m):
    """Quadratic-drag oscillation about a straight line C + m*tt."""
    return drag(tt, z0, v0, omega, k, C) + m * tt


def damped_exp(tt, A, gamma, omega, phi, C, D, ts):
    """Damped oscillation about a level that settles exponentially: C + D exp(-tt / ts)."""
    return damped(tt, A, gamma, omega, phi, C) + D * np.exp(-tt / ts)


GAS_GAMMA = 1.4   # Heat capacity ratio of air, for the gas-spring model's shape


def _motion_path(tt, z0: float, v0: float, omega: float, beta: float = 0.0, k: float = 0.0,
                 f: float = 0.0, L: float = 0.0) -> np.ndarray:
    """
    Position of z'' = spring(z) - 2 beta z' - k |z'| z' - f sgn(z') at the times tt, from z(0) = z0
    and z'(0) = v0, by one RK4 step per sample interval (as _drag_path). The spring is -omega^2 z,
    or with L > 0 the adiabatic gas spring (omega^2 L / G) [(L / (L + z))^G - 1], which is
    -omega^2 z for small z.
    """
    w2, beta, k, f, L = float(omega) ** 2, float(beta), float(k), float(f), float(L)
    gas = L > 0
    c = w2 * L / GAS_GAMMA if gas else 0.0
    floor = 1e-3 * L   # The column never shrinks below this (a wild trial would divide by zero)

    def acc(z, v):
        if gas:
            spring = c * ((L / max(L + z, floor)) ** GAS_GAMMA - 1.0)
        else:
            spring = -w2 * z
        a = spring - 2.0 * beta * v - k * abs(v) * v
        if f and v:
            a -= f if v > 0 else -f
        return a

    z, v = float(z0), float(v0)
    out = [z]
    with np.errstate(all="ignore"):
        for h in np.diff(np.asarray(tt, dtype=float)).tolist():
            a1 = acc(z, v)
            v2 = v + 0.5 * h * a1
            a2 = acc(z + 0.5 * h * v, v2)
            v3 = v + 0.5 * h * a2
            a3 = acc(z + 0.5 * h * v2, v3)
            v4 = v + h * a3
            a4 = acc(z + h * v3, v4)
            z += h / 6 * (v + 2 * v2 + 2 * v3 + v4)
            v += h / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
            if not abs(z) < 1e12:
                out += [1e12] * (len(tt) - len(out))
                break
            out.append(z)
    return np.array(out)


def both_exp(tt, z0, v0, omega, beta, k, C, D, ts):
    """Linear and quadratic damping, about a level that settles exponentially."""
    return C + D * np.exp(-tt / ts) + _motion_path(tt, z0, v0, omega, beta=beta, k=k)


def gas(tt, z0, v0, omega, beta, k, L, C, m):
    """Adiabatic gas spring with linear and quadratic damping, about a straight line."""
    return C + m * tt + _motion_path(tt, z0, v0, omega, beta=beta, k=k, L=L)


def friction(tt, z0, v0, omega, beta, f, C, m):
    """Linear damping and sliding (dry) friction, about a straight line."""
    return C + m * tt + _motion_path(tt, z0, v0, omega, beta=beta, f=f)


@dataclass(frozen=True)
class FitModel:
    key: str
    label: str
    names: tuple
    func: object
    equation: tuple = ()   # Lines of matplotlib mathtext, shown under the model's name


_DAMPED = r"A\,e^{-\gamma t}\cos(\omega t + \phi)"
_SETTLE = r"D\,e^{-t/t_s}"
_DRAG = r"$\ddot z = -\omega^2 z - k\,|\dot z|\,\dot z$"
_BOTH = r"$\ddot z = -\omega^2 z - 2\beta\dot z - k\,|\dot z|\,\dot z$"
_GAS = (r"$\ddot z = \frac{\omega^2 L}{\Gamma}\left[\left(\frac{L}{L + z}\right)^{\Gamma} - 1\right]"
        r" - 2\beta\dot z - k\,|\dot z|\,\dot z$")
_FRICTION = r"$\ddot z = -\omega^2 z - 2\beta\dot z - f\,\mathrm{sgn}(\dot z)$"
MODELS = {
    "damped": FitModel("damped", "Damped oscillator",
                       ("A", "gamma", "omega", "phi", "C"), damped,
                       (rf"$y = C + {_DAMPED}$",)),
    "damped_linear": FitModel("damped_linear", "Damped + linear drift",
                              ("A", "gamma", "omega", "phi", "C", "m"), damped_linear,
                              (rf"$y = C + m t + {_DAMPED}$",)),
    "damped_exp": FitModel("damped_exp", "Damped + exponential settling",
                           ("A", "gamma", "omega", "phi", "C", "D", "ts"), damped_exp,
                           (rf"$y = C + {_SETTLE} + {_DAMPED}$",)),
    "drag": FitModel("drag", "Quadratic drag",
                     ("z0", "v0", "omega", "k", "C"), drag,
                     (_DRAG + r",  $y = C + z$",)),
    "drag_linear": FitModel("drag_linear", "Quadratic drag + linear drift",
                            ("z0", "v0", "omega", "k", "C", "m"), drag_linear,
                            (_DRAG + r",  $y = C + m t + z$",)),
    "both_exp": FitModel("both_exp", "Linear + quadratic damping + exp. settling",
                         ("z0", "v0", "omega", "beta", "k", "C", "D", "ts"), both_exp,
                         (_BOTH, rf"$y = C + {_SETTLE} + z$")),
    "gas": FitModel("gas", "Gas spring + both dampings + drift",
                    ("z0", "v0", "omega", "beta", "k", "L", "C", "m"), gas,
                    (_GAS, r"$y = C + m t + z$,  $\Gamma = 1.4$")),
    "friction": FitModel("friction", "Sliding friction + drift",
                         ("z0", "v0", "omega", "beta", "f", "C", "m"), friction,
                         (_FRICTION + r",  $y = C + m t + z$",)),
}
EQUATION_NOTE = r"$t$: time from the range's start; $z(0) = z_0$, $\dot z(0) = v_0$"
DEFAULT_MODEL = "damped_linear"

# Parameters that cannot be negative (a rate, a frequency, a strength, a time or a length)
_NON_NEGATIVE = {"gamma", "omega", "beta", "k", "f", "ts", "L"}


@dataclass
class FitResult:
    ok: bool
    message: str = ""
    model: str = DEFAULT_MODEL
    params: dict = field(default_factory=dict)   # Named as in the model
    errors: dict = field(default_factory=dict)   # One standard error per parameter
    r2: float = float("nan")
    period: float = float("nan")                 # 2*pi/omega
    period_err: float = float("nan")
    tau: float = float("nan")                    # Decay time 1/gamma
    t0: float = 0.0                              # Start of the range, the origin of tt
    phi_abs: float = 0.0                         # Phase with absolute time (for warm starts)


@dataclass
class PeakPeriods:
    n_maxima: int
    n_minima: int
    period: float        # Mean spacing of peaks and troughs of the same kind, averaged
    period_err: float    # Standard error of that mean
    n_intervals: int


class FitStopped(Exception):
    """The fit was abandoned (its `stop` said so): the plot was closed, or the range moved on."""


def _stoppable(func, stop):
    """func, raising FitStopped when stop() turns true (checked on every evaluation)."""
    if stop is None:
        return func

    def checked(tt, *p):
        if stop():
            raise FitStopped()
        return func(tt, *p)
    return checked


def fit_model(t, y, model: str = DEFAULT_MODEL, warm: "FitResult | None" = None,
              stop=None) -> FitResult:
    """
    Fits the chosen model to (t, y). Non-finite values are dropped.

    The frequency starts from the largest peak of the spectrum, and the phase is tried at
    several starting values, so the fit does not stop at a wrong local minimum.

    warm: a previous fit with the same model (for example of a slightly different range). Its
    parameters are tried first, which is much faster when the slider only moves a little.
    stop: a function checked on every trial; when it returns True the fit raises FitStopped (so a
    fit on another thread can be abandoned).
    """
    spec = MODELS[model]
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(t) & np.isfinite(y)
    t, y = t[keep], y[keep]
    order = np.argsort(t)
    t, y = t[order], y[order]
    if len(t) < MIN_POINTS:
        return FitResult(ok=False, model=model, message=f"Select at least {MIN_POINTS} points")

    t0 = float(t[0])
    tt = t - t0
    dt = float(np.median(np.diff(tt)))
    duration = float(tt[-1])
    if dt <= 0 or duration <= 0:
        return FitResult(ok=False, model=model, message="The times in the range do not increase")

    C0 = float(np.mean(y))
    A0 = float((y.max() - y.min()) / 2) or 1e-6
    linear = "m" in spec.names
    m0 = float(np.polyfit(tt, y, 1)[0]) if linear else None

    # Starting frequency: the strongest peak of the spectrum (zero-padded for finer steps)
    # A straight line is taken off first, and frequencies with less than one cycle in the range are
    # left out, so a slow fall (a big first drop) is not taken for the swing
    z = (y - np.polyval(np.polyfit(tt, y, 1), tt)) * np.hanning(len(y))
    n_fft = 16 * len(z)
    spectrum = np.abs(np.fft.rfft(z, n_fft))
    freqs = np.fft.rfftfreq(n_fft, dt)
    spectrum[freqs < 1.0 / duration] = 0.0
    w0 = 2 * math.pi * float(freqs[int(np.argmax(spectrum))])
    if w0 <= 0:
        return FitResult(ok=False, model=model, message="No oscillation found in the range", t0=t0)
    g0 = 1.0 / max(duration, dt)

    if "z0" in spec.names:
        return _fit_motion(tt, y, spec, t0, w0, A0, C0, m0, warm, stop)

    lower, upper = _bounds(spec, dt, duration, A0)
    settle = "D" in spec.names
    func = _stoppable(spec.func, stop)

    def attempt(p0, maxfev):
        try:
            popt, pcov = curve_fit(func, tt, y, p0=np.clip(p0, lower, upper),
                                   bounds=(lower, upper), maxfev=maxfev)
        except (RuntimeError, ValueError):
            return None
        return float(np.sum((spec.func(tt, *popt) - y) ** 2)), popt, pcov

    sst = float(np.sum((y - y.mean()) ** 2))
    best = None
    if warm is not None and warm.ok and warm.model == model:
        # The warm phase is measured from the old range start: move it to this one
        p_w = [warm.params[k] for k in spec.names]
        p_w[3] = warm.phi_abs + p_w[2] * t0
        best = attempt(p_w, maxfev=400)
        if best is not None and sst > 0 and 1.0 - best[0] / sst >= GOOD_FIT_R2:
            return _result(best, spec, t0, sst, y)  # Good enough: skip the search

    # A close start, found by linear least squares: for a few frequencies and decay rates the model
    # is linear in C (and m) and the cosine and sine amplitudes. Usually one fit from there is enough
    seed = _linear_seed(tt, y, w0, g0, linear, settle)
    if seed is not None:
        result = attempt(seed, maxfev=2000)
        if result is not None and (best is None or result[0] < best[0]):
            best = result
        if best is not None and sst > 0 and 1.0 - best[0] / sst >= GOOD_FIT_R2:
            return _result(best, spec, t0, sst, y)

    base = [A0, g0, w0, 0.0, C0] + ([m0] if linear else []) + \
        ([0.5 * (float(y[0]) - C0), duration / 5] if settle else [])
    for phi0 in np.linspace(-math.pi, math.pi, 12, endpoint=False):
        p0 = list(base)
        p0[3] = phi0
        result = attempt(p0, maxfev=20000)
        if result is not None and (best is None or result[0] < best[0]):
            best = result

    if best is None:
        return FitResult(ok=False, model=model,
                         message="The fit did not converge; try a different range", t0=t0)
    return _result(best, spec, t0, sst, y)


def _bounds(spec: FitModel, dt: float, duration: float, A0: float):
    """Lower and upper bounds of the model's parameters: rates, strengths, times and lengths are
    non-negative; the settling time stays between half a sample and a few ranges (a longer one is
    a straight line, which C and m already cover); the gas column is longer than half the swing."""
    lower, upper = [], []
    for name in spec.names:
        lo = 0.0 if name in _NON_NEGATIVE else -np.inf
        hi = np.inf
        if name == "ts":
            lo, hi = dt / 2, 5 * duration
        elif name == "L":
            lo = A0
        lower.append(lo)
        upper.append(hi)
    return lower, upper


def _linear_seed(tt, y, w0: float, g0: float, linear: bool, settle: bool = False) -> list | None:
    """Starting parameters (A, gamma, omega, phi, C[, m][, D, ts]) for the damped models: over a
    small grid of omega (about the spectrum's peak), gamma (and the settling time ts), the best
    linear least-squares fit of C (+ m tt) (+ D e^(-tt/ts)) + e^(-gamma tt) (a cos(omega tt) +
    b sin(omega tt))."""
    duration = float(tt[-1])
    best = None
    for w in w0 * np.linspace(0.85, 1.15, 7):
        for g in g0 * np.array([0.5, 1, 2, 4, 8, 16]):
            for ts in (duration * np.array([0.05, 0.1, 0.2, 0.4]) if settle else [None]):
                decay = np.exp(-g * tt)
                columns = [np.ones_like(tt), decay * np.cos(w * tt), decay * np.sin(w * tt)]
                if linear:
                    columns.append(tt)
                if settle:
                    columns.append(np.exp(-tt / ts))
                basis = np.column_stack(columns)
                coef, *_ = np.linalg.lstsq(basis, y, rcond=None)
                sse = float(np.sum((basis @ coef - y) ** 2))
                if best is None or sse < best[0]:
                    best = (sse, w, g, ts, coef)
    if best is None or not np.all(np.isfinite(best[4])):
        return None
    _, w, g, ts, coef = best
    a, b = coef[1], coef[2]   # a cos + b sin = A cos(w tt + phi), with a = A cos phi, b = -A sin phi
    return [float(math.hypot(a, b)), float(g), float(w), float(math.atan2(-b, a)), float(coef[0])] + \
        ([float(coef[3])] if linear else []) + ([float(coef[-1]), float(ts)] if settle else [])


def _motion_starts(spec: FitModel, tt, y, stop) -> list:
    """
    Starts for an equation-of-motion model, from the damped fit of the same data (with the same
    drift or settling): the same first position and speed and the natural frequency, with the
    fitted decay shared out among the model's damping terms in a few ways. A decay rate gamma
    matches, at the amplitude a:
      linear damping:    beta = gamma
      quadratic drag:    k = 3 pi gamma / (4 omega a)    (dA/dt = -(4 / 3 pi) k omega A^2)
      sliding friction:  f = pi omega gamma a / 2        (dA/dt = -2 f / (pi omega))
    """
    names = spec.names
    base_model = "damped_exp" if "D" in names else "damped_linear" if "m" in names else "damped"
    damped_fit = fit_model(tt, y, base_model, stop=stop)
    if not damped_fit.ok:
        return []
    p = damped_fit.params
    A, g, w, phi = p["A"], p["gamma"], p["omega"], p["phi"]
    wn = math.sqrt(w * w + g * g)
    amp = max(A, 1e-9)
    common = dict(z0=A * math.cos(phi), v0=-A * (g * math.cos(phi) + w * math.sin(phi)), omega=wn,
                  C=p["C"], m=p.get("m", 0.0), D=p.get("D", 0.0), ts=p.get("ts", 1.0))

    def k_for(a):
        return 3 * math.pi * g / (4 * wn * max(a, 1e-9))

    if "f" in names:
        shares = [dict(beta=g, f=0.0), dict(beta=g / 2, f=math.pi * wn * g * amp / 8),
                  dict(beta=0.0, f=math.pi * wn * g * amp / 4)]
    elif "beta" in names:
        shares = [dict(beta=g, k=0.0), dict(beta=g / 2, k=k_for(amp) / 2), dict(beta=0.0, k=k_for(amp))]
    else:
        shares = [dict(k=k_for(amp)), dict(k=k_for(amp / 2))]
    if "L" in names:   # A long column (nearly a plain spring) and a short one (a lopsided swing)
        shares = [dict(s, L=Lc) for s in shares[1:2] for Lc in (30 * amp, 3 * amp)] + \
            [dict(shares[0], L=30 * amp)]
    return [[{**common, **s}[name] for name in names] for s in shares]


def _fit_motion(tt, y, spec: FitModel, t0: float, w0: float, A0: float, C0: float,
                m0: float | None, warm: "FitResult | None", stop=None) -> FitResult:
    """
    Fit of an equation-of-motion model (quadratic drag, both dampings, gas spring, sliding
    friction). Each trial integrates the motion, so the search starts close: from the damped fit of
    the same data (_motion_starts). A warm start (the previous fit of this model) is tried first,
    so a slider move is quick. Rough starts from the data are tried only if those fail. Every
    attempt is capped, so the fit takes about a second on a long range, never minutes.
    """
    linear = "m" in spec.names
    sst = float(np.sum((y - y.mean()) ** 2))
    duration = float(tt[-1])
    lower, upper = _bounds(spec, float(np.median(np.diff(tt))), duration, A0)
    func = _stoppable(spec.func, stop)

    def attempt(p0, maxfev):
        try:
            popt, pcov = curve_fit(func, tt, y, p0=np.clip(p0, lower, upper),
                                   bounds=(lower, upper), maxfev=maxfev, x_scale="jac")
        except (RuntimeError, ValueError):
            return None
        return float(np.sum((spec.func(tt, *popt) - y) ** 2)), popt, pcov

    def good(result):
        return result is not None and sst > 0 and 1.0 - result[0] / sst >= GOOD_FIT_R2

    best = None
    if warm is not None and warm.ok and warm.model == spec.key:
        best = attempt([warm.params[k] for k in spec.names], maxfev=60)
        if good(best):
            return _result_drag(best, spec, t0, sst)

    for result in (attempt(p0, maxfev=150) for p0 in _motion_starts(spec, tt, y, stop)):
        if result is not None and (best is None or result[0] < best[0]):
            best = result

    if not good(best):   # The damped start did not lead to a good fit: the rough starts too
        for z0 in (A0, -A0):
            for v0 in (w0 * A0, -w0 * A0):
                rough = dict(z0=z0, v0=v0, omega=w0, beta=0.0, k=0.01 * w0 * w0 / max(A0, 1e-9),
                             f=0.0, L=30 * A0, C=C0, m=m0 or 0.0, D=0.0, ts=duration / 5)
                result = attempt([rough[name] for name in spec.names], maxfev=100)
                if result is not None and (best is None or result[0] < best[0]):
                    best = result

    if best is None:
        return FitResult(ok=False, model=spec.key,
                         message="The fit did not converge; try a different range", t0=t0)
    return _result_drag(best, spec, t0, sst)


def _result_drag(best, spec: FitModel, t0: float, sst: float) -> FitResult:
    """Turns a (sse, popt, pcov) drag fit into a FitResult."""
    sse, popt, pcov = best
    popt = np.array(popt, dtype=float)
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    params = dict(zip(spec.names, (float(v) for v in popt)))
    errors = dict(zip(spec.names, (float(np.sqrt(v)) if v >= 0 else float("nan")
                                   for v in np.diag(pcov))))
    omega = params["omega"]
    period = 2 * math.pi / omega if omega > 0 else float("nan")
    period_err = 2 * math.pi / omega ** 2 * errors["omega"] if omega > 0 else float("nan")
    message = "" if r2 >= GOOD_FIT_R2 else "Poor fit: check the range"
    return FitResult(ok=True, message=message, model=spec.key, params=params, errors=errors,
                     r2=r2, period=period, period_err=period_err, tau=float("nan"), t0=t0,
                     phi_abs=0.0)


# Each parameter's unit ("{u}" is the data's unit), and how many significant figures it gets
_PARAM_UNITS = {"A": "{u}", "z0": "{u}", "C": "{u}", "D": "{u}", "L": "{u}", "v0": "{u}/s",
                "m": "{u}/s", "omega": "rad/s", "gamma": "/s", "beta": "/s", "k": "/{u}",
                "f": "{u}/s²", "phi": "rad", "ts": "s"}
_PRECISE = {"omega", "C", "m"}


def param_lines(fit: FitResult, unit: str = "") -> list:
    """The fit's parameters, one line each with its error and unit (for the results panels).
    gamma also gets its decay time tau = 1/gamma."""
    lines = []
    for name in MODELS[fit.model].names:
        value, err = fit.params[name], fit.errors[name]
        u = _PARAM_UNITS[name].format(u=unit if name != "k" else unit or "unit")
        digits = 4 if name in _PRECISE else 3
        line = f"{name:<5} = {value:.{digits}g} ± {err:.2g}" + (f" {u}" if u else "")
        if name == "gamma":
            line += f"   tau = {fit.tau:.3g} s"
        lines.append(line)
    return lines


def fit_damped(t, y, warm: "FitResult | None" = None) -> FitResult:
    """The plain damped oscillator (kept for existing callers)."""
    return fit_model(t, y, "damped", warm)


def _result(best, spec: FitModel, t0: float, sst: float, y) -> FitResult:
    """Turns a (sse, popt, pcov) fit into a FitResult."""
    sse, popt, pcov = best
    popt = np.array(popt, dtype=float)
    # A negative amplitude is the same curve with the phase shifted by pi: report A > 0
    if popt[0] < 0:
        popt[0], popt[3] = -popt[0], popt[3] + math.pi
    popt[3] = (popt[3] + math.pi) % (2 * math.pi) - math.pi  # Phase in (-pi, pi]
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    params = dict(zip(spec.names, (float(v) for v in popt)))
    errors = dict(zip(spec.names, (float(np.sqrt(v)) if v >= 0 else float("nan")
                                   for v in np.diag(pcov))))

    omega = params["omega"]
    period = 2 * math.pi / omega if omega > 0 else float("nan")
    period_err = 2 * math.pi / omega ** 2 * errors["omega"] if omega > 0 else float("nan")
    gamma = params["gamma"]
    tau = 1.0 / gamma if gamma > 0 else float("inf")
    phi_abs = params["phi"] - omega * t0  # Phase with absolute time, to reuse as a warm start

    message = "" if r2 >= GOOD_FIT_R2 else "Poor fit: check the range"
    return FitResult(ok=True, message=message, model=spec.key, params=params, errors=errors,
                     r2=r2, period=period, period_err=period_err, tau=tau, t0=t0,
                     phi_abs=phi_abs)


def peak_periods(t, y) -> PeakPeriods:
    """
    Periods from the data itself: the spacing between successive maxima and between successive
    minima, each counted as a full period. Peaks must stand out by a fifth of the signal's range,
    which ignores noise.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(t) & np.isfinite(y)
    t, y = t[keep], y[keep]
    order = np.argsort(t)
    t, y = t[order], y[order]
    empty = PeakPeriods(0, 0, float("nan"), float("nan"), 0)
    if len(t) < 3:
        return empty

    prominence = 0.2 * float(np.ptp(y)) if np.ptp(y) > 0 else None
    maxima, _ = find_peaks(y, prominence=prominence)
    minima, _ = find_peaks(-y, prominence=prominence)

    intervals = np.concatenate([np.diff(t[maxima]), np.diff(t[minima])])
    if intervals.size == 0:
        return PeakPeriods(len(maxima), len(minima), float("nan"), float("nan"), 0)
    mean = float(np.mean(intervals))
    err = float(np.std(intervals, ddof=1) / math.sqrt(intervals.size)) if intervals.size > 1 \
        else float("nan")
    return PeakPeriods(len(maxima), len(minima), mean, err, int(intervals.size))


@dataclass
class InitialDrop:
    ok: bool
    message: str = ""
    t_high: float = float("nan")  # Start of the movement: the first high in the range
    y_high: float = float("nan")
    t_low: float = float("nan")   # The first low after it: the first turnaround
    y_low: float = float("nan")

    @property
    def drop(self) -> float:
        """How far the value falls from the start to the first low (positive when it falls)."""
        return self.y_high - self.y_low

    @property
    def duration(self) -> float:
        """Time from the start to the first low."""
        return self.t_low - self.t_high


def initial_drop(t, y) -> InitialDrop:
    """
    The initial drop of a motion: from where the movement starts (the highest point before the
    first low) to the first low (the first turnaround of the period).

    The first low is the first trough that a fall of a fifth of the signal's range leads to. A
    trough only has to stand out by a twentieth of the range to count: in a heavily damped motion
    (a ball in a tube over water) the swing back after the drop is less than a fifth of the drop
    (water 270, trial 1: a 51 cm drop, a 10 cm swing back), and a fifth, as for peak_periods,
    found no low at all. Small dips on the way down (tracking jitter, the hand moving the ball
    before it is let go) have no such fall before them, so they are passed over. The start is the
    highest point before the low, so an object resting at the top before it is let go is measured
    from its resting place (find_peaks would miss that high: it never counts the first sample,
    and a rest has no clear peak).
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(t) & np.isfinite(y)
    t, y = t[keep], y[keep]
    order = np.argsort(t)
    t, y = t[order], y[order]
    if len(t) < 3 or np.ptp(y) <= 0:
        return InitialDrop(ok=False, message="Select a range with a clear movement")
    span = float(np.ptp(y))
    minima, _ = find_peaks(-y, prominence=0.05 * span)
    if minima.size == 0:
        return InitialDrop(ok=False, message="No clear low in the range")
    for low in minima:
        low = int(low)
        start = int(np.argmax(y[:low + 1]))
        if y[start] - y[low] >= 0.2 * span:
            return InitialDrop(ok=True, t_high=float(t[start]), y_high=float(y[start]),
                               t_low=float(t[low]), y_low=float(y[low]))
    return InitialDrop(ok=False, message="No starting high before the first low")


def best_period(fit: FitResult, peaks: PeakPeriods):
    """
    The period to report: the fit's when the fit is good, otherwise the peak spacing.

    Returns:
        (period, error, source), with source "fit" or "peaks", or (nan, nan, None) if neither
        could be measured.
    """
    if fit.ok and fit.r2 >= GOOD_FIT_R2 and math.isfinite(fit.period):
        return fit.period, fit.period_err, "fit"
    if math.isfinite(peaks.period):
        return peaks.period, peaks.period_err, "peaks"
    return float("nan"), float("nan"), None
