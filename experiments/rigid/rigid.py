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

from .mltracker import MLTracker
from .ocr_engine import OcrEngine


class Rigid(Experiment):
    """Orchestrates feature array tracking and automated digit capture."""

    def __init__(self, trimpath: str, vwidth: int, vheight: int, tkqueue: Optional[Queue] = None) -> None:
        super().__init__(trimpath, vwidth, vheight)
        self.tkqueue = tkqueue
        
        # Core Repositories
        self.trackpts: List[List[List[float]]] = []
        self.texts: Optional[OCRData] = OCRData([])
        
        # Isolated Processor Engines
        # self.tracker_engine = FeatureTracker()
        self.mltrackers = []
        self.ocr_engine = OcrEngine()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Modularized Rigid analysis environment ready.")

        self.MIN_TRACK_POINTS = 1

    def inittrackers(self, rects: List[NormalizedRect], initframe: NDArray[np.uint8]) -> None:
        """Initializes deep learning trackers for each region of interest."""
        
        for rect in rects:
            pixrect = rect.norm2pix(self.fwidth, self.fheight)

            tracker = MLTracker(tracking_type="nanotrack")
            
            tracker.initialize_tracker(initframe, pixrect)
            self.mltrackers.append(tracker)

    def track(self, frameidx: int, rects: List[NormalizedRect], ocrrects: List[NormalizedRect],
              filters: Filters, crop: Crop, progress: Optional[IntVar] = None) -> None:
        """Executes analysis sequences across video payloads."""
        
        # Establish frame limits and geometry dimensions
        crpwidth = crop.crprect.width if crop.crprect else self.fwidth
        crpheight = crop.crprect.height if crop.crprect else self.fheight

        self._vidreader.seek(frameidx)
        fcount = self._vidreader.fcount

        # Read initial seed frame
        frame = self._vidreader.read()
        frame = cv2.resize(frame, (self.fwidth, self.fheight))
        frame = filters.appfilter(crop.appcrop(frame))

        self.inittrackers(rects, frame)  # Initialize trackers on the first frame

        # fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # bgray = cv2.GaussianBlur(fgray.copy(), (5, 5), 0)
        # fgray = cv2.addWeighted(fgray, 1.5, bgray, -0.5, 0)

        # 2. Initialize tracking series with None and empty text strings
        self.trackpts = [[[] for _ in range(fcount)] for _ in rects]
        self.textsdata = [[[] for _ in range(fcount)] for _ in ocrrects]

        # Extract features targeting active structures
        # ptstrack, ptsoff = self.tracker_engine.extract_initial_features(fgray, rects, crpwidth, crpheight)
        # fprev = fgray.copy()

        # Main Frame Processing Timeline Loop
        self.logger.info(f"Commencing rigid body tracking and OCR from frame {frameidx} to {fcount - 1}.")
        self.logger.info(f"Textual OCR regions: {len(ocrrects)} | Feature tracking regions: {len(rects)}")

        self._vidreader.seek(frameidx)
        for i in tqdm(range(fcount - 1), desc="Processing Video Rails"):
            frame = self._vidreader.read()

            if i < frameidx:
                continue

            # Standard Transformation Pipeline
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            frame = filters.appfilter(crop.appcrop(frame))
            # bframe = cv2.GaussianBlur(frame, (9, 9), 0)
            # fgray = cv2.cvtColor(bframe, cv2.COLOR_BGR2GRAY)

            # A. Process Spatial Translation Track Vectors
            # for j, p0 in enumerate(ptstrack):
            for j, rect in enumerate(rects):

                tracker = self.mltrackers[j]
                success, rect = tracker.update_tracker(frame)

                if success:
                    # xmin, ymin, width, height = rect
                    # Compute the dynamic object center point
                    # x = int(rect.xmin + width / 2)
                    # y = int(rect.ymin + height / 2)
                    x, y = rect.tocenter()
                    self.trackpts[j][i] = [x, y]

                    cv2.rectangle(frame, (int(rect.xmin), int(rect.ymin)), (int(rect.xmax), int(rect.ymax)), (0, 255, 0), 2)
                else:
                    continue
                # if p0.size == 0:
                #     continue

                # p1p = self.tracker_engine.step_optical_flow(fprev, fgray, p0)

                # Compute center mean point from all points
                # x, y = self.pts2pt(p1p, ptsoff[j])

                # if p1p.shape[0] < self.MIN_TRACK_POINTS:
                #     self.logger.warning(f"Insufficient tracking points ({p1p.shape[0]}) for region {j} at frame {i}. Reinitializing features.")
                #     pixrect = rects[j].norm2pix(crpwidth, crpheight)
                #     box_width = pixrect.xmax - pixrect.xmin
                #     box_height = pixrect.ymax - pixrect.ymin

                #     # 2. Re-center the original box dimensions around the new [x, y]
                #     currxmin = int(x - box_width / 2)
                #     currymin = int(y + box_width / 2)
                #     currwidth = box_width
                #     currheight = box_height

                #     curr_rect = NormalizedRect(
                #         xmin=currxmin / self.fwidth,
                #         ymin=currymin / self.fheight,
                #         width=currwidth / self.fwidth,
                #         height=currheight / self.fheight
                #     )

                #     p1p, ptsoff[j] = self.tracker_engine._feats_rect(fgray, curr_rect, crpwidth, crpheight)

                    # Recompute center mean point from all newly extracted points
                    # x, y = self.pts2pt(p1p, ptsoff[j])

                # for point in p0.reshape(-1, 2):
                #     x, y = point
                #     center = (int(x), int(y))
                #     cv2.circle(frame, center, radius=4, color=(0, 0, 255), thickness=-1)

                
                # ptstrack[j] = p1p
                # self.trackpts[j][i] = [x, y]
            
            # cv2.imwrite(f"debug_frames/frame_{i:04d}.png", frame)  # Save debug frame for inspection

                

            # Process String Digit Conversions
            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(crpwidth, crpheight)
                self.textsdata[j][i] = self.ocr_engine.extract_digits(frame, pixrect)

            # fprev = fgray.copy()

            # Dispatch Visual Buffers via Safe Thread Pipelines
            # if self.tkqueue and not self.tkqueue.full():
            #     self._dispatch_preview_frame(frame.copy(), i, frameidx)

            if progress is not None:
                progress.set(int((i / (fcount - 1)) * 100))

        self.logger.info("Rigid body tracking and OCR processing complete. Compiling final digitized sequences.")

        # Compile final digitized sequences 
        self.texts = OCRData(self.textsdata)
        self.logger.info(f"OCR Data Cleaning Complete: {len(self.texts)} channels with {self.texts.samplecount} samples each.")

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