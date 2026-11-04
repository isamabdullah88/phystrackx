"""
trimvideo.py

Trim a video between two frame indices using ffmpeg.

Author: Isam Balghari
"""

import os
import subprocess
from typing import Optional
import logging

from core import find_ffmpeg

def trimvideo(videopath: str, writepath: str, startidx: int, endidx: int,
              fps: Optional[float] = None, overwrite: bool = True,
              crop: Optional[tuple[int, int, int, int]] = None) -> bool:
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
        
    video_filter = f"trim=start_frame={startidx}:end_frame={endidx+1},setpts=PTS-STARTPTS"
    if crop is not None:
        # Keep only the selected region; x, y, w, h are in pixels of the input video
        x, y, w, h = crop
        video_filter = f"crop={w}:{h}:{x}:{y}," + video_filter

    try:
        ffmpeg = find_ffmpeg()
    except FileNotFoundError as e:
        logger.error(str(e))
        return False

    # Write to a partial file and swap it in on success. Trimming a clip into its own path would
    # otherwise destroy the input while FFmpeg is still reading it, and a failed trim would
    # leave nothing usable behind.
    partial = f"{os.path.splitext(writepath)[0]}.partial.mp4"
    command = [ffmpeg, "-y" if overwrite else "-n", "-i", videopath, "-vf", video_filter,
               partial]

    logger.info(f"Trimming video: {videopath} → {writepath}")
    logger.debug(f"Command: {' '.join(command)}")

    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e}")
        if os.path.exists(partial):
            os.remove(partial)
        return False

    os.replace(partial, writepath)
    logger.info(f"Trim successful: {writepath}")
    return True
