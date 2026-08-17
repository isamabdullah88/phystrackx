"""
rigid.py

Implements rigid body tracking using optical flow and optional OCR from video frames.
Orchestrates isolated calculation processors for performance efficiency.

Author: Isam Balghari
"""

import cv2
import numpy as np
import logging
from typing import Optional, List
from numpy.typing import NDArray

from tqdm import tqdm
from customtkinter import IntVar

from experiments.experiment import Experiment
from experiments.components import OCRData
from core import NormalizedRect
from gui.plugins import Crop, Filters

from .mltracker import MLTracker
from .ocr_engine import OcrEngine


class Rigid(Experiment):
    """Orchestrates feature array tracking and automated digit capture."""

    def __init__(self, trimpath: str, vwidth: int, vheight: int) -> None:
        super().__init__(trimpath, vwidth, vheight)
        # self.tkqueue = tkqueue
        
        # Core Repositories
        self.trackpts: List[List[List[float]]] = []
        self.texts: Optional[OCRData] = OCRData([])
        
        # Isolated Processor Engines
        # self.tracker_engine = FeatureTracker()
        self.mltrackers = []
        self.ocr_engine = OcrEngine()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Modularized Rigid analysis environment ready.")

    def inittrackers(self, rects: List[NormalizedRect], initframe: NDArray[np.uint8], width: int, height: int) -> None:
        """Initializes deep learning trackers for each region of interest."""

        self.mltrackers = []
        for rect in rects:
            pixrect = rect.norm2pix(width, height)

            tracker = MLTracker(tracking_type="nanotrack")
            
            tracker.initialize_tracker(initframe, pixrect)
            self.mltrackers.append(tracker)

    def preprocess(self, frame: NDArray[np.uint8], crop: Crop, filters: Filters) -> NDArray[np.uint8]:
        """Applies cropping and filtering to the input frame."""
        frame = cv2.resize(frame, (self.fwidth, self.fheight))
        frame = filters.apply_filter(crop.apply_crop(frame))
        return frame

    def track(self, frameidx: int, rects: List[NormalizedRect], ocrrects: List[NormalizedRect],
              filters: Filters, crop: Crop, progress: Optional[IntVar] = None) -> None:
        """Executes analysis sequences across video payloads."""
        
        # Establish frame limits and geometry dimensions
        # crpwidth = crop.crprect.width if crop.crprect else self.fwidth
        # crpheight = crop.crprect.height if crop.crprect else self.fheight

        self._vidreader.seek(frameidx)
        fcount = self._vidreader.fcount

        # Read initial seed frame
        frame = self._vidreader.read()
        frame = self.preprocess(frame, crop, filters)

        self.inittrackers(rects, frame, crop.cropwidth, crop.cropheight)  # Initialize trackers on the first frame

        # Initialize tracking series with None and empty text strings
        self.trackpts = [[[] for _ in range(fcount)] for _ in rects]
        self.textsdata = [[[] for _ in range(fcount)] for _ in ocrrects]

        # Main Frame Processing Timeline Loop
        self.logger.info(f"Commencing rigid body tracking and OCR from frame {frameidx} to {fcount - 1}.")
        self.logger.info(f"Textual OCR regions: {len(ocrrects)} | Feature tracking regions: {len(rects)}")

        for i in tqdm(range(fcount - 1), desc="Processing Video Rails"):
            frame = self._vidreader.read()

            if i < frameidx:
                continue

            # Standard Transformation Pipeline
            frame = self.preprocess(frame, crop, filters)

            # Process Spatial Translation Track Vectors
            for j, rect in enumerate(rects):

                tracker = self.mltrackers[j]
                success, rect = tracker.update_tracker(frame)

                if success:
                    x, y = rect.tocenter()
                    self.trackpts[j][i] = [x, y]
                else:
                    continue

            # Process String Digit Conversions
            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(crop.cropwidth, crop.cropheight)
                self.textsdata[j][i] = self.ocr_engine.extract_digits(frame, pixrect)

            # Dispatch Visual Buffers via Safe Thread Pipelines
            # if self.tkqueue and not self.tkqueue.full():
            #     self._dispatch_preview_frame(frame.copy(), i, frameidx)

            if progress is not None:
                progress.set(int((i / (fcount - 1)) * 100))

        self.logger.info("Rigid body tracking and OCR processing complete. Compiling final digitized sequences.")

        # Compile final digitized sequences 
        self.texts = OCRData(self.textsdata)
        self.logger.info(f"OCR Data Cleaning Complete: {len(self.texts)} channels with {self.texts.samplecount} samples each.")


    def set(self, fwidth: int, fheight: int) -> None:
        """Sets the frame width and height for processing."""
        self.fwidth = fwidth
        self.fheight = fheight