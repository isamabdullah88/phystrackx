import threading
from tkinter import messagebox

from gui.app import App
from gui.components.processanim import ProcessAnimation
from gui.components.spinner import Spinner
from gui.components.seekbar import TrimSeekBar, ViewSeekBar
from gui.components.ruler import ScaleRuler
from gui.components.progressbar import ProgressBar
from gui.components.rect import Rect
from gui.components.points import ContPoints
from gui.components.subtoolbar import SubToolbar
from gui.components.plot import Save, Plot, DataManager
from gui.components.label import Label
from gui.components.titlebar import TitleBar
from gui.components.tooltip import ToolTip
from gui.components.circle import Circle
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry
from .videoapp import Video
from experiments.nonrigid import Balloon

class BalloonApp(App):
    def __init__(self, root):
        super().__init__(root)

        buttons = [
            ("assets/circlebd.png", self.drawcircle, "Draw Circle Boundary"),
            ("assets/track.png", self.strack, "Start Tracking"),
            ("assets/plot.png", self.plot, "Plot Tracked Data"),
            ("assets/save.png", self.savedata, "Save Tracked Data"),
            ("assets/reset.png", self.reset, "Clear Everything"),
            ("assets/plugin.png", self.plugins, "Plugins")
        ]

        for imgpath, command, tooltip in buttons:
            btn = self.mkbutton(imgpath, command)
            ToolTip(btn, tooltip)
            self.btnlist[imgpath.split('/')[-1][:-4]] = btn

        self.subtoolbar = SubToolbar(self.videoview, width=self.twidth, btnsize=self.btnsize)

        buttons = [
            ("assets/plugins/filters.png", self.appfilter, "Apply Filters to Video"),
            ("assets/plugins/crop.png", self.drawcrop, "Crop the Video"),
            ("assets/plugins/ocr.png", self.drawocr, "Draw to Apply OCR"),
            ("assets/plugins/geometry.png", self.dogeometry, "Geometry Tool")
        ]

        for imgpath, command, tooltip in buttons:
            self.btn = self.subtoolbar.mkbutton(imgpath, command)
            ToolTip(self.btn, tooltip)
            self.btnlist[imgpath.split('/')[-1][:-4]] = self.btn

        self.filters = Filters(self.scrollframe, self.videoview, self.vwidth, self.vheight, self.updateframe, self.subtoolbar.toggle)
        self.crop = Crop(self.videoview, self.vwidth, self.vheight, self.updateframe, self.subtoolbar.toggle)
        self.geometry = Geometry(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['geometry'])

        self.seekbar = TrimSeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
        # self.trects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['rectanglebd'])
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['ocr'], toggle=self.subtoolbar.toggle)
        self.contpoints = ContPoints(self.videoview, self.vwidth, self.vheight)
        self.pdata = None

        self.processanim = ProcessAnimation(self.videoview, self.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth, vheight=self.vheight)
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist["ruler"])

        self.circle = Circle(self.videoview, self.vwidth, self.vheight)

        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, Balloon, self.crop, self.seekbar, self.filters, self.processanim)
        self.seekbar.settrim(trimvideo=self.trimvideo)

        self.save = None
        self.datamanager = None

    def loadvideo(self, videopath: str):
        """Loads the video into the viewer and initializes related components."""
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        self.spinner = Spinner(self.videoview, self.videoapp.imgview)

        def load(spinner):
            self.videoapp.loadvideo(videopath)
            self.root.after(0, spinner.destroy())
            self.loadcomponents()

        threading.Thread(target=load, args=(self.spinner,)).start()

    def trimvideo(self, startidx, endidx):
        """Trims the video based on user-defined start and end indices."""
        self.spinner = Spinner(self.videoview, self.videoapp.imgview, self.crop)

        def trim(spinner):
            self.videoapp.trimvideo(startidx, endidx)
            self.videoapp.loadvideo(self.videoapp.trimpath)
            self.loadcomponents()
            self.root.after(0, spinner.destroy())

        threading.Thread(target=trim, args=(self.spinner,)).start()

    def loadcomponents(self):
        """Loads and updates components after video is loaded or modified."""
        Label(self.videoview, text="Frame Count: " + str(self.videoapp.fcount)).place(x=10, y=80)
        
        if self.seekbar.disable:
            self.seekbar = ViewSeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
            self.seekbar.set(self.videoapp.fcount)
            self.seekbar.pack()
        else:
            self.seekbar.set(self.videoapp.fcount)

        self.contpoints.addpoints(self.videoapp.trackpts, self.crop.crpx, self.crop.crpy)
        self.updateframe()

    def loadseek(self):
        """Displays seekbar if video has enough frames."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.seekbar.pack()

    def updateframe(self):
        """Updates canvas to show current frame and overlays contpoints."""
        self.videoapp.showframe(self.seekbar.idx)
        self.contpoints.drawpoints(self.seekbar.idx)

    def scale(self):
        """Displays the scale ruler on canvas."""
        self.scruler.pack()

    def appfilter(self):
        """Activates video filter UI for user input."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
        self.filters.spawnfilter()
        self.subtoolbar.toggle()

    def drawcrop(self):
        """Activates the cropping tool to trim the video frame area."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        self.crop.drawrect()
        self.subtoolbar.toggle()

    def drawocr(self):
        """Draws a region for OCR (optical character recognition)."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
        self.ocrrects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
        self.subtoolbar.toggle()

    def dogeometry(self):
        """Launches the geometry analysis plugin UI."""
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.geometry.pack()
        self.subtoolbar.toggle()

    def clearcomponents(self):
        """Clears all active UI drawing elements and overlays."""
        self.filters.clear()
        self.axes.clear()
        self.contpoints.clear()
        self.scruler.clear()

    def reset(self):
        """Resets the video view and related tracking/overlay data."""
        print('Clear')
        self.clearcomponents()
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        # self.trects.clear()
        self.crop.clear()
        self.seekbar.clear()
        self.loadvideo(self.videopath)

    def plot(self):
        """Creates plots from tracked data or OCR values."""
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.ocrdata) == 0):
            messagebox.showerror("Error", "No tracked and text data available. Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")

        if self.datamanager is not None:
            self.plot = Plot(self.videoview, self.datamanager)
        else:
            self.datamanager = DataManager(
                self.points.tpts, self.videoapp.ocrdata, self.axes,
                self.vwidth, self.vheight, self.fwidth, self.fheight,
                self.videoapp.fps, self.scruler.scalef
            )
            self.datamanager.transform()
            self.plot = Plot(self.videoview, self.datamanager)

    def savedata(self):
        """Saves data from tracking or OCR to file (CSV or other format)."""
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.ocrdata) == 0):
            messagebox.showerror("Error", "No tracked and text data and available. Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")

        if self.datamanager is not None:
            self.save = Save(self.videoview, self.datamanager)
        else:
            self.datamanager = DataManager(
                self.points.tpts, self.videoapp.ocrdata, self.axes,
                self.vwidth, self.vheight, self.fwidth, self.fheight,
                self.videoapp.fps, self.scruler.scalef
            )
            self.datamanager.transform()
            self.save = Save(self.videoview, self.datamanager)

    def plugins(self):
        """Toggles the plugin selection toolbar interface."""
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()

    def drawcircle(self):
        """Draws circle"""
        self.circle.drawcircle(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)

    def strack(self):
        """Performs point tracking across video frames and visualizes result."""
        if (self.videoapp.fcount < 10) or ((len(self.circle.circles) == 0) and (len(self.ocrrects.rects) == 0)):
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        self.axes.clear()
        self.ocrrects.clearrects()
        self.circle.clearrects()

        self.processanim.pack()
        self.progressbar.pack()

        def oncomplete():
            self.processanim.destroy()
            self.progressbar.destroy()
            self.loadcomponents()

        def trackbg():
            self.videoapp.track(self.circle.mask, self.ocrrects, self.progressbar.progress)
            self.root.after(0, oncomplete)

        threading.Thread(target=trackbg).start()
        self.progressbar.update()