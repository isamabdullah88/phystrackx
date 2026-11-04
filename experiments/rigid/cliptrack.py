"""
cliptrack.py

Tracks one object through a whole clip, with any of the engines, behind one call:

    result = track_frames(frames, rect, engine="blob", settings={...})

`frames` is any sequence of grey or BGR images (a list, an array, a memory-mapped file), `rect` the
object's box on frame 0. The result has a centre for every frame, and a status that says where
it came from: measured, filled in (the object was hidden and its position comes from the frames
around), or lost.

Engines:
- "blob": the blob tracker (blobtracker.py), frame by frame, as it runs live. Given the clip, it
  also gets the clip's still background (background.py) when its settings use one.

No GUI here. Author: Isam Balghari
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import cv2
import numpy as np

from core import PixelRect

LOST, MEASURED, FILLED = 0, 1, 2
_run = threading.local()   # The running track_frames' progress callback, per thread (see track_frames)
RING_FROM = 0.9            # Share of the progress before the ring-centre pass (when there is one)


def _stage(lo: float, hi: float, name: str) -> None:
    """The next part of the run: it fills the progress from `lo` to `hi`."""
    _run.stage = (lo, hi if not getattr(_run, "ring", False) or hi < RING_FROM else RING_FROM, name)


def _tick(done: int, total: int) -> None:
    """Progress within the current stage (frame `done` of its `total`)."""
    report = getattr(_run, "progress", None)
    if report is not None:
        lo, hi, name = getattr(_run, "stage", (0.0, 1.0, "Tracking"))
        report(lo + (hi - lo) * done / max(1, total), done, name)


@dataclass
class ClipTrack:
    centre: np.ndarray       # (n, 2) sub-pixel centre per frame (the last known one where lost)
    status: np.ndarray       # (n,) LOST, MEASURED or FILLED
    score: np.ndarray        # (n,) how sure the engine is (0..1; 0 where lost)
    ms_per_frame: float      # The engine's CPU time per frame, everything included
    stopped_at: int | None = None  # The frame a time budget stopped it at (the rest counts as lost)
    background: np.ndarray | None = None  # The still background the engine used, if any

    @property
    def lost(self) -> np.ndarray:
        return self.status == LOST


def track_frames(frames, rect: PixelRect, engine: str = "blob", settings: dict | None = None,
                 budget: float | None = None, outline=None, progress=None, partial=None) -> ClipTrack:
    """Tracks the object selected by `rect` on frame 0 through `frames`. With a `budget` (ms per
    frame), a run that is slower than that on average after 10 frames stops there. With the
    setting "physics" true, the track is refined by the ball's motion (physics.refine) at the end.
    `outline` is the object's outline on frame 0 when the selection gives one (a polygon of (x, y)
    points or a boolean mask): its centroid is the centre and its area the size, and `rect` may
    then be None. `progress`, if given, is called as progress(fraction, frame, stage) as it goes:
    the share of the whole run done (0..1, over all its passes), the frame it is on, and what it
    is doing (an exception it raises stops the run there). `partial`, if given, is called as
    partial(centre, status) with the best path so far while the whole-clip engine reads (a few
    times a second). With the setting "ring_centre" true, each position is moved to the centre of
    the ball's round outline at the end (ringfit.py: a shiny ball's highlights, smeared by motion
    blur, pull a blob centre aside)."""
    _run.progress, _run.partial = progress, partial
    values = settings or {}
    ring = bool(values.get("ring_centre"))
    _run.ring = ring
    if outline is not None:
        from experiments.rigid.blobtracker import outline_circle
        (cx, cy), rad = outline_circle(outline)
        k = int(round(rad))
        rect = PixelRect(int(round(cx)) - k, int(round(cy)) - k, 2 * k, 2 * k)
    sel = (rect, outline)     # The selection, as the engines take it
    if engine == "blob":
        out = _track_blob(frames, sel, values, budget)
    elif engine == "offline":
        out = _track_offline(frames, sel, values, budget)
    else:
        raise ValueError(f"unknown tracking engine: {engine}")
    if ring and out.stopped_at is None:
        from experiments.rigid.ringfit import ring_refine
        start = time.process_time()
        _stage(RING_FROM, 1.0, "Finding the centres")
        out.centre, _, _ = ring_refine(frames, out.centre, out.status, _radius(sel), out.background,
                                       MEASURED, _tick)
        out.ms_per_frame += 1000 * (time.process_time() - start) / max(1, len(frames) - 1)
    if values.get("physics"):
        from experiments.rigid.physics import PhysicsSettings, refine
        start = time.process_time()
        out.centre, out.status = refine(out.centre, out.status, _radius(sel),
                                        PhysicsSettings.from_dict(values))
        out.ms_per_frame += 1000 * (time.process_time() - start) / max(1, len(frames) - 1)
    return out


def _track_blob(frames, sel, values, budget) -> ClipTrack:
    """The blob tracker frame by frame. With a background, a first track that shows the ball
    resting in one place long enough to be in the background (a ghost there would hide it) is
    followed by a second, on the background taken again without the ball."""
    from experiments.rigid.blobtracker import BlobSettings
    s = BlobSettings.from_dict(values)
    start = time.process_time()  # This process's CPU time: not inflated by other work on the machine
    if s.background_mix <= 0:
        _stage(0.0, 1.0, "Tracking")
        return _blob_pass(frames, sel, s, None, budget, start)
    first, background, again = _background_passes(frames, sel, s, budget, start)
    if not again:
        first.background = background
        return first
    _stage(0.5, 1.0, "Tracking, second pass")
    out = _blob_pass(frames, sel, s, background, budget, start)
    out.background = background
    return out


def _background_passes(frames, sel, s, budget, start):
    """The clip's background, and a first blob-tracker pass on it: (first pass, background, whether
    the background was taken again without the ball's resting place)."""
    from experiments.rigid.background import estimate_background, rested, sample_frames
    _stage(0.0, 0.05, "Taking the still background")
    _tick(0, 1)
    background = estimate_background(frames)
    _stage(0.05, 0.5, "Tracking")
    first = _blob_pass(frames, sel, s, background, budget, start)
    if background is None or first.stopped_at is not None:
        return first, background, False
    r = _radius(sel)
    picks = sample_frames(len(frames))
    points = np.where(first.lost[picks][:, None], np.nan, first.centre[picks])
    if not rested(points, r, s.ghost_share):
        return first, background, False
    exclude = {int(i): (*first.centre[i], 2 * r) for i in picks if not first.lost[i]}
    return first, estimate_background(frames, exclude=exclude, base=background), True


