"""How good is the tracker? Short synthetic scenarios, from easy to hard, with known ball paths.

Each scenario draws a background (white = easy; noise or camouflage = hard), foreground objects
that only make it harder (decoys that look like the ball, shapes that cross its path, occluders
that pass in front of it, a "hand" holding it at the start), and the ball, which moves about the
screen. The ball is selected the way the circle tool selects it: the tracker is given the circle's
bounding square on frame 0. The tracker's centre on every frame is compared with the true one.

Scores per scenario (errors in pixels, measured at the ball's centre):
    median   typical error
    p95      the error that 95% of frames stay under
    on-ball  fraction of frames whose centre is within the ball's radius of the truth
    lost     frames where the tracker reported that it lost the object

The scenarios are drawn in memory and run through the raw tracker (no video file), so they take
seconds. The pipeline around the tracker (proxy, frame bookkeeping, full resolution) is covered by
test_tracker_accuracy. No window is needed.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Callable

import cv2
import numpy as np

from tests import harness as h
h.setup_env()

from core import PixelRect  # noqa: E402
from experiments.rigid.blobtracker import BlobTracker  # noqa: E402
from experiments.rigid.mltracker import MLTracker  # noqa: E402

W, H, N = 640, 480, 120
SHIFT = 4  # cv2 draws at 1/16 pixel with this shift, so the true centre is not rounded to a pixel


# -------------------------------------------------------------------------------------------------
class Jitter:
    """Random variation for another draw of the same scenarios (sizes, paths, timings, dirt,
    noise), to tune and test for robustness rather than for one picture. Draw 0 returns every
    value unchanged, so the tests always see the same scenarios."""

    def __init__(self, draw: int = 0):
        self.draw = draw
        self.rng = np.random.default_rng(10007 * draw + 1) if draw else None

    def scale(self, value, rel):
        """value times a random factor within 1 +- rel."""
        return value if not self.draw else value * float(self.rng.uniform(1 - rel, 1 + rel))

    def shift(self, value, by):
        """value plus a random amount within +- by (each element, for a tuple)."""
        if not self.draw:
            return value
        if isinstance(value, tuple):
            return tuple(v + float(self.rng.uniform(-by, by)) for v in value)
        return value + float(self.rng.uniform(-by, by))

    def int(self, value, by):
        return value if not self.draw else max(1, int(value + self.rng.integers(-by, by + 1)))

    def seed(self, value):
        """A seed for the draw's own dirt, noise and shapes."""
        return value + 7919 * self.draw


# -------------------------------------------------------------------------------------------------
# Backgrounds
def bg_white(rng):
    return np.full((H, W, 3), 255, np.uint8)


def bg_paper(rng):
    """Off-white with a slow shading, like a wall in room light."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    shade = 232 + 14 * np.sin(x / 190.0) + 10 * np.cos(y / 130.0)
    img = np.dstack([shade - 4, shade, shade + 3])
    return np.clip(img, 0, 255).astype(np.uint8)


def bg_noise(rng):
    """Fixed random grey pixels: texture at every scale, nothing smooth to lock onto."""
    grey = np.clip(rng.normal(128, 55, (H, W)), 0, 255).astype(np.uint8)
    return cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)


def _blobs(rng, scales):
    field_ = np.zeros((H, W), np.float32)
    for size, weight in scales:
        small = rng.random((H // size + 3, W // size + 3)).astype(np.float32)
        field_ += weight * cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
    lo, hi = field_.min(), field_.max()
    return (field_ - lo) / (hi - lo)


CAMO = np.array([(52, 84, 66), (36, 58, 40), (104, 140, 150), (46, 66, 92), (84, 112, 92)], np.uint8)


def bg_camo(rng):
    """Blobs of green, brown and tan, as on camouflage cloth."""
    f = _blobs(rng, [(90, 1.0), (45, 0.6), (22, 0.3)])
    edges = np.quantile(f, np.linspace(0, 1, len(CAMO) + 1)[1:-1])
    return CAMO[np.digitize(f, edges)]


def bg_camo_fine(rng):
    """Camouflage with small blobs, close to the ball's own size."""
    f = _blobs(rng, [(36, 1.0), (18, 0.8), (9, 0.5)])
    edges = np.quantile(f, np.linspace(0, 1, len(CAMO) + 1)[1:-1])
    return CAMO[np.digitize(f, edges)]


