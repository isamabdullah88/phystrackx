"""
fpoint.py

This module defines the ContPoint class for creating, drawing, and removing interactive 
points (or polygons) on a Tkinter canvas.

Author: Isam Balghari
"""

from typing import List, Tuple
import tkinter as tk


class ContPoint:
    """
    Represents an interactive polygon (or a set of points) on a canvas.
    
    Attributes:
        conts (List[Tuple[float, float]]): List of (x, y) coordinates.
        cpt (int | None): Canvas object ID if drawn, otherwise None.
    """
    def __init__(self, conts: List[Tuple[float, float]], fx: float, fy: float) -> None:
        """
        Initialize with a set of coordinates and apply an offset.

        Args:
            conts: List of (x, y) coordinates.
            fx: X-offset.
            fy: Y-offset.
        """
        # Apply offset to each point
        self.conts = [(x + fx, y + fy) for x, y in conts]
        self.cpt: int | None = None

    def draw(self, canvas: tk.Canvas) -> None:
        """Draw the polygon if not already drawn."""
        if self.cpt is not None:
            return
        flat = [coord for pt in self.conts for coord in pt]
        self.cpt = canvas.create_polygon(
            *flat,
            outline="magenta",
            fill="",
            width=2,
            smooth=False
        )

    def undraw(self, canvas: tk.Canvas) -> None:
        """Remove the polygon from the canvas."""
        if self.cpt is not None:
            canvas.delete(self.cpt)
            self.cpt = None

    def select(self, canvas: tk.Canvas) -> None:
        """Highlight the polygon."""
        if self.cpt is not None:
            canvas.itemconfig(self.cpt, fill='green', width=2)

    def deselect(self, canvas: tk.Canvas) -> None:
        """Remove highlight."""
        if self.cpt is not None:
            canvas.itemconfig(self.cpt, fill='magenta', width=1)


def main() -> None:
    """Test the ContPoint class in a standalone Tkinter window."""
    root = tk.Tk()
    root.title("ContPoint Test")

    canvas = tk.Canvas(root, width=500, height=400, bg="white")
    canvas.pack(fill=tk.BOTH, expand=True)

    # Example points
    points = [(50, 50), (150, 80), (200, 150), (120, 200), (60, 150)]
    
    # Create ContPoint with offsets
    poly = ContPoint(points, fx=50, fy=50)
    poly.draw(canvas)

    # Buttons to interact
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Select", command=lambda: poly.select(canvas)).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Deselect", command=lambda: poly.deselect(canvas)).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Undraw", command=lambda: poly.undraw(canvas)).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Redraw", command=lambda: poly.draw(canvas)).pack(side=tk.LEFT, padx=5)

    root.mainloop()


if __name__ == "__main__":
    main()