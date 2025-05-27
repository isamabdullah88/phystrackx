import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import ImageTk, Image, ImageDraw
from video_processing import VideoProcessor
# from utils import resize_frame
import cv2
import numpy as np
from tkinter import ttk
import csv
import imageio
from PIL import ImageSequence

# class MenuScreen:
#     def __init__(self, master):
#         self.master = master
#         self.master.title("Select Tracking Type")
#         self.master.geometry("960x640") 

#         # Load and display the logo, resized to fit the window
#         self.load_and_display_logo(master)

#         # Title label
#         tk.Label(master, text="Choose a tracking type:", font=("Helvetica", 16)).pack(pady=(20, 10))

#         # Buttons for menu options
#         ttk.Button(master, text="Rigid Object Tracking", command=self.on_rigid).pack(fill='x', padx=50, pady=5)
#         ttk.Button(master, text="Non-Rigid Object Tracking", command=self.on_non_rigid).pack(fill='x', padx=50, pady=5)

#     def load_and_display_logo(self, master):
#         # Load the image
#         image_path = "phys_track_logo.png" 
#         image = Image.open(image_path)

#         # Resize the image to fit the window width while maintaining aspect ratio
#         base_width = 700  # Set width smaller than the window width for padding considerations
#         w_percent = (base_width / float(image.size[0]))
#         h_size = int((float(image.size[1]) * float(w_percent)))
#         image = image.resize((base_width, h_size), Image.Resampling.LANCZOS)

#         photo = ImageTk.PhotoImage(image)

#         # Create a label to display the image
#         image_label = tk.Label(master, image=photo)
#         image_label.image = photo  # Keep a reference, prevent GC
#         image_label.pack(pady=(10, 0))

#     def on_rigid(self):
#         self.master.destroy()
#         root = tk.Tk()
#         root.geometry("960x640")
#         app = VideoApp(root)
#         root.mainloop()

#     def on_non_rigid(self):
        self.master.destroy()
        root = tk.Tk()
        from nonrigid import VideoApp2  # Delayed import
        root.geometry("960x640")
        app = VideoApp2(root)
        root.mainloop()

# class VideoApp:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Phys TrackerX")
        
#         # Make the window cover the entire screen
#         self.root.geometry("960x640")
#         self.processor = VideoProcessor()
#         self.create_widgets()
#         self.root.protocol("WM_DELETE_WINDOW", self.on_close)

#     def exit_fullscreen(self):
#         self.root.attributes('-fullscreen', False)

#     def show_progress_bar(self):
#         self.progress_popup = tk.Toplevel(self.root)
#         self.progress_popup.title("Applying Filters")

#         self.progress_label = tk.Label(self.progress_popup, text="Processing frames...")
#         self.progress_label.pack(pady=10)

#         self.progress_bar = ttk.Progressbar(self.progress_popup, orient="horizontal", length=300, mode="determinate")
#         self.progress_bar.pack(pady=10)

#         self.progress_popup.update()

#     def update_progress_bar(self, value, max_value):
#         self.progress_bar["value"] = value
#         self.progress_bar["maximum"] = max_value
#         self.progress_label.config(text=f"Processing frames... {value}/{max_value}")
#         self.progress_popup.update()

#     def close_progress_bar(self):
#         self.progress_popup.destroy()

#     def create_widgets(self):
#             # Create a frame to hold the filter widgets on the left side
#             self.filter_frame = tk.Frame(self.root)
#             self.filter_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
            
#             self.open_button = tk.Button(self.filter_frame, text="Open Video", command=self.open_video)
#             self.open_button.pack(pady=10)
            
#             self.fps_label = tk.Label(self.filter_frame, text="")
#             self.fps_label.pack(pady=5)
            
#             self.filter_button = tk.Button(self.filter_frame, text="Apply Filters", command=self.show_filter_popup)
#             self.filter_button.pack(pady=10)
            
#             self.undo_button = tk.Button(self.filter_frame, text="Reset", command=self.undo_filter)
#             self.undo_button.pack(pady=10)
            
#             self.frame_button = tk.Button(self.filter_frame, text="Select Initial and Final Frames", command=self.select_frames)
#             self.frame_button.pack(pady=10)
            
