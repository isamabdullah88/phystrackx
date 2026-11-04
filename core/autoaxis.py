"""
autoaxis.py

Lines a hand-placed axis up with a straight line in the picture: a tube, a track, a table's edge.
The axis is placed roughly along the line; Auto Axis turns it (by up to MAX_TURN degrees) to the
line's direction, and slides the origin a little sideways onto it. The edge must lie within
`search` pixels of the origin. Where the origin lies between two opposite edges (the two walls of a
tube or a bar), the line is the one midway between them, and the other wall may be up to
PAIR_REACH times further out.

How it works: the picture along the axis is cut out as a strip, turned so the axis runs straight
down its middle. Each column's sideways change in colour is summed along every line through the
strip at small slopes: along a straight edge the changes add up, and the picture's texture cancels
out. The strongest sum gives the edge's slope and place; each row's edge is then found to a fraction
of a pixel and a line fitted through them, leaving out the rows that disagree.

Works in image pixels. Rotation is the axes' (Qt's): degrees clockwise on screen, with the x axis
along (cos r, sin r) and the y axis along (sin r, -cos r), so y points up. No GUI here, so it can be
tested on a synthetic picture.
"""

import math

import cv2
import numpy as np

MAX_TURN = 10.0      # Degrees: the line is sought within this much of the axis' direction
TURN_STEP = 0.25     # Degrees between the slopes tried (the fit then refines it)
MIN_EDGE = 1.0       # Lab units per row: weaker sums are texture, not an edge
PAIR_SHARE = 0.4     # An opposite edge at least this strong (of the strongest) makes a pair
MIN_ROWS = 30        # Rows that must agree on an edge for it to count
FIT_TOLERANCE = 1.5  # Pixels: rows further than this from the fitted edge are left out
PEAK_SEARCH = 3      # Pixels either side of the found line that each row's edge is sought in
PAIR_REACH = 3.0     # The opposite wall is sought this many times `search` from the origin


def default_search(image) -> float:
    """How far the origin may slide, and how far from it edges are sought: 3% of the picture's
    smaller side (about 32 px in a 1080p frame), at least 15 px."""
    h, w = np.asarray(image).shape[:2]
    return max(15.0, 0.03 * min(w, h))


def axis_direction(rotation: float, axis: str) -> np.ndarray:
    r = math.radians(rotation)
    if axis == "x":
        return np.array([math.cos(r), math.sin(r)])
    if axis == "y":
        return np.array([math.sin(r), -math.cos(r)])
    raise ValueError(f"axis must be 'x' or 'y', not {axis!r}")


