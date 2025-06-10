from math import floor
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from tkinter import filedialog, simpledialog, messagebox, Text, END, TOP, X, NONE
from .components import CutSeekBar, ScrollBar
# from video_processing import VideoProcessor

class App:
    def __init__(self, root):
        # root.destroy()
        self.root = root
        # self.root.title("Phys TrackerX")
        # self.root = ctk.CTk()
        
        # Make the window cover the entire screen
        
        self.cwidth = 900
        self.cheight = 600
        self._padx = floor(self.cwidth * 0.01)
        self._pady = floor(self.cheight * 0.01)
        print('pdx, pady:', self._padx, self._pady)
        
        self.root.geometry(f"{self.cwidth}x{self.cheight}")
        self.toolbar()
        self.root.protocol("WM_DELETE_WINDOW", self.onclose)
        
        # self.toolbar()

    def toolbar(self):
        
        self._twidth = floor(self.cwidth * 0.1)
        self._theight = self.cheight - 2*self._pady
        # self._seekbarh = floor(self.cheight * 0.1)
        # ==== LEFT TOOLBAR PANEL ====
        """
        toolbar = ctk.CTkFrame(self.root, width=self._twidth, height=self._theight, fg_color="black")
        toolbar.pack(side=ctk.LEFT, fill=None, expand=False, padx=(self._padx, 0), pady=self._pady)
        # toolbar = ctk.CTkFrame(self.root)
        # toolbar.pack(side=ctk.RIGHT)


        # Scrollbar for the canvas
        scrollbar = ctk.CTkScrollbar(toolbar, orientation="vertical", height=self._theight)
        scrollbar.pack(side=ctk.RIGHT, fill="y")
        
        self._tcanvas = ctk.CTkCanvas(toolbar, width=self._twidth, height=self._theight, bg="silver")
        # self._tcanvas = ctk.CTkCanvas(toolbar, yscrollcommand=scrollbar.set)
        # self._tcanvas.pack(side=TOP, fill=X)
        # self._tcanvas.configure(yscrollcommand=scrollbar.set)
        scrollframe = ctk.CTkFrame(self._tcanvas, width=self._twidth, height=2*self._theight)
        self._tcanvas.create_window((0, 0), window=scrollframe, anchor="nw", width=self._twidth, height=2*self._theight)
        
        self._tcanvas.configure(scrollregion=self._tcanvas.bbox("all"))
        self._tcanvas.pack(side=ctk.LEFT, fill=None, expand=False, padx=(self._padx, 0), pady=self._pady)
        
        # t = Text(toolbar, width = 15, height = 15, wrap = NONE, 
        #          yscrollcommand = scrollbar.set)

        # insert some text into the text widget
        # for i in range(20):
            # t.insert(END,"this is some text\n")
        # btn = ctk.CTkButton(toolbar, height=1000)
        # btn.pack()

        scrollbar.configure(command=self._tcanvas.yview)
        # self.root.mainloop()
        # attach Text widget to root window at top
        # t.pack(side=TOP, fill=X)
        """
        scroll_toolbar = ScrollBar(self.root, width=self._twidth, height=self._theight, padx=self._padx, pady=self._pady)
        self.scrollframe = scroll_toolbar.scrollframe

        # Create a frame to hold the filter widgets on the left side
        # self.toolbarf = ctk.CTkFrame(self.scrollframe, width=self._twidth, height=self._theight)
        # self.toolbarf.pack(side=ctk.TOP)
        # self.toolbarwin = tcanvas.create_window((0, 0), window=self.toolbarf, anchor="nw", width=self._twidth)
        # self.toolbarwin = tcanvas.create_window((0, 0), anchor="nw", width=self._twidth)

        sfimg = Image.open("assets/open-video.png").resize((self._twidth, self._twidth), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.openbtn = ctk.CTkButton(self.scrollframe, command=self.openvideo,width=self._twidth,
                                            height=self._twidth, image=sfimg, text="")
        self.openbtn.pack(pady=10)
        
        # self.fps_label = ctk.CTkLabel(self.scrollframe, text="")
        # self.fps_label.pack(pady=5)
        
        sfimg = Image.open("assets/axis.png").resize((self._twidth, self._twidth), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.axisbtn = ctk.CTkButton(self.scrollframe, text="", width=self._twidth, height=self._twidth,
                                            image=sfimg, command=self.markaxes)
        self.axisbtn.pack(pady=10)

        sfimg = Image.open("assets/start.png").resize((self._twidth, self._twidth), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.strackbtn = ctk.CTkButton(self.scrollframe, text="", width=self._twidth,
                                                height=self._twidth, image=sfimg,
                                                command=self.strack)
        self.strackbtn.pack(pady=10)
        
        sfimg = Image.open("assets/plot.png").resize((self._twidth, self._twidth), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.plotbtn = ctk.CTkButton(self.scrollframe, text="", width=self._twidth,
                                                    height=self._twidth, image=sfimg,
                                                    command=self.plot)
        self.plotbtn.pack(pady=10)
        self.plotbtn.configure(state=ctk.DISABLED)  # Disable the button initially

        sfimg = Image.open("assets/back.png").resize((self._twidth, self._twidth), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.menubtn = ctk.CTkButton(self.scrollframe, text="", width=self._twidth, height=self._twidth,
                                            image=sfimg, command=self.tomenu)
        self.menubtn.pack(pady=10)

        # self.info_label = ctk.CTkLabel(self.scrollframe, text="")
        # self.info_label.pack(pady=10)
        
        # Create a frame to hold the video and slider widgets on the right side
        
        """
        self.vidframe = ctk.CTkFrame(self.root, width=self.cwidth-self._twidth - 3*self._padx, height=self._theight, fg_color="black")
        self.vidframe.pack(side=ctk.LEFT, fill=None, expand=False, padx=self._padx, pady=self._pady)
        
        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.cwidth-self._twidth - 3*self._padx, height=self._theight-self._seekbarh-2*self._pady, bg="silver", highlightbackground="black")
        self.videoview.pack(side=ctk.TOP, expand=False)
        
        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self._twidth - 3*self._padx, height=self._seekbarh, bg="silver", highlightbackground="black")
        # self.seekbar.pack(side=ctk.TOP, pady=(self._pady, 0))
        """
        
        # Bind updates to scrollbar & resizing
        # self.toolbarf.bind("<Configure>", self.onfconfigure)
        # tcanvas.bind("<Configure>", self.oncconfigure)

        # # Enable mousewheel scrolling
        # self._tcanvas.bind_all("<MouseWheel>", self.onmwheel)  # Windows/macOS
        # self._tcanvas.bind_all("<Button-4>", self.onmwheel)    # Linux scroll up
        # self._tcanvas.bind_all("<Button-5>", self.onmwheel)    # Linux scroll down


    # def onfconfigure(self, event):
    #     self.canvas.configure(scrollregion=self.canvas.bbox("all"), width=self._twidth)

    # def oncconfigure(self, event):
    #     # Resize inner frame's width to match canvas width
    #     cwidth = event.width
    #     self.canvas.itemconfig(self.toolbarwin, width=self._twidth)

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