def _blob_pass(frames, sel, s, background, budget, start) -> ClipTrack:
    from experiments.rigid.blobtracker import BlobTracker
    n = len(frames)
    centre, status, score = np.zeros((n, 2)), np.zeros(n, int), np.zeros(n)
    tracker = BlobTracker(s)
    tracker.background = background
    tracker.initialize_tracker(np.asarray(frames[0]), *sel)
    centre[0], status[0], score[0] = tracker.centre, MEASURED, 1.0
    stopped = None
    for t in range(1, n):
        _tick(t, n)
        ok, _ = tracker.update_tracker(np.asarray(frames[t]))
        if ok:
            centre[t], status[t], score[t] = tracker.centre, MEASURED, tracker.score()
        else:
            centre[t] = centre[t - 1]
        if budget and t >= 10 and 1000 * (time.process_time() - start) / t > budget:
            stopped = t
            centre[t + 1:] = centre[t]
            break
    ms = 1000 * (time.process_time() - start) / (stopped or n - 1)
    return ClipTrack(centre, status, score, ms, stopped)


# -------------------------------------------------------------------------------------------------
# Offline: candidates in every frame, then the best path through all of them
@dataclass
class LinkSettings:
    # Candidates (lengths in ball radii)
    candidates: int = 12          # Strongest peaks of the whole frame kept per frame,
    floor: float = 4.0            # ...if they have this many times the mass of a typical patch (noise)
    scale_radius: float = 4.0     # Whole frames are searched shrunk so the ball is this many pixels
    online: bool = True           # The blob tracker's own sighting is a candidate too,
    online_bonus: float = 0.0     # ...cheaper by this much
    online_ref: bool = True       # Likeness also against the online tracker's learned picture
    # The path
    max_gap: int = 45             # Longest stretch without the ball that a path may jump (frames)
    miss: float = 1.2             # Cost of a frame without the ball
    w_motion: float = 1.0         # Cost of a step: w_motion * (distance from the path's prediction / tolerance)^2
    tol: float = 0.5              # Tolerance of a one-frame step (ball radii),
    tol_gap: float = 0.3          # plus this per frame jumped,
    tol_gap2: float = 0.02        # plus this per frame jumped squared (the motion may have changed),
    tol_speed: float = 0.2        # plus this fraction of the path's speed (px)
    follow_v: float = 0.6         # How much of a step's surprise goes into the path's velocity,
    follow_a: float = 0.15        # and into its acceleration
    max_step: float = 12.0        # Steps costlier than this are not taken
    # A kick: the motion changed at once (a bounce, a push, the release). Such a step costs `kick`
    # plus w_motion * (distance from the last position / reach)^2, the reach being the tolerance
    # plus the path's speed and kick_reach ball radii per frame; the velocity starts again from the
    # step, and the acceleration (gravity) carries on
    kick: float = 2.5
    kick_reach: float = 2.0

    @classmethod
    def from_dict(cls, values: dict) -> "LinkSettings":
        from dataclasses import fields
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in values.items() if k in names})


