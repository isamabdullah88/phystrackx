"""
experiment.py

Handles video loading, trimming, proxy resizing, and motion-based frame filtering
for time-bounded experiments.

Author: Isam Balghari
"""

import os
import sys
import logging
from math import floor
from itertools import groupby

import cv2
from cv2.typing import MatLike
import numpy as np

from media.videoreader import VideoReader
from media import proxyvideo, trimvideo
from media.proxyvideo import source_is_plain, display_size


# -------------------------------------------------------------------------------------------------
###################################################################################
# ---------------------------------- Experiment Class ---------------------------------------------
class Experiment:
    """
    Handles video preprocessing, proxy generation, trimming, and motion analysis
    for frame selection.
    """
    def __init__(self, trimpath: str, vwidth: int, vheight: int) -> None:
        self._setup_logging()

        self._vidreader: VideoReader | None = None
        self._nativereader: VideoReader | None = None  # Full-resolution copy, for zoomed views
        self._native_cache: tuple | None = None  # (frame index, decoded frame): reused while panning
        self.fwidth: int = 0
        self.fheight: int = 0
        self.fps: int = 0
        self.fcount: int = 0

        self.vwidth: int = vwidth
        self.vheight: int = vheight

        self.videopath: str | None = None
        self.proxypath: str | None = None
        self.trimpath: str = trimpath
        self.active_duration: list[int] = []

        # The original file, the display proxy's size and frame count, and the full-resolution copy
        self.sourcepath: str | None = None
        self.proxysize: tuple[int, int] | None = None
        self.proxyfcount: int = 0
        self.nativepath: str | None = None

        self.logger = logging.getLogger(__name__)

    # ---------------------------------------------------------------------------------------------
    def _setup_logging(self) -> None:
        if not sys.stdout or not sys.stdout.isatty():
            os.makedirs("logs", exist_ok=True)
            sys.stdout = open("logs/stdout.log", "a")
            sys.stderr = open("logs/stderr.log", "a")

    # ---------------------------------------------------------------------------------------------
    def addvideo(self, videopath: str, istrim=False, fwidth: int = 0, fheight: int = 0,
                 on_progress=None) -> None:
        """
        Load the video and extract dimensions and frame count.

        Args:
            on_progress (callable, optional): Receives proxy encoding progress (0.0 to 1.0).
        """
        self.videopath = videopath
        if not istrim:
            self.sourcepath = videopath
        self._vidreader = VideoReader(videopath)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        self.fps = self._vidreader.fps

        if fwidth > 0 and fheight > 0:
            self.fwidth = fwidth
            self.fheight = fheight
            self.logger.info(f"Setting custom frame dimensions: width={self.fwidth}, height={self.fheight}")

        if not istrim:
            self.resize(on_progress)

    # ---------------------------------------------------------------------------------------------
    def setseek(self, index: int) -> None:
        """
        Set the video reader to a specific frame index.

        Args:
            index (int): Frame index to seek to.
        """
        if self._vidreader:
            self._vidreader.seek(index)

    # ---------------------------------------------------------------------------------------------
    def resize(self, on_progress=None) -> None:
        """
        Resize dimensions to fit inside the viewer while maintaining aspect ratio.
        """
        # The proxy is scaled from the video as it is shown, so the ratio is the shown one: a
        # phone video's rotation is metadata that OpenCV does not apply to the stored frames
        shown = display_size(self.videopath) or (self.fwidth, self.fheight)
        ratio = shown[0] / shown[1]
        self.fheight = self.vheight
        self.fwidth = floor(self.fheight * ratio)

        # Width and height must be even for ffmpeg
        self.fwidth = floor(self.fwidth/2)*2
        self.fheight = floor(self.fheight/2)*2

        # Generate proxy video
        self._proxymize(on_progress)

    # ---------------------------------------------------------------------------------------------
    def _proxymize(self, on_progress=None) -> None:
        """
        Create a lower-resolution proxy video and update internal reader.
        """
        os.makedirs("./temp", exist_ok=True)
        proxy = proxyvideo(self.videopath, width=self.fwidth, height=self.fheight,
                           on_progress=on_progress, total_frames=self.fcount)
        if proxy is None:
            raise IOError(f"Could not create a proxy video for: {self.videopath}")
        self.videopath = proxy
        self._vidreader = VideoReader(self.videopath)

        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        self.fps = self._vidreader.fps
        self.proxysize = (self.fwidth, self.fheight)
        self.proxyfcount = self.fcount

    # ---------------------------------------------------------------------------------------------
    def ensure_native(self, on_progress=None) -> str:
        """
        Make, or reuse, a copy of the source at its full size, with rotation applied. Its frames
        match the proxy's one for one, so a frame index means the same moment in both.

        Args:
            on_progress (callable, optional): Receives encoding progress (0.0 to 1.0).

        Returns:
            str: Path to the full-resolution copy.
        """
        if not self.sourcepath:
            raise RuntimeError("No source video to make a full-resolution copy from.")
        # A source with even size and no rotation already holds these pixels: read it directly
        # instead of encoding a copy of it (which takes as long as the proxy did).
        if source_is_plain(self.sourcepath):
            self.nativepath = self.sourcepath
            if on_progress:
                on_progress(1.0)
            return self.sourcepath
        # iw and ih are the source size after rotation, so the copy keeps the source's size
        native = proxyvideo(self.sourcepath, width="trunc(iw/2)*2", height="trunc(ih/2)*2",
                            on_progress=on_progress, total_frames=self.proxyfcount)
        if native is None:
            raise IOError(f"Could not create a full-resolution copy of: {self.sourcepath}")
        self.nativepath = native
        return native

    # ---------------------------------------------------------------------------------------------
    def trim(self, startidx: int = 0, endidx: int = 0, crop=None) -> bool:
        """
        Trim the video between specified frame indices using FFmpeg.

        Args:
            startidx (int): Starting frame index.
            endidx (int): Ending frame index.

        Returns:
            bool: True if the trimmed clip was written. On False the old clip is untouched.
        """
        return trimvideo(self.videopath, self.trimpath, startidx, endidx, self.fps, crop=crop)

    # ---------------------------------------------------------------------------------------------
    def frame(self, index: int | None = None) -> MatLike:
        """
        Retrieve a specific frame from the video.

        Args:
            index (int | None): Frame index to read.

        Returns:
            np.ndarray: Frame image as array.
        """
        if not self._vidreader:
            raise RuntimeError("VideoReader not initialized.")
        
        if self.active_duration:
            return self._vidreader.read(self.active_duration[index])
        return self._vidreader.read(index)

    # ---------------------------------------------------------------------------------------------
    def native_region(self, frameidx: int, region: tuple[int, int, int, int]) -> MatLike | None:
        """
        A region of a frame from the full-resolution copy, at the copy's own pixels.

        Args:
            frameidx (int): Frame of the source video (the proxy's frame numbers).
            region (tuple): (x, y, w, h) in the proxy's pixels.

        Returns:
            The region as an image, or None when there is no copy yet or its frames do not match
            the proxy's (so the proxy must be shown instead).
        """
        found = self.native_region_at(frameidx, region)
        return None if found is None else found[0]

    def native_region_at(self, frameidx: int, region: tuple[int, int, int, int]):
        """
        Like native_region, but also says where the image sits, so it can be drawn exactly.

        Returns:
            (image, x0, y0, sx, sy), or None as native_region does. x0 and y0 are the image's
            top-left corner in the copy's pixels, and sx and sy are copy pixels per proxy pixel.
        """
        if not self.nativepath or not self.proxysize:
            return None
        if self._nativereader is None:
            self._nativereader = VideoReader(self.nativepath)
        native = self._nativereader
        if native.fcount != self.proxyfcount:
            return None

        sx, sy = native.width / self.proxysize[0], native.height / self.proxysize[1]
        x, y, w, h = region
        x0, y0 = round(x * sx), round(y * sy)
        x1, y1 = min(round((x + w) * sx), native.width), min(round((y + h) * sy), native.height)
        if x1 <= x0 or y1 <= y0:
            return None
        if self._native_cache is None or self._native_cache[0] != frameidx:
            self._native_cache = (frameidx, native.read(frameidx))
        return self._native_cache[1][y0:y1, x0:x1], x0, y0, sx, sy

    def release(self) -> None:
        """
        Release the video reader resources.
        """
        if self._vidreader:
            self._vidreader.release()
        if self._nativereader:
            self._nativereader.release()
            self._nativereader = None
        self._native_cache = None

    # ---------------------------------------------------------------------------------------------
    def crop_intime(self) -> None:
        """
        Automatically detect active duration in the video using motion scoring.
        """
        if not self._vidreader:
            raise RuntimeError("VideoReader not initialized.")

        bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16,
                                                           detectShadows=True)

        motion_scores = []
        for _ in range(self.fcount):
            frame = self._vidreader.read()
            mask = bg_subtractor.apply(frame)
            score = 0 if len(motion_scores) == 0 else np.sum(mask) / 255
            motion_scores.append(score)

        motion_scores = np.array(motion_scores)
        motion_scores = motion_scores / np.max(motion_scores)

        scores_bin = []
        win_len = 15
        for i in range(1, self.fcount + 1):
            window = motion_scores[max(0, i - win_len):i]
            scores_bin.append(1 if np.mean(window) > 0.4 else 0)

        self._vidreader.seek(0)

        groups = []
        idx = 0
        for _, group in groupby(scores_bin):
            g = list(group)
            if sum(g) >= 0.8 * len(g):
                groups.append((idx, idx + len(g)))
            idx += len(g)

        if not groups:
            raise RuntimeError("No active motion segment found.")

        groups = sorted(groups, key=lambda g: g[1] - g[0], reverse=True)
        start, end = groups[0]

        start = max(start - 20, 0)
        end = min(end + 20, self._vidreader.fcount)

        self.active_duration = list(range(start, end))
        self.fcount = len(self.active_duration)

    # ---------------------------------------------------------------------------------------------
    def pts2pt(self, pts: np.ndarray, ptoff: tuple[int, int]) -> tuple[int, int]:
        """
        Convert a collection of (x, y) points to a single mean point.

        Args:
            pts (np.ndarray): Array of shape (N, 2) or (N, 1, 2).
            ptoff (tuple[int, int]): Offset to apply to the mean point.

        Returns:
            tuple[int, int]: Mean (x, y) as integer coordinates.
        """
        if pts.shape[0] == 0:
            return ptoff[0], ptoff[1]
        
        pts = pts.reshape(-1, 2)
        x, y = np.mean(pts, axis=0)
        return floor(x) + floor(ptoff[0]), floor(y) + floor(ptoff[1])
# -------------------------------------------------------------------------------------------------
###################################################################################
# ---------------------------------- Experiment Class ---------------------------------------------