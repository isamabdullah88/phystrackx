
import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import messagebox
from math import floor

from .App import App
from experiments.SlidingFriction import SlidingFriction
from core.Rect import PixelRect
from .Plot import Plot
from .components import SpinnerPopup
from .components import CutSeekBar
from .components import ScaleRuler
from core import abspath

class SlidingFrictionApp(App):
    def __init__(self, root):
        """
        ox, oy: Position of origin of coordinate axes specified by user in the video frame.
        fx, fy: Position of origin of image in the video frame.
        """
        super().__init__(root)
        
        img = Image.open(abspath("assets/ruler.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.ruler = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.scale)
        self.ruler.pack(padx=5, pady=5)
        self.ruler.image = img
        
        img = Image.open(abspath("assets/rectanglebd.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.rectbd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawrect)
        self.rectbd.pack(padx=5, pady=5)
        self.rectbd.image = img
        
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        self.scroll_toolbar.pack()
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-sfriction.mp4')
        self.sfriction = SlidingFriction(trackpath=self._trackpath, vwidth=self.vwidth, vheight=self.vheight)
        

    def load_video(self, videopath):
        self.sfriction.add_video(videopath)
        
        self.seekbar.setcount(self.sfriction.fcount)

        frame1 = self.sfriction.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame=None):
        """Displays the first frame in videoviewer."""
        fwidth = self.sfriction.fwidth
        fheight = self.sfriction.fheight
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

        frame = self.sfriction.frame(index=self.seekbar.idx)
        fwidth = self.sfriction.fwidth
        fheight = self.sfriction.fheight
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

    def plotx(self):
        if len(self.sfriction.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        scale = 1
        if self.scruler is not None:
            scale = self.scruler.scalef
        plot = Plot(self.sfriction.trackpts, self.vwidth, self.vheight, self.fwidth, self.fheight,
                    ox=self.ox, oy=self.oy, scale=scale)
        plot.plotx()
        plot.plotdrv()
        plot.show()


    def strack(self):
        """
        Detects and tracks radius for the main sfriction circle using classical techniques.
        """
        if self.sfriction.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        
        self.popup = SpinnerPopup(self.videoview, self.vwidth, self.vheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.sfriction.track(self._rects, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,)).start()
        
    def tomenu(self):
        """Clears almost everything"""
        super().tomenu()
        
        del self.sfriction
        self.sfriction = SlidingFriction(trackpath=self._trackpath)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        self.seekbar.setcount(100)