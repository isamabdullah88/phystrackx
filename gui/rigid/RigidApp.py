
import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import messagebox
from math import floor

from .App import App
from experiments.Rigid import Rigid
from .Plot import Plot
from .components import (Spinner, CutSeekBar, ScaleRuler, ProgressBar, Rect, TPoints,
    SubToolbar, Save, Checkbox, Label)
from experiments.components import OCRData
from .plugins import Filters, Crop, Geometry
from core import PlotTypes
from .components.Titlebar import TitleBar
from .VideoApp import Video

class RigidApp(App):
    def __init__(self, root):
        """
        ox, oy: Position of origin of coordinate axes specified by user in the video frame.
        fx, fy: Position of origin of image in the video frame.
        """
        super().__init__(root)
        
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
        
        self.geometry = Geometry(self.videoview, self.vwidth, self.vheight)
        
        # Main toolbar ----------------------------------------------------------------------------
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        self.trects = Rect(self.videoview, self.vwidth, self.vheight)
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, toggle=self.subtoolbar.toggle)
        
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)
        self.pdata = None
        
        self.spinner = Spinner(self.videoview, self.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth, vheight=self.vheight)
        
        # TODO: Restructure this to make more consistent
        self.scruler = None
        
        # TODO: Make this handle more gracefully
        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.crop, self.seekbar, self.filters, self.spinner)

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
        
        self.tpoints.addpoints(self.videoapp.trackpts, self.crop.crpx, self.crop.crpy)
        
        self.updateframe()

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""
        self.videoapp.showframe()
        
        # draw tracked points
        self.tpoints.drawpoint(self.seekbar.idx)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, cwidth=self.cwidth, cheight=self.cheight)

    def drawrect(self):
        """Draws rectangle with simple lines"""
        self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
        
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.trects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
    
    
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

    def strack(self):
        """
        Detects and tracks radius for the main videoapp circle using classical techniques.
        """
        if (self.videoapp.fcount < 10) or ((len(self.trects.rects) == 0) and (len(self.ocrrects.rects) == 0)):
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        # Clear previous Axes, rectangles and OCRs
        self.axes.clear()
        self.trects.clearrects()
        self.ocrrects.clearrects()
        
        self.spinner.pack()
        self.progressbar.pack()

        def trackbg(spinner, progressbar):
            
            self.videoapp.track(self.trects, self.ocrrects, self.progressbar.progress)
            
            self.root.after(0, spinner.destroy())
            self.root.after(0, progressbar.destroy())

            self.loadvideo(self.videoapp.trackpath, clear=False)

        threading.Thread(target=trackbg, args=(self.spinner,self.progressbar)).start()
        
        self.progressbar.update()
        
    # TODO: Clear implementation of clear/abort while processing
    def clearcomponents(self):
        """Clear components"""
        self.scruler = None
        self.seekbar.setcount(100)
        self.crop.cleardata()
        self.ocrrects.cleardata()
        self.trects.cleardata()
        self.filters.clear()
        self.axes.clear()
        
    def clear(self):
        self.videoapp.trackpts.clear()
        self.clearcomponents()
        # super().clear()
    
    def plot(self):
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.texts) == 0):
            messagebox.showerror("Error", "No tracked and text data available. Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        # TODO: Remove points from plot data as well when user removed the point
        self.gen_plotdata() 
        
        Checkbox(self.videoview, PlotTypes, self.pdata.showplots)

    def savedata(self):
        """
        Saves the tracked data to a CSV file.
        """
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.texts) == 0):
            messagebox.showerror("Error", "No tracked and text data and available. Please start tracking first.")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")
        self.gen_plotdata()
        ocrdata = OCRData(self.videoapp.texts)
        
        save = Save(self.pdata, ocrdata)
        save.askfilepath()
        save.savedata()
        
        messagebox.showinfo("Success", "Tracked data saved successfully.")
        
    def plugins(self):
        """
        Opens a spinner to select a filter type and apply it to the video frame.
        """
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()
        
    
    def gen_plotdata(self):
        """Evolve raw data into plot data"""
        if self.pdata is None:    
            scale = 1
            if self.scruler is not None:
                scale = self.scruler.scalef
                
            self.pdata = Plot(self.videoapp.trackpts, self.axes, self.vwidth, self.vheight, self.fwidth,
                    self.fheight, scale=scale, fps=self.videoapp.fps)