# -------------------------------------------------------------------------------------------------
# Things in the scene
def _c(v):
    return (int(round(v[0] * (1 << SHIFT))), int(round(v[1] * (1 << SHIFT))))


def draw_ball(img, x, y, r, body, rim, shine=True):
    """A ball: a body colour, a darker rim, and (if asked) a small bright highlight."""
    cv2.circle(img, _c((x, y)), int(r * (1 << SHIFT)), body, -1, cv2.LINE_AA, SHIFT)
    cv2.circle(img, _c((x, y)), int(r * (1 << SHIFT)), rim, max(1, int(r / 6)), cv2.LINE_AA, SHIFT)
    if shine and r >= 8:
        cv2.circle(img, _c((x - r * 0.35, y - r * 0.35)), int(r * 0.22 * (1 << SHIFT)),
                   (235, 235, 235), -1, cv2.LINE_AA, SHIFT)


@dataclass
class Thing:
    """A foreground object on a straight bouncing path (or standing still: speed 0)."""
    kind: str                    # "circle", "rect", "ellipse", "triangle", "line"
    colour: tuple
    size: float                  # radius, or half the side
    start: tuple
    velocity: tuple = (0.0, 0.0)
    front: bool = False          # drawn over the ball (an occluder) rather than behind it
    ball_like: bool = False      # drawn as a ball (body, rim, highlight)
    rim: tuple = (20, 20, 20)

    def position(self, t):
        pos = []
        for p0, v, limit in ((self.start[0], self.velocity[0], W), (self.start[1], self.velocity[1], H)):
            span = limit - 2 * self.size
            u = (p0 - self.size + v * t) % (2 * span)  # Reflects off the frame's edges
            u = u if u <= span else 2 * span - u
            pos.append(self.size + u)
        return tuple(pos)

    def draw(self, img, t):
        x, y = self.position(t)
        s = self.size
        if self.ball_like:
            draw_ball(img, x, y, s, self.colour, self.rim)
        elif self.kind == "circle":
            cv2.circle(img, _c((x, y)), int(s * (1 << SHIFT)), self.colour, -1, cv2.LINE_AA, SHIFT)
        elif self.kind == "rect":
            cv2.rectangle(img, (int(x - s), int(y - s * 0.7)), (int(x + s), int(y + s * 0.7)),
                          self.colour, -1, cv2.LINE_AA)
        elif self.kind == "ellipse":
            cv2.ellipse(img, (int(x), int(y)), (int(s * 1.4), int(s * 0.8)), 25, 0, 360,
                        self.colour, -1, cv2.LINE_AA)
        elif self.kind == "triangle":
            pts = np.array([(x, y - s), (x - s, y + s * 0.8), (x + s, y + s * 0.8)], np.int32)
            cv2.fillPoly(img, [pts], self.colour, cv2.LINE_AA)
        elif self.kind == "line":
            cv2.line(img, (int(x - 2 * s), int(y)), (int(x + 2 * s), int(y)), self.colour, 3, cv2.LINE_AA)


# Paths: a function from frame index to the ball's centre
def path_lissajous(speed: float, phase=(0.1, 0.35)) -> Callable:
    """A smooth loop over the screen. speed 1 is about 6 px per frame at its fastest."""
    def at(t):
        return (W / 2 + 0.36 * W * np.sin(2 * np.pi * (0.5 * speed * t / N + phase[0])),
                H / 2 + 0.34 * H * np.sin(2 * np.pi * (0.7 * speed * t / N + phase[1])))
    return at


def path_bounce(speed_px: float, start=(120.0, 90.0), angle_deg=33.0, r=10) -> Callable:
    """Constant speed in a straight line, reflecting off the frame's edges."""
    vx, vy = speed_px * np.cos(np.radians(angle_deg)), speed_px * np.sin(np.radians(angle_deg))

    def at(t):
        out = []
        for p0, v, limit in ((start[0], vx, W), (start[1], vy, H)):
            span = limit - 2 * r
            u = (p0 - r + v * t) % (2 * span)
            u = u if u <= span else 2 * span - u
            out.append(r + u)
        return tuple(out)
    return at