#             self.distance_button = tk.Button(self.filter_frame, text="Set Reference Distance", command=self.set_reference_distance)
#             self.distance_button.pack(pady=10)
            
#             # self.clip_button = tk.Button(self.filter_frame, text="Clip Video", command=self.clip_video)
#             # self.clip_button.pack(pady=10)
            
#             self.axis_button = tk.Button(self.filter_frame, text="Mark Axes", command=self.check_reference_distance)
#             self.axis_button.pack(pady=10)
            
#             self.track_button = tk.Button(self.filter_frame, text="Mark Points to Track", command=self.choose_tracking_method)
#             self.track_button.pack(pady=10)

#             self.track_start_button = tk.Button(self.filter_frame, text="Start Tracking", command=self.start_tracking)
#             self.track_start_button.pack(pady=10)
            
#             self.track_coords_button = tk.Button(self.filter_frame, text="Tracked Coordinates", command=self.show_tracked_coordinates_window)
#             self.track_coords_button.pack(pady=10)
#             self.track_coords_button.config(state=tk.DISABLED)  # Disable the button initially

#             self.info_label = tk.Label(self.filter_frame, text="")
#             self.info_label.pack(pady=10)
            
#             # Create a button to show tracked points in a table
#             # self.table_button = tk.Button(self.filter_frame, text="Show Tracked Points Table", command=self.show_tracked_points_table)
#             # self.table_button.pack(pady=10)
            
#             # Create a frame to hold the video and slider widgets on the right side
#             self.video_frame = tk.Frame(self.root)
#             self.video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            
#             self.videoview = tk.Canvas(self.video_frame, width=640, height=480)
#             self.videoview.pack(pady=20, expand=True)
            
#             self.slider = tk.Scale(self.video_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=400, resolution=1, command=self.update_frame)
#             self.slider.pack(pady=10)

#             self.menu_button = tk.Button(self.filter_frame, text="Back to Menu", command=self.back_to_menu)
#             self.menu_button.pack(pady=10)

#             # self.filter_frame2 = tk.Frame(self.root)

#             # self.filter_frame2.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

#             # self.open_button = tk.Button(self.filter_frame2, text="Ass", command=self.open_video)
#             # self.open_button.pack(pady=10)
    


#     def open_video(self):
#         self.processor.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
#         if self.processor.video_path:
#             self.processor.fps = int(simpledialog.askinteger("FPS", "Enter FPS:"))
#             self.fps_label.config(text=f"FPS: {self.processor.fps}")
#             self.load_video()
    
#     def load_video(self):
#         cap = cv2.VideoCapture(self.processor.video_path)
#         if not cap.isOpened():
#             messagebox.showerror("Error", "Failed to open video")
#             return

#         ret, frame = cap.read()
#         if not ret:
#             messagebox.showerror("Error", "Failed to read video frame")
#             return
#         cap.release()

#         # Show cropping interface
#         self.show_crop_interface(frame)

#     def show_crop_interface(self, frame):
#         top = tk.Toplevel(self.root)
#         top.title("Draw cropping area")
#         original_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
#         # Compute scaling factor to maintain aspect ratio within 640x640 limit
#         max_size = 640
#         scale = min(max_size / original_img.width, max_size / original_img.height)
#         display_img = original_img.resize((int(original_img.width * scale), int(original_img.height * scale)), Image.Resampling.LANCZOS)

#         photo = ImageTk.PhotoImage(image=display_img)
#         canvas = tk.Canvas(top, width=display_img.width, height=display_img.height)
#         canvas.pack()
#         canvas.create_image(0, 0, image=photo, anchor='nw')
#         canvas.image = photo  # Keep a reference!

#         self.crop_rectangle = None

#         def on_mouse_click(event):
#             self.start_x, self.start_y = event.x, event.y
#             self.crop_rectangle = canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline='red')

#         def on_mouse_move(event):
#             if self.crop_rectangle:
#                 canvas.coords(self.crop_rectangle, self.start_x, self.start_y, event.x, event.y)

#         def on_mouse_release(event):
#             if self.crop_rectangle:
#                 # Scale coordinates back to original dimensions
#                 self.crop_coords = (
#                     int(self.start_x / scale),
#                     int(self.start_y / scale),
#                     int(event.x / scale),
#                     int(event.y / scale)
#                 )
#                 top.destroy()
#                 self.read_and_crop_video()  # Call to process the video after cropping is set
#             else:
#                 self.crop_coords = None

