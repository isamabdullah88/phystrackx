"""
autoruler.py

Snaps a hand-placed scale ruler onto an object's edge. The ruler is drawn roughly over the
object, with its width (half_width on each side of its line) covering the object's width. The
ruler's two ends then move to the object's ends, and the ruler runs along one of its sides (the
left side by default), so the calibration length is the object's length.

How it works: the picture is turned so the ruler runs straight up and down. On each row, the
background is the picture just outside the ruler's width, so the object is whatever differs from
its surroundings (its colour, its shade, its edge). The piece of the object under the ruler's
centre column gives its edge and its two ends. The turn is then repeated along the object's own
edge, so its ends are square to it.

Works in image pixels (row and column of the frame being shown). No GUI here, so it can be tested
on a synthetic picture.

Author: Isam Balghari
"""

import math

import cv2
import numpy as np

OBJECT_DELTA = 8.0   # Lab distance from the local background that counts as object
MIN_LENGTH = 20.0    # Shorter rulers, and objects shorter than this, are too small to snap
PASSES = 3           # Turns: the first along the ruler, then along the object's edge
TAPE_GAP = 31        # Rows: gaps this short in the object (pale tape across it) are bridged
EDGE_TOLERANCE = 2.0 # Pixels: edge rows further than this from the fitted edge are left out
EDGE_SEARCH = 6      # Pixels either side of the mask's edge that the sharpest colour step is sought in