def path_drop_and_bounce(x=330.0, top=70.0, floor=410.0) -> Callable:
    """Held still by a hand for 14 frames, then dropped: falls under gravity and bounces on the
    floor, losing energy each time."""
    gravity, restitution, hold = 0.9, 0.78, 14

    def at(t):
        pos, vel = top, 0.0
        for _ in range(max(0, t - hold)):
            vel += gravity
            pos += vel
            if pos >= floor:
                pos = floor - (pos - floor)
                vel = -vel * restitution
        return x, min(pos, floor)
    return at


@dataclass
class Scenario:
    name: str
    tier: str                        # "easy" | "medium" | "hard" | "extreme"
    background: Callable
    path: Callable
    radius: float
    body: tuple
    rim: tuple
    things: list = field(default_factory=list)
    noise: float = 0.0               # Sensor noise (grey levels, standard deviation) added per frame
    flicker: float = 0.0             # Brightness changes between frames (grey levels)
    hand: bool = False               # A hand holds the ball for the first frames, then lets go
    seed: int = 1
    # A scenario the tracker misses its tier's target on today. It is still run and reported, and
    # it must not get worse than the floor; when it starts meeting the target, remove this flag
    known_weak: bool = False
    floor_on_ball: float = 0.85
    max_lost: int = 0

    @property
    def target(self):
        """(max median, max 95th percentile, min on-ball fraction) for this scenario's tier."""
        return TARGETS[self.tier]

    def __post_init__(self):
        self._bg = self.background(np.random.default_rng(self.seed))
        self._rng_noise = np.random.default_rng(self.seed + 1000)

    def truth(self, t):
        return self.path(t)

    def frame(self, t):
        img = self._bg.copy()
        for thing in self.things:
            if not thing.front:
                thing.draw(img, t)
        x, y = self.truth(t)
        if self.hand and t < 30:
            self._draw_hand(img, x, y, t)
        draw_ball(img, x, y, self.radius, self.body, self.rim)
        if self.hand and t < 30:
            self._draw_fingers(img, x, y, t)
        for thing in self.things:
            if thing.front:
                thing.draw(img, t)
        if self.flicker:
            img = np.clip(img.astype(np.float32) + self._rng_noise.uniform(-self.flicker, self.flicker),
                          0, 255).astype(np.uint8)
        if self.noise:
            img = np.clip(img.astype(np.float32) + self._rng_noise.normal(0, self.noise, img.shape),
                          0, 255).astype(np.uint8)
        return img

    # A hand: a skin-coloured shape beside and behind the ball that leaves to the right after the
    # release (frame 14), plus fingers over the ball's upper side while it is held
    def _draw_hand(self, img, x, y, t):
        shift = 0 if t < 14 else 9 * (t - 14)
        cv2.ellipse(img, (int(x + 34 + shift), int(y - 6)), (46, 30), -10, 0, 360, (120, 150, 215), -1,
                    cv2.LINE_AA)

    def _draw_fingers(self, img, x, y, t):
        if t < 14:
            cv2.ellipse(img, (int(x + 10), int(y - self.radius - 2)), (16, 6), 10, 0, 360,
                        (110, 140, 205), -1, cv2.LINE_AA)


# What each tier must reach: (median error, 95th percentile error, fraction of frames on the ball)
TARGETS = {"easy": (1.5, 4.0, 0.99), "medium": (2.0, 5.0, 0.98), "hard": (2.5, 6.0, 0.98),
           "extreme": (3.0, 8.0, 0.95)}


# -------------------------------------------------------------------------------------------------
# The scenarios, from easy to hard
RED = ((40, 40, 205), (20, 20, 120))          # body, rim
DARK = ((60, 55, 50), (20, 20, 20))
GREEN_CAMO = ((70, 110, 80), (25, 40, 30))    # a ball whose body is in the camouflage palette


def _decoys(n, colour, rim, size, rng, front=False, speed=3.0):
    out = []
    for _ in range(n):
        ang = rng.uniform(0, 2 * np.pi)
        out.append(Thing("circle", colour, size, (rng.uniform(60, W - 60), rng.uniform(60, H - 60)),
                         (speed * np.cos(ang), speed * np.sin(ang)), front=front, ball_like=True, rim=rim))
    return out


def _shapes(rng, n, speed, colours, front=False, size=(14, 26)):
    kinds = ["rect", "ellipse", "triangle", "circle", "line"]
    out = []
    for i in range(n):
        ang = rng.uniform(0, 2 * np.pi)
        out.append(Thing(kinds[i % len(kinds)], colours[i % len(colours)], rng.uniform(*size),
                         (rng.uniform(80, W - 80), rng.uniform(80, H - 80)),
                         (speed * np.cos(ang), speed * np.sin(ang)), front=front))
    return out


