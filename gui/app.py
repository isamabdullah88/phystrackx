"""
app.py

Main application window for PhysTrackX: Rigid Body Tracker.

This module defines the user interface structure and essential logic for
loading videos, interacting with toolbars, and initializing tracking operations.

Author: Isam Balghari
"""

from math import floor
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image

from core import abspath
from .components.titlebar import TitleBar
from .components.axes import Axes
from .components.tooltip import ToolTip


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PhysTrackX")

        # Window dimensions
        self.cwidth = 1280
        self.cheight = 800
        self.padx = floor(self.cwidth * 0.01)
        self.pady = floor(self.cheight * 0.01)
        self.root.geometry(f"{self.cwidth}x{self.cheight}")

        # Layout configuration
        self.twidth = floor(self.cwidth * 0.1)
        self.theight = self.cheight
        self.seekbarh = floor(self.cheight * 0.1)
        self.btnsize = self.twidth - 40

        self.vwidth = self.cwidth - self.twidth
        self.vheight = self.theight - self.seekbarh
        self.fwidth = self.vwidth
        self.fheight = self.vheight

        self.btnlist = {}

        self.toolbar()
        self.root.protocol("WM_DELETE_WINDOW", self.onclose)

        self.videopath = None

    def mkbutton(self, imgpath: str, command: callable) -> ctk.CTkButton:
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath))
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(self.btnsize, self.btnsize))
        button = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                               image=img, command=command)
        button.pack(padx=5, pady=5)
        button.image = img  # prevent garbage collection
        return button

    def toolbar(self) -> None:
        """Constructs toolbar and video area layout."""
        self.scrollframe = ctk.CTkScrollableFrame(self.root, width=self.twidth-20, height=self.theight,
                                                  bg_color="#899fbd", fg_color="#5bdada")
        self.scrollframe.pack(side=ctk.LEFT)

        buttons = [
            ("assets/video.png", self.openvideo, "Load Video File"),
            ("assets/seek.png", self.loadseek, "Trim Video"),
            ("assets/axis.png", self.markaxes, "Setup Coordinate Axes"),
            ("assets/ruler.png", self.scale, "Add Scale"),
            ("assets/rectanglebd.png", self.drawrect, "Mark Objects"),
            ("assets/track.png", self.strack, "Start Tracking"),
            ("assets/plot.png", self.plot, "Plot Tracked Data"),
            ("assets/save.png", self.savedata, "Save Tracked Data"),
            ("assets/reset.png", self.reset, "Clear Everything")
        ]

        for imgpath, command, tooltip in buttons:
            btn = self.mkbutton(imgpath, command)
            ToolTip(btn, tooltip)
            self.btnlist[imgpath.split('/')[-1][:-4]] = btn

        # Video panel layout
        self.vidframe = ctk.CTkFrame(self.root, width=self.vwidth, height=self.theight,
                                     bg_color="#899fbd", fg_color="#5bdada")
        self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT)

        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="#4d535c")
        self.videoview.pack_propagate(False)
        self.videoview.pack(side=ctk.TOP, expand=False)

        # Title and Axes setup
        self.title = TitleBar(self.videoview, self.vwidth, "Welcome!")
        self.axes = Axes(self.vidframe, self.videoview, self.vwidth, self.vheight,
                         self.btnlist, self.btnlist["axis"])

    def openvideo(self) -> None:
        """Open a video file using file dialog."""
        self.videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if self.videopath:
            self.loadvideo(self.videopath)

    def loadseek(self) -> None:
        """Placeholder for seek bar (trimming video)."""
        pass

    def markaxes(self) -> None:
        """Trigger axes placement."""
        self.axes.markaxes()

    def scale(self) -> None:
        """Placeholder for adding scale feature."""
        pass

    def drawrect(self) -> None:
        """Placeholder for marking regions/objects."""
        pass

    def strack(self) -> None:
        """
        Placeholder for tracking algorithm (Lucas-Kanade).
        Should track marked points frame-by-frame.
        """
        pass

    def plot(self) -> None:
        """Placeholder for plotting tracked data."""
        pass

    def savedata(self) -> None:
        """Placeholder for saving tracked data."""
        pass

    def reset(self) -> None:
        """Placeholder for resetting app state."""
        pass

    def onclose(self) -> None:
        """Clean shutdown on close."""
        self.root.destroy()

    def updateframe(self) -> None:
        """Placeholder for updating frame view (future animation hook)."""
        pass

    def resize(self, fwidth: int, fheight: int) -> None:
        """Resize content frame maintaining aspect ratio within video view."""
        if fwidth > self.vwidth:
            ratio = fheight / fwidth
            fwidth = self.vwidth
            fheight = floor(fwidth * ratio)

        if fheight > self.vheight:
            ratio = fwidth / fheight
            fheight = self.vheight
            fwidth = floor(fheight * ratio)

        self.fwidth = fwidth
        self.fheight = fheight
