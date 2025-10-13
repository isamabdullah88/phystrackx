"""
video_reader.py

A lightweight OpenCV-based video reader class.

Author: Isam Balghari
"""

from math import floor
from typing import Optional
import logging
import cv2
import numpy as np


class VideoReader:
    """
    A simple wrapper for OpenCV's VideoCapture using the FFmpeg backend.
    Provides basic methods for frame reading and seeking.
    """

    def __init__(self, videopath: str) -> None:
        """
        Initialize the video reader.

        Args:
            videopath: Path to the video file.
        """
        self._reader = cv2.VideoCapture(videopath, cv2.CAP_FFMPEG)
        self._idx = 0
        self._start_idx = 0

        if not self._reader.isOpened():
            raise IOError(f"Unable to open video: {videopath}")

        self.fcount: int = floor(self._reader.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width: int = floor(self._reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height: int = floor(self._reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps: int = floor(self._reader.get(cv2.CAP_PROP_FPS))

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"VideoReader initialized at: {videopath}.")

    def read(self, index: Optional[int] = None) -> Optional[any]:
        """
        Read a single frame from the video.

        Args:
            index: Optional frame index to seek before reading.

        Returns:
            The read frame as a NumPy array, or None if reading fails.
        """
        if index is not None:
            self.seek(index)
            self._idx = index
        else:
            self._idx += 1

        ret, frame = self._reader.read()

        if not ret:
            self.logger.warning("Sending blank frame!")
            return np.zeros((self.height, self.width, 3), np.uint8)

        return frame

    def seek(self, index: int) -> None:
        """
        Seek to a specific frame index.

        Args:
            index: Frame number to seek to.
        """
        self._reader.set(cv2.CAP_PROP_POS_FRAMES, index)
        self.logger.debug(f"Seeked to frame {index}.")

    def release(self) -> None:
        """
        Release the video capture object.
        """
        self._reader.release()
        self.logger.info("VideoReader released.")
