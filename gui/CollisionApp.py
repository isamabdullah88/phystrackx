
import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from .App import App
from experiments.Collision import Collision
from core.Rect import PixelRect
from .components.Spinner import SpinnerPopup
from .components.Seekbar import CutSeekBar
from .Plot import Plot

class CollisionApp(App):
    def __init__(self, root):
        super().__init__(root)
        
        sfimg = Image.open("assets/rectanglebd.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.rectbd = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                      image=sfimg, command=self.drawrect)
        self.rectbd.pack(pady=10)
        
        self.seekbar = CutSeekBar(self.vidframe, ondrag=self.updateframe)
        
        self._rcoords = None
        self._rects = []
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-collision.mp4')
        self.collision = Collision(trackpath=self._trackpath)
        

    def load_video(self, videopath):
        self.collision.add_video(videopath)
        # self.collision.crop_intime()
        
        self.seekbar.pack(pady=10)
        self.seekbar.setcount(self.collision.fcount)

        frame1 = self.collision.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame=None):
        fwidth = self.collision.fwidth
        fheight = self.collision.fheight
        frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]
        
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.fx = floor(self.cwidth/2 - self.collision.fwidth/2)
        self.fy = floor(self.cheight/2 - self.collision.fheight/2)

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""

        frame = self.collision.frame(index=self.seekbar.idx)
        fwidth = self.collision.fwidth
        fheight = self.collision.fheight
        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def markaxes(self):

        def update_axes(event):
            """ Update the axes to follow the mouse cursor. """
            self.videoview.delete("axes")  # Remove old axes
            x, y = event.x, event.y  # Get mouse position

            # Draw new axes centered on mouse position
            self.videoview.create_line(0, y, self.cwidth, y, fill="red", width=2, tags="axes")  # X-axis
            self.videoview.create_line(x, 0, x, self.cheight, fill="blue", width=2, tags="axes")  # Y-axis

        def store_click(event):
            """ Store the clicked coordinates and draw a point. """
            x, y = event.x, event.y

            self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Button>")

        self.videoview.bind("<Motion>", update_axes)
        self.videoview.bind("<Button>", store_click)

    def drawrect(self):
        """Draws rectangle with simple lines"""
        
        def ondown(event):
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
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)
        self.videoview.bind("<ButtonRelease-1>", onrelease)

    def plotx(self):
        if len(self.collision.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        plot = Plot(self.collision.trackpts)
        plot.plotx()
        plot.plotdrv()
        plot.show()


    def strack(self):
        """
        Detects and tracks radius for the main collision circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.videoview, self.cwidth, self.cheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.collision.track(self._rects, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

            self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()