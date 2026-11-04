"""
SeekType Enum for Seek Operations
This module defines the SeekType enum which categorizes different types of seek operations.
"""
from enum import Enum, auto

class SeekType(Enum):
    """
    Enum for different types of seek operations.
    FIXED: Fixed position, LEFT: Left side of the bar, RIGHT: Right side of the bar.
    """
    FIXED = auto()
    LEFT = auto()
    RIGHT = auto()