#         def skip_cropping():
#             messagebox.showinfo("Skip Cropping", "No cropping will be applied.")
#             self.crop_coords = None
#             top.destroy()
#             self.read_and_crop_video()  # Process without cropping

#         canvas.bind("<ButtonPress-1>", on_mouse_click)
#         canvas.bind("<B1-Motion>", on_mouse_move)
#         canvas.bind("<ButtonRelease-1>", on_mouse_release)

#         skip_button = tk.Button(top, text="Skip Cropping", command=skip_cropping)
#         skip_button.pack(side=tk.BOTTOM, pady=10)


#     def read_and_crop_video(self):
#         cap = cv2.VideoCapture(self.processor.video_path)
#         self.processor.frames = []

#         total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#         self.show_progress_bar()
#         self.update_progress_bar(0, total_frames)

#         frame_count = 0
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break
#             if self.crop_coords:
#                 x1, y1, x2, y2 = self.crop_coords
#                 frame = frame[min(y1, y2):max(y1, y2), min(x1, x2):max(x1, x2)]
#             frame = resize_frame(frame, 640, 480)
#             self.processor.frames.append(frame)

#             frame_count += 1
#             self.update_progress_bar(frame_count, total_frames)
#         cap.release()

#         self.close_progress_bar()

#         if self.processor.frames:
#             self.display_first_frame()

#     def display_first_frame(self):
#         frame = self.processor.frames[0]
#         img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#         photo = ImageTk.PhotoImage(image=img)
#         self.videoview.create_image(0, 0, image=photo, anchor='nw')
#         self.photo = photo
#         self.slider['to'] = len(self.processor.frames) - 1

#     def update_frame(self, event):
#         frame_number = int(self.slider.get())
#         if self.processor.filtered_images is not None and len(self.processor.filtered_images) > frame_number:
#             frame = self.processor.filtered_images[frame_number]
#         else:
#             frame = self.processor.frames[frame_number]  # Use frames directly

#         img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#         photo = ImageTk.PhotoImage(image=img)

#         self.videoview.delete('all')
#         self.videoview.create_image(0, 0, image=photo, anchor='nw')
#         self.photo = photo

#     def select_frames(self):
#         self.processor.initial_frame = int(simpledialog.askinteger("Initial Frame", "Enter the initial frame number:"))
#         self.processor.final_frame = int(simpledialog.askinteger("Final Frame", "Enter the final frame number:"))
#         self.info_label.config(text=f"Initial Frame: {self.processor.initial_frame}, Final Frame: {self.processor.final_frame}")
#         self.clip_video()

#     def set_reference_distance(self):
#         self.processor.line_coords = []
#         messagebox.showinfo("Instruction", "Please click two points on the video to set the reference distance.")
#         self.videoview.bind("<Button-1>", self.mark_line)
    
#     def mark_line(self, event):
#         if len(self.processor.line_coords) < 2:
#             self.processor.line_coords.append((event.x, event.y))
#             if len(self.processor.line_coords) == 2:
#                 self.videoview.create_line(self.processor.line_coords[0], self.processor.line_coords[1], fill="red", width=2)
#                 self.processor.ref_distance = simpledialog.askfloat("Reference Distance", "Enter the reference distance in your chosen unit:")
#                 self.info_label.config(text=f"Reference Distance: {self.processor.ref_distance} units")
    
#     def clip_video(self):
#         if self.processor.initial_frame is None or self.processor.final_frame is None:
#             messagebox.showerror("Error", "Please select initial and final frames first.")
#             return

#         self.processor.clip_video()

#         # Replace original frames with the clipped frames
#         self.processor.frames = self.processor.cropped_frames.copy()

#         # If there are filtered images, apply the filters to the clipped frames
#         if self.processor.filtered_images:
#             self.processor.apply_filters_to_clipped_frames()

#         self.display_clipped_frames()

