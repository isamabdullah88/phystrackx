"""
path.py

Utility functions for resolving absolute paths and checking file existence.

Author: Isam Balghari
"""

import os
import sys


def abspath(rpath: str) -> str:
    """
    Return the absolute path of a resource, handling PyInstaller context.

    Args:
        rpath: Relative path to the resource.

    Returns:
        Absolute path based on execution context.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, rpath)


def filexists(filepath: str) -> bool:
    """
    Check if the given file exists.

    Args:
        filepath: Path to the file.

    Returns:
        True if file exists, False otherwise.
    """
    return os.path.isfile(filepath)
