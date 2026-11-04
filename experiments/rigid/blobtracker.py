"""
blobtracker.py

A ball tracker for lab footage: trackpy finds ball-like blobs, and a motion model says which one is
the ball.

- Finding: only a window around the predicted position is searched (a few ms per frame). The
  window is turned into a feature image in which the ball is one round peak (by default its
  contrast with its surroundings, so a shiny ball's bright and dark parts both count, blurred so
  the whole ball is one peak), and trackpy.locate finds the ball-sized blobs in it, with sub-pixel
  centres and their mass. A ball with too little contrast to stand out as a blob is found by
  matching its picture (template matching) instead.
- Choosing: each candidate is scored by how far it is from the prediction, measured against how
  sure the prediction is; how much it looks like the ball (normalised correlation with the inside
  of the ball, so a veil or fog on the lens does not matter); and how close its mass is to the
  ball's. A candidate far from the prediction must clearly look like the ball.
- Motion: a Kalman filter (constant acceleration by default). When the ball is not seen, the
  prediction carries on and its uncertainty grows, so the search widens by itself; a weak
  sighting (partly covered, merged with something) is a noisy measurement that barely changes
  the motion. When nothing clearly like the ball is near the prediction (it bounced, or was
  pushed), the area all around the last sighting is searched for it.

This is trackpy's linking idea (a search range, memory of a vanished particle, a motion
predictor) for one object, done frame by frame so tracking can be shown live and stopped.

Every constant is in BlobSettings, so the tracker can be tuned against the benchmarks
(tests/tune_tracker.py). Lengths are in ball radii, so one setting works for any ball size. The
parts that may be swapped are named there too: the feature image (FEATURES) and the motion model
(MOTIONS).

Same interface as MLTracker. No GUI here. Author: Isam Balghari
"""

from dataclasses import asdict, dataclass, fields

import cv2
import numpy as np

from core import PixelRect


@dataclass
class BlobSettings:
    # Finding blobs (lengths in ball radii)
    finder: str = "direct"            # "direct": trackpy's locate steps in numpy/OpenCV; "trackpy": trackpy.locate
    feature: str = "contrast"         # The feature image: a name in FEATURES
    surround: float = 1.5             # Size of the surroundings the ball is compared with
    spread: float = 0.5               # Blur that makes the whole ball one peak
    # The still background (background.py; used when the tracker is given one): the feature image
    # is this much of the feature of (frame - background), and the rest the frame's own, so static
    # clutter fades. 0 ignores the background; 1 sees only what differs from it
    background_mix: float = 0.0
    ghost_share: float = 0.35         # When a first track has the ball in one place in this share of the
                                      # sampled frames, the background is taken again without it (cliptrack)
    # Likeness: normalised correlation of the inside of the ball
    patch: float = 0.7                # Half-size of the ball's picture
    flat_ref: float = 4.0             # A picture flatter than this (grey-level spread) also takes the edge
    flat: float = 2.0                 # A patch flatter than this says nothing (likeness 0)
    shift: int = 2                    # Pixels of shift allowed when comparing pictures
    # Template matching, for a ball too faint to stand out as a blob
    template_score: float = 0.8       # Least match to count as a candidate
    template_reach: float = 0.5       # Searched within this fraction of the search radius
    template_mass: tuple = (0.5, 2.0)  # Its blob mass must be within these multiples of the ball's
    template_min_patch: int = 3       # Not for a ball picture smaller than this half-size (pixels)
    # Choosing
    strong: float = 0.6               # Likeness that is clearly the ball (and may steer the motion)
    least: float = 0.35               # Least likeness for a candidate away from the prediction
    near_least: float = 0.1           # ...and for one within a radius of it
    mass_range: tuple = (0.3, 3.0)    # Allowed blob mass, as multiples of the ball's
    gate: float = 4.0                 # Search out to this many standard deviations of the prediction
    w_far: float = 1.0                # Cost weights: distance from the prediction (per gate),
    w_unlike: float = 1.5             # unlikeness (1 - likeness),
    w_mass: float = 0.5               # and mass (log ratio, per factor of three)
    # Search area (lengths in ball radii)
    base: float = 3.0                 # Smallest search radius
    base_min: float = 12.0            # ...but at least this many pixels
    max_reach: float = 12.0           # Largest search radius, plus the ball's speed
    wide: float = 1.5                 # Wide search: this many times the distance it could have gone
    # Motion (Kalman filter)
    motion: str = "acceleration"      # A name in MOTIONS
    jerk: float = 0.4                 # How fast the motion may change (px / frame^3, or ^2 for velocity)
    start_pos: float = 0.5            # Uncertainty at the start (ball radii): position,
    start_vel: float = 1.0            # velocity,
    start_acc: float = 0.5            # and acceleration (px / frame^2)
    noise: float = 0.7                # Measurement noise of a perfect match (px)
    noise_unlike: float = 6.0         # ...plus this much per unit of unlikeness (px)
    noise_weak: float = 1.0           # Noise of a weak sighting (ball radii)
    # Learning the ball's look
    learn_above: float = 0.7          # Learn the picture only from matches better than this
    learn_first: int = 3              # ...except on the first few sightings
    learn_picture: float = 0.3        # How fast the picture and
    learn_mass: float = 0.2           # the mass follow the latest sighting
    # Where the centre is: the blob's centre is off the ball's when the ball is lit from one side
    # (a shiny ball's bright top pulls it up). With this, the offset between the selection's
    # centre and the blob's on the first frame is kept and added to every position (up to half a
    # radius; for fixed lighting)
    selection_offset: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict) -> "BlobSettings":
        names = {f.name for f in fields(cls)}
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in values.items() if k in names})


