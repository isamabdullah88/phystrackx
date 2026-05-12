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

import os
import platform
import logging
import subprocess
from typing import Optional
from core.path import abspath

def proxyvideo(videopath: str, width: int = 1000, height: int = -2, 
               writepath: Optional[str] = None, overwrite: bool = False) -> Optional[str]:
    """
    Create a low-resolution proxy video using ffmpeg. 
    Automatically bakes in rotation metadata and outputs as a standard .mp4.

    Args:
        videopath: Path to the original high-res video.
        width: Target width for the proxy video (e.g., 1000).
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

    # Force the proxy output to be an .mp4 container.
    # This destroys the proprietary .MOV metadata and bakes the rotation 
    # directly into the physical pixels for OpenCV.
    if writepath is None:
        base, _ = os.path.splitext(os.path.basename(videopath))
        writepath = os.path.join("./temp", f"{base}_proxy.mp4")
    else:
        # Ensure even a user-provided writepath ends in .mp4
        base, _ = os.path.splitext(writepath)
        writepath = f"{base}.mp4"

    if os.path.exists(writepath) and not overwrite:
        logger.info(f"Proxy already exists: {writepath}")
        return writepath

    os.makedirs(os.path.dirname(writepath), exist_ok=True)

    # Cross-platform FFmpeg execution
    if platform.system() == "Windows":
        ffmpeg = abspath("ffmpeg/ffmpeg.exe")
    else:
        ffmpeg = abspath("ffmpeg/ffmpeg")

    resolution = f"{width}:{height}"
    
    # By default, FFmpeg applies -autorotate before video filters.
    # So it will rotate the portrait video upright, THEN apply the scale filter.
    command = [
        'ffmpeg', 
        "-y" if overwrite else "-n", 
        "-i", videopath, 
        "-vf", f"scale={resolution}", 
        "-c:v", "libx264", 
        "-preset", "fast", 
        "-crf", "28", 
        "-an", # Strips audio to speed up proxy generation
        writepath
    ]

    logger.info(f"Creating proxy video: {writepath}")
    try:
        # Add text=True to cleanly capture FFmpeg error logs
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        logger.info(f"Proxy created: {writepath}")
        return writepath
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed with exit code {e.returncode}")
        # This will now log the actual red text FFmpeg spits out if it crashes!
        logger.error(f"FFmpeg Error Output:\n{e.stderr}") 
        return None
