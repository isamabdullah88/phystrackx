
import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import messagebox
from math import floor

from .App import App
from experiments.Rigid import Rigid
from core.Rect import PixelRect
from .Plot import Plot
from .components import (SpinnerPopup, CutSeekBar, ScaleRuler, ProgressBar, Rect, TPoints,
    SubToolbar, Save)
from .plugins import Filters, Crop

class RigidApp(App):
    def __init__(self, root):
        """
        ox, oy: Position of origin of coordinate axes specified by user in the video frame.
        fx, fy: Position of origin of image in the video frame.
        """
        super().__init__(root)
        
        self.subtoolbar = SubToolbar(self.videoview, width=self.twidth, btnsize=self.btnsize)
        
        # TODO: Use enum for these
        self.subtoolbar.button("assets/plugins/filters.png", self.filter).pack(pady=2)
        self.subtoolbar.button("assets/plugins/crop.png", self.drawcrop).pack(pady=2)
        self.subtoolbar.button("assets/plugins/ocr.png", self.drawocr).pack(pady=2)
        self.subtoolbar.button("assets/plugins/geometry.png", self.drawocr).pack(pady=2)
        
        self.button("assets/plugin.png", self.plugins)
        
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        self.filters = Filters(self.scrollframe, self.updateframe)
        
        self.trects = Rect(self.videoview, self.vwidth, self.vheight)
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight)
        self.crop = Crop(self.videoview, self.vwidth, self.vheight, self.updateframe)
        
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)
        self.pdata = None
        
        # TODO: Move this var to inside progressbar class.
        # Progress bar for tracking
        self._progressbarh = 20
        self.progress = ctk.IntVar()
        self.progress.set(0)
        
        # TODO: Restructure this to make more consistent
        self.scruler = None
        
        # TODO: Make this handle more gracefully
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-rigid.mp4')
        self.rigid = Rigid(trackpath=self._trackpath, vwidth=self.vwidth, vheight=self.vheight)

    def loadvideo(self, videopath, clear=True):
        """Loads a new video from user click."""
        if clear:
            self.clear()
        else:
            self.clearcomponents()
        
        self.rigid.addvideo(videopath)
        
        self.seekbar.setcount(self.rigid.fcount)
        
        self.tpoints.addpoints(self.rigid.trackpts, self.crop.crpx, self.crop.crpy)

        self.resize(self.rigid.fwidth, self.rigid.fheight)

        self.crop.set(self.fwidth, self.fheight)

        self.imgview = self.videoview.create_image(self.crop.fx, self.crop.fy, anchor='nw')
        
        self.updateframe()

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""
        frame = self.rigid.frame(index=self.seekbar.idx)
        frame = self.resizef(frame, self.crop.fwidth, self.crop.fheight)
        
        # Apply filter
        frame = self.filters.appfilter(frame)
        # Apply crop
        self.frame = self.crop.appcrop(frame)

        img = Image.fromarray(cv2.cvtColor(self.frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.videoview.coords(self.imgview, self.crop.crpx, self.crop.crpy)
        self.videoview.itemconfig(self.imgview, image=self.photo)
        
        # draw tracked points
        self.tpoints.drawpoint(self.seekbar.idx)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

    def drawrect(self):
        """Draws rectangle with simple lines"""
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.trects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
        
    def drawcrop(self):
        """Crop for crop plugin. This crop the all frames of video"""
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.crop.drawrect()
        
    def drawocr(self):
        """Draws rectangle for OCR"""
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.ocrrects.drawrect(self.fwidth, self.fheight, self.fx, self.fy)
        
    
    def update_progress(self):
        pc = self.progress.get()
        self.progressbar.set(pc)
        
        if pc < 100:
            self.root.after(100, self.update_progress)
        else:
            self.progressbar.set(100)
            

    def strack(self):
        """
        Detects and tracks radius for the main rigid circle using classical techniques.
        """
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        
        # Clear previous Axes, rectangles and OCRs
        self.axes.clear()
        self.trects.clearrects()
        self.ocrrects.clearrects()
        
        self.popup = SpinnerPopup(self.videoview, self.vwidth, self.vheight-self._progressbarh)
        self.progressbar = ProgressBar(self.videoview, vwidth=self.vwidth, vheight=self.vheight, bheight=self._progressbarh)

        def trackbg(popup, progressbar):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            
            self.rigid.track(self.trects.rects, self.ocrrects.rects, self.filters, self.crop, startidx, endidx, self.progress)
            
            self.root.after(0, popup.destroy())
            self.root.after(0, progressbar.destroy())

            self.loadvideo(self._trackpath, clear=False)

        threading.Thread(target=trackbg, args=(self.popup,self.progressbar)).start()
        
        self.update_progress()
        
        
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
        self.rigid.trackpts.clear()
        self.clearcomponents()
        # super().clear()
    
    def gen_plotdata(self):
        """Evolve raw data into plot data"""
        if self.pdata is None:    
            scale = 1
            if self.scruler is not None:
                scale = self.scruler.scalef
                
            self.pdata = Plot(self.rigid.trackpts, self.axes, self.vwidth, self.vheight, self.fwidth,
                    self.fheight, scale=scale, fps=self.rigid.fps)
    
    def plot(self):
        if len(self.rigid.trackpts) == 0:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        self.gen_plotdata() 
            
        self.pdata.plotx()
        self.pdata.plotdrv()
        self.pdata.plotdrv2()
        self.pdata.intgr()
        self.pdata.show()

    def savedata(self):
        """
        Saves the tracked data to a CSV file.
        """
        if len(self.rigid.trackpts) == 0:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return
        
        self.gen_plotdata()
        
        save = Save(self.pdata, None)
        save.askfilepath()
        save.savedata()
        
        messagebox.showinfo("Success", "Tracked data saved successfully.")
        
    def plugins(self):
        """
        Opens a popup to select a filter type and apply it to the video frame.
        """
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        
        self.subtoolbar.toggle()
        
    def filter(self):
        self.filters.spawnfilter()