# -------------------------------------------------------------------------------------------------
# Feature images: the ball becomes one round peak; any (window, radius, settings) -> float image
def _contrast_feature(win, r, s):
    """How much each pixel differs from its surroundings (bright and dark parts both count),
    blurred so a shiny ball, bright above and dark below its middle, is one peak at its centre."""
    contrast = np.abs(win - cv2.GaussianBlur(win, (0, 0), s.surround * r))
    return cv2.GaussianBlur(contrast, (0, 0), max(1.0, s.spread * r))


def _dog_feature(win, r, s):
    """Difference of Gaussians at the ball's size (a blob detector), either sign."""
    small = cv2.GaussianBlur(win, (0, 0), max(1.0, s.spread * r))
    return np.abs(small - cv2.GaussianBlur(win, (0, 0), s.surround * r))


FEATURES = {"contrast": _contrast_feature, "dog": _dog_feature}


def feature_image(win, r, s, background=None):
    """The feature image (FEATURES[s.feature]) of a grey float32 picture, for a ball of radius r.
    With the still `background` (same size), it is s.background_mix of the feature of what differs
    from the background (scaled to the picture's brightness first, for flicker), and the rest the
    picture's own."""
    feature, mix = FEATURES[s.feature], s.background_mix
    if background is None or mix <= 0:
        return feature(win, r, s)
    moving = feature(win - background * (float(win.mean()) / max(float(background.mean()), 1e-3)), r, s)
    if mix >= 1:
        return moving
    return (1 - mix) * feature(win, r, s) + mix * moving


# Motion models: (F, Q) for one frame step, the state is (x, y, vx, vy, ax, ay)
def _constant_acceleration(jerk):
    f = np.array([[1, 1, 0.5], [0, 1, 1], [0, 0, 1]])
    q = np.array([[1 / 20, 1 / 8, 1 / 6], [1 / 8, 1 / 3, 1 / 2], [1 / 6, 1 / 2, 1]]) * jerk ** 2
    return np.kron(f, np.eye(2)), np.kron(q, np.eye(2))


def _constant_velocity(jerk):
    f = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 0]])  # Acceleration is not used (kept at zero)
    q = np.array([[1 / 3, 1 / 2, 0], [1 / 2, 1, 0], [0, 0, 0]]) * jerk ** 2
    return np.kron(f, np.eye(2)), np.kron(q, np.eye(2))


MOTIONS = {"acceleration": _constant_acceleration, "velocity": _constant_velocity}


# -------------------------------------------------------------------------------------------------
# trackpy.locate's steps (preprocess off), on numpy arrays without its pandas tables: on the small
# windows searched here, the tables and checks cost most of trackpy's time
_discs: dict = {}


