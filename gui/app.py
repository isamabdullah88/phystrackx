"""
app.py

Main application window for PhysTrackX: Rigid Body Tracker.

This module defines the user interface structure and essential logic for
loading videos, interacting with toolbars, and initializing tracking operations.

Author: Isam Balghari
"""

from logging import getLogger
from math import floor
from tkinter import filedialog, font
import customtkinter as ctk
from PIL import Image

from core import abspath
from .components.titlebar import TitleBar
from .components.axes import Axes
from .components.buttons import *


class App:
    def __init__(self, root):
        self.root = root

        self.logger = getLogger(__name__)
        self.logger.info("Initializing PhysTrackX Base App.")

        defaultfont = font.nametofont("TkDefaultFont")
        defaultfont.configure(family="Arial", size=14)

        self.root.update_idletasks()
        # Window dimensions
        self.cwidth = self.root.winfo_width()
        self.cheight = self.root.winfo_height()
        
        self.padx = floor(self.cwidth * 0.01)
        self.pady = floor(self.cheight * 0.01)
        
        # Layout configuration
        self.twidth = floor(self.cwidth * 0.1)
        self.theight = self.cheight
        self.seekbarh = floor(self.cheight * 0.1)
        self.btnsize = self.twidth - self.padx*5
        
        self.vwidth = self.cwidth - self.twidth - self.padx
        self.vheight = self.theight - self.seekbarh - self.pady
        self.fwidth = self.vwidth
        self.fheight = self.vheight
        self.logger.info(f"App dimensions set: Canvas({self.cwidth}x{self.cheight}), "
                         f"Toolbar({self.twidth}x{self.theight}), "
                         f"Video({self.vwidth}x{self.vheight})")

        self.btnlist = {}

        self.toolbar()
        self.root.protocol("WM_DELETE_WINDOW", self.onclose)

        self.videopath = None


    def toolbar(self) -> None:
        """Constructs toolbar and video area layout."""
        self.logger.info("Setting up scrollable toolbar and video area.")
        self.scrollframe = ctk.CTkScrollableFrame(self.root, width=self.twidth, height=self.theight,
                                                  bg_color="#899fbd", fg_color="#5bdada")
        self.scrollframe.pack(padx=0, pady=0, side=ctk.LEFT)
        self.root.update_idletasks()
        self.twidth = self.scrollframe.winfo_width()
        
        self.vwidth = self.cwidth - self.twidth - self.padx
        self.vheight = self.theight - self.seekbarh
        self.fwidth = self.vwidth
        self.fheight = self.vheight

        self.btnlist = {
            "video": VideoButton(self.scrollframe, command=self.openvideo, size=self.btnsize, tooltip="Load Video File"),
            "seek": SeekButton(self.scrollframe, command=self.loadseek, size=self.btnsize, tooltip="Trim Video"),
            "axis": AxisButton(self.scrollframe, command=self.markaxes, size=self.btnsize, tooltip="Setup Coordinate Axes"),
            "ruler": RulerButton(self.scrollframe, command=self.scale, size=self.btnsize, tooltip="Add Scale"),
            "rectangle": RectangleButton(self.scrollframe, command=self.drawrect, size=self.btnsize, tooltip="Mark Objects"),
            "track": TrackButton(self.scrollframe, command=self.strack, size=self.btnsize, tooltip="Start Tracking"),
            "plot": PlotButton(self.scrollframe, command=self.plot, size=self.btnsize, tooltip="Plot Tracked Data"),
            "save": SaveButton(self.scrollframe, command=self.savedata, size=self.btnsize, tooltip="Save Tracked Data"),
            "reset": ResetButton(self.scrollframe, command=self.reset, size=self.btnsize, tooltip="Clear Everything")
        }

        for button in self.btnlist.values():
            button.pack(padx=self.padx/4, pady=self.pady/4)
        
        self.logger.info("Toolbar buttons created.")

        # Video panel layout
        self.vidframe = ctk.CTkFrame(self.root, width=self.vwidth, height=self.theight,
                                     bg_color="#899fbd", fg_color="#5bdada")
        # self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT, expand=True, fill="both", padx=0, pady=0)

        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="#4d535c")
        # self.videoview.pack_propagate(False)
        # self.videoview.pack(side=ctk.TOP, expand=True, fill=ctk.BOTH, padx=0)
        self.videoview.pack(fill=ctk.BOTH, expand=True)

        # Title and Axes setup
        self.title = TitleBar(self.videoview, self.vwidth, "Welcome!")

        self.axes = Axes(self.vidframe, self.videoview, self.vwidth, self.vheight,
                         self.btnlist, self.btnlist["axis"])
        
        self.logger.info("Axes component initialized.")

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