def _shrink(image, scale):
    return image if image is None or scale >= 1 else cv2.resize(image, None, fx=scale, fy=scale,
                                                                interpolation=cv2.INTER_AREA)


def _small_gray(frame, scale) -> np.ndarray:
    """The frame in grey, shrunk by `scale`, as float32 (shrunk while 8-bit: several times faster)."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    if g.dtype != np.uint8:
        return _shrink(np.asarray(g, np.float32), scale)
    return _shrink(g, scale).astype(np.float32)


class _Frame:
    """A frame's feature image, shrunk by `scale` (so whole frames are cheap to search), or of a
    part of it (`box`: x0, y0, x1, y1 in frame pixels). `background` is already shrunk (and cut to
    the box)."""

    def __init__(self, frame, background, r, s, scale, box=None):
        from experiments.rigid.blobtracker import feature_image
        if box is not None:
            x0, y0, x1, y1 = box
            frame = frame[y0:y1, x0:x1]
        self.origin = (0, 0) if box is None else box[:2]
        gray = _small_gray(np.asarray(frame), scale)
        if background is not None and background.shape != gray.shape:
            background = cv2.resize(background, gray.shape[::-1], interpolation=cv2.INTER_AREA)
        self.scale = scale
        self.image = feature_image(gray, r * scale, s, background)
        self.k = k = max(1, int(round(r * scale)))
        yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
        self.disc = (xx * xx + yy * yy <= k * k).astype(np.float32)
        self.xx, self.yy = xx, yy

    def mass_at(self, p) -> float:
        """The feature summed over the ball's disc at frame position p."""
        k, img = self.k, self.image
        x, y = (int(round((v - o + 0.5) * self.scale - 0.5)) for v, o in zip(p, self.origin))
        if x < k or y < k or x >= img.shape[1] - k or y >= img.shape[0] - k:
            return 0.0
        return float((img[y - k:y + k + 1, x - k:x + k + 1] * self.disc).sum())

    def peaks(self, count, floor):
        """The `count` strongest ball-sized peaks with at least `floor` times the mass of a typical
        patch of the image (noise): rows of (x, y, mass) in frame pixels."""
        image, k = self.image, self.k
        size = 2 * k + 1
        least = floor * float(np.median(image[::4, ::4])) * float(self.disc.sum())
        peak = (image >= cv2.dilate(image, np.ones((size, size), np.uint8))) & (image > 0)
        peak[:k], peak[-k:], peak[:, :k], peak[:, -k:] = False, False, False, False
        ys, xs = np.nonzero(peak)
        if not len(xs):
            return np.zeros((0, 3))
        order = np.argsort(-image[ys, xs])[:count]
        out = []
        for x, y in zip(xs[order].tolist(), ys[order].tolist()):
            part = image[y - k:y + k + 1, x - k:x + k + 1] * self.disc
            mass = float(part.sum())
            if mass <= least or mass <= 0:
                continue
            out.append((x + float((part * self.xx).sum()) / mass, y + float((part * self.yy).sum()) / mass, mass))
        out = np.array(out).reshape(-1, 3)
        out[:, :2] = (out[:, :2] + 0.5) / self.scale - 0.5 + np.array(self.origin, float)
        return out


