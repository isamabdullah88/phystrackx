"""
savetype.py

Defines the types of data that can be saved during export.

Author: Isam Balghari
"""

from enum import Enum, auto

class SaveType(Enum):
    """
    Enum representing different save options for exported data.
    Each value corresponds to a component of the data file.
    """
    HEADER = auto()  # Include column headers in the CSV
    TIME = auto()    # Include timestamps
    XY = auto()      # Include (x, y) coordinates
    OCR = auto()     # Include OCR text data
