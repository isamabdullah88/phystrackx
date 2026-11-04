"""
path.py

Utility functions for resolving absolute paths and checking file existence.

Author: Isam Balghari
"""

import os
import platform
import shutil
import sys


def abspath(rpath: str) -> str:
    """
    Return the absolute path of a resource, handling PyInstaller context.

    Args:
        rpath: Relative path to the resource.

    Returns:
        Absolute path based on execution context.
    """
    if hasattr(sys, "_MEIPASS"):  # PyInstaller temp directory
        return os.path.join(sys._MEIPASS, rpath)
    # Resources live in the project folder, whatever the working directory is (tests run elsewhere)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rpath)


def find_ffmpeg() -> str:
    """
    Locate an ffmpeg executable.

    Lookup order:
        1. System PATH.
        2. Bundled copy in the project's ffmpeg/ folder (or PyInstaller bundle).
        3. The binary shipped with the imageio-ffmpeg package.

    Returns:
        Path or command name to invoke ffmpeg with.

    Raises:
        FileNotFoundError: If ffmpeg cannot be found by any method.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    exe = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    bundled = abspath(os.path.join("ffmpeg", exe))
    if os.path.isfile(bundled):
        return bundled

    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise FileNotFoundError("ffmpeg not found in PATH, the ffmpeg/ folder, or imageio-ffmpeg")


def filexists(filepath: str) -> bool:
    """
    Check if the given file exists.

    Args:
        filepath: Path to the file.

    Returns:
        True if file exists, False otherwise.
    """
    return os.path.isfile(filepath)
