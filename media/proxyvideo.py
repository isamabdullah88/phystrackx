"""
proxyvideo.py

Generate a low-resolution proxy video for fast frame seeking.

Author: Isam Balghari
"""

import os
import subprocess
from typing import Optional
import logging


def proxyvideo(
    input_path: str,
    width: int = 640,
    height: int = -2,
    output_path: Optional[str] = None,
    overwrite: bool = False
) -> Optional[str]:
    """
    Create a low-resolution proxy video using ffmpeg.

    Args:
        input_path: Path to the original high-res video.
        width: Target width for the proxy video (e.g., 640).
        height: Target height (e.g., -2 preserves aspect ratio).
        output_path: Optional output path. If None, auto-generated.
        overwrite: Whether to overwrite an existing proxy video.

    Returns:
        Path to the generated proxy video or None if failed.
    """
    logger = logging.getLogger(__name__)

    if not os.path.isfile(input_path):
        logger.error(f"Input video not found: {input_path}")
        return None

    # Default proxy output path
    if output_path is None:
        base, ext = os.path.splitext(os.path.basename(input_path))
        output_path = os.path.join("./temp", f"{base}_proxy{ext}")

    if os.path.exists(output_path) and not overwrite:
        logger.info(f"Proxy already exists: {output_path}")
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    resolution = f"{width}:{height}"

    command = [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-i", input_path,
        "-vf", f"scale={resolution}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "28",
        "-an",  # remove audio
        output_path
    ]

    logger.info(f"Creating proxy video: {output_path}")
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info(f"Proxy created: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e}")
        return None