def snap_axis(image, origin, rotation: float, axis: str = "x", search: float | None = None,
              max_turn: float = MAX_TURN):
    """
    Turns the axes so `axis` lies along the straight line nearest it, and slides the origin onto
    that line.

    Args:
        image: The frame, as an (H, W, 3) BGR array (or grayscale).
        origin: The axes' origin, in image pixels.
        rotation: The axes' rotation, degrees clockwise on screen (AxesItem.rotation()).
        axis: "x" or "y": the axis to line up.
        search: How far either side of the origin the edge is sought, in image pixels (the most
            the origin slides onto a single edge). Default: default_search(image).
        max_turn: The most the axes turn, in degrees.

    Returns:
        ((x, y), rotation, strength): the new origin and rotation (within 180 degrees of the old
        one, so the axes never flip), and the line's strength (Lab units summed along it, for
        choosing between the x and y axes).

    Raises:
        ValueError: If no straight line lies along the axis near the origin.
    """
    img = np.asarray(image)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    height, width = img.shape[:2]
    o = np.asarray(origin, dtype=float)
    if not (0 <= o[0] <= width and 0 <= o[1] <= height):
        raise ValueError("The origin is outside the picture.")
    search = default_search(img) if search is None else float(search)
    d = axis_direction(rotation, axis)
    n = np.array([-d[1], d[0]])  # Across the axis

    # The strip: row v runs along the axis (v = 0 at the origin), column u across it
    corners = np.array([[0, 0], [width, 0], [0, height], [width, height]], dtype=float)
    reach = int(math.ceil(np.max(np.abs((corners - o) @ d))))
    max_slope = math.tan(math.radians(max_turn))
    wide = PAIR_REACH * search  # A tube's other wall may lie further out than the near edge
    half = int(math.ceil(wide + max_slope * reach)) + PEAK_SEARCH + 3
    v = np.arange(-reach, reach + 1, dtype=float)
    to_image = np.array([[n[0], d[0], o[0] - half * n[0] - reach * d[0]],
                         [n[1], d[1], o[1] - half * n[1] - reach * d[1]]])
    size = (2 * half + 1, 2 * reach + 1)
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    strip = cv2.warpAffine(lab, to_image, size, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_REPLICATE)
    inside = cv2.warpAffine(np.ones((height, width), np.uint8), to_image, size,
                            flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    inside = cv2.erode(inside, np.ones((5, 5), np.uint8)) > 0  # Away from the picture's edge
    grad = np.zeros_like(strip)
    grad[:, 1:-1] = (strip[:, 2:] - strip[:, :-2]) / 2  # The change in colour across the axis
    grad[~inside] = 0
    rows_in = int(inside[:, half].sum())
    if rows_in < MIN_ROWS:
        raise ValueError("Too little of the axis lies in the picture to line it up.")

    # Each line: column c at the origin's row, slope s (columns per row). Sum the change along it.
    offsets = np.arange(-int(wide), int(wide) + 1)
    near = np.abs(offsets) <= search  # The edge itself must lie this close to the origin
    slopes = np.tan(np.radians(np.arange(-max_turn, max_turn + 1e-9, TURN_STEP)))
    every = slice(None, None, 2)  # Every other row is enough to find the slope (the fit uses all)
    row_idx = np.arange(len(v))[every, None]
    best = None  # (strength, slope, sums over the offsets (offsets x 3), magnitudes)
    for s in slopes:
        cols = np.rint(half + offsets[None, :] + s * v[every, None]).astype(int)
        sums = grad[row_idx, cols].sum(axis=0)          # (offsets, 3): signed, per colour channel
        mags = np.linalg.norm(sums, axis=1)
        top = mags[near].max()
        if best is None or top > best[0]:
            best = (float(top), float(s), sums, mags)
    strength, slope, sums, mags = best
    if strength < MIN_EDGE * rows_in / 2:
        raise ValueError("No straight line lies along the axis near the origin: the picture "
                         "beside it has no edge to line up with.")

    # The edges at that slope: the strongest, and an opposite one beside it (a tube's other wall)
    peaks = [i for i in range(len(mags))
             if mags[i] >= PAIR_SHARE * strength
             and mags[i] >= mags[max(i - 1, 0)] and mags[i] >= mags[min(i + 1, len(mags) - 1)]]
    first = int(np.argmax(np.where(near, mags, -1.0)))
    edges = [first]
    opposite = [i for i in peaks if abs(i - first) > 2 and np.dot(sums[i], sums[first]) < 0
                and (offsets[i] > 0) != (offsets[first] > 0)]  # On the other side of the origin
    if opposite:
        edges.append(min(opposite, key=lambda i: abs(offsets[i])))

    fits = [_fit_edge(grad, v, half + offsets[i], slope, sums[i]) for i in edges]
    b = float(np.mean([f[1] for f in fits]))   # Slope: the walls' mean
    a = float(np.mean([f[0] for f in fits]))   # Offset at the origin's row: midway, for a pair
    a -= half                                  # Column to u (u = 0 on the axis)

    # The line u = a + b v, in the picture
    new_d = d + b * n
    new_d /= np.hypot(*new_d)
    foot_v = -a * b / (1 + b * b)              # The point on the line nearest the origin
    foot_u = a / (1 + b * b)
    new_o = o + foot_u * n + foot_v * d
    if axis == "x":
        new_rot = math.degrees(math.atan2(new_d[1], new_d[0]))
    else:
        new_rot = math.degrees(math.atan2(new_d[0], -new_d[1]))
    new_rot = rotation + ((new_rot - rotation + 180) % 360 - 180)  # The nearest turn, no flip
    return (float(new_o[0]), float(new_o[1])), float(new_rot), strength


def _fit_edge(grad, v, column, slope, sums):
    """
    The edge near the line through `column` (at the origin's row) with `slope`: each row's
    strongest change of this edge's colour (`sums` gives its direction in colour), to a fraction
    of a pixel, with a line fitted through them. Returns (column at the origin's row, slope).
    """
    tone = sums / np.linalg.norm(sums)
    along = grad @ tone                       # The change in this edge's colour, signed
    rows, cols, heights = [], [], []
    for j, vj in enumerate(v):
        c = column + slope * vj
        c0 = int(round(c)) - PEAK_SEARCH
        c1 = int(round(c)) + PEAK_SEARCH
        if c0 < 1 or c1 > along.shape[1] - 2:
            continue
        seg = along[j, c0:c1 + 1]
        k = int(np.argmax(seg))
        if seg[k] <= 0:
            continue
        offset = 0.0
        if 0 < k < len(seg) - 1:  # Parabola through the peak, for a fraction of a pixel
            denom = seg[k - 1] - 2 * seg[k] + seg[k + 1]
            if denom != 0:
                offset = 0.5 * (seg[k - 1] - seg[k + 1]) / denom
        rows.append(vj)
        cols.append(c0 + k + offset)
        heights.append(seg[k])
    rows, cols, heights = np.array(rows), np.array(cols), np.array(heights)
    if len(rows) < MIN_ROWS:
        return column, slope
    strong = heights >= 0.3 * np.percentile(heights, 90)  # Rows where the edge is (not texture)
    r, e = rows[strong], cols[strong]
    if len(r) < MIN_ROWS:
        return column, slope
    keep = np.ones(len(r), dtype=bool)
    b, a = np.polyfit(r, e, 1)
    for _ in range(10):
        resid = e - (a + b * r)
        spread = 1.4826 * np.median(np.abs(resid[keep] - np.median(resid[keep])))
        new_keep = np.abs(resid) <= max(FIT_TOLERANCE, 3.0 * spread)
        if new_keep.sum() < MIN_ROWS or np.array_equal(new_keep, keep):
            break
        keep = new_keep
        b, a = np.polyfit(r[keep], e[keep], 1)
    return float(a), float(b)
