"""
trimvideo.py

Trim a video between two frame indices using ffmpeg.

Author: Isam Balghari
"""

import os
import sys
import subprocess
from typing import Optional
import logging

def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller bundle.
    """
    if hasattr(sys, "_MEIPASS"):  # PyInstaller temp directory
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def trimvideo(
    videopath: str,
    writepath: str,
    startidx: int,
    endidx: int,
    fps: Optional[float] = None,
    overwrite: bool = True
) -> bool:
    """
    Trim a video between startidx and endidx using ffmpeg.

    Args:
        videopath: Path to the input video file.
        writepath: Path to save the trimmed video.
        startidx: Start frame index (inclusive).
        endidx: End frame index (exclusive).
        fps: Frames per second of the video. If None, assumes 30.
        overwrite: Whether to overwrite output file if it exists.

    Returns:
        True if trimming succeeded, False otherwise.
    """
    logger = logging.getLogger(__name__)

    if not os.path.exists(videopath):
        logger.error(f"Input video does not exist: {videopath}")
        return False

    if startidx >= endidx:
        logger.error("Invalid frame range: startidx >= endidx")
        return False

    if fps is None:
        fps = 30.0  # Default if not given

    start_time = startidx / fps
    duration = (endidx - startidx) / fps

    ffmpeg = resource_path("ffmpeg/ffmpeg.exe")
    command = [
        ffmpeg,
        "-y" if overwrite else "-n",
        "-i", videopath,
        "-ss", str(start_time),
        "-to", str(duration+start_time),
        "-c",
        "copy",
        writepath
    ]

    logger.info(f"Trimming video: {videopath} → {writepath}")
    logger.debug(f"Command: {' '.join(command)}")

    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info(f"Trim successful: {writepath}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e}")
        return False
