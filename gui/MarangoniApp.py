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
from .Core import Circle, circilize
from .Components import SpinnerPopup

class MarangoniApp(App):
    def __init__(self, root):
        super().__init__(root)
        self.processor = VideoProcessor()

        self.circle = Circle()

        self.boundary = ctk.CTkButton(self.filter_frame, text="Mark Boundary", command=self.drawcircle)
        self.boundary.pack(pady=10)
        self._idx = 0

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
        # self.marangoni.crop_intime()
        print('frameconut1: ', self.marangoni.frame_count)

        frame1 = self.marangoni.frame(0)
        self.display_first_frame(frame1)

    def display_first_frame(self, frame):
        fwidth = self.marangoni.frame_width
        fheight = self.marangoni.frame_height
        frame = self.resize_frame(frame, fwidth, fheight)
        print('display first frame: ', frame.shape)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.fx = floor(self.canvas_width/2 - frame.shape[1]/2)
        self.fy = floor(self.canvas_height/2 - frame.shape[0]/2)
        # print('canvas width: ', self.canvas_width)

        # print('frame ox: ', self.frame_ox)
        # self.video_view.configure(width=frame.shape[1], height=frame.shape[0])
        self.imgview = self.video_view.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        # self.video_view.itemconfig(self.imgview, image=self.photo)
        # self.video_view.photo = photo
        print('framecount2: ', self.marangoni.frame_count)

        self.slider.configure(from_=0, to=self.marangoni.frame_count - 1)
        self.slider.set(0)

    def update_frame(self, event):
        print('In update!')
        frame_idx = int(self.slider.get())
        # print('frameidx: ', frame_idx)

        frame = self.marangoni.frame(index=frame_idx)
        fwidth = self.marangoni.frame_width
        fheight = self.marangoni.frame_height

        frame = self.resize_frame(frame, fwidth, fheight)
        # cv2.imwrite(f"frame-{self._idx}.png", frame)
        # self._idx += 1

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.video_view.itemconfig(self.imgview, image=self.photo)

        # x = floor(self.canvas_width/2 - self.marangoni.frame_width/2)
        # y = floor(self.canvas_height/2 - self.marangoni.frame_height/2)
        # self.video_view.delete('all')
        # self.video_view.create_image(self.fx, self.fy, image=photo, anchor='nw')
        # self.video_view.photo = photo

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
            # self._ref_frame = [x-self.frame_ox, y-self.frame_oy]  # Store coordinates
            self.video_view.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            # print(self._ref_frame)
            self.video_view.unbind("<Motion>")
            self.video_view.unbind("<Button>")

        self.video_view.bind("<Motion>", update_axes)
        self.video_view.bind("<Button>", store_click)

    def drawcircle(self):

        # coords = (0, 0)
        circle = None
        rad = 0

        def ondown(event):
            self.ccoords = (event.x-self.fx, event.y-self.fy)
            print('cx, cy: ', (self.ccoords[0], self.ccoords[1]))
            # circle = self.video_view.create_aa_circle(self.ccoords[0], self.ccoords[1], 1)
            self.photo = ImageTk.PhotoImage(circilize(10, 10))
            # self.video_view.create_image(self.ccoords[0], self.ccoords[1], image=circle)
            # self.video_view.photo = circle
            self.video_view.itemconfig(self.imgview, image=self.photo)
            # print('self.ccoords[0], self.ccoords[1]: ', (self.ccoords[0], self.ccoords[1]))
            # self.video_view.bind("<B1-Motion>", oncircle)
            # self.video_view.bind("<ButtonRelease-1>", circle_end)
            # self.video_view.bind("<Motion>", circle)

        def incircle(event):
            # rad = floor(np.sqrt(np.pow(event.x - self.ccoords[0], 2) + np.pow(event.y - self.ccoords[1], 2)))
            # print('self.ccoords[0], self.ccoords[1]: ', (self.ccoords[0], self.ccoords[1]))
            # print('rad: ', rad)
            ex = (event.x-self.fx)
            ey = (event.y-self.fy)
            radx = 2*abs(ex - self.ccoords[0])
            rady = 2*abs(ey - self.ccoords[1])
            # print('radx, rady: ', (radx, rady))

            circ, matte = circilize(radx, rady)
            # circle = np.array(circ)[:,:,:3]
            # circlealpha = np.array(circ)[:,:,3]
            # circle[circlealpha < ]
            
            height, width = self._frame.shape[:2]
            cx, cy = self.ccoords
            frame = self._frame.copy()


            cysrt = cy-floor(rady/2)
            cyend = cy+ceil(rady/2)
            cxsrt = cx-floor(radx/2)
            cxend = cx+ceil(radx/2)

            if cxsrt < 0:
                circ = circ[:,-cxsrt:]
                matte = matte[:,-cxsrt:]
                cxsrt = 0

            if cxend > width:
                cxend = width
                circ = circ[:,:cxend-cxsrt]
                matte = matte[:,:cxend-cxsrt]

            if cysrt < 0:
                circ = circ[-cysrt:,:]
                matte = matte[-cysrt:,:]
                cysrt = 0

            if cyend > height:
                cyend = height
                circ = circ[:cyend-cysrt, :radx]
                matte = matte[:cyend-cysrt, :radx]


            # print('circ: ', circ.shape)

            frame_crop = frame[cysrt:cyend, cxsrt:cxend]
            # print('frame crop: ', frame_crop.shape)
            frame_cropbd = cv2.addWeighted(frame_crop, 0.6, circ, 0.4, 0)
            frame_cropbd[matte < 150] = frame_crop[matte < 150]
            
            matte_frame = np.zeros((height, width), np.uint8)
            matte_frame[cysrt:cyend, cxsrt:cxend] = matte
            frame[cysrt:cyend, cxsrt:cxend] = frame_cropbd
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.photo = ImageTk.PhotoImage(image=img)
            # img.save("circle.png")
            # self.video_view.create_image(self.ccoords[0], self.ccoords[1], image=circle)
            # self.video_view.photo = circle
            self.video_view.itemconfig(self.imgview, image=self.photo)
            # self.video_view.self.ccoords(circle, self.ccoords[0], self.ccoords[1], rad)
            # self.video_view.create_image(self.ccoords[0], self.ccoords[1], image=circle)
            self._mask = matte_frame

        # def end(event):
        #     pass
            # self.video_view.unbind("<Button-1>")
            # self.video_view.unbind("<ButtonRelease-1>")
            # rad = np.sqrt(np.pow(event.x - self.ccoords[0], 2) + np.pow(event.y - self.ccoords[1], 2))
            # self.circle = Circle(cx=self.ccoords[0], cy=self.ccoords[1], rad=rad)

        self.video_view.bind("<Button-1>", ondown)
        self.video_view.bind("<B1-Motion>", incircle)
        # self.video_view.bind("<ButtonRelease-1>", end)



    def start_tracking(self):
        """
        Detects and tracks radius for the main marangoni circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.video_view, self.canvas_width, self.canvas_height)

        def trackbg(popup):
            self.marangoni.track(self._mask)
            # popup.destroy()
            # popup = None
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

            self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()





    def plot_distances(self):
        if len(self.marangoni.tracked_pts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        # ox, oy = self._ref_frame

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