def build_scenarios(draw: int = 0) -> list:
    """The scenarios; `draw` above 0 gives a random variation of each (see Jitter)."""
    j = Jitter(draw)
    r = np.random.default_rng(j.seed(7))
    bright = [(60, 160, 40), (200, 90, 30), (30, 190, 230), (150, 40, 150)]

    def liss(speed):
        return path_lissajous(j.scale(speed, 0.2), phase=j.shift((0.1, 0.35), 0.2))

    def bounce(speed, rad):
        return path_bounce(j.scale(speed, 0.2), start=j.shift((120.0, 90.0), 40),
                           angle_deg=j.shift(33.0, 15), r=rad)

    def size(v):
        return j.scale(v, 0.15)

    seed, noise = j.seed(1), (lambda v: j.scale(v, 0.3))
    return [
        Scenario("white, clean", "easy", bg_white, liss(1.0), size(14), *RED, seed=seed),
        Scenario("white, small and fast", "easy", bg_white, bounce(9, 7), size(7), *RED, seed=seed),
        Scenario("white, still shapes", "easy", bg_white, liss(1.0), size(13), *RED,
                 things=_shapes(r, 5, 0.0, bright), seed=seed),
        Scenario("paper wall, moving shapes", "medium", bg_paper, liss(1.2), size(12), *RED,
                 things=_shapes(r, 5, 2.5, bright), noise=noise(2.0), seed=seed),
        Scenario("paper wall, look-alike ball", "medium", bg_paper, liss(1.2), size(12), *RED,
                 things=_decoys(2, RED[0], RED[1], 9, r, speed=2.5) + _shapes(r, 3, 2.0, bright),
                 noise=noise(2.0), seed=seed),
        Scenario("noise background", "hard", bg_noise, liss(1.0), size(13), *DARK,
                 things=_shapes(r, 4, 2.5, bright), noise=noise(3.0), seed=seed),
        Scenario("camouflage background", "hard", bg_camo, liss(1.0), size(14), *GREEN_CAMO,
                 things=_shapes(r, 4, 2.5, [(60, 90, 70), (110, 150, 170), (40, 60, 40)]),
                 noise=noise(2.0), seed=seed),
        Scenario("camouflage, fine pattern, look-alikes", "extreme", bg_camo_fine, liss(1.2), size(12),
                 *GREEN_CAMO,
                 things=_decoys(3, GREEN_CAMO[0], GREEN_CAMO[1], 12, r, speed=3.0),
                 noise=noise(3.0), flicker=4.0, seed=seed),
        Scenario("camouflage, fast, occluders", "extreme", bg_camo, bounce(13, 12), size(12), *GREEN_CAMO,
                 things=_decoys(2, GREEN_CAMO[0], GREEN_CAMO[1], 11, r, speed=3.0)
                 + _shapes(r, 3, 4.0, [(40, 60, 40), (104, 140, 150)], front=True, size=(20, 30)),
                 noise=noise(3.0), known_weak=True, seed=seed),
        Scenario("dropped by a hand", "hard", bg_paper,
                 path_drop_and_bounce(x=j.shift(330.0, 120), top=j.shift(70.0, 20)), size(6), *DARK,
                 hand=True, noise=noise(2.0), known_weak=True, seed=seed),
    ]


# -------------------------------------------------------------------------------------------------
@dataclass
class Result:
    median: float
    p95: float
    on_ball: float
    lost: int
    worst: float
    first_miss: int | None


@dataclass
class Trace:
    """Everything a run produced, per frame (frame 0 is the selection the tracker started from)."""
    truth: np.ndarray    # (N, 2) true centre
    box: np.ndarray      # (N, 4) tracker's box as x, y, w, h
    centre: np.ndarray   # (N, 2) tracker's centre (the last known one when it reports being lost)
    error: np.ndarray    # (N,) distance between the two centres, in pixels
    lost: np.ndarray     # (N,) True where the tracker reported that it lost the object
    ms_per_frame: float = 0.0  # The tracker's own time per frame


