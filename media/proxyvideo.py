"""
proxyvideo.py

Generate a low-resolution proxy video for fast frame seeking.

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


def proxyvideo(
    videopath: str,
    width: int = 640,
    height: int = -2,
    writepath: Optional[str] = None,
    overwrite: bool = False
) -> Optional[str]:
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
    
    ffmpeg_bin = resource_path("ffmpeg/ffmpeg.exe")

    command = [
        ffmpeg_bin,
        "-y" if overwrite else "-n",
        "-i", videopath,
        "-vf", f"scale={resolution}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "28",
        "-an",  # remove audio
        writepath
    ]

    logger.info(f"Creating proxy video: {writepath}")
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info(f"Proxy created: {writepath}")
        return writepath
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e}")
        return None
