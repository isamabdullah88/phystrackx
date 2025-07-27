"""
viewseekbar.py

This module implements the ViewSeekBar class, which displays a fixed seek region and a
draggable bar to view the current frame position within a video.

Author: Isam Balghari
"""

import tkinter as tk
from typing import Optional, Callable
from .seek import Seek
from .bar import Bar


class ViewSeekBar:
    """
    View-only seek bar for displaying a fixed seek region and a draggable bar to
    represent video playback position.
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
        Initialize the ViewSeekBar widget.

        Args:
            frame (tk.Frame): Parent frame to attach the canvas.
            width (int): Width of the seekbar canvas.
            height (int): Height of the seekbar canvas.
            fcount (int): Total number of frames in the video.
            callback (Optional[Callable]): Function called when bar is moved.
        """
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount: int = fcount
        self.padx: int = 10
        self.width: int = width
        self.height: int = height
        self.callback: Optional[Callable] = callback
        self.idx: int = 0
        self.xstart: int = 0
        self.xend: int = 100

        self.seek: Optional[Seek] = None
        self.seekbar: Optional[Bar] = None
        self.disable: bool = False

    def setparams(self) -> None:
        """
        Calculate and update internal layout parameters.
        """
        self.xstart: int = self.padx
        self.xend: int = self.width - self.padx

        if self.seekbar:
            self.seekbar.setcount(self.fcount)

    def clear(self) -> None:
        """
        Clear the seek bar from the canvas.
        """
        if self.seekbar:
            self.seekbar.clear()

    def pack(self) -> None:
        """
        Draw and initialize the seek and bar widgets on the canvas.
        """
        self.clear()
        self.setparams()

        self.seek = Seek(
            self.canvas,
            self.xstart,
            self.xend,
            self.height / 2,
            color="#9c97d6"
        )
        self.seek.pack()

        self.seekbar = Bar(
            self.canvas,
            self.xstart,
            self.xstart,
            self.xend,
            self.height / 2,
            self.fcount,
            callback=self.callback
        )
        self.seekbar.pack()

        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)

    def set(self, fcount: int) -> None:
        """
        Update the total frame count and reconfigure the layout.

        Args:
            fcount (int): New total number of frames.
        """
        self.fcount = fcount
        self.setparams()

    def onclick(self, event: tk.Event) -> None:
        """
        Handle mouse click events on the canvas.

        Args:
            event (tk.Event): Tkinter event object.
        """
        if self.seekbar:
            self.seekbar.onclick(event)

    def ondrag(self, event: tk.Event) -> None:
        """
        Handle mouse drag events and update the seekbar position.

        Args:
            event (tk.Event): Tkinter event object.
        """

        def clamp(x: float, xlim: float) -> float:
            return min(x, xlim)

        if self.seekbar:
            self.seekbar.ondrag(event, clamp, self.xend)
            self.idx = self.seekbar.idx


class App(tk.Tk):
    """
    Minimal example application demonstrating the ViewSeekBar.
    """

    def __init__(self) -> None:
        """
        Initialize the demo application.
        """
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = tk.Frame(self, width=700, height=300)
        self.frame.pack(fill="both", expand=True)

        self.seekbar = ViewSeekBar(
            self.frame,
            width=700,
            height=100,
            fcount=100,
            callback=self.callback
        )
        self.seekbar.pack()

    def callback(self) -> None:
        """
        Sample callback to be invoked on bar movement.
        """
        print("callback called:", time.time())


if __name__ == "__main__":
    import time
    app = App()
    app.mainloop()
