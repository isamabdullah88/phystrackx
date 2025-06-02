
import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from .App import App
from experiments.SlidingFriction import SlidingFriction
from core.Rect import PixelRect
from .components.Spinner import SpinnerPopup
from .components.Seekbar import CutSeekBar

class SlidingFrictionApp(App):
    def __init__(self, root):
        super().__init__(root)
        
        sfimg = Image.open("assets/rectanglebd.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.rectbd = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                      image=sfimg, command=self.drawrect)
        self.rectbd.pack(pady=10)
        
        self.seekbar = CutSeekBar(self.video_frame, ondrag=self.update_frame)
        
        self._rcoords = None
        self._rect = None
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self._trackpath = os.path.join(tempdir, 'track-sfriction.mp4')
        self.sfriction = SlidingFriction(trackpath=self._trackpath)
        

    def load_video(self, videopath):
        self.sfriction.add_video(videopath)
        # self.sfriction.crop_intime()
        
        self.seekbar.pack(pady=10)
        self.seekbar.setcount(self.sfriction.fcount)

        frame1 = self.sfriction.frame(0)
        self.display_first_frame(frame1)

    def display_first_frame(self, frame=None):
        fwidth = self.sfriction.fwidth
        fheight = self.sfriction.fheight
        frame = self.resize_frame(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]
        
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)
        

        self.fx = floor(self.cwidth/2 - self.sfriction.fwidth/2)
        self.fy = floor(self.cheight/2 - self.sfriction.fheight/2)

        # print('frame ox: ', self.frame_ox)
        self.imgview = self.videoview.create_image(self.fx, self.fy, image=photo, anchor='nw')
        # self.videoview.photo = photo

        self.slider.configure(from_=0, to=self.sfriction.frame_count - 1)
        self.slider.set(0)

    def update_frame(self):
        """Updates the frame displayed in the video view based on the slider position."""

        frame = self.sfriction.frame(index=self.seekbar.idx)
        fwidth = self.sfriction.fwidth
        fheight = self.sfriction.fheight
        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def mark_axes(self):

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
            if self._ctkbox is not None:
                self.videoview.delete(self._ctkbox)
            
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            print('Rect Orig: ', (sx, sy, ex, ey))

            self.videoview.coords(self._ctkbox, sx, sy, event.x, event.y)

            self._rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy)
            print('Rect tr: ', self._rect.totuple())
            self._rect = self._rect.pix2norm(self.fwidth, self.fheight)
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)

    def plot_distances(self):
        if len(self.sfriction.tracked_pts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        # ox, oy = self._ref_frame

        num_tracks = len(self.sfriction.tracked_pts)
        _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

        for i in range(num_tracks):
            tracked_pts = self.sfriction.tracked_pts[i]
            xcoords = tracked_pts[0, :] - self.fx
            ycoords = tracked_pts[1, :] - self.fy

            axes[i][0].plot(xcoords)
            axes[i][0].set_title("x coordinates")
            axes[i][1].plot(ycoords)
            axes[i][1].set_title("y coordinates")
        plt.tight_layout()
        plt.show()


    def start_tracking(self):
        """
        Detects and tracks radius for the main sfriction circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.videoview, self.cwidth, self.cheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.sfriction.track(self._rect, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

            self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()