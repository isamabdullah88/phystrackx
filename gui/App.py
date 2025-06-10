from math import floor
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from tkinter import filedialog, simpledialog, messagebox, Text, END, TOP, X, NONE
from .components import CutSeekBar, ScrollBar
# from video_processing import VideoProcessor

class App:
    def __init__(self, root):
        self.root = root
        # self.root.title("Phys TrackerX")
        # self.root = ctk.CTk()
        
        # Make the window cover the entire screen
        
        self.cwidth = 900
        self.cheight = 600
        self.padx = floor(self.cwidth * 0.01)
        self.pady = floor(self.cheight * 0.01)
        print('pdx, pady:', self.padx, self.pady)
        
        screen = f"{self.cwidth}x{self.cheight}"
        print('screen:', screen)
        self.root.geometry(screen)
        self.toolbar()
        # self.root.protocol("WM_DELETE_WINDOW", self.onclose)
        # self.root.mainloop()

    def toolbar(self):
        
        self.twidth = floor(self.cwidth * 0.1)
        self.theight = self.cheight - 2*self.pady
        self.seekbarh = floor(self.cheight * 0.1)
        self.btnsize = self.twidth - 20
        
        self.padx = 0
        self.pady = 0
        
        # ==== LEFT TOOLBAR PANEL ====
        scroll_toolbar = ScrollBar(self.root, width=self.twidth, height=self.theight, padx=self.padx, pady=self.pady)
        self.scrollframe = scroll_toolbar.scrollframe
        
        buttons = [
            ("assets/open-video.png", self.openvideo),
            # ("assets/fps.png", self.set_fps),  # Uncomment if you want to set FPS
            ("assets/axis.png", self.markaxes),
            ("assets/start.png", self.strack),
            ("assets/plot.png", self.plot),
            ("assets/back.png", self.tomenu)
        ]
        
        for img_path, command in buttons:
            img = Image.open(img_path).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img)
            button = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                   image=img, command=command)
            button.pack(pady=10)
            # Store the image reference to prevent garbage collection
            button.image = img

        """
        img = Image.open("assets/open-video.png").resize((self.twidth, self.twidth), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        self.openbtn = ctk.CTkButton(self.scrollframe, command=self.openvideo,width=self.twidth,
                                            height=self.twidth, image=img, text="")
        self.openbtn.pack(pady=10)
        
        # self.fps_label = ctk.CTkLabel(self.scrollframe, text="")
        # self.fps_label.pack(pady=5)
        
        img = Image.open("assets/axis.png").resize((self.twidth, self.twidth), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        self.axisbtn = ctk.CTkButton(self.scrollframe, text="", width=self.twidth, height=self.twidth,
                                            image=img, command=self.markaxes)
        self.axisbtn.pack(pady=10)

        img = Image.open("assets/start.png").resize((self.twidth, self.twidth), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        self.strackbtn = ctk.CTkButton(self.scrollframe, text="", width=self.twidth,
                                                height=self.twidth, image=img,
                                                command=self.strack)
        self.strackbtn.pack(pady=10)
        
        img = Image.open("assets/plot.png").resize((self.twidth, self.twidth), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        self.plotbtn = ctk.CTkButton(self.scrollframe, text="", width=self.twidth,
                                                    height=self.twidth, image=img,
                                                    command=self.plot)
        self.plotbtn.pack(pady=10)
        self.plotbtn.configure(state=ctk.DISABLED)  # Disable the button initially

        img = Image.open("assets/back.png").resize((self.twidth, self.twidth), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        self.menubtn = ctk.CTkButton(self.scrollframe, text="", width=self.twidth, height=self.twidth,
                                            image=img, command=self.tomenu)
        self.menubtn.pack(pady=10)
        
        self.plotbtn2 = ctk.CTkButton(self.scrollframe, text="", width=self.twidth,
                                                    height=self.twidth, image=img,
                                                    command=self.plot)
        self.plotbtn2.pack(pady=10)
        self.plotbtn2.configure(state=ctk.DISABLED)  # Disable the button initially
        """
        scroll_toolbar.pack()
        
        # temp1 = ctk.CTkFrame(self.root, width=100, bg_color="#899fbd", fg_color="#e75ad0")
        # temp1.pack_propagate(False)
        # temp1.pack(side=ctk.LEFT)

        # temp2 = ctk.CTkCanvas(temp1, width=100)
        # temp2.pack(side=ctk.LEFT)
        
        # temp3 = ctk.CTkCanvas(temp2, width=100)
        # temp3.pack(side=ctk.LEFT)
        
        self.vidframe = ctk.CTkFrame(self.root, width=self.cwidth-self.twidth, height=self.theight, bg_color="#899fbd", fg_color="#5bdada")
        self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT)
        
        self.vwidth = self.cwidth - self.twidth
        self.vheight = self.theight-self.seekbarh-2*self.pady
        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="silver") #, highlightbackground="black")
        self.videoview.pack(side=ctk.TOP, expand=False)
        
        # self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, bg="silver") #, highlightbackground="black")
        
        # Bind updates to scrollbar & resizing
        # self.toolbarf.bind("<Configure>", self.onfconfigure)
        # tcanvas.bind("<Configure>", self.oncconfigure)

        # # Enable mousewheel scrolling
        # self._tcanvas.bind_all("<MouseWheel>", self.onmwheel)  # Windows/macOS
        # self._tcanvas.bind_all("<Button-4>", self.onmwheel)    # Linux scroll up
        # self._tcanvas.bind_all("<Button-5>", self.onmwheel)    # Linux scroll down
        


    # def onfconfigure(self, event):
    #     self.canvas.configure(scrollregion=self.canvas.bbox("all"), width=self.twidth)

    # def oncconfigure(self, event):
    #     # Resize inner frame's width to match canvas width
    #     cwidth = event.width
    #     self.canvas.itemconfig(self.toolbarwin, width=self.twidth)

    # def onmwheel(self, event):
    #     if event.num == 5 or event.delta == -120:
    #         self._tcanvas.yview_scroll(1, "units")
    #     elif event.num == 4 or event.delta == 120:
    #         self._tcanvas.yview_scroll(-1, "units")


    def openvideo(self):
        videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if videopath:
            # self.processor.fps = int(simpledialog.askinteger("FPS", "Enter FPS:"))
            # self.fps_label.configure(text=f"FPS: {self.processor.fps}")
            self.load_video(videopath)
    
    # def load_video(self, videopath):
    #     pass

    # def dispframe(self, frame=None):
    #     pass

    # def updateframe(self, event):
    #     pass
        
    
    # def mark_line(self, event):
    #     if len(self.processor.line_coords) < 2:
    #         self.processor.line_coords.append((event.x, event.y))
    #         if len(self.processor.line_coords) == 2:
    #             self.videoview.create_line(self.processor.line_coords[0],
    #                                         self.processor.line_coords[1], fill="red", width=2)
    #             self.processor.ref_distance = simpledialog.askfloat("Reference Distance",
    #                                         "Enter the reference distance in your chosen unit:")
    #             self.info_label.configure(
    #                 text=f"Reference Distance: {self.processor.ref_distance} units")
    

    # def markaxes(self):
    #     pass

    # def mark_points_to_track(self):
    #     self.processor.points_to_track = []
    #     messagebox.showinfo("Instruction", "Please click points on the video to mark them for tracking.")
    #     self.videoview.bind("<Button-1>", self.mark_point)
    
    # def mark_point(self, event):
    #     self.processor.points_to_track.append((event.x, event.y))
    #     self.videoview.create_oval(event.x-3, event.y-3, event.x+3, event.y+3, fill="red")

    # def choose_tracking_method(self):
    #     self.tracking_method = ctk.StringVar()
    #     self.tracking_method.set("points")  # default value

    #     method_popup = ctk.CTkToplevel(self.root)
    #     method_popup.title("Select Tracking Method")

    #     ctk.CTkLabel(method_popup, text="Choose tracking method:").pack(pady=10)
    #     ctk.CTkRadioButton(method_popup, text="Track Points", variable=self.tracking_method, value="points").pack(anchor=ctk.W)
    #     ctk.CTkRadioButton(method_popup, text="Track Centroid", variable=self.tracking_method, value="bbox").pack(anchor=ctk.W)

    #     ctk.CTkButton(method_popup, text="OK", command=lambda: self.confirm_tracking_method(method_popup)).pack(pady=10)

    # def confirm_tracking_method(self, popup):
    #     method = self.tracking_method.get()
    #     popup.destroy()

    #     if method == "points":
    #         self.mark_points_to_track()
    #     elif method == "bbox":
    #         self.mark_bboxes_to_track()
    #     else:
    #         messagebox.showerror("Error", "Invalid method. Please select 'points' or 'bbox'.")

    # def mark_bboxes_to_track(self):
    #     # self.bboxes_to_track = []
    #     messagebox.showinfo("Instruction", "Please draw bounding boxes around the objects to track. Draw multiple bounding boxes if needed.")
    #     self.videoview.bind("<Button-1>", self.start_bbox)

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

    def resizeframe(self, frame, fwidth, fheight):
        if (fwidth > self.vwidth):
            ratio = fheight/fwidth
            fwidth = self.cwidth
            fheight = floor(fwidth * ratio)
            
            frame = cv2.resize(frame, (fwidth, fheight))

        if (fheight > self.vheight):
            ratio = fwidth/fheight
            fheight = self.vheight
            fwidth = floor(fheight*ratio)
            
            frame = cv2.resize(frame, (fwidth, fheight))

        return frame

    def plot(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title("Tracked Coordinates Options")

        ctk.CTkButton(popup, text="Plot X and Y", command=self.plotx).pack(pady=5)

    def plotx(self):
        pass

    def onclose(self):
        self.root.destroy()


    def strack(self):
        """
        Implements Lucas-Kanade optical flow tracking for marked points across video frames.
        This method processes the entire video sequence and tracks the motion of selected points.
        """
        pass
    

    def tomenu(self):
        self.root.update()
        self.root.deiconify()