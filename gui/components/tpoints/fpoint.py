"""
fpoint.py

This module defines the FPoint class for creating, drawing, and removing interactive 
points on a CustomTkinter canvas. These points are intended to be part of a graphical 
interface that tracks and allows interaction with motion paths or individual markers.

Classes:
    FPoint: Represents a single point that can be drawn on and removed from a canvas.

Typical usage:
    point = FPoint([100, 200], fx=5, fy=10, button=delete_button)
    point.draw(canvas)
    point.undraw(canvas)
"""

class FPoint:
    """
    Represents a single interactive and drawable point on a canvas.
    
    Attributes:
        x (float): X-coordinate of the point (after offset).
        y (float): Y-coordinate of the point (after offset).
        button (CTkButton): A reference to a button (e.g., delete button).
        cpt (int | None): Canvas object ID if drawn, otherwise None.
    """
    def __init__(self, pt, fx, fy, button):
        """
        Initialize a point with position offset and button reference.

        Args:
            pt (list | tuple): Original [x, y] coordinates.
            fx (float): X-axis offset.
            fy (float): Y-axis offset.
            button (CTkButton): Associated button (e.g. for deletion).
        """
        self.x, self.y = pt.copy()
        self.x += fx
        self.y += fy
        self.button = button
        self.cpt = None  # Canvas point ID

    def draw(self, canvas):
        """
        Draw the point on the canvas if not already drawn.

        Args:
            canvas (CTkCanvas): The canvas to draw on.
        """
        if self.cpt is not None:
            return

        self.cpt = canvas.create_oval(
            self.x - 6, self.y - 6, self.x + 6, self.y + 6,
            fill='magenta', outline='black', width=1,
            tags="points"
        )

    def undraw(self, canvas):
        """
        Remove the point from the canvas if it exists.

        Args:
            canvas (CTkCanvas): The canvas to remove from.
        """
        if self.cpt is not None:
            canvas.delete(self.cpt)
            self.cpt = None
