
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
from .components import SpinnerPopup, CutSeekBar, ScaleRuler, ProgressBar, Rect, TPoints
from .plugins import Filters
import csv

class RigidApp(App):
    def __init__(self, root):
        """
        ox, oy: Position of origin of coordinate axes specified by user in the video frame.
        fx, fy: Position of origin of image in the video frame.
        """
        super().__init__(root)
        
        self.button("assets/ruler.png", self.scale)
        
        self.button("assets/rectanglebd.png", self.drawrect)
        
        self.button("assets/ocr.png", self.drawocr)
        
        self.button("assets/plugin.png", self.appfilter)
        
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        self.filters = Filters(self.scrollframe, self.updateframe)
        
        self.trects = Rect(self.videoview, self.vwidth, self.vheight)
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight)
        
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)
        
        # Progress bar for tracking
        self._progressbarh = 20
        self.progress = ctk.IntVar()
        self.progress.set(0)
        
        self.fx = self.fy = 0
        self.scruler = None
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-rigid.mp4')
        self.rigid = Rigid(trackpath=self._trackpath, vwidth=self.vwidth, vheight=self.vheight)
        

    def load_video(self, videopath):
        self.rigid.add_video(videopath)
        
        self.seekbar.setcount(self.rigid.fcount)
        
        self.tpoints.addpoints(self.rigid.trackpts, self.fx, self.fy)

        frame1 = self.rigid.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame=None):
        """Displays the first frame in videoviewer."""
        fwidth = self.rigid.fwidth
        fheight = self.rigid.fheight
        self.frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = self.frame.shape[:2]
        
        img = Image.fromarray(cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
        # draw tracked points
        self.tpoints.drawpoint(0)

    def updateframe(self, frame=None):
        """Updates the frame displayed in the video view based on the slider position."""
        if frame is None:
            frame = self.rigid.frame(index=self.seekbar.idx)
            fwidth = self.rigid.fwidth
            fheight = self.rigid.fheight
            self.frame = self.resizeframe(frame, fwidth, fheight)
        else:
            self.frame = frame

        img = Image.fromarray(cv2.cvtColor(self.frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.videoview.itemconfig(self.imgview, image=self.photo)
        
        # draw tracked points
        self.tpoints.drawpoint(self.seekbar.idx)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

    def drawrect(self):
        """Draws rectangle with simple lines"""
        self.trects.drawrect(self.fwidth, self.fheight, self.fx, self.fy)
        
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
        self.trects.delrects()
        self.ocrrects.delrects()
        
        self.popup = SpinnerPopup(self.videoview, self.vwidth, self.vheight-self._progressbarh)
        self.progressbar = ProgressBar(self.videoview, vwidth=self.vwidth, vheight=self.vheight, bheight=self._progressbarh)

        def trackbg(popup, progressbar):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            
            self.rigid.track(self.trects.rects, self.ocrrects.rects, startidx, endidx, self.progress)
            
            self.root.after(0, popup.destroy())
            self.root.after(0, progressbar.destroy())

            self.load_video(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,self.progressbar)).start()
        
        self.update_progress()
        
        
    def tomenu(self):
        """Clears almost everything"""
        super().tomenu()
        
        del self.rigid
        self.rigid = Rigid(trackpath=self._trackpath)
        
        self.scruler = None
        
        self.seekbar.setcount(100)
        
    
    def plot(self):
        if len(self.rigid.trackpts) < 1:
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
        if len(self.rigid.trackpts) < 1:
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
        
    def appfilter(self):
        """
        Opens a popup to select a filter type and apply it to the video frame.
        """
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        
        self.filters.spawnfilter(self.frame)