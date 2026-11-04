"""Muddied footage and covered balls: the scenarios the clean benchmark does not reach.

test_tracker_scenarios shows the tracker on clean, synthetic footage. Real footage is dirtier: a
smeared lens, water drops on it, glare, a glass tube that bends and reflects what is behind it,
heavy video compression, a ball that is a small shiny sphere, and things that pass in front of it.
These scenarios build that, from the setup of the real experiment (a ball released by a hand into
a glass tube, with a clamp stand and a ruler beside it), and from other simpler sets.

Every ball starts at rest: it is held still for the first frames, the tracker is given the circle
selection on frame 0, and the ball is then released and speeds up smoothly. The camera is fixed.

Covers pass in front of the ball for a short time, partly or fully. Scores are taken on the frames
where the ball can be seen (less than half of it hidden), and then, for each time it was hidden, how
many frames the tracker needs to be back on the ball afterwards (and stay on it for five frames).

THESE ARE EXPECTED TO FAIL TODAY. They say what good would look like for dirty and covered
footage; the failures are the list of what to work on. No window is needed.
"""

import os
from dataclasses import dataclass, field
from typing import Callable

import cv2
import numpy as np

from tests import harness as h
h.setup_env()

from tests.test_tracker_scenarios import (  # noqa: E402
    N, W, H, Jitter, Thing, bg_paper, bg_white, draw_ball, path_bounce, path_lissajous, trace)

HAND = (26, 26, 30)    # A black sleeve and glove, as in the real footage
RECOVERY_LIMIT = 6   # Frames the tracker may take to be back on the ball after it is uncovered
STAY = 5             # ...and it must then stay on the ball this many frames


# -------------------------------------------------------------------------------------------------
# Motion that starts from rest
def from_rest(path: Callable, hold: int = 20, ramp: int = 15) -> Callable:
    """The ball sits still for `hold` frames, then speeds up smoothly over `ramp` frames to the
    path's own speed. (Time runs at zero speed, then at a growing rate, then at the path's rate.)"""
    def at(t):
        s = t - hold
        if s <= 0:
            tau = 0.0
        elif s < ramp:
            tau = s * s / (2.0 * ramp)
        else:
            tau = s - ramp / 2.0
        return path(tau)
    return at


def path_tube_drop(x=320.0, top=70.0, rest=240.0, period=70.0, decay=0.018) -> Callable:
    """Released at the top of a tube, falls past the rest point and oscillates to a stop, as a ball
    in a viscous liquid does. About 15 px per frame at its fastest."""
    w = 2 * np.pi / period

    def at(s):
        return (x + 1.2 * np.sin(0.23 * s),
                rest - (rest - top) * np.exp(-decay * s) * np.cos(w * s))
    return at


# -------------------------------------------------------------------------------------------------
# A polished steel ball
_chrome_cache: dict = {}


