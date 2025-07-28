"""
trimvideo.py

Trim a video between two frame indices using ffmpeg.

Author: Isam Balghari
"""

import os
import subprocess
from typing import Optional
import logging


def trimvideo(
    input_path: str,
    output_path: str,
    start_frame: int,
    end_frame: int,
    fps: Optional[float] = None,
    overwrite: bool = True
) -> bool:
    """
    Trim a video between start_frame and end_frame using ffmpeg.

    Args:
        input_path: Path to the input video file.
        output_path: Path to save the trimmed video.
        start_frame: Start frame index (inclusive).
        end_frame: End frame index (exclusive).
        fps: Frames per second of the video. If None, assumes 30.
        overwrite: Whether to overwrite output file if it exists.

    Returns:
        True if trimming succeeded, False otherwise.
    """
    logger = logging.getLogger(__name__)

    if not os.path.exists(input_path):
        logger.error(f"Input video does not exist: {input_path}")
        return False

    if start_frame >= end_frame:
        logger.error("Invalid frame range: start_frame >= end_frame")
        return False

    if fps is None:
        fps = 30.0  # Default if not given

    start_time = start_frame / fps
    duration = (end_frame - start_frame) / fps

    command = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-i", input_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-an",  # disable audio
        output_path
    ]

    logger.info(f"Trimming video: {input_path} → {output_path}")
    logger.debug(f"Command: {' '.join(command)}")

    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info(f"Trim successful: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e}")
        return False
