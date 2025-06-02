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
from .components.Spinner import SpinnerPopup
from .components.Seekbar import CutSeekBar

class MarangoniApp(App):
    def __init__(self, root):
        super().__init__(root)

        sfimg = Image.open("assets/boundary.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.boundary = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                      image=sfimg, command=self.drawcircle)
        self.boundary.pack(pady=10)
        self._idx = 0

        self.seekbar = CutSeekBar(self.video_frame, ondrag=self.updateframe)

        self.ccoords = (0, 0)

        # mask from user for tracking
        self._mask = None

        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        self._trackpath = os.path.join(tempdir, 'track-marangoni.mp4')

        self.marangoni = Marangoni(trackpath=self._trackpath)



    def load_video(self, videopath):
        self.marangoni.add_video(videopath)
        
        self.seekbar.pack(pady=10)
        self.seekbar.setcount(self.marangoni.fcount)

        frame1 = self.marangoni.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame):
        fwidth = self.marangoni.fwidth
        fheight = self.marangoni.fheight
        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.fx = floor(self.cwidth/2 - frame.shape[1]/2)
        self.fy = floor(self.cheight/2 - frame.shape[0]/2)

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
    def updateframe(self):
        
        frame = self.marangoni.frame(index=self.seekbar.idx)
        fwidth = self.marangoni.fwidth
        fheight = self.marangoni.fheight

        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

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

            self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Button>")

        self.videoview.bind("<Motion>", update_axes)
        self.videoview.bind("<Button>", store_click)

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


    def start_tracking(self):
        """
        Detects and tracks radius for the main marangoni circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.videoview, self.cwidth, self.cheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.marangoni.track(self._mask, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

            self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()





    def plot_distances(self):
        if len(self.marangoni.tracked_pts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        num_tracks = len(self.marangoni.tracked_pts)
        _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

        for i in range(num_tracks):
            tracked_pts = self.marangoni.tracked_pts[i]
            xcoords = tracked_pts[0, :] - self.fx
            ycoords = tracked_pts[1, :] - self.fy

            axes[i][0].plot(xcoords)
            axes[i][0].set_title("x coordinates")
            axes[i][1].plot(ycoords)
            axes[i][1].set_title("y coordinates")

        plt.tight_layout()
        plt.show()