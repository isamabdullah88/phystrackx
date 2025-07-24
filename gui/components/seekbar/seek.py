from typing import Optional
import tkinter as tk


class Seek:
    """
    Draws and manages a seek line — a horizontal bar used to visualize progress or range selection.
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        xstart: float,
        xend: float,
        y: float,
        color: str = "#e2bcc5",
        height: int = 8
    ) -> None:
        """
        Initialize the Seek bar.

        Args:
            canvas: The canvas to draw on.
            xstart: Left x-bound of the seek bar.
            xend: Right x-bound of the seek bar.
            y: Vertical center position of the seek bar.
            height: Thickness of the seek bar.
        """
        self.canvas = canvas
        self.xstart = xstart
        self.xend = xend
        self.y = y
        self.hhalf = height / 2
        self.color = color

        self.tkrect: Optional[int] = None

    def pack(self) -> None:
        """Packs the seek."""
        self.tkrect = self.canvas.create_rectangle(
            self.xstart,
            self.y - self.hhalf,
            self.xend,
            self.y + self.hhalf,
            fill=self.color
        )

    def draw(
        self, 
        xstart: float,
        xend: float
    ) -> None:
        """Draws the seek."""
        if self.tkrect is not None:
            self.canvas.coords(
                self.tkrect,
                xstart,
                self.y - self.hhalf,
                xend,
                self.y + self.hhalf
            )

    def clear(self) -> None:
        """Remove all parts of the seek bar from the canvas."""
        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)
            self.tkrect = None

        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)
            self.tkrect = None
