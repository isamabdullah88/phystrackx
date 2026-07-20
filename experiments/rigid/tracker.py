from logging import getLogger
import cv2
import numpy as np
from typing import Tuple

from core import NormalizedRect

class FeatureTracker:
    """Manages Lucas-Kanade optical flow tracking calculations across frame transformations."""
    
    def __init__(self, lk_params: dict = None) -> None:
        self.lk_params = lk_params or dict(
            winSize=(50, 50),
            maxLevel=5,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
        )

        self.logger = getLogger(__name__)

    def _feats_rect(self, gframe: np.ndarray, rect: NormalizedRect, crpwidth: int,
                    crpheight: int) -> Tuple[np.ndarray, list]:
        """Extracts feature points within a normalized rectangle."""
        pixrect = rect.norm2pix(crpwidth, crpheight)
        mask = np.zeros_like(gframe, dtype=np.uint8)
        mask[pixrect.ymin:pixrect.ymax, pixrect.xmin:pixrect.xmax] = 255

        p0 = cv2.goodFeaturesToTrack(gframe, maxCorners=150, qualityLevel=0.005,
                                     minDistance=3, blockSize=10, mask=mask,
                                     useHarrisDetector=True, k=0.04)
        off = []
        
        if p0 is not None:
            p0 = p0.astype(np.float32).reshape(-1, 1, 2)
            self.logger.info(f"Extracted {p0.shape[0]} feature points for tracking.")

            rcent = pixrect.tocenter()
            mean_pt = np.mean(p0, axis=0).ravel()
            off = [int(rcent[0] - mean_pt[0]), int(rcent[1] - mean_pt[1])]
        else:
            p0 = np.empty((0, 1, 2), dtype=np.float32)
            off = [0, 0]
            self.logger.warning("No feature points found in the specified rectangle.")

        return p0, off

    def extract_initial_features(self, gframe: np.ndarray, rects: list, crpwidth: int,
                                 crpheight: int) -> Tuple[list, list]:
        """Identifies prominent points to track inside designated regions of interest."""
        ptstrack = []
        ptsoff = []
        
        for k, rect in enumerate(rects):
            p0, off = self._feats_rect(gframe, rect, crpwidth, crpheight)

            ptstrack.append(p0)
            ptsoff.append(off)

            self.logger.info(f"Extracted {p0.shape[0]} feature point sets for tracking for rectangle {k}.")
                
        return ptstrack, ptsoff

    def step_optical_flow(self, prev_gray: np.ndarray, curr_gray: np.ndarray,
                          p0: np.ndarray) -> np.ndarray:
        """Calculates displacement translations safely without losing vector alignments."""
        if p0.size == 0:
            return p0
            
        p1, st, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, p0, None, **self.lk_params)
        if p1 is not None and st is not None:
            p1p = p1[st == 1].reshape(-1, 1, 2)
            return p1p if p1p.size > 0 else p0
        return p0