#     def display_clipped_frames(self):
#         def update_display(frame_index):
#             if self.processor.filtered_images is not None and len(self.processor.filtered_images) > frame_index:
#                 frame = self.processor.filtered_images[frame_index]
#             else:
#                 frame = self.processor.frames[frame_index]  # Use frames directly
#             img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#             photo = ImageTk.PhotoImage(image=img)
#             self.videoview.delete('all')
#             self.videoview.create_image(0, 0, image=photo, anchor='nw')
#             self.photo = photo

#         self.slider['to'] = len(self.processor.frames) - 1  # Use frames directly
#         self.slider.config(command=lambda event: update_display(int(self.slider.get())))
#         update_display(0)

#     def check_reference_distance(self):
#         if not hasattr(self.processor, 'ref_distance') or self.processor.ref_distance is None:
#             messagebox.showerror("Error", "Please set the reference distance before marking axes.")
#         else:
#             self.mark_axes()

#     def mark_axes(self):
#         self.processor.axis_coords = []
#         messagebox.showinfo("Instruction", "Please click to set the origin of the axes.")
#         self.videoview.bind("<Button-1>", self.set_origin)

#     def set_origin(self, event):
#         self.processor.axis_coords = [(event.x, event.y)]  # Origin point
#         self.videoview.create_oval(event.x-3, event.y-3, event.x+3, event.y+3, fill="blue", width=2)
#         self.videoview.unbind("<Button-1>")
#         messagebox.showinfo("Instruction", "Click Again To Finalize The Axes")
#         self.videoview.bind("<Motion>", self.update_axes_image)
#         self.videoview.bind("<Button-1>", self.drop_axes)

#     def update_axes_image(self, event):
#         if len(self.processor.axis_coords) == 1:
#             origin = self.processor.axis_coords[0]
#             if self.processor.axis_image_id:
#                 self.videoview.delete(self.processor.axis_image_id)
            
#             img = Image.new('RGBA', (640, 480), (0, 0, 0, 0))
#             draw = ImageDraw.Draw(img)
            
#             # Draw axes extending to the borders of the image/frame
#             # X-axis
#             draw.line([(0, origin[1]), (640, origin[1])], fill="blue", width=2)
#             # Y-axis
#             draw.line([(origin[0], 0), (origin[0], 480)], fill="green", width=2)
            
#             self.processor.axis_image = ImageTk.PhotoImage(img)
#             self.processor.axis_image_id = self.videoview.create_image(0, 0, image=self.processor.axis_image, anchor='nw')

#     def drop_axes(self, event):
#         if len(self.processor.axis_coords) == 1:
#             origin = self.processor.axis_coords[0]
#             self.processor.axis_coords.append((640, origin[1]))  # Positive X-axis end point
#             self.processor.axis_coords.append((0, origin[1]))    # Negative X-axis end point
#             self.processor.axis_coords.append((origin[0], 480))  # Positive Y-axis end point
#             self.processor.axis_coords.append((origin[0], 0))    # Negative Y-axis end point

#             # Draw axes to the borders of the image/frame
#             self.videoview.create_line(0, origin[1], 640, origin[1], fill="blue", width=2)  # X-axis
#             self.videoview.create_line(origin[0], 0, origin[0], 480, fill="green", width=2)  # Y-axis
            
#             self.videoview.unbind("<Motion>")
#             self.videoview.unbind("<Button-1>")

#     def translate_to_real_coordinates(self, points):
#         origin = self.processor.axis_coords[0]
#         ref_pixel_dist = np.linalg.norm(np.array(self.processor.line_coords[0]) - np.array(self.processor.line_coords[1]))
#         scale_factor = self.processor.ref_distance / ref_pixel_dist
        
#         real_coords = []
#         for point in points:
#             x_real = (point[0] - origin[0]) * scale_factor
#             y_real = (origin[1] - point[1]) * scale_factor
#             real_coords.append((x_real, y_real))
        
#         return real_coords

#     def mark_points_to_track(self):
#         self.processor.points_to_track = []
#         messagebox.showinfo("Instruction", "Please click points on the video to mark them for tracking.")
#         self.videoview.bind("<Button-1>", self.mark_point)
    
#     def mark_point(self, event):
#         self.processor.points_to_track.append((event.x, event.y))
#         self.videoview.create_oval(event.x-3, event.y-3, event.x+3, event.y+3, fill="red")
    