def _track_offline(frames, sel, values, budget) -> ClipTrack:
    """Every frame gives a few candidates: the strongest ball-like peaks of the whole frame, and
    the online blob tracker's sighting. A candidate costs more the less it looks like the ball
    (its picture against the ball's on frame 0 and against the online tracker's learned picture)
    and the more its blob mass differs. The chosen path starts at the selection and runs through
    one candidate per frame, or jumps frames where the ball is hidden at a cost per frame; a step
    costs more the farther it lands from where the path's own motion (position, velocity,
    acceleration, followed along the path) puts the ball. Dynamic programming finds the cheapest
    path over the whole clip (each candidate keeps its cheapest way in, as in the Viterbi
    algorithm), so a cover or a look-alike is judged by what comes before and after it. Jumped
    frames are filled in between the path's two sides.

    The path is worked out as the frames are read, so the best path so far can be shown while it
    runs (track_frames' `partial`); later frames can still change it.

    With a background: when the path has the ball resting in one place long enough to be in the
    background (a ghost there would hide it), the background is taken again without it, and the
    candidates near that place are found again (a second, local pass over the frames)."""
    from experiments.rigid.background import estimate_background, rested, sample_frames
    from experiments.rigid.blobtracker import BlobSettings
    s, L = BlobSettings.from_dict(values), LinkSettings.from_dict(values)
    start = time.process_time()
    refine = not getattr(_run, "ring", False)   # The ring-centre pass finds the centres otherwise
    _stage(0.0, 0.05, "Taking the still background")
    _tick(0, 1)
    background = estimate_background(frames) if s.background_mix > 0 else None
    link = _Linker(frames, sel, s, L, background)
    _stage(0.05, 0.75 if refine else 0.8, "Reading")
    stopped = link.read_all(budget, start)
    if background is None or stopped is not None:
        _stage(0.75, 1.0, "Finding the centres")
        out = link.result(stopped, start, refine)
        out.background = background
        return out
    out = link.result(stopped, start, refine=False)   # Where it rested; centres at the end
    r = _radius(sel)
    picks = sample_frames(len(frames))
    seen = out.status[picks] == MEASURED
    again = None
    if rested(np.where(seen[:, None], out.centre[picks], np.nan), r, s.ghost_share):
        exclude = {int(i): (*out.centre[i] - link.offset, 2 * r) for i, ok in zip(picks, seen) if ok}
        again = estimate_background(frames, exclude=exclude, base=background)
    changed = np.abs(again - background) > 2.0 if again is not None else np.zeros(1, bool)  # Where it rested
    _stage(0.75 if refine else 0.8, 1.0, "Finding the centres")
    if not changed.any():
        out = link.result(None, start, refine)
        out.background = background
        return out
    ys, xs = np.nonzero(changed)
    pad = int(4 * r + 2 * s.surround * r)
    h, w = background.shape
    box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(w, xs.max() + pad + 1), min(h, ys.max() + pad + 1))
    _stage(0.75 if refine else 0.8, 0.88 if refine else 1.0, "Second pass, where the ball rested")
    link.redo_area(again, box)
    _stage(0.88, 1.0, "Finding the centres")
    out = link.result(None, start, refine)
    out.background = again
    return out


