"""
assist.py

Two tracking engines: the fast tracker (NanoTrack) on every frame, and Segment Anything only on
the frames where the fast tracker is likely to be fooled.

Most of a run is easy: the ball moves alone (down a tube, say), and only the ball changes the
pixels around it. The hard part is usually the start, when a hand lets go of the ball and moves
away: the fast tracker can follow the hand instead. So each frame is checked:

- the change in a ring of pixels around the tracked box, against the previous frame (a hand or
  another object moving next to the ball changes the ring; the ball alone hardly does), and
- the fast tracker's own confidence, as a backstop.

When a frame is hard, Segment Anything finds the object again from the last good position, and the
fast tracker restarts on it. Segment Anything takes seconds per frame on a CPU, so it runs at most
once every `cooldown` frames.

No GUI here. Author: Isam Balghari
"""

from dataclasses import dataclass

import cv2
import numpy as np

from core import PixelRect


@dataclass
class AssistSettings:
    ring_change: float = 4.0    # Mean grey-level change in the ring that marks a hard frame
    score_min: float = 0.7      # Fast-tracker confidence below this marks a hard frame
    cooldown: int = 15          # Frames between two uses of the hard engine
    ring_scale: float = 1.0     # Ring width, as a multiple of the box's larger side


def ring_change(prev_gray: np.ndarray, gray: np.ndarray, box: PixelRect,
                prev_box: PixelRect | None = None, scale: float = 1.0) -> float:
    """
    Mean absolute change between two grey frames in a ring around `box`. The object's own path is
    left out (its box in this frame and in the previous one, with a small margin), so a fast ball
    moving alone hardly counts, while a hand or anything else moving beside it does.
    """
    h, w = gray.shape[:2]
    boxes = [box] + ([prev_box] if prev_box is not None else [])
    pad = int(round(max(box.width, box.height) * scale)) or 1
    x0 = max(0, int(min(b.xmin for b in boxes)) - pad)
    y0 = max(0, int(min(b.ymin for b in boxes)) - pad)
    x1 = min(w, int(max(b.xmin + b.width for b in boxes)) + pad)
    y1 = min(h, int(max(b.ymin + b.height for b in boxes)) + pad)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    diff = cv2.absdiff(gray[y0:y1, x0:x1], prev_gray[y0:y1, x0:x1]).astype(np.float32)
    mask = np.ones(diff.shape, bool)
    margin = max(2, int(round(0.15 * max(box.width, box.height))))
    for b in boxes:
        bx0, by0 = int(b.xmin) - x0 - margin, int(b.ymin) - y0 - margin
        bx1, by1 = bx0 + int(b.width) + 2 * margin, by0 + int(b.height) + 2 * margin
        mask[max(0, by0):max(0, by1), max(0, bx0):max(0, bx1)] = False
    return float(diff[mask].mean()) if mask.any() else 0.0


class HardEngine:
    """Decides which frames are hard, and finds the object again on them with a segmenter."""

    def __init__(self, segmenter, settings: AssistSettings | None = None) -> None:
        self.segmenter = segmenter
        self.settings = settings or AssistSettings()
        self._last_used = None
        self.uses = 0  # How many frames the hard engine was run on

    def ready(self, index: int) -> bool:
        """True when the hard engine may run on frame `index` (it has cooled down)."""
        return self._last_used is None or index - self._last_used >= self.settings.cooldown

    def is_hard(self, prev_gray, gray, box: PixelRect, prev_box: PixelRect | None, score: float,
                index: int) -> bool:
        s = self.settings
        if not self.ready(index):
            return False
        if score < s.score_min:
            return True
        return ring_change(prev_gray, gray, box, prev_box, s.ring_scale) > s.ring_change

    def redetect(self, frame_bgr: np.ndarray, centre: tuple[float, float], box: PixelRect,
                 index: int) -> PixelRect | None:
        """
        The object's box in this frame, from Segment Anything prompted with the last good centre
        and a box twice the last box's size. None when nothing sensible is found.
        """
        self._last_used = index
        self.uses += 1
        h, w = frame_bgr.shape[:2]
        cx, cy = centre
        half_w, half_h = box.width, box.height  # Twice the box: room for the object to have moved
        prompt = (max(0, cx - half_w), max(0, cy - half_h), min(w, cx + half_w), min(h, cy + half_h))
        self.segmenter.set_image(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        mask, score = self.segmenter.predict(points=[(cx, cy)], labels=[1], box=prompt)
        if score < 0.5 or not mask.any():
            return None
        count, labels = cv2.connectedComponents(mask.astype(np.uint8))
        label = labels[int(round(min(max(cy, 0), h - 1))), int(round(min(max(cx, 0), w - 1)))]
        if label == 0:  # The point is not on the mask: take the largest piece
            sizes = np.bincount(labels.ravel())
            sizes[0] = 0
            label = int(sizes.argmax())
        ys, xs = np.nonzero(labels == label)
        found = PixelRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1),
                          int(ys.max() - ys.min() + 1))
        # A mask far bigger than the object (the whole wall, the hand) is not the object
        if found.width * found.height > 9 * max(1, box.width * box.height):
            return None
        return found
