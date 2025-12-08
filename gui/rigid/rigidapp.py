"""
rigidapp.py

Defines the RigidApp class, the main interface for video-based tracking, measurement,
and physics data visualization using plugins such as filters, geometry tools, OCR, and more.

Author: Isam Balghari
"""

import threading
from tkinter import messagebox

from gui.app import App
from gui.components.processanim import ProcessAnimation
from gui.components.spinner import Spinner
from gui.components.seekbar import TrimSeekBar, ViewSeekBar
from gui.components.ruler import ScaleRuler
from gui.components.progressbar import ProgressBar
from gui.components.rect import Rect
from gui.components.tpoints import TPoints
from gui.components.subtoolbar import SubToolbar
from gui.components.plot import Save, Plot, DataManager
from gui.components.label import Label
from gui.components.titlebar import TitleBar
from gui.components.tooltip import ToolTip
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry
from .videoapp import Video

class RigidApp(App):
    """Main GUI application class for the PhysTrack Rigid tool."""
    def __init__(self, root):
        """Initializes the RigidApp interface and its associated components."""
        super().__init__(root)

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

        self.pluginsbtn = self.mkbutton("assets/plugin.png", self.plugins)
        ToolTip(self.pluginsbtn, "Plugins")

        self.filters = Filters(self.scrollframe, self.videoview, self.vwidth, self.vheight,
                               self.updateframe, self.subtoolbar.toggle)
        self.crop = Crop(self.videoview, self.vwidth, self.vheight, self.updateframe,
                         self.subtoolbar.toggle)
        self.geometry = Geometry(self.videoview, self.vwidth, self.vheight, self.btnlist,
                                 self.btnlist['geometry'])

        self.trimseekbar = TrimSeekBar(self.vidframe, self.vwidth, self.seekbarh,
                                       callback=self.updateframe)
        self.viewseekbar = ViewSeekBar(self.vidframe, self.vwidth, self.seekbarh,
                                       callback=self.updateframe)
        self.trects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist,
                           self.btnlist['rectanglebd'])
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist,
                             self.btnlist['rectanglebd'], toggle=self.subtoolbar.toggle)
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)

        self.processanim = ProcessAnimation(self.videoview, self.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth,
                                       vheight=self.vheight)
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, self.btnlist,
                                  self.btnlist["ruler"])

        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.crop, self.filters,
                              self.processanim)
        self.trimseekbar.settrim(trimvideo=self.trimvideo)

        self.save = None
        self.plotobj = None
        self.datamanager = None
        self.viewsb = False

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
            self.viewsb = True
            
            self.trimseekbar.clear()
            self.videoapp.loadvideo(self.videoapp.trimpath, True)
            self.loadcomponents()
            self.root.after(0, spinner.destroy())

        threading.Thread(target=trim, args=(self.spinner,)).start()

    def loadcomponents(self):
        """Loads and updates components after video is loaded or modified."""
        Label(self.videoview, text="Frame Count: " + str(self.videoapp.fcount)).place(x=10, y=80)

        if self.viewsb:
            self.viewseekbar.set(self.videoapp.fcount)
            self.viewseekbar.pack()

        self.tpoints.addpoints(self.videoapp.trackpts, self.crop.crpx, self.crop.crpy)
        self.updateframe()

    def loadseek(self):
        """Displays seekbar if video has enough frames."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.trimseekbar.set(self.videoapp.fcount)
        self.trimseekbar.pack()

    def updateframe(self):
        """Updates canvas to show current frame and overlays points."""
        if self.viewsb:
            idx = self.viewseekbar.idx
        else:
            idx = self.trimseekbar.idx

        self.videoapp.showframe(idx)
        self.tpoints.drawpoints(idx)
            


    def scale(self):
        """Displays the scale ruler on canvas."""
        self.scruler.pack()

    def drawrect(self):
        """Enables rectangle drawing mode for object tracking."""
        self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.trects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx,
                             self.crop.crpy)

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
        self.ocrrects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx,
                               self.crop.crpy)
        self.subtoolbar.toggle()

    def dogeometry(self):
        """Launches the geometry analysis plugin UI."""
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.geometry.pack()
        self.subtoolbar.toggle()

    def strack(self):
        """Performs point tracking across video frames and visualizes result."""
        if (self.videoapp.fcount < 10) or ((len(self.trects.rects) == 0) and 
            (len(self.ocrrects.rects) == 0)):
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        self.axes.clear()
        self.trects.cleartkrects()
        self.ocrrects.cleartkrects()

        self.processanim.pack()
        self.progressbar.pack()

        def trackbg(processanim, progressbar):
            self.videoapp.track(self.trects, self.ocrrects, self.progressbar.progress)
            self.root.after(0, processanim.destroy())
            self.root.after(0, progressbar.destroy())
            self.loadcomponents()

        threading.Thread(target=trackbg, args=(self.processanim, self.progressbar)).start()
        self.progressbar.update()

    def clearcomponents(self):
        """Clears all active UI drawing elements and overlays."""
        self.filters.clear()
        self.axes.clear()
        self.tpoints.clear()
        self.scruler.clear()

    def reset(self):
        """Resets the video view and related tracking/overlay data."""
        self.clearcomponents()
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        self.trects.clear()
        self.crop.clear()
        self.tpoints.clear()
        
        self.trimseekbar.clear()
        self.viewseekbar.clear()
        self.viewsb = False
        
        if self.videopath:
            self.loadvideo(self.videopath)

    def plot(self):
        """Creates plots from tracked data or OCR values."""
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.ocrdata) == 0):
            messagebox.showerror("Error", "No tracked and text data available. " \
            "Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        print('fps: ', self.videoapp.fps)
        if self.datamanager is not None:
            self.plotobj = Plot(self.videoview, self.datamanager)
        else:
            self.datamanager = DataManager(
                self.tpoints.tpts, self.videoapp.ocrdata, self.axes,
                self.vwidth, self.vheight, self.fwidth, self.fheight,
                self.videoapp.fps, self.scruler.scalef
            )
            self.datamanager.transform()
            self.plotobj = Plot(self.videoview, self.datamanager)

    def savedata(self):
        """Saves data from tracking or OCR to file (CSV or other format)."""
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.ocrdata) == 0):
            messagebox.showerror("Error", "No tracked and text data and available. " \
            "Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")

        if self.datamanager is not None:
            self.save = Save(self.videoview, self.datamanager)
        else:
            self.datamanager = DataManager(
                self.tpoints.tpts, self.videoapp.ocrdata, self.axes,
                self.vwidth, self.vheight, self.fwidth, self.fheight,
                self.videoapp.fps, self.scruler.scalef
            )
            self.datamanager.transform()
            self.save = Save(self.videoview, self.datamanager)

    def plugins(self):
        """Toggles the plugin selection toolbar interface."""
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()
