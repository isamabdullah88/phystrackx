"""
plottype.py

Enum defining the types of plots available for visualization in the Plot component.

Author: Isam Balghari
"""

from enum import Enum, auto

class PlotType(Enum):
    X = auto()     # Position along x-axis vs time
    Y = auto()     # Position along y-axis vs time
    XY = auto()    # Trajectory (x vs y)
    DX = auto()    # First derivative (velocity) along x
    DY = auto()    # First derivative (velocity) along y
    D2X = auto()   # Second derivative (acceleration) along x
    D2Y = auto()   # Second derivative (acceleration) along y
