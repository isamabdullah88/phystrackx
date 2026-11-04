"""
Auto object for the Qt spike: finds an object's outline from a rough box drawn around it, for any
shape (a ball, a stopper, a clamp). GrabCut (OpenCV's interactive segmentation) separates the object
from its surroundings inside the box. The piece that holds the box's centre is the object, and its
outline is the object's. The user confirms the result before it is tracked (see MainWindow).

The result is in picture pixels: the outline's points, and the bounding box the tracker is given.
"""

import cv2
import numpy as np

MARGIN = 0.15      # The box is searched a little wider than drawn: the object may spill past it
MIN_AREA = 25      # Pixels: smaller pieces are specks, not the object
LIGHTNESS_WEIGHT = 0.5  # How much a difference in lightness counts against a difference in colour
DEFAULT_TOLERANCE = 50.0
GRABCUT_ROUNDS = 8


def tolerance_to_delta(tolerance: float) -> float:
    """The distance from the wall that counts as object. A higher tolerance selects more: it lowers
    the distance, so more of the picture counts as object before GrabCut settles the edge."""
    t = min(max(float(tolerance), 0.0), 100.0)
    return 3.0 + 30.0 * (1.0 - t / 100.0)

NO_OBJECT = ("No object found in the box. Draw it a little tighter around the object, with the "
             "object inside it.")


def find_object(frame: np.ndarray, box: tuple[float, float, float, float],
                tolerance: float = DEFAULT_TOLERANCE) -> dict:
    """
    Finds the object in a rough box (x, y, width, height, in picture pixels).

    What differs from the wall around the box (in lightness and colour) seeds GrabCut, and GrabCut
    settles the edge. `tolerance` (0 to 100) sets how far from the wall a pixel must be to count as
    object: higher selects more. An object with no difference from the wall (grey on grey) is found
    from the box alone instead.

    Returns:
        {"points": (N, 2) outline in picture pixels, "bbox": (x, y, w, h) integers, "area": pixels}

    Raises:
        ValueError: If no object is found, or the box covers only background, or the box is too small.
    """
    x, y, w, h = (float(v) for v in box)
    if w < 4 or h < 4:
        raise ValueError("The box is too small. Drag a box around the object.")
    height, width = frame.shape[:2]
    m = MARGIN * max(w, h) + 4
    x0, y0 = int(max(0, np.floor(x - m))), int(max(0, np.floor(y - m)))
    x1, y1 = int(min(width, np.ceil(x + w + m))), int(min(height, np.ceil(y + h + m)))
    crop = frame[y0:y1, x0:x1]
    if crop.ndim == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    rect = (int(round(x - x0)), int(round(y - y0)), int(round(w)), int(round(h)))

    piece = None
    try:
        piece = _grabcut(crop, rect, seeded=True, delta=tolerance_to_delta(tolerance))
    except ValueError:
        piece = None
    if piece is None:
        piece = _grabcut(crop, rect, seeded=False)  # Grey on grey: the box alone
    if piece is None:
        raise ValueError(NO_OBJECT)

    # Fill the holes (a highlight or a mark inside the object is still the object)
    contours, _ = cv2.findContours(piece, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    outer = max(contours, key=cv2.contourArea)
    filled = np.zeros_like(piece)
    cv2.drawContours(filled, [outer], -1, 1, thickness=-1)

    # An object that reaches the edge of the search on three sides is the background, not an object
    touched = [filled[0].any(), filled[-1].any(), filled[:, 0].any(), filled[:, -1].any()]
    if sum(touched) >= 3:
        raise ValueError(NO_OBJECT)

    ys, xs = np.nonzero(filled)
    bbox = (int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1))
    approx = cv2.approxPolyDP(outer, 0.8, True).reshape(-1, 2).astype(float)
    points = approx + np.array([x0, y0], dtype=float)
    return {"points": points, "bbox": bbox, "area": float(filled.sum())}


def _grabcut(crop: np.ndarray, rect: tuple[int, int, int, int], seeded: bool,
             delta: float = 18.0) -> np.ndarray | None:
    """The piece of the object (a uint8 mask in the crop), or None if nothing usable was found."""
    centre_x = int(np.clip(round(rect[0] + rect[2] / 2), 0, crop.shape[1] - 1))
    centre_y = int(np.clip(round(rect[1] + rect[3] / 2), 0, crop.shape[0] - 1))
    background, foreground = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    if seeded:
        lab = cv2.cvtColor(cv2.GaussianBlur(crop, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
        inside = np.zeros(crop.shape[:2], bool)
        inside[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]] = True
        ring = ~inside
        ring[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]] = False
        if not ring.any():
            return None
        wall = np.median(lab[ring], axis=0)
        distance = np.sqrt((LIGHTNESS_WEIGHT * (lab[..., 0] - wall[0])) ** 2
                           + (lab[..., 1] - wall[1]) ** 2 + (lab[..., 2] - wall[2]) ** 2)
        colour = (distance > delta).astype(np.uint8)
        colour = cv2.morphologyEx(colour, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(colour, connectivity=8)
        if count <= 1:
            return None  # No colour of its own: the caller tries the box alone
        seed = labels[centre_y, centre_x] or 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask = np.full(crop.shape[:2], cv2.GC_BGD, np.uint8)
        mask[inside] = np.where(colour[inside] > 0, cv2.GC_PR_FGD, cv2.GC_PR_BGD)
        sure = cv2.erode((labels == seed).astype(np.uint8), np.ones((5, 5), np.uint8))
        mask[sure > 0] = cv2.GC_FGD
        cv2.grabCut(crop, mask, None, background, foreground, GRABCUT_ROUNDS, cv2.GC_INIT_WITH_MASK)
    else:
        mask = np.zeros(crop.shape[:2], np.uint8)
        cv2.grabCut(crop, mask, rect, background, foreground, GRABCUT_ROUNDS, cv2.GC_INIT_WITH_RECT)

    fg = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if count <= 1:
        return None
    label = labels[centre_y, centre_x]
    if label == 0:  # The centre is not object: take the largest piece instead
        label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    piece = (labels == label).astype(np.uint8)
    return piece if piece.sum() >= MIN_AREA else None


def outline_relative(points: np.ndarray, bbox: tuple[int, int, int, int]) -> list[list[float]]:
    """The outline as fractions of its bounding box, so it can be drawn at any box size (the tracker
    may change the box as the object moves)."""
    x, y, w, h = bbox
    rel = (np.asarray(points, dtype=float) - [x, y]) / [max(w, 1), max(h, 1)]
    return np.clip(rel, 0.0, 1.0).tolist()
