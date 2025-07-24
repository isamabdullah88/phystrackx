import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from experiments.nonrigid import Balloon
from gui.app import App
from gui.components.spinner import Spinner
from gui.components.seekbar.seekbar import CutSeekBar
from gui.components.ruler import ScaleRuler
from core.rect import PixelRect
from core import abspath

class BalloonApp(App):
    def __init__(self, root):
        super().__init__(root)
        
        img = Image.open(abspath("assets/ruler.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.ruler = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.scale)
        self.ruler.pack(padx=5, pady=5)
        self.ruler.image = img

        # For drawing ellipse over tracking area
        img = Image.open(abspath("assets/circlebd.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.circlebd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawcircle)
        self.circlebd.pack(pady=10)
        
        # For drawing rectangle over text area
        img = Image.open(abspath("assets/rectanglebd.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.rectbd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawrect)
        self.rectbd.pack(pady=10)
        

        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        # self.scroll_toolbar.pack()
        
        self.scruler = None

        self.ccoords = (0, 0)

        # mask from user for tracking
        self._mask = None
        # rect for text detection
        self._rect = None

        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        self._trackpath = os.path.join(tempdir, 'track-balloon.mp4')

        self.balloon = Balloon(trackpath=self._trackpath)



    def loadvideo(self, videopath):
        self.balloon.addvideo(videopath)
        
        self.seekbar.setcount(self.balloon.fcount)

        frame1 = self.balloon.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame):
        fwidth = self.balloon.fwidth
        fheight = self.balloon.fheight
        frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame
        
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
        frame = self.balloon.frame(index=self.seekbar.idx)
        fwidth = self.balloon.fwidth
        fheight = self.balloon.fheight

        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

    def drawcircle(self):
        """Draws circle with filled transparent image laid over region of interest"""
        
        def ondown(event):
            self.ccoords = (event.x-self.fx, event.y-self.fy)
            
            self.photo = ImageTk.PhotoImage(circilize(10, 10))
            
            self.videoview.itemconfig(self.imgview, image=self.photo)
            
        def incircle(event):
            ex = (event.x-self.fx)
            ey = (event.y-self.fy)

            frame, mask = fcrop_coords(self._frame, self.ccoords, (ex, ey))

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.photo = ImageTk.PhotoImage(image=img)
            self._mask = mask

            self.videoview.itemconfig(self.imgview, image=self.photo)
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", incircle)

    
    def drawrect(self):
        """Draws rectangle with simple lines"""
        self.rbox = None
        
        def ondown(event):
            if self.rbox is not None:
                self.videoview.delete(self.rbox)
            
            self.rcoords = (event.x, event.y)
            
            self.rbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self.rcoords
            ex, ey = (event.x, event.y)
            
            self.videoview.coords(self.rbox, sx, sy, event.x, event.y)

            self._rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy).pix2norm(self.fwidth, self.fheight)

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)


    def strack(self):
        """
        Detects and tracks radius for the main balloon circle using classical techniques.
        """
        if self.balloon.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return

        self.popup = Spinner(self.videoview, self.vwidth, self.vheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.balloon.track(self._mask, self._rect, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.loadvideo(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,)).start()



    def clear(self):
        """Clears almost everything"""
        super().clear()
        
        del self.balloon
        self.balloon = Balloon(trackpath=self._trackpath)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        self.seekbar.setcount(100)


    def plot_distances(self):
        if len(self.balloon.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        num_tracks = len(self.balloon.trackpts)
        _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

        for i in range(num_tracks):
            trackpts = self.balloon.trackpts[i]
            xcoords = trackpts[0, :] - self.fx
            ycoords = trackpts[1, :] - self.fy

            axes[i][0].plot(xcoords)
            axes[i][0].set_title("x coordinates")
            axes[i][1].plot(ycoords)
            axes[i][1].set_title("y coordinates")

        plt.tight_layout()
        plt.show()