from math import ceil
import tkinter as tk
from typing import Optional, Callable
from .seek import Seek
from .bar import Bar


class ViewSeekBar:
    """
    Seekbar that is view-only and acts as a video viewer.
    It does not support trimming. It displays a fixed seek region
    and a draggable bar to view the current position.
    """

    def __init__(
        self,
        frame: tk.Frame,
        width: int,
        height: int,
        fcount: int = 100,
        callback: Optional[Callable] = None
    ) -> None:
        """
        Initialize the ViewSeekBar.

        Args:
            frame: Parent Tkinter frame.
            width: Width of the seekbar canvas.
            height: Height of the seekbar canvas.
            fcount: Total number of frames.
            callback: Callback function on bar movement.
        """
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self.padx = 10
        self.width = width
        self.height = height
        self.callback = callback

        self.sheight = 8
        self.fixedseek: Optional[Seek] = None
        self.leftbar: Optional[Bar] = None

    def setparams(self) -> None:
        """Set internal layout parameters based on current frame count."""
        self.idx = ceil(0.01 * self.fcount)
        self.xstart = self.padx
        self.xend = self.width - self.padx
        print('xend: ', self.xend)

        if self.leftbar is not None:
            self.leftbar.setcount(self.fcount)

    def clear(self) -> None:
        """Clear bar from canvas."""
        if self.leftbar is not None:
            self.leftbar.clear()

    def pack(self) -> None:
        """Render the seek and bar on the canvas."""
        self.clear()
        self.setparams()

        self.fixedseek = Seek(
            self.canvas,
            self.xstart,
            self.xend,
            self.height / 2,
            color="#9c97d6"
        )
        self.fixedseek.pack()

        self.leftbar = Bar(
            self.canvas,
            self.xstart,
            self.xstart,
            self.xend,
            self.height / 2,
            self.fcount,
            callback=self.callback
        )
        self.leftbar.pack()

        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)

    def set(self, fcount: int) -> None:
        """Update frame count and refresh internal parameters."""
        self.fcount = fcount
        self.setparams()

    def onclick(self, event: tk.Event) -> None:
        """Handle mouse click event."""
        self.leftbar.onclick(event)

    def ondrag(self, event: tk.Event) -> None:
        """Handle drag event and update the seekbar."""
        func = lambda x, xlim: min(x, xlim)
        self.leftbar.ondrag(event, func, self.xend)
        self.fixedseek.draw(self.leftbar.xstart, self.leftbar.xend)


# --- Optional minimal test app ---



class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = tk.Frame(self, width=700, height=300)
        self.frame.pack(fill="both", expand=True)

        self.seekbar = ViewSeekBar(self.frame, 700, 100, fcount=100, callback=self.callback)
        self.seekbar.pack()

    def callback(self):
        print('callback called: ' + str(time.time()))


if __name__ == "__main__":
    import time
    app = App()
    app.mainloop()
