
import cv2
# import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from video_processing import VideoProcessor
from math import floor

from .App import App
from experiments.SlidingFriction import SlidingFriction

class SlidingFrictionApp(App):
    def __init__(self, root):
        super().__init__(root)
        self.processor = VideoProcessor()
        self.sliding_friction = SlidingFriction()

    def load_video(self):
        self.sliding_friction.add_video(self.processor.video_path)
        self.sliding_friction.crop_intime()

        frame1 = self.sliding_friction.frame(0)
        self.display_first_frame(frame1)

    def display_first_frame(self, frame=None):
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)

        self.fx = floor(self.cwidth/2 - self.sliding_friction.fwidth/2)
        self.fy = floor(self.cheight/2 - self.sliding_friction.fheight/2)

        # print('frame ox: ', self.frame_ox)
        self.videoview.create_image(self.fx, self.fy, image=photo, anchor='nw')
        self.videoview.photo = photo

        self.slider.configure(from_=0, to=self.sliding_friction.frame_count - 1)
        self.slider.set(0)

    def update_frame(self, event):
        frame_idx = int(self.slider.get())

        frame = self.sliding_friction.frame(index=frame_idx)

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)

        # x = floor(self.cwidth/2 - self.sliding_friction.fwidth/2)
        # y = floor(self.cheight/2 - self.sliding_friction.fheight/2)
        # self.videoview.delete('all')
        self.videoview.create_image(self.fx, self.fy, image=photo, anchor='nw')
        self.videoview.photo = photo

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

    def start_bbox(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.current_bbox = self.videoview.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")
        self.videoview.bind("<B1-Motion>", self.draw_bbox)
        self.videoview.bind("<ButtonRelease-1>", self.finish_bbox)

    def draw_bbox(self, event):
        self.videoview.coords(self.current_bbox, self.start_x, self.start_y, event.x, event.y)

    def finish_bbox(self, event):
        self.videoview.unbind("<B1-Motion>")
        self.videoview.unbind("<ButtonRelease-1>")
        bbox_coords = (self.start_x, self.start_y, event.x, event.y)
        # self.bboxes_to_track.append(bbox_coords)
        cx = (bbox_coords[0] + bbox_coords[2]) / 2
        cy = (bbox_coords[1] + bbox_coords[3]) / 2

        self.videoview.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="red")

        # frame_ox, frame_oy = self._ref_frame

        cx -= self.fx
        cy -= self.fy
        self.processor.points_to_track.append((cx, cy))

    def plot_distances(self):
        if len(self.sliding_friction.tracked_pts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        # ox, oy = self._ref_frame

        num_tracks = len(self.sliding_friction.tracked_pts)
        _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

        for i in range(num_tracks):
            tracked_pts = self.sliding_friction.tracked_pts[i]
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

        self.sliding_friction.track(self.processor.points_to_track)

        self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button