"""
bar.py

Defines the Bar class, a draggable vertical marker for a seek bar interface.

Author: Isam Balghari
"""

from math import floor
from typing import Callable, Optional
import tkinter as tk


class Bar:
    """
    A draggable vertical bar on a canvas representing a position in a frame timeline.
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        x: float,
        xstart: float,
        xend: float,
        y: float,
        fcount: int,
        color: str = "#de459b",
        callback: Optional[Callable[[], None]] = None,
        width: int = 6,
        height: int = 50
    ) -> None:
        """
        Initialize the draggable bar.

        Args:
            canvas: Parent canvas.
            x: Initial x position.
            xstart: Minimum x-bound.
            xend: Maximum x-bound.
            y: Center y-position.
            fcount: Total number of frames.
            color: Bar fill color.
            callback: Function to call on movement.
            width: Width of the bar.
            height: Height of the bar.
        """
        self.canvas = canvas
        self.xstart = xstart
        self.xend = xend
        self.y = y
        self.fcount = fcount
        self.callback = callback

        self.width = width
        self.height = height
        self.whalf = width / 2
        self.hhalf = height / 2

        self.color = color
        self.x = x
        self.idx = self._x2fidx(self.x)

        self.tkrect = None
        self.clicked = False
        self.trigger = True

    def setcount(self, fcount: int) -> None:
        """
        Update frame count and recalculate current index.

        Args:
            fcount: New total frame count.
        """
        self.fcount = fcount
        self.idx = self._x2fidx(self.x)

    def pack(self) -> None:
        """
        Draw the bar on the canvas.
        """
        self.tkrect = self.canvas.create_rectangle(
            self.x - self.whalf, self.y - self.hhalf,
            self.x + self.whalf, self.y + self.hhalf,
            fill=self.color,
            outline=""
        )
        self.canvas.tag_raise(self.tkrect)

    def unpack(self):
        self.canvas.itemconfigure(self.tkrect, state="hidden")

    def clear(self) -> None:
        """
        Remove the bar from the canvas.
        """
        if self.tkrect:
            self.canvas.delete(self.tkrect)
            self.tkrect = None

    def onclick(self, event: tk.Event) -> None:
        """
        Handle mouse click on the canvas.

        Args:
            event: Mouse click event.
        """
        self.clicked = self._contains(event.x)

    def ondrag(
        self,
        event: tk.Event,
        adjust_fn: Callable[[float, float], float],
        xlim: float
    ) -> None:
        """
        Handle drag interaction and redraw bar.

        Args:
            event: Mouse drag event.
            adjust_fn: Adjustment function for new x (e.g., snapping or constraint).
            xlim: Additional constraint passed to adjust_fn.
        """
        if not self.clicked:
            return

        x = event.x

        if x < self.xstart:
            x = self.xstart
            self.trigger = False
        elif x > self.xend:
            x = self.xend
            self.trigger = False
        else:
            self.trigger = True

        self.x = adjust_fn(x, xlim)

        self.canvas.coords(
            self.tkrect,
            self.x - self.whalf, self.y - self.hhalf,
            self.x + self.whalf, self.y + self.hhalf
        )

        self.idx = self._x2fidx(self.x)

        if self.trigger and self.callback:
            self.callback()

    def _contains(self, x: float) -> bool:
        """
        Check if x-coordinate is within draggable area.

        Args:
            x: X-coordinate to test.

        Returns:
            True if x is within bar bounds.
        """
        return abs(x - self.x) < self.whalf

    def _x2fidx(self, x: float) -> int:
        """
        Convert x-coordinate on canvas to frame index.

        Args:
            x: X-position.

        Returns:
            Corresponding frame index.
        """
        effective_width = self.xend - self.xstart + 2 * self.whalf
        adjusted_x = x - (self.xstart - self.whalf)
        return floor(adjusted_x / effective_width * self.fcount)


# --- Minimal test application --- #

class App(tk.Tk):
    """
    A minimal app to demonstrate the Bar widget.
    """

    def __init__(self) -> None:
        super().__init__()
        self.geometry("800x500")
        self.title("Bar Widget Test")

        self.canvas = tk.Canvas(self, width=700, height=300, bg="#4d535c")
        self.canvas.pack(pady=40)

        self.bar = Bar(
            canvas=self.canvas,
            x=100,
            xstart=0,
            xend=700,
            y=100,
            fcount=100,
            callback=self.bar_update
        )
        self.bar.pack()

        # Bind canvas interactions
        self.canvas.bind("<Button-1>", self.bar.onclick)
        self.canvas.bind(
            "<B1-Motion>",
            lambda e: self.bar.ondrag(e, lambda x, _: x, 0)
        )

    def bar_update(self) -> None:
        print("Bar moved to index:", self.bar.idx)


if __name__ == "__main__":
    app = App()
    app.mainloop()
