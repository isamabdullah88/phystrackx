"""Line segment representation for geometry plugin in PhysTrackX."""
import math
import tkinter as tk
from .point import Point


class Line:
    """
    Represents a line segment defined by two points and a tkinter canvas line ID.
    """
    def __init__(self, tkline: int, ptstart: Point, ptend: Point):
        self.tkline = tkline
        self.ptstart = ptstart
        self.ptend = ptend
        self.tktxt = None

    def is_pt_online(self, point: Point, threshold: float = 10.0) -> bool:
        """
        Check if a given point is within 'threshold' distance from this line segment.
        Uses orthogonal projection.
        """
        x0, y0 = point.x, point.y
        x1, y1 = self.ptstart.x, self.ptstart.y
        x2, y2 = self.ptend.x, self.ptend.y

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return False  # Line is a point

        # Project point onto the line segment
        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        distance = math.hypot(x0 - proj_x, y0 - proj_y)
        return distance <= threshold

    def label_length(self, canvas: tk.Canvas, color: str = "#5EDC16") -> None:
        """
        Draws the length of the line on the canvas at its midpoint.
        """
        mid_x = (self.ptstart.x + self.ptend.x) / 2
        mid_y = (self.ptstart.y + self.ptend.y) / 2
        length = self.ptstart.distance(self.ptend)

        self.tktxt = canvas.create_text(
            mid_x, mid_y,
            text=f"{length:.1f}",
            fill=color,
            font=("Arial", 9, "italic")
        )

    def clear(self, canvas: tk.Canvas):
        """
        Clears text.
        """
        if self.tktxt:
            canvas.delete(self.tktxt)

        if self.tkline:
            canvas.delete(self.tkline)

    def __repr__(self):
        return f"Line({self.ptstart}, {self.ptend})"