def snap_ruler(image, p1, p2, side: str = "left", half_width: float = 15.0, segmenter=None):
    """
    Moves the ruler ends p1 and p2 onto the object's ends, along its `side` edge.

    Args:
        image: The frame, as an (H, W, 3) BGR array (or grayscale).
        p1, p2: The ruler ends, in image pixels.
        side: "left" or "right" of the object, as seen on screen (smaller or larger x).
        half_width: Half the ruler's width, in image pixels. The object lies within it.
        segmenter: An object finder with set_image(rgb) and predict(points, labels, box) (see
            media.segmenter.SamSegmenter). When given, it finds the object's outline from the
            ruler; otherwise the object is found from its colour and edges against the wall.

    Returns:
        ((x1, y1), (x2, y2)): the new ends, in the same order as p1 and p2.

    Raises:
        ValueError: If the ruler is too short, lies outside the picture, or no object is under
        it (the picture is the same on both sides of the ruler).
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', not {side!r}")
    img = np.asarray(image)
    height, width = img.shape[:2]
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    delta = p2 - p1
    length = float(np.hypot(*delta))
    if length < MIN_LENGTH:
        raise ValueError("The ruler is too short to snap. Stretch it over the object first.")
    centre = (p1 + p2) / 2

    # A window around the ruler, with room for an object longer than it
    pad = max(2 * half_width + 12, 0.5 * length)
    x0 = int(max(0, math.floor(min(p1[0], p2[0]) - pad)))
    x1 = int(min(width, math.ceil(max(p1[0], p2[0]) + pad)))
    y0 = int(max(0, math.floor(min(p1[1], p2[1]) - pad)))
    y1 = int(min(height, math.ceil(max(p1[1], p2[1]) + pad)))
    if x1 - x0 < 4 or y1 - y0 < 4:
        raise ValueError("The ruler is outside the picture.")
    window = img[y0:y1, x0:x1]
    if window.ndim == 2:
        window = cv2.cvtColor(window, cv2.COLOR_GRAY2BGR)
    lab = cv2.cvtColor(cv2.GaussianBlur(window, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    centre_w = centre - np.array([x0, y0])

    outline = None
    if segmenter is not None:
        rgb = cv2.cvtColor(window, cv2.COLOR_BGR2RGB)
        segmenter.set_image(rgb)
        box = np.array([min(p1[0], p2[0]) - half_width - x0, min(p1[1], p2[1]) - half_width - y0,
                        max(p1[0], p2[0]) + half_width - x0, max(p1[1], p2[1]) + half_width - y0])
        outline, _ = segmenter.predict(points=[centre_w], labels=[1], box=box)

    direction = delta / length
    use_min = None  # True when the object's left edge is the smaller column of the turned picture
    ends_w = None
    for _ in range(PASSES):
        frame, to_window, size, matrix = _turned(lab, centre_w, direction)
        turned_outline = None
        if outline is not None:
            turned_outline = cv2.warpAffine(outline.astype(np.uint8), matrix, (size, size),
                                            flags=cv2.INTER_NEAREST) > 0
        rows, left, right = _object_rows(frame, size, half_width, turned_outline)
        if use_min is None:
            # Which edge is the left one on screen: the one whose points sit further left
            left_x = to_window(np.column_stack([left, rows]))[:, 0].mean()
            right_x = to_window(np.column_stack([right, rows]))[:, 0].mean()
            use_min = (left_x < right_x) == (side == "left")
        top_pt, bottom_pt = _ends(rows, left if use_min else right)
        ends_w = to_window(np.array([top_pt, bottom_pt]))
        new_dir = ends_w[1] - ends_w[0]
        new_dir = new_dir / np.hypot(*new_dir)
        direction = new_dir if np.dot(new_dir, direction) >= 0 else -new_dir

    e_top, e_bottom = ends_w[0] + np.array([x0, y0]), ends_w[1] + np.array([x0, y0])
    # Keep the ends in the order the user gave them
    keep = np.hypot(*(e_top - p1)) + np.hypot(*(e_bottom - p2)) <= \
        np.hypot(*(e_bottom - p1)) + np.hypot(*(e_top - p2))
    q1, q2 = (e_top, e_bottom) if keep else (e_bottom, e_top)
    return (float(q1[0]), float(q1[1])), (float(q2[0]), float(q2[1]))


def _turned(lab, centre, direction):
    """
    The window turned so that `direction` points straight down, with `centre` in the middle.

    Returns (frame, to_window, size, matrix): the turned picture, a function mapping points of the
    turned picture (rows of (x, y)) back to window pixels, the picture's side length, and the
    affine matrix of the turn (to turn other pictures, such as a mask, the same way).
    """
    h, w = lab.shape[:2]
    size = int(math.ceil(math.hypot(w, h))) + 2
    ux, uy = direction
    rot = np.array([[uy, -ux], [ux, uy]])  # Maps the direction to (0, 1)
    shift = np.array([size / 2, size / 2]) - rot @ centre
    matrix = np.hstack([rot, shift[:, None]])
    frame = cv2.warpAffine(lab, matrix, (size, size), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)

    def to_window(points):
        pts = np.atleast_2d(np.asarray(points, dtype=float)) - size / 2
        return pts @ rot + centre  # Inverse of the turn (rot is a rotation: rot.T == inverse)

    return frame, to_window, size, matrix


def _object_rows(frame, size: int, half_width: float, outline=None):
    """
    The object under the ruler's centre column, in the turned picture: for each of its rows,
    the columns of its left and right edges.

    outline: the object's mask in the turned picture, when a segmenter found it. Otherwise the
    object is found from the picture's colours and edges, against the wall beside the ruler.

    Returns (rows, left, right) as arrays, one entry per row of the object.
    """
    cx = size / 2
    distance = None
    if outline is not None:
        mask = outline.astype(np.uint8)
    else:
        left_strip = slice(max(int(cx - half_width - 16), 0), max(int(cx - half_width - 4), 0))
        right_strip = slice(int(cx + half_width + 4), int(cx + half_width + 16))
        # The background of each row: the picture just outside the ruler's width
        background = np.median(np.concatenate([frame[:, left_strip], frame[:, right_strip]],
                                              axis=1), axis=1)
        # Colour only (Lab a and b): shadows and pale tape change lightness, not colour
        diff = frame[..., 1:] - background[:, None, 1:]
        distance = np.sqrt(diff[..., 0] ** 2 + diff[..., 1] ** 2)

        band = slice(max(int(cx - 2 * half_width - 6), 0), min(int(cx + 2 * half_width + 6), size))
        mask = np.zeros((size, size), np.uint8)
        mask[:, band] = (distance[:, band] > OBJECT_DELTA).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        # Pale tape across the object has no colour, so it cuts the object in two. A tall closing
        # joins the pieces across it, so the ends are the object's ends and not the tape's.
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((TAPE_GAP, 1), np.uint8))

    # The object: the piece the ruler's centre column runs through. Closing joins the pieces
    # that a shadow or a mark has cut it into.
    _, labels = cv2.connectedComponents(mask, connectivity=8)
    column = labels[:, int(cx)]
    hits = column[column != 0]
    if hits.size == 0:
        raise ValueError("No object lies under the ruler: the picture is the same on both sides"
                         " of it, so there is no edge to snap to.")
    label = int(np.bincount(hits).argmax())
    ys, xs = np.nonzero(labels == label)
    rows = np.unique(ys)
    left = np.array([xs[ys == r].min() for r in rows], dtype=float)
    right = np.array([xs[ys == r].max() for r in rows], dtype=float)
    if rows[-1] - rows[0] < MIN_LENGTH:
        raise ValueError("The object under the ruler is too small to snap to.")
    if distance is not None:  # The mask's edges sit a pixel or two off the true edge (see _refine_edges)
        left = _refine_edges(distance, rows, left)
        right = _refine_edges(distance, rows, right)
    return rows.astype(float), left, right


def _refine_edges(distance, rows, edge):
    """
    Moves each row's edge to the sharpest step in colour near the mask's edge, to a fraction of a
    pixel. The mask's edge is where the colour is just past the threshold, which lies outside the
    object's real edge, and further out where a shadow or pale tape touches it. The object's own
    edge is the strongest step, so it wins over those.
    """
    refined = edge.astype(float).copy()
    cols = distance.shape[1]
    for i, (r, e) in enumerate(zip(rows.astype(int), edge)):
        c0, c1 = int(round(e)) - EDGE_SEARCH, int(round(e)) + EDGE_SEARCH
        if c0 < 1 or c1 > cols - 2:
            continue
        seg = distance[r, c0 - 1:c1 + 2]
        grad = np.abs((seg[2:] - seg[:-2]) / 2.0)  # Central difference at each column c0..c1
        k = int(np.argmax(grad))
        offset = 0.0
        if 0 < k < len(grad) - 1:  # Parabola through the peak, for a fraction of a pixel
            denom = grad[k - 1] - 2 * grad[k] + grad[k + 1]
            if denom != 0:
                offset = 0.5 * (grad[k - 1] - grad[k + 1]) / denom
        refined[i] = c0 + k + offset
    return refined


def _ends(rows, edge):
    """
    The two ends of an object's edge: the edge is fitted as a line through its middle (the ends
    of an object are often rounded), then taken at the object's first and last rows.

    The fit leaves out rows that sit off the line (a pale tape or a shadow beside the object pulls
    the edge sideways there), and refits, until the rows left agree with the line.
    """
    top, bottom = rows.min(), rows.max()
    span = bottom - top
    inner = (rows > top + 0.05 * span) & (rows < bottom - 0.05 * span)
    if inner.sum() >= 2:
        r, e = rows[inner], edge[inner]
        keep = np.ones(len(r), dtype=bool)
        slope, offset = np.polyfit(r, e, 1)
        for _ in range(10):
            resid = e - (offset + slope * r)
            spread = 1.4826 * np.median(np.abs(resid[keep] - np.median(resid[keep])))
            limit = max(EDGE_TOLERANCE, 3.0 * spread)
            new_keep = np.abs(resid) <= limit
            if new_keep.sum() < 2 or np.array_equal(new_keep, keep):
                break
            keep = new_keep
            slope, offset = np.polyfit(r[keep], e[keep], 1)
    else:
        slope, offset = 0.0, float(edge.mean())
    return (offset + slope * top, top), (offset + slope * bottom, bottom)
