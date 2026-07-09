import cv2
import numpy as np
from typing import Tuple

class FeatureTracker:
    """Manages Lucas-Kanade optical flow tracking calculations across frame transformations."""
    
    def __init__(self, lk_params: dict = None) -> None:
        self.lk_params = lk_params or dict(
            winSize=(15, 15),
            maxLevel=5,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )

    def extract_initial_features(self, gray_frame: np.ndarray, rects: list, crwidth: int, crheight: int) -> Tuple[list, list]:
        """Identifies prominent points to track inside designated regions of interest."""
        ptstrack = []
        ptsoff = []
        
        for rect in rects:
            pixrect = rect.norm2pix(crwidth, crheight)
            mask = np.zeros_like(gray_frame, dtype=np.uint8)
            mask[pixrect.ymin:pixrect.ymax, pixrect.xmin:pixrect.xmax] = 255

            p0 = cv2.goodFeaturesToTrack(
                gray_frame, maxCorners=100, qualityLevel=0.4,
                minDistance=5, blockSize=5, mask=mask
            )
            if p0 is not None:
                ptstrack.append(p0.astype(np.float32).reshape(-1, 1, 2))
                # Note: Assuming self.pts2pt logic conversion is handled here or accessible
                # For decoupled scaling math, map initial offsets relative to center bounds
                rcent = pixrect.tocenter()
                # Default fallback calculation array structure matching standard points
                mean_pt = np.mean(p0, axis=0).ravel()
                ptsoff.append([int(rcent[0] - mean_pt[0]), int(rcent[1] - mean_pt[1])])
            else:
                ptstrack.append(np.empty((0, 1, 2), dtype=np.float32))
                ptsoff.append([0, 0])
                
        return ptstrack, ptsoff

    def step_optical_flow(self, prev_gray: np.ndarray, curr_gray: np.ndarray, p0: np.ndarray) -> np.ndarray:
        """Calculates displacement translations safely without losing vector alignments."""
        if p0.size == 0:
            return p0
            
        p1, st, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, p0, None, **self.lk_params)
        if p1 is not None and st is not None:
            p1p = p1[st == 1].reshape(-1, 1, 2)
            return p1p if p1p.size > 0 else p0
        return p0