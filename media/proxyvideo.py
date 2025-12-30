"""
proxyvideo.py

Generate a low-resolution proxy video for fast frame seeking.

Author: Isam Balghari
"""

import os
import subprocess
from typing import Optional
import logging

from core import abspath

def proxyvideo(videopath: str, width: int = 1000, height: int = -2, 
               writepath: Optional[str] = None, overwrite: bool = False) -> Optional[str]:
    """
    Create a low-resolution proxy video using ffmpeg.

    Args:
        videopath: Path to the original high-res video.
        width: Target width for the proxy video (e.g., 640).
        height: Target height (e.g., -2 preserves aspect ratio).
        writepath: Optional output path. If None, auto-generated.
        overwrite: Whether to overwrite an existing proxy video.

    Returns:
        Path to the generated proxy video or None if failed.
    """
    logger = logging.getLogger(__name__)

    if not os.path.isfile(videopath):
        logger.error(f"Input video not found: {videopath}")
        return None

    # Default proxy output path
    if writepath is None:
        base, ext = os.path.splitext(os.path.basename(videopath))
        writepath = os.path.join("./temp", f"{base}_proxy{ext}")

    if os.path.exists(writepath) and not overwrite:
        logger.info(f"Proxy already exists: {writepath}")
        return writepath

    os.makedirs(os.path.dirname(writepath), exist_ok=True)

    resolution = f"{width}:{height}"
    
    ffmpeg = abspath("ffmpeg/ffmpeg.exe")

    command = [ffmpeg, "-y" if overwrite else "-n", "-i", videopath, "-vf", 
               f"scale={resolution}", "-c:v", "libx264", "-preset", "fast", "-crf", "28", "-an",
               writepath]

    logger.info(f"Creating proxy video: {writepath}")
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info(f"Proxy created: {writepath}")
        return writepath
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e}")
        print(' '.join(command))
        return None
