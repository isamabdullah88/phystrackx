
import cv2
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageSequence
import numpy as np
from matplotlib import pyplot as plt
from tkinter import ttk
from tkinter import filedialog, simpledialog, messagebox
from video_processing import VideoProcessor
import csv
import imageio
from math import floor

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Phys TrackerX")
        
        # Make the window cover the entire screen
        self.root.geometry("960x640")
        self.processor = VideoProcessor()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._ref_frame = [0.0, 0.0]

        # self.collision = Collision()

    def exit_fullscreen(self):
        self.root.attributes('-fullscreen', False)

    def show_progress_bar(self):
        self.progress_popup = ctk.CTkToplevel(self.root)
        self.progress_popup.title("Applying Filters")

        self.progress_label = ctk.CTkLabel(self.progress_popup, text="Processing frames...")
        self.progress_label.pack(pady=10)

        self.progress_bar = ctk.CTkProgressBar(self.progress_popup, orientation="horizontal", mode="determinate")
        self.progress_bar.pack(pady=10)

        self.progress_popup.update()

    def update_progress_bar(self, value, max_value):
        self.progress_bar["value"] = value
        self.progress_bar["maximum"] = max_value
        self.progress_label.configure(text=f"Processing frames... {value}/{max_value}")
        self.progress_popup.update()

    def close_progress_bar(self):
        self.progress_popup.destroy()

    def create_widgets(self):
            # Create a frame to hold the filter widgets on the left side
            self.filter_frame = ctk.CTkFrame(self.root)
            self.filter_frame.pack(side=ctk.LEFT, fill=ctk.Y, padx=10, pady=10)
            
            self.open_button = ctk.CTkButton(self.filter_frame, text="Open Video", command=self.open_video)
            self.open_button.pack(pady=10)
            
            self.fps_label = ctk.CTkLabel(self.filter_frame, text="")
            self.fps_label.pack(pady=5)
            
            # self.filter_button = ctk.CTkButton(self.filter_frame, text="Apply Filters", command=self.show_filter_popup)
            # self.filter_button.pack(pady=10)
            
            self.undo_button = ctk.CTkButton(self.filter_frame, text="Reset", command=self.undo_filter)
            self.undo_button.pack(pady=10)
            
            # self.frame_button = ctk.CTkButton(self.filter_frame, text="Select Initial and Final Frames", command=self.select_frames)
            # self.frame_button.pack(pady=10)
            
            # self.distance_button = ctk.CTkButton(self.filter_frame, text="Set Reference Distance", command=self.set_reference_distance)
            # self.distance_button.pack(pady=10)
            
            # self.clip_button = ctk.CTkButton(self.filter_frame, text="Clip Video", command=self.clip_video)
            # self.clip_button.pack(pady=10)
            
            self.axis_button = ctk.CTkButton(self.filter_frame, text="Mark Axes", command=self.mark_axes)
            self.axis_button.pack(pady=10)
            
            self.track_button = ctk.CTkButton(self.filter_frame, text="Mark Points to Track", command=self.choose_tracking_method)
            self.track_button.pack(pady=10)

            self.track_start_button = ctk.CTkButton(self.filter_frame, text="Start Tracking", command=self.start_tracking)
            self.track_start_button.pack(pady=10)
            
            self.track_coords_button = ctk.CTkButton(self.filter_frame, text="Tracked Coordinates", command=self.show_tracked_coordinates_window)
            self.track_coords_button.pack(pady=10)
            self.track_coords_button.configure(state=ctk.DISABLED)  # Disable the button initially

            self.info_label = ctk.CTkLabel(self.filter_frame, text="")
            self.info_label.pack(pady=10)
            
            # Create a button to show tracked points in a table
            # self.table_button = ctk.CTkButton(self.filter_frame, text="Show Tracked Points Table", command=self.show_tracked_points_table)
            # self.table_button.pack(pady=10)
            
            # Create a frame to hold the video and slider widgets on the right side
            self.video_frame = ctk.CTkFrame(self.root)
            self.video_frame.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=10, pady=10)
            
            self.canvas_width = 640
            self.canvas_height = 480
            self.video_view = ctk.CTkCanvas(self.video_frame, width=self.canvas_width, height=self.canvas_height)
            self.video_view.pack(pady=20, expand=True)
            
            # self.slider = ctk.Scale(self.video_frame, from_=0, to=100, orient=ctk.HORIZONTAL, length=400, resolution=1, command=self.update_frame)
            self.slider = ctk.CTkSlider(self.video_frame, orientation="horizontal", from_=0,
                                        width=400, fg_color="red", progress_color="green",
                                        button_color="yellow", command=self.update_frame)
            self.slider.set(0)
            # self.slider = ctk.CTkSlider(self.video_frame)
            self.slider.pack(pady=10)

            self.menu_button = ctk.CTkButton(self.filter_frame, text="Back to Menu", command=self.back_to_menu)
            self.menu_button.pack(pady=10)

    


    def open_video(self):
        self.processor.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if self.processor.video_path:
            self.processor.fps = int(simpledialog.askinteger("FPS", "Enter FPS:"))
            self.fps_label.configure(text=f"FPS: {self.processor.fps}")
            self.load_video()
    
    def load_video(self):
        pass

    def display_first_frame(self, frame=None):
        pass

    def update_frame(self, event):
        pass
        
    
    def mark_line(self, event):
        if len(self.processor.line_coords) < 2:
            self.processor.line_coords.append((event.x, event.y))
            if len(self.processor.line_coords) == 2:
                self.video_view.create_line(self.processor.line_coords[0], self.processor.line_coords[1], fill="red", width=2)
                self.processor.ref_distance = simpledialog.askfloat("Reference Distance", "Enter the reference distance in your chosen unit:")
                self.info_label.configure(text=f"Reference Distance: {self.processor.ref_distance} units")
    

    def mark_axes(self):
        pass

    def mark_points_to_track(self):
        self.processor.points_to_track = []
        messagebox.showinfo("Instruction", "Please click points on the video to mark them for tracking.")
        self.video_view.bind("<Button-1>", self.mark_point)
    
    def mark_point(self, event):
        self.processor.points_to_track.append((event.x, event.y))
        self.video_view.create_oval(event.x-3, event.y-3, event.x+3, event.y+3, fill="red")

    def choose_tracking_method(self):
        self.tracking_method = ctk.StringVar()
        self.tracking_method.set("points")  # default value

        method_popup = ctk.CTkToplevel(self.root)
        method_popup.title("Select Tracking Method")

        ctk.CTkLabel(method_popup, text="Choose tracking method:").pack(pady=10)
        ctk.CTkRadioButton(method_popup, text="Track Points", variable=self.tracking_method, value="points").pack(anchor=ctk.W)
        ctk.CTkRadioButton(method_popup, text="Track Centroid", variable=self.tracking_method, value="bbox").pack(anchor=ctk.W)

        ctk.CTkButton(method_popup, text="OK", command=lambda: self.confirm_tracking_method(method_popup)).pack(pady=10)

    def confirm_tracking_method(self, popup):
        method = self.tracking_method.get()
        popup.destroy()

        if method == "points":
            self.mark_points_to_track()
        elif method == "bbox":
            self.mark_bboxes_to_track()
        else:
            messagebox.showerror("Error", "Invalid method. Please select 'points' or 'bbox'.")

    def mark_bboxes_to_track(self):
        self.bboxes_to_track = []
        messagebox.showinfo("Instruction", "Please draw bounding boxes around the objects to track. Draw multiple bounding boxes if needed.")
        self.video_view.bind("<Button-1>", self.start_bbox)

    def start_bbox(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.current_bbox = self.video_view.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")
        self.video_view.bind("<B1-Motion>", self.draw_bbox)
        self.video_view.bind("<ButtonRelease-1>", self.finish_bbox)

    def draw_bbox(self, event):
        self.video_view.coords(self.current_bbox, self.start_x, self.start_y, event.x, event.y)

    def finish_bbox(self, event):
        self.video_view.unbind("<B1-Motion>")
        self.video_view.unbind("<ButtonRelease-1>")
        bbox_coords = (self.start_x, self.start_y, event.x, event.y)
        self.bboxes_to_track.append(bbox_coords)
        centroid_x = (bbox_coords[0] + bbox_coords[2]) / 2 - self.frame_ox
        centroid_y = (bbox_coords[1] + bbox_coords[3]) / 2 - self.frame_oy
        self.processor.points_to_track.append((centroid_x, centroid_y))
        self.video_view.create_oval(centroid_x - 3, centroid_y - 3, centroid_x + 3, centroid_y + 3, fill="red")

    def show_tracked_coordinates_window(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title("Tracked Coordinates Options")

        ctk.CTkButton(popup, text="Plot X and Y Distances", command=self.plot_distances).pack(pady=5)
        ctk.CTkButton(popup, text="1st Derivative (Velocity)", command=lambda: self.calculate_and_export_derivative(1)).pack(pady=5)
        ctk.CTkButton(popup, text="2nd Derivative (Acceleration)", command=lambda: self.calculate_and_export_derivative(2)).pack(pady=5)
        # ctk.CTkButton(popup, text="Calculate Path Length", command=self.calculate_path_length).pack(pady=5)
        # ctk.CTkButton(popup, text="Calculate Angle of Movement", command=self.calculate_angle_of_movement).pack(pady=5)
        ctk.CTkButton(popup, text="Track Angle Between Three Points", command=self.select_third_point).pack(pady=5)
        ctk.CTkButton(popup, text="Show Tracked Points Table", command=self.show_tracked_points_table).pack(pady=5)

    def plot_distances(self):
        pass

    def on_close(self):
        self.root.destroy()


    def start_tracking(self):
        """
        Implements Lucas-Kanade optical flow tracking for marked points across video frames.
        This method processes the entire video sequence and tracks the motion of selected points.
        """
        pass
    

    def back_to_menu(self):
        # self.root.destroy()
        # root = ctk.Tk()
        # root.geometry("960x640")
        # menu_x = MenuScreen(root)
        # root.mainloop()
        # self._restart()
        self.root.update()
        self.root.deiconify()