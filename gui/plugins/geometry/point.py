
from typing import Self

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
    def distance(self, point: Self) -> float:
        """Calculate distance to another point."""
        return ((self.x - point.x) ** 2 + (self.y - point.y) ** 2) ** 0.5
    
    def meets(self, point: Self, threshold: float = 10.0) -> bool:
        """Check if this point is within a certain distance of another point."""
        # print('dist: ', self.distance(point))
        return self.distance(point) <= threshold