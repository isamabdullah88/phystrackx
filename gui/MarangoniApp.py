
import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from video_processing import VideoProcessor
from math import floor

from .App import App
from experiments.Marangoni import Marangoni

class MarangoniApp(App):
    def __init__(self, root):
        super().__init__(root)
        self.processor = VideoProcessor()
        self.marangoni = Marangoni()

        self.boundary = ctk.CTkButton(self.filter_frame, text="Mark Boundary", command=self.drawcircle)
        self.boundary.pack(pady=10)


    def load_video(self):
        self.marangoni.add_video(self.processor.video_path)
        # self.marangoni.crop_intime()
        print('frameconut1: ', self.marangoni.frame_count)

        frame1 = self.marangoni.frame(0)
        self.display_first_frame(frame1)

    def display_first_frame(self, frame=None):
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)

        self.fx = floor(self.canvas_width/2 - self.marangoni.frame_width/2)
        self.fy = floor(self.canvas_height/2 - self.marangoni.frame_height/2)

        # print('frame ox: ', self.frame_ox)
        self.video_view.create_image(self.fx, self.fy, image=photo, anchor='nw')
        self.video_view.photo = photo
        print('framecount2: ', self.marangoni.frame_count)

        self.slider.configure(from_=0, to=self.marangoni.frame_count - 1)
        self.slider.set(0)

    def update_frame(self, event):
        frame_idx = int(self.slider.get())
        print('frameidx: ', frame_idx)

        frame = self.marangoni.frame(index=frame_idx)

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)

        # x = floor(self.canvas_width/2 - self.marangoni.frame_width/2)
        # y = floor(self.canvas_height/2 - self.marangoni.frame_height/2)
        # self.video_view.delete('all')
        self.video_view.create_image(self.fx, self.fy, image=photo, anchor='nw')
        self.video_view.photo = photo

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

    def drawcircle(self, event):
        self.sx, self.sy = event.x, event.y
        self.curr_circ = self.video_view.create_aa_circle(self.sx, self.sy, 1, outline="red")
        self.video_view.bind("<B1-Motion>", self.on_circle)
        self.video_view.bind("<ButtonRelease-1>", self.circle_end)

    def on_circle(self, event):
        rad = np.sqrt(np.pow(event.x - self.sx, 2) + np.pow(event.y - self.sy, 2))
        self.video_view.coords(self.curr_circ, self.sx, self.sy, rad)

    def circle_end(self, event):
        self.video_view.unbind("<B1-Motion>")
        self.video_view.unbind("<ButtonRelease-1>")
        rad = np.sqrt(np.pow(event.x - self.sx, 2) + np.pow(event.y - self.sy, 2))
        # self.bboxes_to_track.append(bbox_coords)
        # cx = (bbox_coords[0] + bbox_coords[2]) / 2
        # cy = (bbox_coords[1] + bbox_coords[3]) / 2

        # self.video_view.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="red")

        # frame_ox, frame_oy = self._ref_frame

        # cx -= self.fx
        # cy -= self.fy
        # self.processor.points_to_track.append((cx, cy))

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


    def start_tracking(self):
        """
        Implements Lucas-Kanade optical flow tracking for marked points across video frames.
        This method processes the entire video sequence and tracks the motion of selected points.
        """
        # Input validation: ensure points have been marked for tracking
        if not self.processor.points_to_track:
            messagebox.showerror("Error", "Please mark points to track first.")
            return

        self.marangoni.track(self.processor.points_to_track)

        self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button