"""
experiment.py

Handles video loading, trimming, proxy resizing, and motion-based frame filtering
for time-bounded experiments.

Author: Isam Balghari
"""

import os
import sys
from math import floor
from itertools import groupby

import cv2
import numpy as np

from media.videoreader import VideoReader
from media import proxyvideo, trimvideo


class Experiment:
    """
    Handles video preprocessing, proxy generation, trimming, and motion analysis
    for frame selection.
    """

    def __init__(self, trimpath: str, vwidth: int, vheight: int) -> None:
        self._setup_logging()

        self._vidreader: VideoReader | None = None
        self.fwidth: int | None = None
        self.fheight: int | None = None
        self.fps: int = 0
        self.fcount: int = 0

        self.vwidth: int = vwidth
        self.vheight: int = vheight

        self.videopath: str | None = None
        self.proxypath: str | None = None
        self.trimpath: str = trimpath
        self.active_duration: list[int] = []

    def _setup_logging(self) -> None:
        if not sys.stdout or not sys.stdout.isatty():
            os.makedirs("logs", exist_ok=True)
            sys.stdout = open("logs/stdout.log", "a")
            sys.stderr = open("logs/stderr.log", "a")

    def addvideo(self, videopath: str) -> None:
        """
        Load the video and extract dimensions and frame count.
        """
        self.videopath = videopath
        self._vidreader = VideoReader(videopath)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        self.fps = self._vidreader.fps
        self.resize()

    def resize(self) -> None:
        """
        Resize dimensions to fit inside the viewer while maintaining aspect ratio.
        """
        ratio = self.fwidth / self.fheight
        self.fheight = self.vheight
        self.fwidth = floor(self.fheight * ratio)
        
        # Width and height must be even for ffmpeg
        self.fwidth = floor(self.fwidth/2)*2
        self.fheight = floor(self.fheight/2)*2

        # Generate proxy video
        self._proxymize()

    def _proxymize(self) -> None:
        """
        Create a lower-resolution proxy video and update internal reader.
        """
        os.makedirs("./temp", exist_ok=True)
        self.videopath = proxyvideo(self.videopath, width=self.fwidth, height=self.fheight)
        self._vidreader = VideoReader(self.videopath)

        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        self.fps = self._vidreader.fps

    def trim(self, startidx: int = 0, endidx: int = 0) -> None:
        """
        Trim the video between specified frame indices using FFmpeg.

        Args:
            startidx (int): Starting frame index.
            endidx (int): Ending frame index.
        """
        trimvideo(self.videopath, self.trimpath, startidx, endidx, self.fps)

    def frame(self, index: int | None = None) -> np.ndarray:
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

    def release(self) -> None:
        """
        Release the video reader resources.
        """
        if self._vidreader:
            self._vidreader.release()

    def crop_intime(self) -> None:
        """
        Automatically detect active duration in the video using motion scoring.
        """
        if not self._vidreader:
            raise RuntimeError("VideoReader not initialized.")

        bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=True
        )

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

    def pts2pt(self, pts: np.ndarray) -> tuple[int, int]:
        """
        Convert a collection of (x, y) points to a single mean point.

        Args:
            pts (np.ndarray): Array of shape (N, 2) or (N, 1, 2).

        Returns:
            tuple[int, int]: Mean (x, y) as integer coordinates.
        """
        pts = pts.reshape(-1, 2)
        x, y = np.mean(pts, axis=0)
        return floor(x), floor(y)