def _disc(k: int):
    if k not in _discs:
        yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
        mask = (xx * xx + yy * yy <= k * k).astype(np.float32)
        _discs[k] = (mask, (xx * mask).astype(np.float32), (yy * mask).astype(np.float32))
    return _discs[k]


def locate_direct(image: np.ndarray, diameter: int, percentile: float = 64.0,
                  max_iterations: int = 10, shift_thresh: float = 0.6) -> np.ndarray:
    """Blobs in `image` as rows of (x, y, mass), as trackpy.locate(image, diameter,
    separation=diameter, preprocess=False) finds them: local maxima (over the largest square
    inside the separation circle) brighter than the image's `percentile`, away from the edges;
    each refined to its centre of mass over a disc of the blob's radius, moving the disc while the
    centre is more than `shift_thresh` off; maxima that end up closer than the separation keep the
    one with more mass. (trackpy rounds the image to 8 bits first; this keeps full precision.)"""
    k = diameter // 2
    h, w = image.shape
    size = int(2 * diameter / np.sqrt(2))
    dilated = cv2.dilate(image, np.ones((size, size), np.uint8))
    threshold = np.percentile(image, percentile)
    ys, xs = np.nonzero((image == dilated) & (image > threshold))
    margin = max(k, diameter // 2 - 1)
    keep = (xs >= margin) & (ys >= margin) & (xs < w - margin) & (ys < h - margin)
    xs, ys = xs[keep], ys[keep]
    if not len(xs):
        return np.zeros((0, 3))
    mask, mx, my = _disc(k)
    out = []
    for cx, cy in zip(xs.tolist(), ys.tolist()):
        ox = oy = mass = 0.0
        for _ in range(max_iterations):
            part = image[cy - k:cy + k + 1, cx - k:cx + k + 1]
            mass = float((part * mask).sum())
            if mass <= 0:
                break
            ox, oy = float((part * mx).sum()) / mass, float((part * my).sum()) / mass
            if abs(ox) <= shift_thresh and abs(oy) <= shift_thresh:
                break
            nx, ny = cx + int(round(ox)), cy + int(round(oy))
            if nx < k or ny < k or nx > w - k - 1 or ny > h - k - 1 or (nx, ny) == (cx, cy):
                break
            cx, cy = nx, ny
        out.append((cx + ox, cy + oy, mass))
    found = np.array(out)
    if len(found) > 1:  # Flat peaks give several maxima: keep the heaviest within the separation
        order = np.argsort(-found[:, 2])
        kept = []
        for i in order:
            if all((found[i, 0] - found[j, 0]) ** 2 + (found[i, 1] - found[j, 1]) ** 2 >= diameter ** 2 for j in kept):
                kept.append(i)
        found = found[sorted(kept)]
    return found


def _std(a) -> float:
    """Standard deviation of a small float32 patch (OpenCV: much faster than numpy's on small arrays)."""
    return float(cv2.meanStdDev(a)[1][0, 0])


def outline_circle(outline) -> tuple[np.ndarray, float]:
    """The centre (centroid) and radius (of the circle with the same area) of an outline: a polygon
    of (x, y) points, or a boolean mask."""
    outline = np.asarray(outline)
    if outline.dtype == bool:
        ys, xs = np.nonzero(outline)
        return np.array([xs.mean(), ys.mean()]), float(np.sqrt(len(xs) / np.pi))
    m = cv2.moments(outline.astype(np.float32).reshape(-1, 1, 2))
    return np.array([m["m10"] / m["m00"], m["m01"] / m["m00"]]), float(np.sqrt(abs(m["m00"]) / np.pi))


# -------------------------------------------------------------------------------------------------
class BlobTracker:
    def __init__(self, settings: BlobSettings | None = None) -> None:
        self.s = settings or BlobSettings()
        self.feature = FEATURES[self.s.feature]
        self.centre = None            # Sub-pixel centre (x, y) of the last update
        self.offset = np.zeros(2)     # Added to the blob's centre (selection_offset)
        self.background = None        # The clip's still background (grey float32), set before initialize_tracker
        self._score = 0.0

    def initialize_tracker(self, frame, rect: PixelRect, outline=None) -> None:
        """Starts on the object in `rect` on `frame`. With an `outline` of it (a polygon of (x, y)
        points or a boolean mask the frame's size, as an automatic selection gives), its centroid
        is the centre and its area gives the radius."""
        s = self.s
        if outline is not None:
            centre, self.r = outline_circle(outline)
        else:
            self.r = max(rect.width, rect.height) / 2.0
            centre = np.array([rect.xmin + rect.width / 2.0, rect.ymin + rect.height / 2.0])
        self.d = int(2 * round(self.r) + 1) | 1                # trackpy wants an odd diameter
        self.half = max(2, int(s.patch * self.r))
        self.base = max(s.base * self.r, s.base_min)
        selected = centre.copy()
        gray = self._gray(frame)
        self.ref = self._patch(gray, centre)
        if self.ref is not None and float(self.ref.std()) < s.flat_ref:
            # A plain ball looks flat inside: use its edge and a little of what is around it
            self.half = int(np.ceil(self.r)) + 1
            self.ref = self._patch(gray, centre)
        self.mass, self.found_count = None, 0
        found = self._blobs(gray, centre, self.base)
        if len(found):
            k = int(np.argmin(np.hypot(found[:, 0] - centre[0], found[:, 1] - centre[1])))
            if np.hypot(*(found[k, :2] - centre)) <= self.r:
                centre, self.mass, self.found_count = found[k, :2].copy(), float(found[k, 2]), 1
                self.ref = self._patch(gray, centre)
        self.F, self.Q = MOTIONS[s.motion](s.jerk)
        self.H = np.hstack([np.eye(2), np.zeros((2, 4))])
        self.x = np.array([centre[0], centre[1], 0, 0, 0, 0], float)
        self.P = np.diag([(s.start_pos * self.r) ** 2] * 2 + [(s.start_vel * self.r) ** 2] * 2
                         + [s.start_acc ** 2] * 2)
        self.seen, self.missing = centre.copy(), 0
        self.offset = np.zeros(2)
        if s.selection_offset and np.hypot(*(selected - centre)) <= 0.5 * self.r:
            self.offset = selected - centre
        self.centre = (float(centre[0] + self.offset[0]), float(centre[1] + self.offset[1]))
        self._score = 1.0

    def score(self) -> float:
        """How much the last sighting looked like the ball (0 when it was not found)."""
        return self._score

    def update_tracker(self, frame) -> tuple[bool, PixelRect]:
        s = self.s
        gray = self._gray(frame)
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        pred = self.x[:2].copy()
        speed = float(np.hypot(*self.x[2:4]))
        S = self.H @ self.P @ self.H.T + np.eye(2) * s.noise ** 2
        sigma = float(np.sqrt(np.linalg.eigvalsh(S).max()))
        reach = min(s.gate * sigma + self.r, s.max_reach * self.r + speed)
        found = self._choose(gray, pred, pred, reach, np.linalg.inv(S), near=self.r)
        tiny = self.half < s.template_min_patch     # A tiny ball's few pixels never match well
        strong = found is not None and (found[1] >= s.strong or tiny)
        if not strong and self.found_count:
            # Nothing clearly the ball near the prediction. It may have bounced or been pushed:
            # look all around the last sighting, as far as it could have gone since, for something
            # that clearly looks like the ball
            wide = self.base + s.wide * speed * (self.missing + 1)
            other = self._choose(gray, self.seen, pred, wide, None, near=0.0, least=s.strong)
            if other is not None:
                found, strong = other, True
        if found is None:
            self.missing += 1
            self._score = 0.0
            self.centre = (float(pred[0] + self.offset[0]), float(pred[1] + self.offset[1]))
            return False, PixelRect(0, 0, 0, 0)
        best, match, mass = found
        if strong and np.hypot(*(best - pred)) > reach:
            # Found by the wide search: start the motion again from here
            self.x[:2], self.x[2:4], self.x[4:] = best, (best - self.seen) / (self.missing + 1), 0
            self.P = np.diag([1.0] * 2 + [(s.start_vel * self.r) ** 2] * 2 + [s.start_acc ** 2] * 2)
        else:
            # A weak sighting is a noisy measurement: it barely moves the motion
            noise = s.noise + s.noise_unlike * (1.0 - min(match, 1.0)) if strong else s.noise_weak * self.r
            S = self.H @ self.P @ self.H.T + np.eye(2) * noise ** 2
            K = self.P @ self.H.T @ np.linalg.inv(S)
            self.x = self.x + K @ (best - pred)
            self.P = (np.eye(6) - K @ self.H) @ self.P
        if strong:
            self.seen, self.missing = best.copy(), 0
            self.found_count += 1
            # Learn how the ball looks where it is clearly found (a hand or a veil on the first
            # frame fades out of the reference; a cover does not get into it)
            if mass is not None:
                self.mass = mass if self.mass is None else (1 - s.learn_mass) * self.mass + s.learn_mass * mass
            patch = self._patch(gray, best)
            if patch is not None and (self.ref is None or match > s.learn_above
                                      or self.found_count < s.learn_first):
                self.ref = patch if self.ref is None else (
                    (1 - s.learn_picture) * self.ref + s.learn_picture * patch)
        else:
            self.missing += 1
        self._score = match
        self.centre = (float(best[0] + self.offset[0]), float(best[1] + self.offset[1]))
        r = int(round(self.r))
        return True, PixelRect(int(round(best[0])) - r, int(round(best[1])) - r, 2 * r, 2 * r)

    # ---------------------------------------------------------------------------------------------
    def _choose(self, gray, around, pred, reach, s_inv, near, least=None):
        """The best candidate within `reach` of `around`, as (centre, match, mass), or None.
        The cost adds the distance from the prediction (per gate, in standard deviations when
        `s_inv` is given, else as a fraction of `reach`), how unlike the ball it looks, and how far
        its mass is from the ball's. Within `near` of the prediction a weak likeness is enough;
        farther out it must clearly look like the ball (at least `least`, if given)."""
        s = self.s
        cands = [(x, y, mass) for x, y, mass in self._blobs(gray, around, reach)]
        if near > 0:  # Not in the wide search: a picture match far away is too easily something else
            peak = self._template_peak(gray, pred, min(reach, max(self.r, s.template_reach * reach)))
            if peak is not None:
                mass = self._mass_at(gray, peak)
                # A picture match alone is weak evidence (a chrome ball's horizon looks like any
                # edge), so its blob mass must also be close to the ball's
                lo, hi = s.template_mass
                if self.mass is None or lo * self.mass <= mass <= hi * self.mass:
                    cands.append((peak[0], peak[1], mass))
        best, best_cost = None, np.inf
        for x, y, mass in cands:
            if np.hypot(x - around[0], y - around[1]) > reach:
                continue
            nu = np.array([x - pred[0], y - pred[1]])
            dist = float(np.hypot(*nu))
            if self.mass is not None and not (
                    s.mass_range[0] * self.mass <= mass <= s.mass_range[1] * self.mass):
                continue
            match = self._match(gray, (x, y))
            if self.found_count == 0 and dist > self.r and match < s.strong:
                continue  # Not found yet: the ball is near where it was selected
            if match < (least if least is not None else s.near_least if dist <= near else s.least):
                continue
            if s_inv is not None:
                d2 = float(nu @ s_inv @ nu)
                if d2 > s.gate ** 2 and dist > near:
                    continue
                far = d2 / s.gate ** 2
            else:
                far = dist / max(reach, 1.0)
            off = np.log(mass / self.mass) / np.log(3.0) if self.mass and mass > 0 else 0.0
            cost = s.w_far * far + s.w_unlike * (1.0 - match) + s.w_mass * off * off
            if cost < best_cost:
                best, best_cost = (np.array([x, y]), match, mass), cost
        return best

    @staticmethod
    def _gray(frame) -> np.ndarray:
        """The frame in grey, as it comes (8-bit stays 8-bit: only the windows looked at are
        turned into float32, which saves converting whole large frames)."""
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        return g if g.dtype in (np.uint8, np.float32) else g.astype(np.float32)

    def _feature(self, gray, centre, reach):
        """The feature image of a window around `centre`, and the window's corner."""
        h, w = gray.shape
        pad = int(reach + 2 * self.s.surround * self.r + self.d)
        x0, y0 = max(0, int(centre[0]) - pad), max(0, int(centre[1]) - pad)
        x1, y1 = min(w, int(centre[0]) + pad + 1), min(h, int(centre[1]) + pad + 1)
        if x1 - x0 < 2 * self.d or y1 - y0 < 2 * self.d:
            return None, x0, y0
        bg = None if self.background is None else self.background[y0:y1, x0:x1]
        return feature_image(gray[y0:y1, x0:x1].astype(np.float32), self.r, self.s, bg), x0, y0

    def _blobs(self, gray, centre, reach) -> np.ndarray:
        """Ball-sized blobs within `reach` of `centre`, as rows of (x, y, mass) in frame pixels."""
        image, x0, y0 = self._feature(gray, centre, reach)
        if image is None:
            return np.zeros((0, 3))
        if self.s.finder == "direct":
            found = locate_direct(image, self.d)
            if not len(found):
                return found
            found[:, 0] += x0
            found[:, 1] += y0
            return found
        import trackpy as tp   # Only for finder "trackpy" (it needs pandas; "direct" does not)
        tp.quiet()
        found = tp.locate(image, self.d, separation=self.d, preprocess=False,
                          characterize=False, engine="python")
        if not len(found):
            return np.zeros((0, 3))
        return np.column_stack([found["x"].to_numpy() + x0, found["y"].to_numpy() + y0,
                                found["mass"].to_numpy()])

    def _mass_at(self, gray, centre) -> float:
        """The blob mass at `centre`, as trackpy.locate measures it (the feature summed over a disc)."""
        image, x0, y0 = self._feature(gray, centre, 0)
        if image is None:
            return 0.0
        k = self.d // 2
        yy, xx = np.ogrid[-k:k + 1, -k:k + 1]
        cx, cy = int(round(centre[0])) - x0, int(round(centre[1])) - y0
        part = image[max(0, cy - k):cy + k + 1, max(0, cx - k):cx + k + 1]
        disc = (xx * xx + yy * yy <= k * k)[:part.shape[0], :part.shape[1]]
        return float(part[disc].sum())

    def _patch(self, gray, centre) -> np.ndarray | None:
        k = self.half
        cx, cy = int(round(centre[0])), int(round(centre[1]))
        if cx - k < 0 or cy - k < 0 or cx + k + 1 > gray.shape[1] or cy + k + 1 > gray.shape[0]:
            return None
        return gray[cy - k:cy + k + 1, cx - k:cx + k + 1].astype(np.float32)

    def _match(self, gray, centre) -> float:
        """Normalised correlation between the ball's picture and the picture at `centre`,
        allowing a few pixels of shift either way."""
        if self.ref is None:
            return 1.0
        k = self.half + self.s.shift
        cx, cy = int(round(centre[0])), int(round(centre[1]))
        if cx - k < 0 or cy - k < 0 or cx + k + 1 > gray.shape[1] or cy + k + 1 > gray.shape[0]:
            return 0.0
        area = gray[cy - k:cy + k + 1, cx - k:cx + k + 1].astype(np.float32)
        if _std(area) < self.s.flat or _std(self.ref) < self.s.flat:
            return 0.0  # A flat patch matches anything: it says nothing
        return float(cv2.matchTemplate(area, self.ref, cv2.TM_CCOEFF_NORMED).max())

    def _template_peak(self, gray, around, reach):
        """Where the ball's picture matches best within `reach` of `around`, if it matches well."""
        s = self.s
        if self.ref is None or self.half < s.template_min_patch or float(self.ref.std()) < s.flat:
            return None  # A tiny or flat picture matches too much to be a finder on its own
        k = self.half
        h, w = gray.shape
        x0, y0 = max(0, int(around[0] - reach) - k), max(0, int(around[1] - reach) - k)
        x1, y1 = min(w, int(around[0] + reach) + k + 1), min(h, int(around[1] + reach) + k + 1)
        if x1 - x0 <= 2 * k + 1 or y1 - y0 <= 2 * k + 1:
            return None
        res = cv2.matchTemplate(gray[y0:y1, x0:x1].astype(np.float32), self.ref, cv2.TM_CCOEFF_NORMED)
        _, score, _, (px, py) = cv2.minMaxLoc(res)
        if score < s.template_score:
            return None
        return x0 + px + k, y0 + py + k
