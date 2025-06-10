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
            
        scroll_toolbar.pack()
        
        self.vidframe = ctk.CTkFrame(self.root, width=self.cwidth-self.twidth, height=self.theight, bg_color="#899fbd", fg_color="#5bdada")
        self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT)
        
        self.vwidth = self.cwidth - self.twidth
        self.vheight = self.theight-self.seekbarh-2*self.pady
        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="silver") #, highlightbackground="black")
        self.videoview.pack(side=ctk.TOP, expand=False)


    def openvideo(self):
        videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if videopath:
            # self.processor.fps = int(simpledialog.askinteger("FPS", "Enter FPS:"))
            # self.fps_label.configure(text=f"FPS: {self.processor.fps}")
            self.load_video(videopath)
    
    
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
    

    def markaxes(self):
        pass


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