"""
rigid.py

Implements rigid body tracking using optical flow and optional OCR from video frames.
Orchestrates isolated calculation processors for performance efficiency.

Author: Isam Balghari
"""

import cv2
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional, List
from numpy.typing import NDArray

from tqdm import tqdm
from customtkinter import IntVar

from experiments.experiment import Experiment
from experiments.components import OCRData
from core import NormalizedRect
from gui.plugins import Crop, Filters
from media.videoreader import VideoReader

from .mltracker import MLTracker
from .ocr_engine import OcrEngine


@dataclass
class FullResSource:
    """Where the full-resolution frames come from.

    Attributes:
        path (str): The full-resolution copy of the source video.
        start (int): Proxy frame that frame 0 of the trimmed clip comes from.
        origin (tuple[int, int]): Top-left of the trimmed clip in proxy pixels (0, 0 if not cropped).
    """
    path: str
    start: int = 0
    origin: tuple[int, int] = (0, 0)


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
              filters: Filters, crop: Crop, progress: Optional[IntVar] = None,
              on_frame=None, should_stop=None, fullres: Optional[FullResSource] = None,
              assist=None) -> None:
        """Executes analysis sequences across video payloads.

        Stored positions are in pixels of the clip as shown on screen, whichever size the
        tracker worked at. So the ruler, axes, and exports keep the units they always had.

        Args:
            on_frame (callable, optional): Called as on_frame(index, frame, boxes) after each
                frame, with the frame at on-screen size and each object's (x, y, w, h) in
                on-screen pixels, or None if lost.
            fullres (FullResSource, optional): When given, the frames are read from the
                full-resolution copy and tracked at that size, so the on-screen size does not
                limit the measurement.
            assist (HardEngine, optional): Segment Anything for the hard frames (see assist.py).
        """
        dw, dh = crop.cropwidth, crop.cropheight  # The clip's size on screen
        self.assist = assist

        if fullres is None:
            self._track_clip(frameidx, rects, ocrrects, filters, crop, progress, on_frame,
                             should_stop, self._vidreader, self._vidreader.fcount, None)
            return

        native = VideoReader(fullres.path)
        try:
            region = self._fullres_region(fullres, native, dw, dh)
            self._track_clip(frameidx, rects, ocrrects, filters, crop, progress, on_frame,
                             should_stop, native, self.fcount, (fullres.start, region))
        finally:
            native.release()

    def _fullres_region(self, fullres: FullResSource, native: VideoReader, dw: float,
                        dh: float) -> tuple[int, int, int, int]:
        """The clip's area in the full-resolution copy, as (x0, y0, x1, y1) in full-size pixels."""
        if self.proxysize is None:
            raise RuntimeError("No proxy size: load the video before tracking.")
        if native.fcount != self.proxyfcount:
            raise RuntimeError(f"The full-resolution copy has {native.fcount} frames but the proxy "
                               f"has {self.proxyfcount}, so frame numbers would not match.")

        pw, ph = self.proxysize
        sx, sy = native.width / pw, native.height / ph
        ox, oy = fullres.origin
        x0, y0 = round(ox * sx), round(oy * sy)
        x1 = min(x0 + round(dw * sx), native.width)
        y1 = min(y0 + round(dh * sy), native.height)
        return x0, y0, x1, y1

    def _track_clip(self, frameidx: int, rects: List[NormalizedRect],
                    ocrrects: List[NormalizedRect], filters: Filters, crop: Crop,
                    progress: Optional[IntVar], on_frame, should_stop, reader: VideoReader,
                    count: int, native: Optional[tuple[int, tuple[int, int, int, int]]]) -> None:
        """
        Runs the frame loop over one reader.

        Args:
            reader (VideoReader): The display clip, or the full-resolution copy.
            count (int): Number of frames in the clip.
            native (tuple, optional): (start, region) when reading the full-resolution copy.
                start is the copy frame that clip frame 0 comes from, and region is the clip's
                (x0, y0, x1, y1) area in the copy.
        """
        dw, dh = crop.cropwidth, crop.cropheight
        if native is None:
            tw, th = dw, dh  # Tracked at the size on screen
            offset = 0

            def prepare(raw):
                return self.preprocess(raw, crop, filters)
        else:
            offset, (x0, y0, x1, y1) = native
            tw, th = x1 - x0, y1 - y0

            def prepare(raw):
                return filters.apply_filter(raw[y0:y1, x0:x1])

        kx, ky = dw / tw, dh / th  # Tracked pixels -> pixels on screen

        # Establish frame limits and geometry dimensions
        reader.seek(offset + frameidx)

        # Read initial seed frame
        frame = prepare(reader.read())

        self.inittrackers(rects, frame, tw, th)  # Initialize trackers on the first frame

        # Initialize tracking series with None and empty text strings
        self.trackpts = [[[] for _ in range(count)] for _ in rects]
        self.textsdata = [[[] for _ in range(count)] for _ in ocrrects]

        # The seed frame's position is the box the user drew
        for j, rect in enumerate(rects):
            self.trackpts[j][frameidx] = list(rect.norm2pix(dw, dh).tocenter())

        # Main Frame Processing Timeline Loop
        self.logger.info(f"Commencing rigid body tracking and OCR from frame {frameidx} to {count - 1}.")
        self.logger.info(f"Textual OCR regions: {len(ocrrects)} | Feature tracking regions: {len(rects)}")

        # The seed frame was read above, so the loop starts at the next frame. Each read below is
        # frame i, which keeps every stored point on the frame it was measured from.
        # Several objects are tracked side by side: OpenCV releases the GIL while a tracker runs,
        # so three objects take about 60% of the time they take one after another. One object is
        # faster without the hand-off to a thread.
        pool = ThreadPoolExecutor(max_workers=len(rects)) if len(rects) > 1 else None
        try:
            self._track_frames(frameidx, count, rects, ocrrects, reader, prepare, should_stop,
                               on_frame, progress, kx, ky, tw, th, dw, dh, native, pool)
        finally:
            if pool is not None:
                pool.shutdown(wait=True)

        self.logger.info("Rigid body tracking and OCR processing complete. Compiling final digitized sequences.")

        # Compile final digitized sequences
        self.texts = OCRData(self.textsdata)
        self.logger.info(f"OCR Data Cleaning Complete: {len(self.texts)} channels with {self.texts.samplecount} samples each.")

    def _track_frames(self, frameidx, count, rects, ocrrects, reader, prepare, should_stop,
                      on_frame, progress, kx, ky, tw, th, dw, dh, native, pool) -> None:
        """The frame loop: reads each frame, updates every tracker, and reports progress."""
        assist = getattr(self, "assist", None)
        prev_gray = None
        prev_boxes = [rect.norm2pix(tw, th) for rect in rects]  # Last good box of each object
        for i in tqdm(range(frameidx + 1, count), desc="Processing Video Rails"):
            if should_stop is not None and should_stop():
                self.logger.info(f"Tracking stopped by user at frame {i}; keeping results so far.")
                break
            frame = prepare(reader.read())

            # Process Spatial Translation Track Vectors
            live_boxes = []  # (x, y, w, h) per tracked object in this frame, for the live display
            if pool is not None:
                results = list(pool.map(lambda tracker: tracker.update_tracker(frame),
                                        self.mltrackers))
            else:
                results = [tracker.update_tracker(frame) for tracker in self.mltrackers]
            if assist is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    results = [self._assisted(j, ok, box, frame, gray, prev_gray, prev_boxes[j],
                                              assist, i) for j, (ok, box) in enumerate(results)]
                prev_gray = gray
                prev_boxes = [box if ok else prev for (ok, box), prev in zip(results, prev_boxes)]
            for j, (success, box) in enumerate(results):
                if success:
                    x, y = box.tocenter()
                    self.trackpts[j][i] = [x * kx, y * ky]
                    live_boxes.append((box.xmin * kx, box.ymin * ky, box.width * kx, box.height * ky))
                else:
                    live_boxes.append(None)
                    continue

            # Process String Digit Conversions
            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(tw, th)
                self.textsdata[j][i] = self.ocr_engine.extract_digits(frame, pixrect)

            # Dispatch Visual Buffers via Safe Thread Pipelines
            # if self.tkqueue and not self.tkqueue.full():
            #     self._dispatch_preview_frame(frame.copy(), i, frameidx)

            if on_frame is not None:
                shown = frame
                if native is not None:
                    shown = cv2.resize(frame, (round(dw), round(dh)), interpolation=cv2.INTER_AREA)
                on_frame(i, shown, live_boxes)

            if progress is not None:
                progress.set(int(((i - frameidx) / max(count - 1 - frameidx, 1)) * 100))

    def _assisted(self, j, success, box, frame, gray, prev_gray, prev_box, assist, index):
        """
        The fast tracker's result for object j, checked by the hard engine. On a hard frame (or a
        lost object), Segment Anything finds the object again from its last good position and the
        fast tracker restarts on it.
        """
        tracker = self.mltrackers[j]
        if success:
            hard = assist.is_hard(prev_gray, gray, box, prev_box, tracker.score(), index)
        else:
            hard = assist.ready(index)
        if not hard:
            return success, box
        found = assist.redetect(frame, prev_box.tocenter(), prev_box, index)
        if found is None:
            return success, box
        tracker.initialize_tracker(frame, found)
        self.logger.info(f"Frame {index}: object {j + 1} found again by Segment Anything")
        return True, found

    def set(self, fwidth: int, fheight: int) -> None:
        """Sets the frame width and height for processing."""
        self.fwidth = fwidth
        self.fheight = fheight
