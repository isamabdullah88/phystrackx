"""
trimseekbar.py

This module defines the TrimSeekBar class for video trimming using two draggable bars
and dynamic seek regions.

Author: Isam Balghari
"""

import tkinter as tk
from typing import Optional, Callable
from math import ceil
import customtkinter as ctk
from PIL import Image
from core import abspath
from .seek import Seek
from .bar import Bar


class TrimSeekBar:
    """
    Seekbar widget with two draggable bars to allow video trimming.
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
        Initialize the TrimSeekBar.

        Args:
            frame (tk.Frame): Parent frame.
            width (int): Canvas width.
            height (int): Canvas height.
            fcount (int): Total number of frames.
            callback (Optional[Callable]): Callback on bar movement.
        """
        self.frame = frame
        
        self.btnsize: int = 50
        self.mintrim: int = 50
        self.fcount: int = fcount
        self.idx: int = 0
        self.padx: int = 0.01*width
        self.width: int = width - self.btnsize - 3*self.padx
        self.height: int = height
        self.xstart: int = self.padx
        self.xend: int = self.width - self.padx
        
        self.seekframe = None
        self.btnframe = None
        
        self.callback: Optional[Callable] = callback

        self.fixedseek: Optional[Seek] = None
        self.varseek: Optional[Seek] = None
        self.leftbar: Optional[Bar] = None
        self.rightbar: Optional[Bar] = None
        self.applybtn: ctk.CTkButton = None

        self.disable: bool = False
        self.trimvideo: Optional[Callable] = None
        self.loadvideo: Optional[Callable] = None

    @property
    def startidx(self) -> int:
        """Return index of the left bar."""
        return self.leftbar.idx if self.leftbar else 0

    @property
    def endidx(self) -> int:
        """Return index of the right bar."""
        return self.rightbar.idx if self.rightbar else self.fcount

    def setparams(self) -> None:
        """
        Set internal layout parameters based on frame count.
        """
        self.idx = ceil(0.01 * self.fcount)
        self.xstart = self.padx

        if self.leftbar:
            self.leftbar.setcount(self.fcount)
        if self.rightbar:
            self.rightbar.setcount(self.fcount)

    def clear(self) -> None:
        """
        Clear all seekcanvas elements related to trimming.
        """
        if self.leftbar:
            self.leftbar.clear()
        if self.rightbar:
            self.rightbar.clear()

        if self.fixedseek:
            self.fixedseek.clear()
        if self.varseek:
            self.varseek.clear()
        
        if self.seekframe is not None:
            self.seekframe.destroy()
        
        if self.btnframe is not None:
            self.btnframe.destroy()

    def pack(self) -> None:
        """
        Render seek regions and bars on the seekcanvas.
        """
        self.clear()
        self.setparams()
        
        self.seekframe = tk.Frame(self.frame)
        self.btnframe = tk.Frame(self.frame)
        self.seekcanvas = tk.Canvas(self.seekframe, width=self.width, height=self.height, bg="#4d535c")
        self.seekframe.pack(side="left", fill="x", expand=True)
        self.btnframe.pack(side="right", fill="x", expand=True)
        self.seekcanvas.pack()

        self.fixedseek = Seek(
            self.seekcanvas,
            self.xstart,
            self.xend,
            self.height / 2,
            color="#9c97d6"
        )
        self.fixedseek.pack()

        self.varseek = Seek(
            self.seekcanvas,
            self.xstart + self.padx,
            self.xend - self.padx,
            self.height / 2,
            color="#42f2c9"
        )
        self.varseek.pack()

        self.leftbar = Bar(
            self.seekcanvas,
            self.xstart + self.padx,
            self.xstart,
            self.xend,
            self.height / 2,
            self.fcount,
            callback=self.callback
        )
        self.leftbar.pack()

        self.rightbar = Bar(
            self.seekcanvas,
            self.xend - self.padx,
            self.xstart,
            self.xend,
            self.height / 2,
            self.fcount,
            callback=self.callback
        )
        self.rightbar.pack()

        self.seekcanvas.tag_raise(self.varseek.tkrect, self.fixedseek.tkrect)

        self.seekcanvas.bind("<Button-1>", self.onclick)
        self.seekcanvas.bind("<B1-Motion>", self.ondrag)

        self.applybtn = self.mkbutton("assets/apply.png", self.onapply, btnsize=self.btnsize)
        self.applybtn.pack(side="right")

    def unpack(self):
        self.fixedseek.unpack()
        self.varseek.unpack()
        self.leftbar.unpack()
        self.rightbar.unpack()

    def set(self, fcount: int) -> None:
        """
        Update frame count and layout.

        Args:
            fcount (int): New total frame count.
        """
        self.fcount = fcount
        self.setparams()

    def settrim(self, trimvideo: Callable) -> None:
        """
        Set external trimming and loading callbacks.

        Args:
            trimvideo (Callable): Function to perform trimming.
            loadvideo (Callable): Function to reload video.
        """
        self.trimvideo = trimvideo

    def onclick(self, event: tk.Event) -> None:
        """
        Handle mouse click on bars.

        Args:
            event (tk.Event): Tkinter event object.
        """
        if self.leftbar:
            self.leftbar.onclick(event)
        if self.rightbar:
            self.rightbar.onclick(event)

        if (self.leftbar and self.leftbar.clicked) or (
            self.rightbar and self.rightbar.clicked
        ):
            if self.callback:
                self.callback()

    def ondrag(self, event: tk.Event) -> None:
        """
        Handle drag motion and update bar and seek positions.

        Args:
            event (tk.Event): Tkinter event object.
        """
        if not self.leftbar or not self.rightbar or not self.fixedseek or not self.varseek:
            return

        self.varseek.draw(self.leftbar.x, self.rightbar.x)

        lfunc = lambda x, xlim: min(x, xlim - self.mintrim)
        self.leftbar.ondrag(event, lfunc, self.rightbar.x)

        rfunc = lambda x, xlim: max(x, xlim + self.mintrim)
        self.rightbar.ondrag(event, rfunc, self.leftbar.x)

        if self.leftbar.clicked:
            self.idx = self.startidx
        if self.rightbar.clicked:
            self.idx = self.endidx

    def onapply(self) -> None:
        """
        Apply trimming logic and reload video.
        """
        self.seekframe.pack_forget()
        self.btnframe.pack_forget()

        if self.trimvideo:
            self.trimvideo(self.startidx, self.endidx)
            self.set(self.endidx - self.startidx)

    def mkbutton(
        self,
        imgpath: str,
        command: Callable,
        btnsize: int = 30
    ) -> ctk.CTkButton:
        """
        Create a CTk image button on the seekcanvas.

        Args:
            imgpath (str): Path to image asset.
            command (Callable): Click event handler.
            btnsize (int): Size of button.

        Returns:
            ctk.CTkButton: The created button widget.
        """
        img = Image.open(abspath(imgpath)).resize(
            (btnsize, btnsize),
            Image.Resampling.LANCZOS
        )
        ctkimg = ctk.CTkImage(
            light_image=img,
            dark_image=img,
            size=(btnsize, btnsize)
        )
        
        self.btncanvas = tk.Canvas(self.btnframe, width=btnsize, height=btnsize)
        self.btncanvas.pack()
        button = ctk.CTkButton(
            self.btncanvas,
            text="",
            width=btnsize,
            height=btnsize,
            image=ctkimg,
            command=command
        )
        button.image = ctkimg  # prevent garbage collection
        return button


class App(tk.Tk):
    """
    Minimal test application for TrimSeekBar.
    """

    def __init__(self) -> None:
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = tk.Frame(self, width=700, height=300)
        self.frame.pack(fill="both", expand=True)

        self.seekbar = TrimSeekBar(
            self.frame,
            width=700,
            height=100,
            fcount=100,
            callback=self.callback
        )
        self.seekbar.pack()
        self.seekbar.settrim(self.trimvideo)

    def callback(self) -> None:
        """
        Sample callback for testing bar movement.
        """
        print("callback called:", time.time())

    def trimvideo(self, start: int, end: int) -> None:
        """
        Sample trimming function.

        Args:
            start (int): Start frame.
            end (int): End frame.
        """
        print("Trim", start, end)


if __name__ == "__main__":
    import time
    app = App()
    app.mainloop()
