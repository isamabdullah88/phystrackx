import os
import cv2
import numpy as np
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from video_processing import VideoProcessor
from math import floor, ceil

from .App import App
from experiments.Marangoni import Marangoni
from .Core import circilize, fcrop_coords
from .components.Spinner import SpinnerPopup
from .components.Seekbar import CutSeekBar

class MarangoniApp(App):
    def __init__(self, root):
        super().__init__(root)

        # self.circle = Circle()

        self.boundary = ctk.CTkButton(self.filter_frame, text="Mark Boundary", command=self.drawcircle)
        self.boundary.pack(pady=5)
        self._idx = 0

        self.seekbar = CutSeekBar(self.video_frame, ondrag=self.update_frame)

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
        self.display_first_frame(frame1)

    def display_first_frame(self, frame):
        fwidth = self.marangoni.frame_width
        fheight = self.marangoni.frame_height
        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.fx = floor(self.canvas_width/2 - frame.shape[1]/2)
        self.fy = floor(self.canvas_height/2 - frame.shape[0]/2)

        self.imgview = self.video_view.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
    def update_frame(self):
        
        frame = self.marangoni.frame(index=self.seekbar.idx)
        fwidth = self.marangoni.frame_width
        fheight = self.marangoni.frame_height

        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.video_view.itemconfig(self.imgview, image=self.photo)

    def mark_axes(self):

        def update_axes(event):
            """ Update the axes to follow the mouse cursor. """
            self.video_view.delete("axes")  # Remove old axes
            x, y = event.x, event.y  # Get mouse position

            # Draw new axes centered on mouse position
            self.video_view.create_line(0, y, self.canvas_width, y, fill="red", width=2, tags="axes")  # X-axis
            self.video_view.create_line(x, 0, x, self.canvas_height, fill="blue", width=2, tags="axes")  # Y-axis

        def store_click(event):
            """ Store the clicked coordinates and draw a point. """
            x, y = event.x, event.y

            self.video_view.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            self.video_view.unbind("<Motion>")
            self.video_view.unbind("<Button>")

        self.video_view.bind("<Motion>", update_axes)
        self.video_view.bind("<Button>", store_click)

    def drawcircle(self):
        
        def ondown(event):
            self.ccoords = (event.x-self.fx, event.y-self.fy)
            
            self.photo = ImageTk.PhotoImage(circilize(10, 10))
            
            self.video_view.itemconfig(self.imgview, image=self.photo)
            
        def incircle(event):
            ex = (event.x-self.fx)
            ey = (event.y-self.fy)

            # radx = 2*abs(ex - self.ccoords[0])
            # rady = 2*abs(ey - self.ccoords[1])
            
            # circ, matte = circilize(radx, rady)
            
            # height, width = self._frame.shape[:2]
            # cx, cy = self.ccoords
            # frame = self._frame.copy()

            # cysrt = cy-floor(rady/2)
            # cyend = cy+ceil(rady/2)
            # cxsrt = cx-floor(radx/2)
            # cxend = cx+ceil(radx/2)

            # if cxsrt < 0:
            #     circ = circ[:,-cxsrt:]
            #     matte = matte[:,-cxsrt:]
            #     cxsrt = 0

            # if cxend > width:
            #     cxend = width
            #     circ = circ[:,:cxend-cxsrt]
            #     matte = matte[:,:cxend-cxsrt]

            # if cysrt < 0:
            #     circ = circ[-cysrt:,:]
            #     matte = matte[-cysrt:,:]
            #     cysrt = 0

            # if cyend > height:
            #     cyend = height
            #     circ = circ[:cyend-cysrt, :radx]
            #     matte = matte[:cyend-cysrt, :radx]

            # frame_crop = frame[cysrt:cyend, cxsrt:cxend]

            # frame_cropbd = cv2.addWeighted(frame_crop, 0.6, circ, 0.4, 0)
            # frame_cropbd[matte < 150] = frame_crop[matte < 150]
            
            # matte_frame = np.zeros((height, width), np.uint8)
            # matte_frame[cysrt:cyend, cxsrt:cxend] = matte
            # frame[cysrt:cyend, cxsrt:cxend] = frame_cropbd
            frame, mask = fcrop_coords(self._frame, self.ccoords, (ex, ey))

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.photo = ImageTk.PhotoImage(image=img)
            self._mask = mask

            self.video_view.itemconfig(self.imgview, image=self.photo)
            

        self.video_view.bind("<Button-1>", ondown)
        self.video_view.bind("<B1-Motion>", incircle)


    def start_tracking(self):
        """
        Detects and tracks radius for the main marangoni circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.video_view, self.canvas_width, self.canvas_height)

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