class _Linker:
    """The whole-clip engine's state: the candidates of every frame read so far, and for each its
    cheapest way in (the forward pass of the Viterbi algorithm), worked out frame by frame."""

    def __init__(self, frames, sel, s, L, background):
        from experiments.rigid.blobtracker import BlobTracker
        self.frames, self.s, self.L = frames, s, L
        self.n = len(frames)
        online = self.online = BlobTracker(s)
        online.background = background
        first = np.asarray(frames[0])
        online.initialize_tracker(first, *sel)
        self.r = r = online.r
        self.scale = min(1.0, L.scale_radius / r)
        self.small_bg = _shrink(background, self.scale)
        self.ref0 = online.ref.copy() if online.ref is not None else None
        self.offset = online.offset.copy()
        # Candidates are blob centres; the offset is added to the path at the end
        begin = np.array(online.centre) - online.offset
        self.mass0 = _Frame(first, self.small_bg, r, s, self.scale).mass_at(begin) or None
        # Per frame: positions, own cost, likeness, which is the online sighting; then the path's
        # cost, way in (frame, candidate), velocity and acceleration
        self.P, self.U, self.M, self.O = [begin[None, :]], [np.zeros(1)], [np.ones(1)], [np.ones(1, bool)]
        self.C, self.back = [np.zeros(1)], [np.full((1, 2), -1)]
        self.V, self.A = [np.zeros((1, 2))], [np.zeros((1, 2))]
        self.alive = [True]

    def _look(self, gray, p):
        """How much the picture at p looks like the ball: the better of frame 0's and the online
        tracker's learned picture."""
        online = self.online
        m = online._match(gray, p) if self.L.online_ref or self.ref0 is None else -1.0
        if self.ref0 is not None:
            current, online.ref = online.ref, self.ref0
            m = max(m, online._match(gray, p))
            online.ref = current
        return m

    def _costs(self, gray, pos, mass, bonus):
        likeness = np.array([self._look(gray, p) for p in pos])
        cost = self.s.w_unlike * (1.0 - np.clip(likeness, -1, 1)) - np.array(bonus, float).reshape(-1)
        if self.mass0:
            ratio = np.maximum(np.array(mass, float), 1e-6) / self.mass0
            cost = cost + self.s.w_mass * (np.log(ratio) / np.log(3.0)) ** 2
        return likeness, cost

    def read_all(self, budget, start):
        """Reads every frame: candidates, then the path's step to them. The frame it was stopped
        at by the time budget, or None."""
        partial = getattr(_run, "partial", None)
        shown = time.perf_counter()
        # Two stages: a helper thread reads frame t + 1 and finds its peaks (OpenCV work, which
        # runs alongside) while this one takes frame t's online sighting, likeness and path step
        pool = ThreadPoolExecutor(1)
        try:
            ahead = pool.submit(self._prepare, 1) if self.n > 1 else None
            for t in range(1, self.n):
                _tick(t, self.n)
                frame, found, image = ahead.result()
                if t + 1 < self.n:
                    ahead = pool.submit(self._prepare, t + 1)
                self.add_frame(t, frame, found, image)
                if partial is not None and time.perf_counter() - shown >= PARTIAL_INTERVAL:
                    shown = time.perf_counter()
                    centre, status = self.path(t)
                    partial(centre, status)
                if budget and t >= 10 and 1000 * (time.process_time() - start) / t > budget:
                    return t
            return None
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

    def _prepare(self, t):
        """Frame t and its strongest peaks (the part of a frame's work that needs no state)."""
        frame = np.asarray(self.frames[t])
        image = _Frame(frame, self.small_bg, self.r, self.s, self.scale)
        return frame, image.peaks(self.L.candidates, self.L.floor), image

    def add_frame(self, t, frame, found, image):
        s, L, online, r = self.s, self.L, self.online, self.r
        gray = online._gray(frame)
        pos, mass, bonus = list(found[:, :2]), list(found[:, 2]), [0.0] * len(found)
        ok = False
        if L.online:
            ok, _ = online.update_tracker(frame)
            if ok:
                c = np.array(online.centre) - online.offset
                keep = [i for i, p in enumerate(pos) if np.hypot(*(p - c)) > r]  # The sighting replaces peaks on it
                pos, mass, bonus = [pos[i] for i in keep], [mass[i] for i in keep], [bonus[i] for i in keep]
                pos.append(c)
                mass.append(image.mass_at(c))
                bonus.append(L.online_bonus)
        is_online = np.zeros(len(pos), bool)
        if ok:
            is_online[-1] = True    # The sighting was added last
        pos = np.array(pos, float).reshape(-1, 2)
        likeness, cost = self._costs(gray, pos, mass, bonus)
        self.P.append(pos), self.U.append(cost), self.M.append(likeness), self.O.append(is_online)
        self._step(t)

    def _step(self, t):
        """The cheapest way into each candidate of frame t (from frames up to max_gap back)."""
        L, r, P = self.L, self.r, self.P
        k = len(P[t])
        C, back = np.full(k, np.inf), np.full((k, 2), -1)
        V, A = np.zeros((k, 2)), np.zeros((k, 2))
        frames_from = [u for u in range(max(0, t - L.max_gap), t) if self.alive[u]]
        if k and frames_from:
            pp = np.concatenate([P[u] for u in frames_from])
            vv = np.concatenate([self.V[u] for u in frames_from])
            aa = np.concatenate([self.A[u] for u in frames_from])
            cc = np.concatenate([self.C[u] for u in frames_from])
            gap = np.concatenate([np.full(len(P[u]), t - u) for u in frames_from]).astype(float)
            ids = np.concatenate([np.column_stack([np.full(len(P[u]), u), np.arange(len(P[u]))])
                                  for u in frames_from])
            pred = pp + vv * gap[:, None] + 0.5 * aa * (gap ** 2)[:, None]
            jumped = gap - 1
            speed = np.hypot(*vv.T)
            tol = r * (L.tol + L.tol_gap * jumped + L.tol_gap2 * jumped ** 2) + L.tol_speed * speed * gap
            d = np.hypot(pred[:, None, 0] - P[t][None, :, 0], pred[:, None, 1] - P[t][None, :, 1])
            step = L.w_motion * (d / tol[:, None]) ** 2
            # ...or a kick, judged by the distance from the last position only
            reach = r * L.tol + (speed + L.kick_reach * r) * gap
            d0 = np.hypot(pp[:, None, 0] - P[t][None, :, 0], pp[:, None, 1] - P[t][None, :, 1])
            kick = L.kick + L.w_motion * (d0 / reach[:, None]) ** 2
            kicked = kick < step
            step = np.where(kicked, kick, step)
            step[step > L.max_step] = np.inf
            total = (cc + L.miss * jumped)[:, None] + step + self.U[t][None, :]
            best = np.argmin(total, axis=0)
            cols = np.arange(k)
            C = total[best, cols]
            back = ids[best]
            g = gap[best][:, None]
            surprise = P[t] - pred[best]
            smooth_v = vv[best] + aa[best] * g + L.follow_v * surprise / g
            V = np.where(kicked[best, cols][:, None], (P[t] - pp[best]) / g, smooth_v)
            A = np.where(kicked[best, cols][:, None], aa[best], aa[best] + L.follow_a * surprise / g ** 2)
        if t < len(self.C):
            self.C[t], self.back[t], self.V[t], self.A[t], self.alive[t] = C, back, V, A, bool(np.isfinite(C).any())
        else:
            self.C.append(C), self.back.append(back), self.V.append(V), self.A.append(A)
            self.alive.append(bool(np.isfinite(C).any()))

    def redo_area(self, background, box):
        """The second pass: with a new background, the candidates inside `box` (x0, y0, x1, y1) are
        found again on every frame (those outside, and the online sightings, are kept), and the
        path is worked out again."""
        partial = getattr(_run, "partial", None)
        x0, y0, x1, y1 = box
        cut = background[y0:y1, x0:x1]
        small = _shrink(cut, self.scale)
        self.online.background = background
        shown = time.perf_counter()
        for t in range(1, len(self.P)):
            _tick(t, self.n)
            frame = np.asarray(self.frames[t])
            pos, keep = self.P[t], ~self.O[t]
            inside = keep & (pos[:, 0] >= x0) & (pos[:, 0] < x1) & (pos[:, 1] >= y0) & (pos[:, 1] < y1)
            image = _Frame(frame, small, self.r, self.s, self.scale, box=box)
            found = image.peaks(self.L.candidates, self.L.floor)
            if len(found):
                gray = self.online._gray(frame)
                likeness, cost = self._costs(gray, found[:, :2], found[:, 2], np.zeros(len(found)))
            else:
                likeness, cost = np.zeros(0), np.zeros(0)
            stay = ~inside
            self.P[t] = np.concatenate([pos[stay], found[:, :2]])
            self.U[t] = np.concatenate([self.U[t][stay], cost])
            self.M[t] = np.concatenate([self.M[t][stay], likeness])
            self.O[t] = np.concatenate([self.O[t][stay], np.zeros(len(found), bool)])
            self._step(t)
            if partial is not None and time.perf_counter() - shown >= PARTIAL_INTERVAL:
                shown = time.perf_counter()
                partial(*self.path(t))

    def path(self, upto, refine=False):
        """The cheapest path over frames 0..upto (frames after it count as missed): (centre,
        status) for all n frames, the offset added. With `refine`, peaks of the shrunk frames are
        found again at full size (sub-pixel; it reads those frames again)."""
        L, n = self.L, self.n
        best = None
        for t in range(upto + 1):
            if self.alive[t]:
                k = int(np.argmin(self.C[t]))
                cost = self.C[t][k] + L.miss * (n - 1 - t)
                if best is None or cost < best[0]:
                    best = (cost, t, k)
        _, t, k = best
        chosen = {}
        while t > 0:
            chosen[t] = k
            t, k = self.back[t][k]
        chosen[0] = 0
        centre, status = np.zeros((n, 2)), np.zeros(n, int)
        self.score = np.zeros(n)
        times = sorted(chosen)
        for i, t in enumerate(times):
            k = chosen[t]
            if refine:
                _tick(i, len(times))
            centre[t], status[t] = self.P[t][k], MEASURED
            self.score[t] = float(np.clip(self.M[t][k], 0, 1))
            if refine and t and not self.O[t][k]:
                found = self.online._blobs(self.online._gray(np.asarray(self.frames[t])), self.P[t][k], self.r)
                if len(found):
                    j = int(np.argmin(np.hypot(*(found[:, :2] - self.P[t][k]).T)))
                    if np.hypot(*(found[j, :2] - self.P[t][k])) <= self.r:
                        centre[t] = found[j, :2]
        self.score[0] = 1.0
        for a, b in zip(times, times[1:]):   # Jumped frames: a cubic between the two sides' motion
            if b - a > 1:
                va, vb = self.V[a][chosen[a]], self.V[b][chosen[b]]
                for t in range(a + 1, b):
                    centre[t] = _hermite(centre[a], va, centre[b], vb, (t - a) / (b - a), b - a)
                    status[t] = FILLED
        last = times[-1]
        centre[last + 1:] = centre[last]
        centre += self.offset
        self.chosen = chosen
        return centre, status

    def result(self, stopped, start, refine=True) -> ClipTrack:
        centre, status = self.path(len(self.P) - 1, refine=refine)
        ms = 1000 * (time.process_time() - start) / (stopped or self.n - 1)
        LAST_RUN.update(P=self.P, U=self.U, M=self.M, C=self.C, chosen=self.chosen)  # For inspecting a run
        return ClipTrack(centre, status, self.score, ms, stopped)


PARTIAL_INTERVAL = 0.3   # Seconds between the best paths so far sent while reading (track_frames' partial)


LAST_RUN: dict = {}


def _radius(sel) -> float:
    """The object's radius from the selection (rect, outline)."""
    rect, outline = sel
    if outline is not None:
        from experiments.rigid.blobtracker import outline_circle
        return outline_circle(outline)[1]
    return max(rect.width, rect.height) / 2.0


def _hermite(p0, v0, p1, v1, u, span):
    """Cubic from p0 (velocity v0, per frame) to p1 (velocity v1) at fraction u of `span` frames."""
    h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
    return h00 * p0 + h10 * span * v0 + h01 * p1 + h11 * span * v1
