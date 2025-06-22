
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
from .components import SpinnerPopup, CutSeekBar, ScaleRuler, ProgressBar
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
        
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        self.scroll_toolbar.pack()
        
        # Progress bar for tracking
        self._progressbarh = 20
        self.progress = ctk.IntVar()
        self.progress.set(0)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        self._ocrs = []
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-rigid.mp4')
        self.rigid = Rigid(trackpath=self._trackpath, vwidth=self.vwidth, vheight=self.vheight)
        

    def load_video(self, videopath):
        self.rigid.add_video(videopath)
        
        self.seekbar.setcount(self.rigid.fcount)

        frame1 = self.rigid.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame=None):
        """Displays the first frame in videoviewer."""
        fwidth = self.rigid.fwidth
        fheight = self.rigid.fheight
        frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]
        
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)
        
        # Default coordinate system
        if self.ox is None:
            self.ox = self.fx
        
        if self.oy is None:
            self.oy = self.fy + self.fheight

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""

        frame = self.rigid.frame(index=self.seekbar.idx)
        fwidth = self.rigid.fwidth
        fheight = self.rigid.fheight
        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

    def drawrect(self):
        """Draws rectangle with simple lines"""
        self._ctkbox = None
        
        def ondown(event):
            # if self._ctkbox is not None:
            #     self.videoview.delete(self._ctkbox)
            self._ctbox = None
            
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            self.videoview.coords(self._ctkbox, sx, sy, ex, ey)
            
        def onrelease(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy)
            self._rects.append(rect.pix2norm(self.fwidth, self.fheight))
            
            self.videoview.unbind("<Button-1>")
            self.videoview.unbind("<B1-Motion>")
            self.videoview.unbind("<ButtonRelease-1>")
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)
        self.videoview.bind("<ButtonRelease-1>", onrelease)
        
    
    def drawocr(self):
        """Draws rectangle for OCR"""
        if self.rigid.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self._ctkbox = None
        
        def ondown(event):
            
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            self.videoview.coords(self._ctkbox, sx, sy, ex, ey)
            
        def onrelease(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy)
            self._ocrs.append(rect.pix2norm(self.fwidth, self.fheight))
            
            self.videoview.unbind("<Button-1>")
            self.videoview.unbind("<B1-Motion>")
            self.videoview.unbind("<ButtonRelease-1>")
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)
        self.videoview.bind("<ButtonRelease-1>", onrelease)
        
    
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
        
        self.popup = SpinnerPopup(self.videoview, self.vwidth, self.vheight-self._progressbarh)
        self.progressbar = ProgressBar(self.videoview, vwidth=self.vwidth, vheight=self.vheight, bheight=self._progressbarh)

        def trackbg(popup, progressbar):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            
            self.rigid.track(self._rects, self._ocrs, startidx, endidx, self.progress)
            
            self.root.after(0, popup.destroy())
            self.root.after(0, progressbar.destroy())

            self.load_video(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,self.progressbar)).start()
        # threading.Thread(target=trackbg, args=(self.progressbar,)).start()
        
        self.update_progress()
        
        
    def tomenu(self):
        """Clears almost everything"""
        super().tomenu()
        
        del self.rigid
        self.rigid = Rigid(trackpath=self._trackpath)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        self.seekbar.setcount(100)
        
    
    def plot(self):
        if len(self.rigid.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        scale = 1
        if self.scruler is not None:
            scale = self.scruler.scalef
        plot = Plot(self.rigid.trackpts, self.vwidth, self.vheight, self.fwidth, self.fheight,
                    ox=self.ox, oy=self.oy, scale=scale, fps=self.rigid.fps)
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
        plot = Plot(self.rigid.trackpts, self.vwidth, self.vheight, self.fwidth, self.fheight,
                    ox=self.ox, oy=self.oy, scale=scale, fps=self.rigid.fps)

        datalist = plot.dataprocessed()
        
        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            for data in datalist:
                writer.writerow(["Frame", "Centroid X (real units)", "Centroid Y (real units)"])
                for i in range(plot.samplecount):
                    cx, cy = data[i]
                    writer.writerow([i, f"{cx:.02f}", f"{cy:.02f}"])
        messagebox.showinfo("Success", "Tracked data saved successfully.")