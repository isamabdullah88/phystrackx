"""
rigid.py

Implements rigid body tracking using optical flow and optional OCR from video frames.
Orchestrates isolated calculation processors for performance efficiency.

Author: Isam Balghari
"""

import cv2
import numpy as np
import logging
from queue import Queue
from typing import Optional, List
from numpy.typing import NDArray

from tqdm import tqdm
from customtkinter import IntVar

from experiments.experiment import Experiment
from experiments.components import OCRData
from core import NormalizedRect
from gui.plugins import Crop, Filters

# Internal decoupled engine imports
from .tracker import FeatureTracker
from .ocr_engine import OcrEngine


class Rigid(Experiment):
    """Orchestrates feature array tracking and automated digit capture."""

    def __init__(self, trimpath: str, vwidth: int, vheight: int, tkqueue: Optional[Queue] = None) -> None:
        super().__init__(trimpath, vwidth, vheight)
        self.tkqueue = tkqueue
        
        # Core Repositories
        self.trackpts: List[List[NDArray[np.float32]]] = []
        self.texts: Optional[OCRData] = None
        
        # Isolated Processor Engines
        self.tracker_engine = FeatureTracker()
        self.ocr_engine = OcrEngine()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Modularized Rigid analysis environment ready.")

    def track(self, 
              frameidx: int, 
              rects: List[NormalizedRect], 
              ocrrects: List[NormalizedRect], 
              filters: Filters,
              crop: Crop, 
              progress: Optional[IntVar] = None) -> None:
        """Executes analysis sequences across video payloads."""
        
        # 1. Establish frame limits and geometry dimensions
        crwidth = crop.crprect.width if crop.crprect else self.fwidth
        crheight = crop.crprect.height if crop.crprect else self.fheight

        self._vidreader.seek(frameidx)
        fcount = self._vidreader.fcount

        # Read initial seed frame
        frame = self._vidreader.read()
        frame = cv2.resize(frame, (self.fwidth, self.fheight))
        frame = filters.appfilter(crop.appcrop(frame))
        fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. Initialize tracking series with None and empty text strings
        self.trackpts = [[[] for _ in range(fcount)] for _ in rects]
        self.textsdata = [[[] for _ in range(fcount)] for _ in ocrrects]

        # Extract features targeting active structures
        ptstrack, ptsoff = self.tracker_engine.extract_initial_features(fgray, rects, crwidth, crheight)
        fprev = fgray.copy()

        # 3. Main Frame Processing Timeline Loop
        self._vidreader.seek(0)
        for i in tqdm(range(fcount - 1), desc="Processing Video Rails"):
            frame = self._vidreader.read()

            if i < frameidx:
                continue

            # Standard Transformation Pipeline
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            frame = filters.appfilter(crop.appcrop(frame))
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # A. Process Spatial Translation Track Vectors
            for j, p0 in enumerate(ptstrack):
                if p0.size == 0:
                    continue
                p1p = self.tracker_engine.step_optical_flow(fprev, fgray, p0)
                ptstrack[j] = p1p
                
                # Transform arrays via point converters
                x, y = self.pts2pt(p1p, ptsoff[j])
                self.trackpts[j][i] = [x, y]

            # B. Process String Digit Conversions
            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(crwidth, crheight)
                self.textsdata[j][i] = self.ocr_engine.extract_digits(frame, pixrect)

            fprev = fgray.copy()

            # 4. Dispatch Visual Buffers via Safe Thread Pipelines
            if self.tkqueue and not self.tkqueue.full():
                self._dispatch_preview_frame(frame.copy(), i, frameidx)

            if progress is not None:
                progress.set(int((i / (fcount - 1)) * 100))

        # Compile final digitized sequences 
        self.texts = OCRData(self.textsdata)

    def _dispatch_preview_frame(self, preview_frame: np.ndarray, current_frame_idx: int, start_idx: int) -> None:
        """Overlays diagnostic visual tracking markers and pushes to the preview UI queue."""
        for pts in self.trackpts:
            # Render trace vectors matching history length constants
            for k in range(max(start_idx, current_frame_idx - 30), current_frame_idx):
                coords = pts[k]
                if coords is None:  # Safely skip uninitialized tracking frames
                    continue
                
                x, y = coords
                cv2.circle(preview_frame, (x, y), 4, (0, 0, 255), -1)
        self.tkqueue.put(preview_frame)