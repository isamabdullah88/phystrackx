
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
from .components.Spinner import SpinnerPopup
from .components.Seekbar import CutSeekBar

class SlidingFrictionApp(App):
    def __init__(self, root):
        super().__init__(root)
        
        img = Image.open("assets/rectanglebd.png").resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        self.rectbd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawrect)
        self.rectbd.pack(padx=5, pady=5)
        self.rectbd.image = img
        
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        self.scroll_toolbar.pack()
        
        self._rcoords = None
        self._rects = []
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-sfriction.mp4')
        self.sfriction = SlidingFriction(trackpath=self._trackpath)
        

    def load_video(self, videopath):
        self.sfriction.add_video(videopath)
        
        # self.seekbar.pack(pady=10)
        self.seekbar.setcount(self.sfriction.fcount)

        frame1 = self.sfriction.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame=None):
        fwidth = self.sfriction.fwidth
        fheight = self.sfriction.fheight
        frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]
        print('shape: ', self.fheight, self.fwidth)
        
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        
        print('self.vwidth, self.vheight: ', self.vwidth, self.vheight)
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)
        print('fx, fy: ', self.fx, self.fy)

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
            # self._ref_frame = [x-self.frame_ox, y-self.frame_oy]  # Store coordinates
            self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            # print(self._ref_frame)
            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Button>")

        self.videoview.bind("<Motion>", update_axes)
        self.videoview.bind("<Button>", store_click)

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
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)
        self.videoview.bind("<ButtonRelease-1>", onrelease)

    def plotx(self):
        if len(self.sfriction.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        plot = Plot(self.sfriction.trackpts)
        plot.plotx()
        plot.plotdrv()
        plot.show()


    def strack(self):
        """
        Detects and tracks radius for the main sfriction circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.videoview, self.cwidth, self.cheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.sfriction.track(self._rects, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

            # self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()