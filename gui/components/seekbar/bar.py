from math import floor
from typing import Callable, Optional
import tkinter as tk


class Bar:
    """A draggable vertical bar on a seekbar canvas."""

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
    ):
        """
        Initialize the Bar.

        Args:
            canvas: The canvas on which to draw.
            x: Initial x position of the bar.
            xstart: Minimum x-bound.
            xend: Maximum x-bound.
            y: Y-position (center) of the bar.
            fcount: Total number of frames.
            color: Fill color of the bar.
            callback: Function to call when bar is dragged.
            width: Width of the bar.
            height: Height of the bar.
        """
        self.canvas = canvas
        self.xstart = xstart
        self.xend = xend
        self.y = y
        self.fcount = fcount

        self.whalf = width / 2
        self.hhalf = height / 2

        self.color = color
        self.callback = callback

        self.x = x
        self.idx = self.x2fidx(self.x)
        self.tkrect = None
        self.clicked = False
        self.trigger = True

    def setcount(self, fcount: int) -> None:
        """Update total frame count and recalculate index."""
        self.fcount = fcount
        self.idx = self.x2fidx(self.x)

    def pack(self) -> None:
        """Draw the bar on the canvas."""
        self.tkrect = self.canvas.create_rectangle(
            self.x - self.whalf, self.y - self.hhalf,
            self.x + self.whalf, self.y + self.hhalf,
            fill=self.color, outline=""
        )
        self.canvas.tag_raise(self.tkrect)

    def clear(self) -> None:
        """Remove the bar from the canvas."""
        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)
            self.tkrect = None

    def onclick(self, event: tk.Event) -> None:
        """Handle mouse click on the canvas."""
        self.clicked = self.contains(event.x)

    def ondrag(self, event: tk.Event, adjust_fn: Callable[[float, float], float], xlim: float) -> None:
        """
        Handle mouse drag motion.

        Args:
            event: Tkinter mouse event.
            adjust_fn: Function to optionally adjust x-position (e.g., snapping).
            xlim: Additional constraint for limit (passed to adjust_fn).
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

        # Update canvas object
        self.canvas.coords(
            self.tkrect,
            self.x - self.whalf, self.y - self.hhalf,
            self.x + self.whalf, self.y + self.hhalf
        )

        self.idx = self.x2fidx(self.x)

        if self.trigger and self.callback:
            self.callback()

    def contains(self, x: float) -> bool:
        """Return True if x is within the draggable bar's area."""
        return abs(x - self.x) < self.whalf

    def x2fidx(self, x: float) -> int:
        """Convert x-position to frame index."""
        adjusted_x = x - (self.xstart - self.whalf)
        return floor(adjusted_x / (self.xend - self.xstart + 2 * self.whalf) * self.fcount)


class App(tk.Tk):
    """Test application to demonstrate the Bar."""

    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Bar Test")

        self.canvas = tk.Canvas(self, width=700, height=300, bg="#4d535c")
        self.canvas.pack(pady=40)

        self.barobj = Bar(
            canvas=self.canvas,
            x=100,
            xstart=0,
            xend=700,
            y=100,
            fcount=100,
            callback=self.barupdate
        )
        self.barobj.pack()

        # Bind interactions
        self.canvas.bind("<Button-1>", self.barobj.onclick)
        self.canvas.bind("<B1-Motion>", lambda e: self.barobj.ondrag(e, lambda x, l: x, 0))

    def barupdate(self):
        print("Bar moved to index:", self.barobj.idx)


if __name__ == "__main__":
    app = App()
    app.mainloop()
