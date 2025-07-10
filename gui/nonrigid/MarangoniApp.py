import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from gui.App import App
from experiments.nonrigid import Marangoni
from gui.components import Spinner, CutSeekBar, ScaleRuler, SubToolbar, TitleBar, Label, Rect, Circle
from gui.plugins import Crop, Filters, Geometry
from core import abspath
from .VideoApp import Video

class MarangoniApp(App):
    def __init__(self, root):
        super().__init__(root)

        # img = Image.open(abspath("assets/ruler.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        # img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        # self.ruler = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
        #                               image=img, command=self.scale)
        # self.ruler.pack(padx=5, pady=5)
        # self.ruler.image = img

        img = Image.open(abspath("assets/marangoni.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.boundary = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawcircle)
        self.boundary.pack(padx=5, pady=5)
        self._idx = 0

        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)

        # self.scroll_toolbar.pack()
        
        self.ccoords = (0, 0)

        # mask from user for tracking
        self._mask = None
        
        # Plugins ---------------------------------------------------------------------------------
        self.subtoolbar = SubToolbar(self.videoview, width=self.twidth, btnsize=self.btnsize)
        
        # TODO: Use enum for these
        self.subtoolbar.button("assets/plugins/filters.png", self.appfilter).pack(pady=2)
        self.subtoolbar.button("assets/plugins/crop.png", self.drawcrop).pack(pady=2)
        self.subtoolbar.button("assets/plugins/ocr.png", self.drawocr).pack(pady=2)
        self.subtoolbar.button("assets/plugins/geometry.png", self.dogeometry).pack(pady=2)
        
        self.button("assets/plugin.png", self.plugins)
        
        self.filters = Filters(self.scrollframe, self.videoview, self.vwidth, self.vheight, self.updateframe, self.subtoolbar.toggle)
        
        self.crop = Crop(self.videoview, self.vwidth, self.vheight, self.updateframe, self.subtoolbar.toggle)
        
        self.spinner = Spinner(self.videoview, self.crop)
        
        self.geometry = Geometry(self.videoview, self.vwidth, self.vheight)
        
        # Main Toolbar ----------------------------------------------------------------------------
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, toggle=self.subtoolbar.toggle)
        
        self.circle = Circle(self.videoview, self.vwidth, self.vheight)
        
        
        # Video Handler ---------------------------------------------------------------------------
        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.crop, self.seekbar, self.filters, self.spinner)
        # tempdir = './temp'
        # if not os.path.exists(tempdir):
        #     os.makedirs(tempdir)

        # self._trackpath = os.path.join(tempdir, 'track-marangoni.mp4')

        # self.marangoni = Marangoni(trackpath=self._trackpath)



    def loadvideo(self, videopath, clear=True):
        """Loads a new video from user click."""
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        
        if clear:
            self.clear()
        else:
            self.clearcomponents()
        
        # Show frame count
        Label(self.videoview, text="Frame Count: " + str(self.videoapp.fcount)).place(x=10, y=10)
        
        self.videoapp.loadvideo(videopath)
        
        self.resize(self.videoapp.fwidth, self.videoapp.fheight)

        self.crop.set(self.fwidth, self.fheight)
        
        
        self.seekbar.setcount(self.videoapp.fcount)
        
        # self.tpoints.addpoints(self.videoapp.trackpts, self.crop.crpx, self.crop.crpy)
        
        self.updateframe()

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""
        self.videoapp.showframe()
        
        # draw tracked points
        # self.tpoints.drawpoint(self.seekbar.idx)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, cwidth=self.cwidth, cheight=self.cheight)
        
    def drawcircle(self):
        """Draws circle"""
        self.circle.drawcircle(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)

    def drawrect(self):
        """Draws rectangle with simple lines"""
        self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
        
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.trects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)

    def plugins(self):
        """
        Opens a spinner to select a filter type and apply it to the video frame.
        """
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()
    
    def appfilter(self):
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
        self.filters.spawnfilter()
        self.subtoolbar.toggle()
        
    def drawcrop(self):
        """Crop for crop plugin. This crop the all frames of video"""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        self.crop.drawrect()
        self.subtoolbar.toggle()
        
    def drawocr(self):
        """Draws rectangle for OCR"""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
        self.ocrrects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
        self.subtoolbar.toggle()
        
    def dogeometry(self):
        """Starts geomtry plugin"""
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.geometry.pack()
        self.subtoolbar.toggle()
    
    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)




    def strack(self):
        """
        Detects and tracks radius for the main marangoni circle using classical techniques.
        """
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.videoapp.track(self._mask, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.loadvideo(self.videoapp.trackpath, clear=False)

        threading.Thread(target=trackbg, args=(self.spinner,)).start()

    # TODO: Clear implementation of clear/abort while processing
    def clearcomponents(self):
        """Clear components"""
        self.scruler = None
        self.seekbar.setcount(100)
        self.crop.cleardata()
        self.ocrrects.cleardata()
        # self.trects.cleardata()
        self.filters.clear()
        self.axes.clear()

    def clear(self):
        """Clears almost everything"""
        # super().clear()
        self.videoapp.trackpts.clear()
        self.clearcomponents()
        
        # del self.marangoni
        # self.marangoni = Marangoni(trackpath=self._trackpath)
        
        # self.scruler = None
        # self._rcoords = None
        # self._rects = []
        
        # self.seekbar.setcount(100)

    def plotx(self):
        if len(self.marangoni.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        rs = [c.r for c in self.marangoni.trackpts]
        x = [c.cx for c in self.marangoni.trackpts]
        y = [c.cy for c in self.marangoni.trackpts]
        
        _, axes = plt.subplots(1, 3, figsize=(6, 5))


        axes[0].plot(rs)
        axes[0].set_title("Radius")
        axes[1].plot(x, y)
        axes[1].set_title("Center")

        plt.tight_layout()
        plt.show()