ENGINES = ("nanotrack", "vittrack", "trackpy")
ENGINE = os.environ.get("PHYSTRACK_TRACKER", "nanotrack")  # The engine the tests score


def make_tracker(engine: str, settings=None):
    if engine == "trackpy":
        return BlobTracker(settings)
    return MLTracker(engine)


def trace(scn: Scenario, engine: str = None, settings=None) -> Trace:
    """Selects the ball on frame 0 with its circle's bounding square, then tracks it. Times only
    the tracker's own work (drawing the frames is not counted). `settings` are the blob tracker's."""
    tracker = make_tracker(engine or ENGINE, settings)
    x0, y0 = scn.truth(0)
    r = int(round(scn.radius))
    selection = PixelRect(int(round(x0)) - r, int(round(y0)) - r, 2 * r, 2 * r)
    tracker.initialize_tracker(scn.frame(0), selection)
    truth = np.array([scn.truth(t) for t in range(N)], float)
    box = np.zeros((N, 4))
    centre = np.zeros((N, 2))
    lost = np.zeros(N, bool)
    box[0] = (selection.xmin, selection.ymin, selection.width, selection.height)
    centre[0] = (x0, y0)
    spent = 0.0
    for t in range(1, N):
        frame = scn.frame(t)
        start = time.perf_counter()
        ok, found = tracker.update_tracker(frame)
        spent += time.perf_counter() - start
        if ok:
            box[t] = (found.xmin, found.ymin, found.width, found.height)
            # A sub-pixel centre when the tracker has one; otherwise the box's centre
            centre[t] = getattr(tracker, "centre", None) or (box[t, :2] + box[t, 2:] / 2)
        else:
            box[t], centre[t] = box[t - 1], centre[t - 1]
            lost[t] = True
    error = np.hypot(*(centre - truth).T)
    return Trace(truth, box, centre, error, lost, 1000.0 * spent / (N - 1))


def score(scn: Scenario, tr: Trace) -> Result:
    e = tr.error[1:]
    misses = np.nonzero(e > scn.radius)[0]
    return Result(float(np.median(e)), float(np.percentile(e, 95)), float((e <= scn.radius).mean()),
                  int(tr.lost.sum()), float(e.max()), int(misses[0]) + 1 if len(misses) else None)


def run(scn: Scenario) -> Result:
    return score(scn, trace(scn))


def _line(scn: Scenario, res: Result) -> str:
    miss = "-" if res.first_miss is None else str(res.first_miss)
    return (f"  [{scn.tier:7}] {scn.name:42} median {res.median:5.2f}  p95 {res.p95:6.2f}  "
            f"on-ball {res.on_ball:4.0%}  lost {res.lost:3}  worst {res.worst:6.1f}  first miss {miss}")


def test_scenarios():
    h.say("\n  Scenario scores (errors in pixels; the ball's radius is the 'on-ball' limit)")
    for scn in build_scenarios():
        res = run(scn)
        h.say(_line(scn, res))
        max_median, max_p95, min_on_ball = scn.target
        meets = (res.median <= max_median and res.p95 <= max_p95 and res.on_ball >= min_on_ball
                 and res.lost <= scn.max_lost)
        if scn.known_weak:
            h.say(f"      known weakness: " + (
                "it now meets its target, so remove known_weak from the scenario" if meets else
                f"below target (median <= {max_median}, p95 <= {max_p95}, on-ball >= {min_on_ball:.0%})"))
            h.check(f"{scn.name}: still tracks the ball on at least {scn.floor_on_ball:.0%} of frames "
                    f"(its floor)", res.on_ball >= scn.floor_on_ball,
                    f"{res.on_ball:.0%}, first miss at frame {res.first_miss}")
            continue
        h.check(f"{scn.name}: median error under {max_median} px", res.median <= max_median,
                f"median {res.median:.2f}")
        h.check(f"{scn.name}: 95% of frames under {max_p95} px", res.p95 <= max_p95, f"p95 {res.p95:.2f}")
        h.check(f"{scn.name}: on the ball on at least {min_on_ball:.0%} of frames",
                res.on_ball >= min_on_ball, f"{res.on_ball:.0%}, first miss at frame {res.first_miss}")
        h.check(f"{scn.name}: lost on at most {scn.max_lost} frames", res.lost <= scn.max_lost,
                f"lost {res.lost}")


if __name__ == "__main__":
    h.run_tests([test_scenarios])
