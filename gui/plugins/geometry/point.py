"""Point representation for geometry plugin in PhysTrackX."""

from dataclasses import dataclass
import math
from typing import Self

@dataclass
class Point:
    """Point representation for geometry plugin in PhysTrackX."""
    x: float
    y: float

    def distance(self, point: Self) -> float:
        """Calculate Euclidean distance to another point."""
        return math.hypot(self.x - point.x, self.y - point.y)

    def meets(self, point: Self, threshold: float = 10.0) -> bool:
        """Check if this point is within a certain distance of another point."""
        return self.distance(point) <= threshold

    def as_tuple(self) -> tuple[float, float]:
        """Return the point as an (x, y) tuple."""
        return (self.x, self.y)
