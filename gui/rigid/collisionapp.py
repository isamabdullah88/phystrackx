
import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import messagebox
from math import floor

from gui.app import App
from experiments.rigid.collision import Collision
from core.rect import PixelRect
from .plot import Plot
from gui.components.spinner import Spinner
from gui.components.seekbar.seekbar import CutSeekBar
from gui.components.ruler import ScaleRuler
from core import abspath

class CollisionApp(App):
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
        
        # self.scroll_toolbar.pack()
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-collision.mp4')
        self.collision = Collision(trackpath=self._trackpath, vwidth=self.vwidth, vheight=self.vheight)
        

    def loadvideo(self, videopath):
        self.collision.addvideo(videopath)
        
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

        frame = self.collision.frame(index=self.seekbar.idx)
        fwidth = self.collision.fwidth
        fheight = self.collision.fheight
        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def markaxes(self):
        
        self._x = self.videoview.create_text(0, 0, text="x", fill="red", font=("Arial", 15, "bold"))
        self._y = self.videoview.create_text(0, 0, text="y", fill="blue", font=("Arial", 15, "bold"))
        
        def onmove(event):
            """ Update the axes to follow the mouse cursor. """
            self.videoview.delete("axes")  # Remove old axes
            x, y = event.x, event.y  # Get mouse position

            # Draw new axes centered on mouse position
            self.videoview.create_line(0, y, self.vwidth, y, fill="red", arrow=ctk.LAST, width=2, tags="axes")  # X-axis
            self.videoview.create_line(x, self.vheight, x, 0, fill="blue", arrow=ctk.LAST, width=2, tags="axes")  # Y-axis
            
            self.videoview.coords(self._x, self.vwidth-50, y+10)
            self.videoview.coords(self._y, x-10, self.vheight-50)

        def onclick(event):
            """ Store the clicked coordinates and draw a point. """
            x, y = event.x, event.y
            
            self.ox = x
            self.oy = y
            
            self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Button>")

        self.videoview.bind("<Motion>", onmove)
        self.videoview.bind("<Button>", onclick)
        
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
        if len(self.collision.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        scale = 1
        if self.scruler is not None:
            scale = self.scruler.scalef
        plot = Plot(self.collision.trackpts, self.vwidth, self.vheight, self.fwidth, self.fheight,
                    ox=self.ox, oy=self.oy, scale=scale, fps=self.collision.fps)
        plot.plotx()
        plot.plotdrv()
        plot.plotdrv2()
        plot.intgr()
        plot.show()


    def strack(self):
        """
        Detects and tracks radius for the main collision circle using classical techniques.
        """
        if self.collision.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        
        self.popup = Spinner(self.videoview, self.vwidth, self.vheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.collision.track(self._rects, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.loadvideo(self._trackpath)

            # self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()
        
    def clear(self):
        """Clears almost everything"""
        super().clear()
        
        del self.collision
        self.collision = Collision(trackpath=self._trackpath)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        self.seekbar.setcount(100)