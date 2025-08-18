"""
balloonapp.py
Application for non-rigid balloon tracking in PhysTrackX.

Author: Isam Balghari
"""

import threading
from tkinter import messagebox, Tk

from gui.app import App
from gui.components.processanim import ProcessAnimation
from gui.components.spinner import Spinner
from gui.components.seekbar import TrimSeekBar, ViewSeekBar
from gui.components.ruler import ScaleRuler
from gui.components.progressbar import ProgressBar
from gui.components.structures import Rect, Circle
from gui.components.visuals import ContPoints
from gui.components.subtoolbar import SubToolbar
from gui.components.plot import Save, Plot, DataManager
from gui.components.label import Label
from gui.components.titlebar import TitleBar
from gui.components.tooltip import ToolTip
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry
from .videoapp import Video
from experiments.nonrigid import Balloon


class BalloonApp(App):
    """Application for tracking balloon deformation and extracting motion data."""

    def __init__(self, root: Tk) -> None:
        """
        Initialize the balloon tracking application.

        Args:
            root (Tk): The root tkinter window.
        """
        super().__init__(root)
        self._setup_main_toolbar()
        self._setup_sub_toolbar()
        self._init_plugins_and_tools()
        self._init_video_components()

        self.save = None
        self.datamanager = None

    # ================== UI Setup ================== #

    def _setup_main_toolbar(self) -> None:
        """Create main toolbar buttons with tooltips."""
        main_buttons = [
            ("assets/circlebd.png", self.drawcircle, "Draw Circle Boundary"),
            ("assets/track.png", self.strack, "Start Tracking"),
            ("assets/plot.png", self.plot, "Plot Tracked Data"),
            ("assets/save.png", self.savedata, "Save Tracked Data"),
            ("assets/reset.png", self.reset, "Clear Everything"),
            ("assets/plugin.png", self.plugins, "Plugins"),
        ]
        for img_path, command, tooltip in main_buttons:
            btn = self.mkbutton(img_path, command)
            ToolTip(btn, tooltip)
            self.btnlist[img_path.split("/")[-1][:-4]] = btn

    def _setup_sub_toolbar(self) -> None:
        """Create plugin toolbar buttons with tooltips."""
        self.subtoolbar = SubToolbar(
            self.videoview, width=self.twidth, btnsize=self.btnsize
        )
        sub_buttons = [
            ("assets/plugins/filters.png", self.appfilter, "Apply Filters to Video"),
            ("assets/plugins/crop.png", self.drawcrop, "Crop the Video"),
            ("assets/plugins/ocr.png", self.drawocr, "Draw to Apply OCR"),
            ("assets/plugins/geometry.png", self.dogeometry, "Geometry Tool"),
        ]
        for img_path, command, tooltip in sub_buttons:
            btn = self.subtoolbar.mkbutton(img_path, command)
            ToolTip(btn, tooltip)
            self.btnlist[img_path.split("/")[-1][:-4]] = btn

    def _init_plugins_and_tools(self) -> None:
        """Initialize plugin modules and drawing tools."""
        self.filters = Filters(
            self.scrollframe,
            self.videoview,
            self.vwidth,
            self.vheight,
            self.updateframe,
            self.subtoolbar.toggle,
        )
        self.crop = Crop(
            self.videoview,
            self.vwidth,
            self.vheight,
            self.updateframe,
            self.subtoolbar.toggle,
        )
        self.geometry = Geometry(
            self.videoview,
            self.vwidth,
            self.vheight,
            self.btnlist,
            self.btnlist["geometry"],
        )
        self.seekbar = TrimSeekBar(
            self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe
        )
        self.ocrrects = Rect(
            self.videoview,
            self.vwidth,
            self.vheight,
            self.btnlist,
            self.btnlist["ocr"],
            toggle=self.subtoolbar.toggle,
        )
        self.contpoints = ContPoints(self.videoview, self.vwidth, self.vheight)
        self.processanim = ProcessAnimation(self.videoview, self.crop)
        self.progressbar = ProgressBar(
            self.root, self.videoview, vwidth=self.vwidth, vheight=self.vheight
        )
        self.scruler = ScaleRuler(
            self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist["ruler"]
        )
        self.circle = Circle(self.videoview, self.vwidth, self.vheight)

    def _init_video_components(self) -> None:
        """Initialize the video player and processing backend."""
        self.videoapp = Video(
            self.videoview,
            self.vwidth,
            self.vheight,
            Balloon,
            self.crop,
            self.seekbar,
            self.filters,
            self.processanim,
        )
        self.seekbar.settrim(trimvideo=self.trimvideo)

    # ================== Video Loading & Processing ================== #

    def loadvideo(self, videopath: str) -> None:
        """Load the video into the viewer and initialize related components."""
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        self.spinner = Spinner(self.videoview, self.videoapp.imgview)

        def load(spinner: Spinner) -> None:
            self.videoapp.loadvideo(videopath)
            self.root.after(0, spinner.destroy)
            self.loadcomponents()

        threading.Thread(target=load, args=(self.spinner,)).start()

    def trimvideo(self, startidx: int, endidx: int) -> None:
        """Trim the video based on user-defined start and end indices."""
        self.spinner = Spinner(self.videoview, self.videoapp.imgview, self.crop)

        def trim(spinner: Spinner) -> None:
            self.videoapp.trimvideo(startidx, endidx)
            self.videoapp.loadvideo(self.videoapp.trimpath)
            self.loadcomponents()
            self.root.after(0, spinner.destroy)

        threading.Thread(target=trim, args=(self.spinner,)).start()

    def loadcomponents(self) -> None:
        """Load and update components after video is loaded or modified."""
        Label(
            self.videoview, text=f"Frame Count: {self.videoapp.fcount}"
        ).place(x=10, y=80)

        if self.seekbar.disable:
            self.seekbar = ViewSeekBar(
                self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe
            )
            self.seekbar.set(self.videoapp.fcount)
            self.seekbar.pack()
        else:
            self.seekbar.set(self.videoapp.fcount)

        self.contpoints.addpoints(
            self.videoapp.trackpts, self.crop.crpx, self.crop.crpy
        )
        self.updateframe()

    # ================== UI Actions ================== #

    def loadseek(self) -> None:
        """Display seekbar if video has enough frames."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.seekbar.pack()

    def updateframe(self) -> None:
        """Update canvas to show current frame and overlays."""
        self.videoapp.showframe(self.seekbar.idx)
        self.contpoints.drawpoints(self.seekbar.idx)

    def scale(self) -> None:
        """Display the scale ruler on canvas."""
        self.scruler.pack()

    def appfilter(self) -> None:
        """Activate video filter UI for user input."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
        self.filters.spawnfilter()
        self.subtoolbar.toggle()

    def drawcrop(self) -> None:
        """Activate the cropping tool."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to crop. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        self.crop.drawrect()
        self.subtoolbar.toggle()

    def drawocr(self) -> None:
        """Draw a region for OCR."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
        self.ocrrects.drawrect(
            self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy
        )
        self.subtoolbar.toggle()

    def dogeometry(self) -> None:
        """Launch geometry analysis plugin."""
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.geometry.pack()
        self.subtoolbar.toggle()

    def clearcomponents(self) -> None:
        """Clear all active UI overlays."""
        self.filters.clear()
        self.axes.clear()
        self.contpoints.clear()
        self.scruler.clear()

    def reset(self) -> None:
        """Reset video view and related tracking/overlay data."""
        self.clearcomponents()
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        self.crop.clear()
        self.seekbar.clear()
        self.loadvideo(self.videopath)

    def plot(self) -> None:
        """Create plots from tracked data or OCR values."""
        if not self.videoapp.trackpts and not self.videoapp.ocrdata:
            messagebox.showerror(
                "Error", "No tracked or text data available. Please start tracking first."
            )
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        if self.datamanager is None:
            self.datamanager = DataManager(
                self.points.tpts,
                self.videoapp.ocrdata,
                self.axes,
                self.vwidth,
                self.vheight,
                self.fwidth,
                self.fheight,
                self.videoapp.fps,
                self.scruler.scalef,
            )
            self.datamanager.transform()
        self.plot = Plot(self.videoview, self.datamanager)

    def savedata(self) -> None:
        """Save data from tracking or OCR to file."""
        if not self.videoapp.trackpts and not self.videoapp.ocrdata:
            messagebox.showerror(
                "Error", "No tracked or text data available. Please start tracking first."
            )
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")
        if self.datamanager is None:
            self.datamanager = DataManager(
                self.contpoints.tpts,
                self.videoapp.ocrdata,
                self.axes,
                self.vwidth,
                self.vheight,
                self.fwidth,
                self.fheight,
                self.videoapp.fps,
                self.scruler.scalef,
            )
            self.datamanager.transform()
        self.save = Save(self.videoview, self.datamanager)

    def plugins(self) -> None:
        """Toggle plugin selection toolbar."""
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()

    def drawcircle(self) -> None:
        """Draw a circle mask for tracking."""
        self.circle.drawcircle(
            self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy
        )

    def strack(self) -> None:
        """Perform point tracking and update UI."""
        if (self.videoapp.fcount < 10 or
            (not self.circle.circles and not self.ocrrects.rects)):
            messagebox.showerror(
                "Error", "No task to track. Upload video and mark points first!"
            )
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        self.axes.clear()
        self.ocrrects.clearrects()
        self.circle.clearrects()

        self.processanim.pack()
        self.progressbar.pack()

        def on_complete() -> None:
            self.processanim.destroy()
            self.progressbar.destroy()
            self.loadcomponents()

        def track_bg() -> None:
            self.videoapp.track(
                self.circle.mask, self.ocrrects, self.progressbar.progress
            )
            self.root.after(0, on_complete)

        threading.Thread(target=track_bg).start()
        self.progressbar.update()