
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
    SubToolbar)
from .plugins import Filters, Crop
import csv

class RigidApp(App):
    def __init__(self, root):
        """
        ox, oy: Position of origin of coordinate axes specified by user in the video frame.
        fx, fy: Position of origin of image in the video frame.
        """
        super().__init__(root)
        
        self.subtoolbar = SubToolbar(self.videoview, width=self.twidth, btnsize=self.btnsize)
        
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

    # def updateparams(self):
    #     """Fundamental parameters"""
    #     if len(self.crop.rects) > 0:
    #         rect = self.crop.rects[0]
    #         self.fx = floor(self.vwidth/2 - rect.width/2)
    #         self.fy = floor(self.vheight/2 - rect.height/2)
    #         print('updated fx, fy: ', (self.fx, self.fy))
    #     else:
    #         self.fx = floor(self.vwidth/2 - self.fwidth/2)
    #         self.fy = floor(self.vheight/2 - self.fheight/2)

    def loadvideo(self, videopath, clear=True):
        """Loads a new video from user click."""
        if clear:
            self.clear()
        else:
            self.clearcomponents()
        
        self.rigid.addvideo(videopath)
        
        self.seekbar.setcount(self.rigid.fcount)
        
        print('rigid pts: ', self.rigid.trackpts)
        self.tpoints.addpoints(self.rigid.trackpts, self.crop.crpx, self.crop.crpy)

        self.resize(self.rigid.fwidth, self.rigid.fheight)
        
        # print('fwidth, fheight: ', self.fwidth, self.fheight)
        self.crop.set(self.fwidth, self.fheight)
        # print('fx, fy: ', self.crop.fx, self.crop.fy)
        # print('actual fx, fy: ', (self.vwidth/2-self.rigid.fwidth/2), (self.vheight/2-self.rigid.fheight/2))

        self.imgview = self.videoview.create_image(self.crop.fx, self.crop.fy, anchor='nw')
        
        self.updateframe()
        
    # def loadvideo(self, videopath):
    #     """Loads locally modified video (like tracked video)"""
    #     self.clearcomponents()
        
    #     self.rigid.addvideo(videopath, self.crop)
        
    #     self.seekbar.setcount(self.rigid.fcount)
        
    #     self.tpoints.addpoints(self.rigid.trackpts, self.fx, self.fy)

    #     self.resize(self.rigid.fwidth, self.rigid.fheight)
        
    #     self.fx = floor(self.vwidth/2 - self.fwidth/2)
    #     self.fy = floor(self.vheight/2 - self.fheight/2)
    #     print('fx: ', self.fx)
    #     print('fy: ', self.fy)

    #     self.imgview = self.videoview.create_image(self.fx, self.fy, anchor='nw')
        
    #     self.updateframe()

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""
        frame = self.rigid.frame(index=self.seekbar.idx)
        
        # print('fx, fy: ', self.crop.fx, self.crop.fy)
        # print('fw, fh: ', self.crop.fwidth, self.crop.fheight)
        frame = self.resizef(frame, self.crop.fwidth, self.crop.fheight)
        
        # Apply filter
        frame = self.filters.appfilter(frame)
        # Apply crop
        self.frame = self.crop.appcrop(frame)
        # cv2.imwrite('frame.png', self.frame)

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
        # if len(self.crop.rects) > 0:
        #     crwidth = self.crop.rects[0].width
        #     crheight = self.crop.rects[0].height
        # else:
        #     crwidth = self.fwidth
        #     crheight = self.fheight
        # print('fwidth, fheight: ', (self.fwidth, self.fheight))
        # print('crwidth, crheight: ', (crwidth, crheight))
        # print('updated (in drawrect) fx, fy: ', (self.fx, self.fy))
        self.videoview.create_oval(self.crop.crpx-5, self.crop.crpy-5, self.crop.crpx+5, self.crop.crpy+5, fill="red", outline="black")
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
        
    
    def plot(self):
        if len(self.rigid.trackpts) == 0:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        scale = 1
        if self.scruler is not None:
            scale = self.scruler.scalef
        plot = Plot(self.rigid.trackpts, self.axes, self.vwidth, self.vheight, self.fwidth,
                self.fheight, scale=scale, fps=self.rigid.fps)
        plot.plotx()
        plot.plotdrv()
        plot.plotdrv2()
        plot.intgr()
        plot.show()

    def savedata(self):
        """
        Saves the tracked data to a CSV file.
        """
        if len(self.rigid.trackpts) < 10:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        filepath = ctk.filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not filepath:
            return
                
        scale = 1
        if self.scruler is not None:
            scale = self.scruler.scalef
        plot = Plot(self.rigid.trackpts, self.axes, self.vwidth, self.vheight, self.fwidth, self.fheight,
                scale=scale, fps=self.rigid.fps)

        datalist = plot.dataprocessed()
        
        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            for data in datalist:
                writer.writerow(["Frame", "Centroid X (real units)", "Centroid Y (real units)"])
                for i in range(plot.samplecount):
                    cx, cy = data[i]
                    writer.writerow([i, f"{cx:.02f}", f"{cy:.02f}"])
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