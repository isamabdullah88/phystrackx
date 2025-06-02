from math import floor
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from tkinter import filedialog, simpledialog, messagebox
# from video_processing import VideoProcessor

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Phys TrackerX")
        
        # Make the window cover the entire screen
        self.root.geometry("960x640")
        # self.processor = VideoProcessor()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # self._ref_frame = [0.0, 0.0]


    # def exit_fullscreen(self):
    #     self.root.attributes('-fullscreen', False)

    # def show_progress_bar(self):
    #     self.progress_popup = ctk.CTkToplevel(self.root)
    #     self.progress_popup.title("Applying Filters")

    #     self.progress_label = ctk.CTkLabel(self.progress_popup, text="Processing frames...")
    #     self.progress_label.pack(pady=10)

    #     self.progress_bar = ctk.CTkProgressBar(self.progress_popup, orientation="horizontal",
    #                                            mode="determinate")
    #     self.progress_bar.pack(pady=10)

    #     self.progress_popup.update()

    # def update_progress_bar(self, value, max_value):
    #     self.progress_bar["value"] = value
    #     self.progress_bar["maximum"] = max_value
    #     self.progress_label.configure(text=f"Processing frames... {value}/{max_value}")
    #     self.progress_popup.update()

    # def close_progress_bar(self):
    #     self.progress_popup.destroy()

    def create_widgets(self):
            
        # ==== LEFT TOOLBAR PANEL ====
        container = ctk.CTkFrame(self.root)
        container.pack(side=ctk.LEFT, fill="both", expand=True)

        self.canvas = ctk.CTkCanvas(container, width=80)
        self.canvas.pack(side=ctk.LEFT, fill="both", expand=True)

        # Scrollbar for the canvas
        scrollbar = ctk.CTkScrollbar(container, orientation="vertical", command=self.canvas.yview)
        scrollbar.pack(side=ctk.LEFT, fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Create a frame to hold the filter widgets on the left side
        self.toolbarf = ctk.CTkFrame(self.canvas, width=80, height=7*80)
        self.toolbarf.pack(side=ctk.LEFT, fill=ctk.Y, padx=10, pady=10)
        self.toolbar_window = self.canvas.create_window((0, 0), window=self.toolbarf, anchor="nw")

        sfimg = Image.open("assets/open-video.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.open_button = ctk.CTkButton(self.toolbarf, command=self.open_video,width=80,
                                            height=80, image=sfimg, text="")
        self.open_button.pack(pady=10)
        
        # self.fps_label = ctk.CTkLabel(self.toolbarf, text="")
        # self.fps_label.pack(pady=5)
        
        sfimg = Image.open("assets/axis.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.axis_button = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                            image=sfimg, command=self.mark_axes)
        self.axis_button.pack(pady=10)
        
        sfimg = Image.open("assets/points.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.track_button = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                            image=sfimg, command=self.choose_tracking_method)
        self.track_button.pack(pady=10)

        sfimg = Image.open("assets/start.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.track_start_button = ctk.CTkButton(self.toolbarf, text="", width=80,
                                                height=90, image=sfimg,
                                                command=self.start_tracking)
        self.track_start_button.pack(pady=10)
        
        sfimg = Image.open("assets/plot.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.track_coords_button = ctk.CTkButton(self.toolbarf, text="", width=80,
                                                    height=80, image=sfimg,
                                                    command=self.show_tracked_coordinates_window)
        self.track_coords_button.pack(pady=10)
        self.track_coords_button.configure(state=ctk.DISABLED)  # Disable the button initially

        sfimg = Image.open("assets/back.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.menu_button = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                            image=sfimg, command=self.back_to_menu)
        self.menu_button.pack(pady=10)

        # self.info_label = ctk.CTkLabel(self.toolbarf, text="")
        # self.info_label.pack(pady=10)
        
        # Create a frame to hold the video and slider widgets on the right side
        self.video_frame = ctk.CTkFrame(self.root)
        self.video_frame.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=10, pady=10)
        
        self.cwidth = 640
        self.cheight = 480
        self.videoview = ctk.CTkCanvas(self.video_frame, width=self.cwidth,
                                        height=self.cheight)
        self.videoview.pack(pady=20, expand=True)

        # self.slider = ctk.CTkSlider(self.video_frame, orientation="horizontal", from_=0,
        #                             width=400, fg_color="red", progress_color="green",
        #                             button_color="yellow", command=self.update_frame)
        
        # self.slider.set(0)
        # self.slider.pack(pady=10)
        # Bind updates to scrollbar & resizing
        self.toolbarf.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Enable mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)  # Windows/macOS
        self.canvas.bind_all("<Button-4>", self.on_mousewheel)    # Linux scroll up
        self.canvas.bind_all("<Button-5>", self.on_mousewheel)    # Linux scroll down


    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        # Resize inner frame's width to match canvas width
        cwidth = event.width
        self.canvas.itemconfig(self.toolbar_window, width=cwidth)

    def on_mousewheel(self, event):
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")


    def open_video(self):
        # print('video path: ', videopath)
        # if videopath is not None:
        #     self.load_video(videopath)
        #     return 
        
        videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if videopath:
            # self.processor.fps = int(simpledialog.askinteger("FPS", "Enter FPS:"))
            # self.fps_label.configure(text=f"FPS: {self.processor.fps}")
            self.load_video(videopath)
    
    def load_video(self, videopath):
        pass

    def display_first_frame(self, frame=None):
        pass

    def update_frame(self, event):
        pass
        
    
    def mark_line(self, event):
        if len(self.processor.line_coords) < 2:
            self.processor.line_coords.append((event.x, event.y))
            if len(self.processor.line_coords) == 2:
                self.videoview.create_line(self.processor.line_coords[0],
                                            self.processor.line_coords[1], fill="red", width=2)
                self.processor.ref_distance = simpledialog.askfloat("Reference Distance",
                                            "Enter the reference distance in your chosen unit:")
                self.info_label.configure(
                    text=f"Reference Distance: {self.processor.ref_distance} units")
    

    def mark_axes(self):
        pass

    def mark_points_to_track(self):
        self.processor.points_to_track = []
        messagebox.showinfo("Instruction", "Please click points on the video to mark them for tracking.")
        self.videoview.bind("<Button-1>", self.mark_point)
    
    def mark_point(self, event):
        self.processor.points_to_track.append((event.x, event.y))
        self.videoview.create_oval(event.x-3, event.y-3, event.x+3, event.y+3, fill="red")

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
        # self.bboxes_to_track = []
        messagebox.showinfo("Instruction", "Please draw bounding boxes around the objects to track. Draw multiple bounding boxes if needed.")
        self.videoview.bind("<Button-1>", self.start_bbox)

    # def start_bbox(self, event):
    #     self.start_x, self.start_y = event.x, event.y
    #     self.current_bbox = self.videoview.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")
    #     self.videoview.bind("<B1-Motion>", self.draw_bbox)
    #     self.videoview.bind("<ButtonRelease-1>", self.finish_bbox)

    # def draw_bbox(self, event):
    #     self.videoview.coords(self.current_bbox, self.start_x, self.start_y, event.x, event.y)

    # def finish_bbox(self, event):
    #     self.videoview.unbind("<B1-Motion>")
    #     self.videoview.unbind("<ButtonRelease-1>")
    #     bbox_coords = (self.start_x, self.start_y, event.x, event.y)
    #     self.bboxes_to_track.append(bbox_coords)

    #     frame_ox, frame_oy = self._ref_frame

    #     centroid_x = (bbox_coords[0] + bbox_coords[2]) / 2 - frame_ox
    #     centroid_y = (bbox_coords[1] + bbox_coords[3]) / 2 - frame_oy
    #     self.processor.points_to_track.append((centroid_x, centroid_y))
    #     self.videoview.create_oval(centroid_x - 3, centroid_y - 3, centroid_x + 3, centroid_y + 3, fill="red")

    def resize_frame(self, frame, fwidth, fheight):
        if (fwidth > self.cwidth):
            ratio = fheight/fwidth
            fwidth = self.cwidth
            fheight = floor(fwidth * ratio)
            
            frame = cv2.resize(frame, (fwidth, fheight))

        if (fheight > self.cheight):
            ratio = fwidth/fheight
            fheight = self.cheight
            fwidth = floor(fheight*ratio)
            
            frame = cv2.resize(frame, (fwidth, fheight))
        
        print('frame: ', frame.shape)

        return frame

    def show_tracked_coordinates_window(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title("Tracked Coordinates Options")

        ctk.CTkButton(popup, text="Plot X and Y Distances", command=self.plot_distances).pack(pady=5)

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
        self.root.update()
        self.root.deiconify()