
import math
from .point import Point

class Line:
    def __init__(self, tkline, line):
        # line: selected line consisting of two points
        # tkline: Tkinter line used to display
        self.tkline = tkline
        self.line = line
        # self.selected = selected
        # self.tktext = tktext
        
    def ptonline(self, point:Point, threshold=10.0) -> bool:
        """Check if point is near a line segment."""
        startl, endl = self.line
        x0, y0 = point.x, point.y
        x1, y1 = startl.x, startl.y
        x2, y2 = endl.x, endl.y

        dx = x2 - x1
        dy = y2 - y1
        if dx == dy == 0:
            return False

        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / float(dx*dx + dy*dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        dist = math.hypot(x0 - proj_x, y0 - proj_y)
        return dist <= threshold