def _chrome_sprite(r: float):
    """A polished steel sphere, as a premultiplied BGR image and an alpha map (both S x S, the ball
    centred in them): it mirrors a bright sky above a dark horizon, has a window's hot spot and a
    sharp highlight, and is dark toward its edge, as a chrome ball bearing looks in a lit room."""
    key = round(float(r), 2)
    if key in _chrome_cache:
        return _chrome_cache[key]
    ss = 8                                       # Drawn at 8x and averaged down, for clean edges
    size = int(2 * np.ceil(r)) + 4
    n = size * ss
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    c, radius = (n - 1) / 2, r * ss
    u, v = (xs - c) / radius, (ys - c) / radius            # v points down the image
    d2 = u * u + v * v
    inside = (d2 <= 1.0).astype(np.float32)
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    rx, ry, rz = 2 * nz * u, 2 * nz * v, 2 * nz * nz - 1   # The mirrored view direction
    up = -ry
    env = 0.20 + 0.66 * np.clip((up + 0.25) / 0.7, 0, 1)   # Bright above the horizon, dark below
    env += 0.32 * np.exp(-((rx + 0.55) ** 2 + (up - 0.55) ** 2 + (rz - 0.62) ** 2) / 0.05)  # A window
    env += 0.16 * np.exp(-((up + 0.85) ** 2) / 0.04)       # Light bounced from below
    val = np.clip(env * (0.28 + 0.72 * nz ** 0.55), 0, 1)  # Darker toward the edge
    light = np.array([-0.40, -0.50, 0.77], np.float32)
    half = light + np.array([0, 0, 1], np.float32)
    half /= np.linalg.norm(half)
    spec = np.clip(u * half[0] + v * half[1] + nz * half[2], 0, 1) ** 90
    val = np.clip(val + 0.9 * spec, 0, 1)
    bgr = np.dstack([val * 1.0, val * 0.985, val * 0.96]) * 255.0
    premult = cv2.resize(bgr * inside[..., None], (size, size), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(inside, (size, size), interpolation=cv2.INTER_AREA)
    _chrome_cache[key] = (premult.astype(np.float32), alpha.astype(np.float32))
    return _chrome_cache[key]


def draw_chrome(img, x: float, y: float, r: float) -> None:
    """Draws the steel ball with its centre at (x, y), placed to a fraction of a pixel."""
    sprite, alpha = _chrome_sprite(r)
    size = alpha.shape[0]
    tx, ty = x - (size - 1) / 2.0, y - (size - 1) / 2.0
    ix, iy = int(np.floor(tx)), int(np.floor(ty))
    shift = np.float32([[1, 0, tx - ix], [0, 1, ty - iy]])
    sp = cv2.warpAffine(sprite, shift, (size, size), flags=cv2.INTER_LINEAR)
    al = cv2.warpAffine(alpha, shift, (size, size), flags=cv2.INTER_LINEAR)
    x0, y0, x1, y1 = max(ix, 0), max(iy, 0), min(ix + size, img.shape[1]), min(iy + size, img.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    sp, al = sp[y0 - iy:y1 - iy, x0 - ix:x1 - ix], al[y0 - iy:y1 - iy, x0 - ix:x1 - ix]
    roi = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = np.clip(roi * (1 - al[..., None]) + sp, 0, 255).astype(np.uint8)


# -------------------------------------------------------------------------------------------------
# A glass tube in a lab: clamp stand, ruler, tape, stopper
def bg_tube(rng):
    img = bg_paper(rng).astype(np.float32)
    # Things on the wall: a clamp stand's pole, a wooden ruler with marks, tape, a stopper
    img[:, 112:128] = (58, 58, 64)
    img[:, 116:119] = (150, 150, 158)
    img[:, 496:526] = (116, 156, 186)
    for y in range(0, H, 12):
        img[y:y + 2, 496:512 if (y // 12) % 5 else 520] = (40, 50, 60)
    for x, y, w, hh, col in ((430, 90, 44, 14, (190, 90, 30)), (60, 300, 36, 12, (190, 90, 30)),
                             (190, 40, 50, 10, (230, 230, 232))):
        img[y:y + hh, x:x + w] = col
    img[408:480, 236:404] = (44, 44, 50)
    img[404:412, 250:390] = (176, 176, 182)
    # The tube: what is behind it is seen flipped and softened, with dark edges and bright streaks
    x0, x1 = 270, 370
    inside = cv2.GaussianBlur(img[:, x0:x1][:, ::-1].copy(), (0, 0), 2.2)
    inside = inside * 0.78 + np.array((236, 228, 220), np.float32) * 0.22
    img[:, x0:x1] = inside
    img[:, x0:x0 + 4] = (52, 52, 56)
    img[:, x1 - 5:x1] = (52, 52, 56)
    fade = np.linspace(1.0, 0.45, H, dtype=np.float32)[:, None]
    for xa, xb, strength in ((x0 + 9, x0 + 17, 0.85), (x1 - 22, x1 - 18, 0.5), (x0 + 24, x0 + 26, 0.3)):
        img[:, xa:xb] = img[:, xa:xb] * (1 - strength * fade[..., None]) + 252 * strength * fade[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


# -------------------------------------------------------------------------------------------------
# A dirty camera
class Lens:
    """What sits on the lens and in the light path, the same on every frame (the camera is fixed)."""

    def __init__(self, seed: int, smudges=0, specks=0, droplets=0, glare=False, vignette=0.0,
                 defocus=0.0, jpeg=None, smears=0, scratches=0, fog=0.0):
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        # Grease: soft patches that blur and veil what is behind them
        alpha = np.zeros((H, W), np.float32)
        for _ in range(smudges):
            cx, cy = rng.uniform(0, W), rng.uniform(0, H)
            rx, ry, ang = rng.uniform(40, 120), rng.uniform(30, 90), rng.uniform(0, np.pi)
            c, s = np.cos(ang), np.sin(ang)
            u, v = ((xx - cx) * c + (yy - cy) * s) / rx, (-(xx - cx) * s + (yy - cy) * c) / ry
            alpha = np.maximum(alpha, np.clip(1 - (u * u + v * v), 0, 1) ** 1.5 * rng.uniform(0.5, 0.95))
        for _ in range(smears):  # Finger-wide streaks of grease
            cx, cy = rng.uniform(0, W), rng.uniform(0, H)
            rx, ry, ang = rng.uniform(80, 170), rng.uniform(8, 20), rng.uniform(0, np.pi)
            c, s = np.cos(ang), np.sin(ang)
            u, v = ((xx - cx) * c + (yy - cy) * s) / rx, (-(xx - cx) * s + (yy - cy) * c) / ry
            alpha = np.maximum(alpha, np.clip(1 - (u * u + v * v), 0, 1) ** 0.8 * rng.uniform(0.6, 0.95))
        self.smudge = cv2.GaussianBlur(alpha, (0, 0), 6)[..., None] if (smudges or smears) else None
        # Fine scratches, which catch the light
        scr = np.zeros((H, W), np.float32)
        for _ in range(scratches):
            x0, y0, ang, length = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0, np.pi), rng.uniform(60, 240)
            cv2.line(scr, (int(x0), int(y0)), (int(x0 + length * np.cos(ang)), int(y0 + length * np.sin(ang))),
                     float(rng.uniform(0.25, 0.7)), 1, cv2.LINE_AA)
        self.scratch = cv2.GaussianBlur(scr, (0, 0), 0.7)[..., None] if scratches else None
        self.fog = fog  # Condensation or a film on the glass: the whole picture loses contrast
        # Dust and dirt: dark specks, out of focus
        sp = np.zeros((H, W), np.float32)
        for _ in range(specks):
            cv2.circle(sp, (int(rng.uniform(0, W)), int(rng.uniform(0, H))), int(rng.integers(1, 5)),
                       float(rng.uniform(0.3, 0.9)), -1, cv2.LINE_AA)
        self.speck = cv2.GaussianBlur(sp, (0, 0), 1.2)[..., None] if specks else None
        # Water drops: each shows a wide, inverted view of what is behind it, with a dark rim
        self.mx, self.my = xx.copy(), yy.copy()
        ring = np.zeros((H, W), np.float32)
        for _ in range(droplets):
            cx, cy, r = rng.uniform(40, W - 40), rng.uniform(40, H - 40), rng.uniform(16, 34)
            dx, dy = xx - cx, yy - cy
            d = np.hypot(dx, dy)
            inside = d < r
            self.mx = np.where(inside, cx - dx * 2.2, self.mx)
            self.my = np.where(inside, cy - dy * 2.2, self.my)
            ring = np.maximum(ring, np.clip(1 - np.abs(d - r * 0.92) / 3.0, 0, 1) * 0.7)
        self.mx, self.my = self.mx.astype(np.float32), self.my.astype(np.float32)
        self.ring = cv2.GaussianBlur(ring, (0, 0), 1.0)[..., None] if droplets else None
        # A light behind or beside the scene: a bright haze from the corner and a streak
        self.glare = None
        if glare:
            corner = np.exp(-(((xx - W * 0.85) ** 2 + (yy - H * 0.1) ** 2) / (2 * (W * 0.28) ** 2))) * 0.55
            streak = np.exp(-(((xx + yy * 0.6) - W * 0.9) ** 2) / (2 * 22.0 ** 2)) * 0.18
            self.glare = ((corner + streak) * 255)[..., None].astype(np.float32)
        self.vig = None
        if vignette:
            r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
            self.vig = np.clip(1 - vignette * r2 / 2, 0, 1)[..., None].astype(np.float32)
        self.defocus, self.jpeg = defocus, jpeg

    def apply(self, img):
        out = img.astype(np.float32)
        if self.ring is not None:
            out = cv2.remap(out, self.mx, self.my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            out = out * (1 - self.ring)
        if self.smudge is not None:
            veil = cv2.GaussianBlur(out, (0, 0), 7) * 0.65 + 205 * 0.35
            out = out * (1 - self.smudge) + veil * self.smudge
        if self.speck is not None:
            out = out * (1 - 0.6 * self.speck)
        if self.scratch is not None:
            out = out + self.scratch * 110
        if self.glare is not None:
            out = out + self.glare
        if self.fog:
            out = out * (1 - self.fog) + 190 * self.fog
        if self.vig is not None:
            out = out * self.vig
        if self.defocus:
            out = cv2.GaussianBlur(out, (0, 0), self.defocus)
        return np.clip(out, 0, 255).astype(np.uint8)


# -------------------------------------------------------------------------------------------------
# Things that pass in front of the ball
@dataclass
class Cover:
    """An object that passes in front of the ball. Anchored to the ball's path: its centre is on
    the ball's position at `cross_t` (plus `lateral` across its direction of travel), and it moves
    in a straight line from there. With `relative` (the default) `velocity` is how fast it moves
    relative to the ball at the crossing, so how long it covers the ball is set by the scenario
    and does not depend on where the ball is going. With `fixed`, it stays at that place instead
    (a clamp arm the ball falls past)."""
    kind: str                       # "rect", "bar", "arm", "blob", "ball"
    size: float
    colour: tuple
    cross_t: float = 0.0
    velocity: tuple = (0.0, 0.0)
    lateral: float = 0.0
    fixed: tuple | None = None
    relative: bool = True
    rim: tuple = (20, 20, 20)

    def position(self, truth, t):
        vx, vy = self.velocity
        if self.fixed is not None:
            return self.fixed[0] + vx * t, self.fixed[1] + vy * t
        px, py = truth(self.cross_t)
        if self.relative:  # Add the ball's own velocity at the crossing
            (ax, ay), (bx, by) = truth(self.cross_t - 0.5), truth(self.cross_t + 0.5)
            vx, vy = vx + (bx - ax), vy + (by - ay)
        rx, ry = self.velocity  # The sideways offset is across the direction it moves relative to the ball
        speed = float(np.hypot(rx, ry)) or 1.0
        nx, ny = -ry / speed, rx / speed
        return (px + nx * self.lateral + vx * (t - self.cross_t),
                py + ny * self.lateral + vy * (t - self.cross_t))

    def draw(self, img, x, y, flat=False):
        s, col = self.size, (255, 255, 255) if flat else self.colour
        if self.kind == "rect":
            cv2.rectangle(img, (int(x - s), int(y - 0.8 * s)), (int(x + s), int(y + 0.8 * s)), col, -1, cv2.LINE_AA)
        elif self.kind == "bar":
            cv2.rectangle(img, (int(x - s), int(y - 150)), (int(x + s), int(y + 150)), col, -1, cv2.LINE_AA)
        elif self.kind == "arm":
            cv2.rectangle(img, (int(x - 90), int(y - s)), (int(x + 90), int(y + s)), col, -1, cv2.LINE_AA)
        elif self.kind == "blob":
            cv2.ellipse(img, (int(x), int(y)), (int(s * 1.3), int(s * 0.9)), 20, 0, 360, col, -1, cv2.LINE_AA)
        elif self.kind == "ball":
            if flat:
                cv2.circle(img, (int(round(x)), int(round(y))), int(round(s)), col, -1, cv2.LINE_AA)
            else:
                draw_chrome(img, x, y, s)


# -------------------------------------------------------------------------------------------------
@dataclass
class Rough:
    name: str
    tier: str                        # "muddy" | "occluded"
    background: Callable
    path: Callable
    radius: float
    body: tuple
    rim: tuple
    blurb: str = ""
    hold: int = 20                   # Frames the ball is held still before its release
    hand: bool = False               # A hand holds it, then lets go
    things: list = field(default_factory=list)
    covers: list = field(default_factory=list)
    lens: Lens | None = None
    blur: int = 1                    # Motion blur: positions averaged over the frame's exposure
    noise: float = 0.0
    flicker: float = 0.0
    jpeg: int | None = None          # Video compression quality (lower is worse)
    seed: int = 1
    chrome: bool = True              # A polished steel ball (otherwise a plain coloured one)
    known_weak: bool = False         # Not used here; kept so reports can treat all scenarios alike
    backdrop: Callable | None = None  # A moving background: frame t -> picture (instead of `background`)

    def __post_init__(self):
        self._bg = self.background(np.random.default_rng(self.seed))
        self._cover_cache = {}

    @property
    def target(self):
        """(max median, max 95th percentile, min on-ball fraction, max recovery frames)."""
        return TARGETS[self.tier]

    def truth(self, t):
        return self.path(t)

    def _ball(self, img, x, y):
        if self.chrome:
            draw_chrome(img, x, y, self.radius)
        else:
            draw_ball(img, x, y, self.radius, self.body, self.rim, shine=self.radius >= 5)

    def frame(self, t):
        rng = np.random.default_rng(self.seed * 100003 + int(t))
        img = (self.backdrop(t) if self.backdrop is not None else self._bg).copy()
        for thing in self.things:
            if not thing.front:
                thing.draw(img, t)
        x, y = self.truth(t)
        if self.hand and t < self.hold + 14:
            shift = 0 if t < self.hold else 11 * (t - self.hold)
            cv2.ellipse(img, (int(x + 30 + shift), int(y - 4)), (46, 30), -10, 0, 360, HAND, -1, cv2.LINE_AA)
            cv2.ellipse(img, (int(x + 30 + shift), int(y - 12)), (30, 8), -10, 0, 360, (44, 44, 50), -1, cv2.LINE_AA)
        if self.blur > 1:  # A fast ball is smeared along its path during the exposure
            acc = np.zeros(img.shape, np.float32)
            for dt in np.linspace(-0.5, 0.5, self.blur):
                layer = img.copy()
                bx, by = self.truth(t + dt)
                self._ball(layer, bx, by)
                acc += layer
            img = (acc / self.blur).astype(np.uint8)
        else:
            self._ball(img, x, y)
        if self.hand and t < self.hold:  # Fingers over the ball's upper side while it is held
            cv2.ellipse(img, (int(x + 9), int(y - self.radius - 2)), (17, 6), 10, 0, 360,
                        (22, 22, 26), -1, cv2.LINE_AA)
        for c in self.covers:
            c.draw(img, *c.position(self.truth, t))
        for thing in self.things:
            if thing.front:
                thing.draw(img, t)
        if self.lens is not None:
            img = self.lens.apply(img)
        out = img.astype(np.float32)
        if self.flicker:
            out += rng.uniform(-self.flicker, self.flicker)
        if self.noise:
            out += rng.normal(0, self.noise, out.shape)
        out = np.clip(out, 0, 255).astype(np.uint8)
        if self.jpeg:
            out = cv2.imdecode(cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg])[1], 1)
        return out

    def cover(self, t) -> float:
        """The fraction of the ball that the covers hide on frame t."""
        if not self.covers:
            return 0.0
        if t not in self._cover_cache:
            x, y = self.truth(t)
            ball = np.zeros((H, W, 3), np.uint8)
            cv2.circle(ball, (int(round(x)), int(round(y))), int(round(self.radius)), (255, 255, 255), -1)
            occ = np.zeros_like(ball)
            for c in self.covers:
                c.draw(occ, *c.position(self.truth, t), flat=True)
            b, o = ball[..., 0] > 0, occ[..., 0] > 127
            self._cover_cache[t] = float((b & o).sum() / max(1, b.sum()))
        return self._cover_cache[t]


# What each tier must reach: (median error, 95th percentile error, fraction of visible frames on
# the ball, frames to recover after a cover), all on the frames where the ball can be seen
TARGETS = {"muddy": (3.0, 8.0, 0.95, RECOVERY_LIMIT), "occluded": (3.0, 8.0, 0.95, RECOVERY_LIMIT)}



def _bubbles(n, rng):
    """Small bright reflections and bubbles that drift in the tube."""
    return [Thing("circle", (214, 214, 220), 3.5, (rng.uniform(285, 355), rng.uniform(80, 400)),
                  (rng.uniform(-0.4, 0.4), rng.uniform(-2.0, 2.0)), ball_like=True, rim=(90, 90, 96))
            for _ in range(n)]


def build_scenarios(draw: int = 0) -> list:
    """The scenarios; `draw` above 0 gives a random variation of each (see Jitter): the ball's size,
    path and release, where the covers cross, the dirt on the lens, noise and compression."""
    j = Jitter(draw)
    rng = np.random.default_rng(j.seed(11))
    tube_drop = from_rest(path_tube_drop(x=j.shift(320.0, 25), top=j.shift(70.0, 15), rest=j.shift(240.0, 50),
                                         period=j.scale(70.0, 0.2), decay=j.scale(0.018, 0.3)),
                          hold=j.int(20, 6), ramp=j.int(6, 2))
    # Cover scenarios use a straight path at constant speed once released, so that how long a cover
    # hides the ball is set by the cover's own speed and not by a curving path
    def straight(hold=20, ramp=15):
        return from_rest(path_bounce(j.scale(6.0, 0.2), start=j.shift((110.0, 80.0), 25),
                                     angle_deg=j.shift(33.0, 10), r=10), hold=hold, ramp=ramp)
    slab = (110, 112, 120)
    # How dirty: the same lens in the tube scenarios that say so (a new Lens each, same dirt)
    greasy = dict(smudges=5, smears=4, specks=70, fog=0.10, defocus=1.4)
    filthy = dict(smudges=7, smears=5, specks=130, droplets=8, scratches=14, fog=0.30, glare=True,
                  vignette=0.6, defocus=2.0)
    tube = dict(background=bg_tube, path=tube_drop, hand=True, blur=5, seed=j.seed(1))
    wall = dict(background=bg_paper, path=straight(), seed=j.seed(1))
    lens, size, q = (lambda k, **kw: Lens(j.seed(k), **kw)), (lambda v: j.scale(v, 0.15)), (lambda v: j.int(v, 8))
    noise = lambda v: j.scale(v, 0.3)
    cross = lambda t: j.shift(t, 4)
    return [
        # --- muddied footage: a steel ball released by a black-gloved hand into a glass tube ---
        Rough(name="glass tube, clean lens", tier="muddy", radius=size(7), body=(0,) * 3, rim=(0,) * 3,
              blurb="A small polished steel ball held by a black-gloved hand at the top of a glass tube, then released. The tube bends and reflects what is behind it, with a clamp stand and a ruler beside it. The lens is clean.",
              noise=noise(2.0), jpeg=q(60), **tube),
        Rough(name="white wall, silver ball, dirty lens", tier="muddy", background=bg_white,
              path=from_rest(path_lissajous(j.scale(1.2, 0.2), phase=j.shift((0.1, 0.35), 0.2)), hold=j.int(20, 6), ramp=15),
              radius=size(8), body=(0,) * 3, rim=(0,) * 3, seed=j.seed(1),
              blurb="A steel ball on a white wall (so its edge is bright against the wall) through a greasy, dusty lens.",
              lens=lens(21, **greasy), blur=3, noise=noise(4.0), jpeg=q(35)),
        Rough(name="glass tube, greasy lens", tier="muddy", radius=size(7), body=(0,) * 3, rim=(0,) * 3,
              blurb="The same tube through a lens with grease smears, finger streaks, dust and a little fog.",
              lens=lens(22, **greasy), noise=noise(3.0), jpeg=q(35), **tube),
        Rough(name="glass tube, water drops and dust", tier="muddy", radius=size(7), body=(0,) * 3, rim=(0,) * 3,
              blurb="Nine water drops on the lens bend the picture into small inverted circles, and the ball falls behind some of them. Dust everywhere.",
              lens=lens(23, smudges=2, specks=120, droplets=9, defocus=1.2), noise=noise(3.0), jpeg=q(35), **tube),
        Rough(name="glass tube, glare, fog and scratches", tier="muddy", radius=size(7), body=(0,) * 3, rim=(0,) * 3,
              blurb="A bright light beside the scene washes out one corner, fog on the glass cuts the contrast, and scratches catch the light. Heavy compression and exposure flicker.",
              lens=lens(24, smudges=3, scratches=16, glare=True, vignette=0.6, fog=0.30, defocus=1.4),
              noise=noise(5.0), flicker=10.0, jpeg=q(22), **tube),
        Rough(name="glass tube, filthy lens", tier="muddy", radius=size(7), body=(0,) * 3, rim=(0,) * 3,
              blurb="Everything at once: grease and finger streaks, dust, water drops, scratches, fog, glare, defocus, heavy compression, noise and flicker, with bubbles drifting in the tube.",
              lens=lens(25, **filthy), things=_bubbles(5, rng), noise=noise(6.0), flicker=10.0, jpeg=q(20), **tube),
        Rough(name="tiny steel ball, greasy lens", tier="muddy", radius=j.scale(4, 0.1), body=(0,) * 3, rim=(0,) * 3,
              blurb="The ball is only 4 px in radius, as it is when the camera is far from the tube, behind a greasy lens.",
              lens=lens(27, **greasy), noise=noise(4.0), jpeg=q(30), **tube),
        Rough(name="tiny steel ball, filthy lens", tier="muddy", radius=j.scale(4, 0.1), body=(0,) * 3, rim=(0,) * 3,
              blurb="A 4 px steel ball behind the filthy lens, with bubbles of about its size: the hardest footage here.",
              lens=lens(29, **filthy), things=_bubbles(6, rng), noise=noise(6.0), flicker=10.0, jpeg=q(20), **tube),
        # --- covered balls: a steel ball on a wall, through a mildly dirty lens ---
        Rough(name="half covered for a moment", tier="occluded", radius=size(8), body=(0,) * 3, rim=(0,) * 3,
              blurb="A grey slab slides across the ball's path and hides about half of it for several frames.",
              covers=[Cover("rect", 16, slab, cross_t=cross(60), velocity=(j.scale(-4.0, 0.2), 0.0), lateral=j.shift(10, 3))],
              lens=lens(31, specks=40, defocus=0.8), noise=noise(2.0), jpeg=q(55), **wall),
        Rough(name="fully covered, briefly", tier="occluded", radius=size(8), body=(0,) * 3, rim=(0,) * 3,
              blurb="A grey bar passes in front of the ball and hides all of it for a few frames.",
              covers=[Cover("bar", 20, slab, cross_t=cross(62), velocity=(j.scale(-3.0, 0.2), 0.0))],
              lens=lens(32, specks=40, defocus=0.8), noise=noise(2.0), jpeg=q(55), **wall),
        Rough(name="fully covered by a black glove", tier="occluded", radius=size(8), body=(0,) * 3, rim=(0,) * 3,
              blurb="A black glove passes over the ball and hides it for about fifteen frames.",
              covers=[Cover("blob", 30, HAND, cross_t=cross(58), velocity=(j.scale(-4.0, 0.2), j.shift(1.3, 0.8)))],
              lens=lens(33, specks=40, defocus=0.8), noise=noise(2.0), jpeg=q(55), **wall),
        Rough(name="covered while still", tier="occluded", background=bg_paper, path=straight(40, 15),
              radius=size(8), body=(0,) * 3, rim=(0,) * 3, hold=40, seed=j.seed(1),
              blurb="The ball is at rest when a slab slides across it, before it is released.",
              covers=[Cover("rect", 22, slab, cross_t=cross(14), velocity=(j.scale(-5.0, 0.2), 0.0))],
              lens=lens(34, specks=40, defocus=0.8), noise=noise(2.0), jpeg=q(55)),
        Rough(name="a second steel ball rolls over it", tier="occluded", radius=size(8), body=(0,) * 3, rim=(0,) * 3,
              blurb="A second steel ball of the same size rolls across the first and out the other side.",
              covers=[Cover("ball", 8, (255, 255, 255), cross_t=cross(60), velocity=(j.scale(-3.0, 0.2), j.shift(0.4, 0.4)))],
              lens=lens(35, specks=40, defocus=0.8), noise=noise(2.0), jpeg=q(55), **wall),
        Rough(name="falls behind a clamp arm in the tube", tier="occluded", radius=size(7), body=(0,) * 3,
              rim=(0,) * 3, blurb="The ball falls behind a horizontal clamp arm, hidden for a few frames, and comes out the other side.",
              covers=[Cover("arm", 16, (62, 62, 68), fixed=(320.0, j.shift(190.0, 20)))],
              lens=lens(26, smudges=3, specks=50, defocus=1.0), noise=noise(3.0), jpeg=q(45), **tube),
        Rough(name="falls behind a clamp arm, filthy lens", tier="occluded", radius=size(7), body=(0,) * 3,
              rim=(0,) * 3, blurb="The same fall behind the clamp arm, through the filthy lens.",
              covers=[Cover("arm", 16, (62, 62, 68), fixed=(320.0, j.shift(190.0, 20)))],
              lens=lens(25, **filthy), things=_bubbles(5, rng), noise=noise(6.0), flicker=10.0, jpeg=q(20), **tube),
    ]


# -------------------------------------------------------------------------------------------------
# A synthetic ball on real footage: the clutter, the person's arm, the noise and the compression
# are real, and the ball's path is known
REAL_FOOTAGE = os.environ.get("PHYSTRACK_REAL_FOOTAGE", os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Classwork/P440/Specific_heat/Measurements/Air_trials"))


def _real_clip(path: str, start: float, top: int) -> np.ndarray:
    """N frames of a video from `start` seconds, scaled to W wide and cut to H tall from `top`
    (cached in the system temp folder)."""
    import hashlib
    import subprocess
    import tempfile
    from core import find_ffmpeg
    key = hashlib.sha1(f"{path}|{start}|{top}|{W}x{H}x{N}".encode()).hexdigest()[:16]
    cache = os.path.join(tempfile.gettempdir(), "phystrack_real_clips", key + ".npy")
    if os.path.exists(cache):
        return np.load(cache)
    out = subprocess.run([find_ffmpeg(), "-v", "error", "-ss", f"{start:.2f}", "-i", path, "-frames:v", str(N),
                          "-vf", f"scale={W}:-2,crop={W}:{H}:0:{top}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(out, np.uint8).reshape(-1, H, W, 3)
    if len(frames) < N:
        frames = np.concatenate([frames, np.repeat(frames[-1:], N - len(frames), 0)])
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, frames)
    return frames


def build_real_scenarios(count: int = 6, draw: int = 0) -> list:
    """Synthetic steel balls dropped into stretches of the real Air Trial videos (none when the
    footage is not on this machine). Each takes a random trial, start time and part of the frame."""
    if not os.path.isdir(REAL_FOOTAGE):
        return []
    videos = sorted(os.path.join(REAL_FOOTAGE, f) for f in os.listdir(REAL_FOOTAGE)
                    if f.lower().endswith((".mp4", ".mov")) and f.lower().startswith("air trial"))
    if not videos:
        return []
    rng = np.random.default_rng(4242 + 7919 * draw)
    out = []
    for k in range(count):
        video = videos[k % len(videos)]
        start = float(rng.uniform(1.0, 20.0))
        top = int(rng.integers(0, 560 // 2) * 2)          # The scaled portrait frame is about 1138 tall
        frames = _real_clip(video, start, top)
        path = from_rest(path_tube_drop(x=float(rng.uniform(120, 520)), top=float(rng.uniform(50, 110)),
                                        rest=float(rng.uniform(220, 380)), period=float(rng.uniform(50, 90))),
                         hold=int(rng.integers(10, 30)), ramp=int(rng.integers(4, 10)))
        name = f"real background: {os.path.splitext(os.path.basename(video))[0]} at {start:.1f} s"
        out.append(Rough(name=name, tier="muddy", background=bg_white, backdrop=(lambda t, f=frames: f[t]),
                         path=path, radius=float(rng.uniform(4.5, 9.0)), body=(0,) * 3, rim=(0,) * 3,
                         blurb="A synthetic steel ball dropped over a stretch of a real trial video.",
                         blur=int(rng.integers(1, 5)), seed=4242 + k))
    return out


# -------------------------------------------------------------------------------------------------
@dataclass
class Result:
    median: float            # Over the frames where the ball can be seen
    p95: float
    on_ball: float
    lost: int
    worst: float
    first_miss: int | None
    hidden_frames: int       # Frames with at least half of the ball covered
    recovery: float | None   # Worst frames-to-recover after a cover (inf if never); None if no cover


def analyse(scn, tr) -> Result:
    """Scores a trace on the frames where the ball is visible, and the recovery after each cover."""
    cover = np.array([scn.cover(t) if hasattr(scn, "cover") else 0.0 for t in range(N)])
    visible = cover < 0.5
    visible[0] = False
    e = tr.error
    ev = e[visible]
    misses = np.nonzero(visible & (e > scn.radius))[0]
    hidden = ~visible
    hidden[0] = False
    recovery = None
    if hidden.any():
        recovery = 0.0
        runs = np.nonzero(hidden & ~np.append(hidden[1:], False))[0]  # Last frame of each hidden run
        for end in runs:
            k = None
            for start in range(end + 1, N - STAY + 1):
                if (e[start:start + STAY] <= scn.radius).all():
                    k = start - end
                    break
            recovery = max(recovery, float("inf") if k is None else float(k))
    return Result(float(np.median(ev)), float(np.percentile(ev, 95)), float((ev <= scn.radius).mean()),
                  int(tr.lost.sum()), float(ev.max()), int(misses[0]) if len(misses) else None,
                  int(hidden.sum()), recovery)


def meets_target(scn, res: Result) -> bool:
    med, p95, on_ball, rec = scn.target
    return (res.median <= med and res.p95 <= p95 and res.on_ball >= on_ball
            and (res.recovery is None or res.recovery <= rec))


def _line(scn, res: Result) -> str:
    miss = "-" if res.first_miss is None else str(res.first_miss)
    rec = "" if res.recovery is None else (
        f"  hidden {res.hidden_frames:2} fr, back after {'never' if res.recovery == float('inf') else int(res.recovery)}")
    return (f"  [{scn.tier:8}] {scn.name:40} median {res.median:5.2f}  p95 {res.p95:6.2f}  "
            f"on-ball {res.on_ball:4.0%}  lost {res.lost:3}  worst {res.worst:6.1f}  first miss {miss}{rec}")


def test_muddied_and_covered():
    h.say("\n  Scores on the frames where the ball can be seen (errors in pixels)")
    for scn in build_scenarios():
        res = analyse(scn, trace(scn))
        h.say(_line(scn, res))
        med, p95, on_ball, rec = scn.target
        h.check(f"{scn.name}: median error under {med} px", res.median <= med, f"median {res.median:.2f}")
        h.check(f"{scn.name}: 95% of visible frames under {p95} px", res.p95 <= p95, f"p95 {res.p95:.2f}")
        h.check(f"{scn.name}: on the ball on at least {on_ball:.0%} of visible frames",
                res.on_ball >= on_ball, f"{res.on_ball:.0%}, first miss at frame {res.first_miss}")
        if res.recovery is not None:
            h.check(f"{scn.name}: back on the ball within {rec} frames of being uncovered",
                    res.recovery <= rec,
                    "never" if res.recovery == float("inf") else f"{int(res.recovery)} frames")


if __name__ == "__main__":
    h.run_tests([test_muddied_and_covered])
