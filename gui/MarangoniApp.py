import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from .App import App
from experiments.Marangoni import Marangoni
from .Core import circilize, fcrop_coords
from .components import SpinnerPopup, CutSeekBar, ScaleRuler
from core import abspath

class MarangoniApp(App):
    def __init__(self, root):
        super().__init__(root)

        img = Image.open(abspath("assets/ruler.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.ruler = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.scale)
        self.ruler.pack(padx=5, pady=5)
        self.ruler.image = img

        img = Image.open(abspath("assets/marangoni.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.boundary = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawcircle)
        self.boundary.pack(padx=5, pady=5)
        self._idx = 0

        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)

        self.scroll_toolbar.pack()
        
        self.ccoords = (0, 0)

        # mask from user for tracking
        self._mask = None

        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        self._trackpath = os.path.join(tempdir, 'track-marangoni.mp4')

        self.marangoni = Marangoni(trackpath=self._trackpath)



    def loadvideo(self, videopath):
        self.marangoni.addvideo(videopath)
        
        self.seekbar.setcount(self.marangoni.fcount)

        frame1 = self.marangoni.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame):
        fwidth = self.marangoni.fwidth
        fheight = self.marangoni.fheight
        frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.fx = floor(self.cwidth/2 - frame.shape[1]/2)
        self.fy = floor(self.cheight/2 - frame.shape[0]/2)
        
        # Default coordinate system
        if self.ox is None:
            self.ox = self.fx
        
        if self.oy is None:
            self.oy = self.fy + self.fheight

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
    def updateframe(self):
        
        frame = self.marangoni.frame(index=self.seekbar.idx)
        fwidth = self.marangoni.fwidth
        fheight = self.marangoni.fheight

        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.videoview.itemconfig(self.imgview, image=self.photo)

    # def markaxes(self):

    #     def update_axes(event):
    #         """ Update the axes to follow the mouse cursor. """
    #         self.videoview.delete("axes")  # Remove old axes
    #         x, y = event.x, event.y  # Get mouse position

    #         # Draw new axes centered on mouse position
    #         self.videoview.create_line(0, y, self.cwidth, y, fill="red", width=2, tags="axes")  # X-axis
    #         self.videoview.create_line(x, 0, x, self.cheight, fill="blue", width=2, tags="axes")  # Y-axis

    #     def store_click(event):
    #         """ Store the clicked coordinates and draw a point. """
    #         x, y = event.x, event.y

    #         self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

    #         self.videoview.unbind("<Motion>")
    #         self.videoview.unbind("<Button>")

    #     self.videoview.bind("<Motion>", update_axes)
    #     self.videoview.bind("<Button>", store_click)
    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

    def drawcircle(self):
        
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


    def strack(self):
        """
        Detects and tracks radius for the main marangoni circle using classical techniques.
        """
        if self.marangoni.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        
        self.popup = SpinnerPopup(self.videoview, self.vwidth, self.vheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.marangoni.track(self._mask, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.loadvideo(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,)).start()



    def clear(self):
        """Clears almost everything"""
        super().clear()
        
        del self.marangoni
        self.marangoni = Marangoni(trackpath=self._trackpath)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        self.seekbar.setcount(100)

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