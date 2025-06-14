from math import floor
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from tkinter import filedialog, simpledialog, messagebox, Text, END, TOP, X, NONE
from .components import CutSeekBar, ScrollBar
from core import abspath
# from video_processing import VideoProcessor

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Phys TrackerX")
        self.cwidth = 900
        self.cheight = 600
        self.padx = floor(self.cwidth * 0.01)
        self.pady = floor(self.cheight * 0.01)
        
        self.root.geometry(f"{self.cwidth}x{self.cheight}")
        self.toolbar()
        self.root.protocol("WM_DELETE_WINDOW", self.onclose)
        
        # Global Coordinate Frame
        self.ox = self.oy = None

    def toolbar(self):
        
        self.twidth = floor(self.cwidth * 0.12)
        self.theight = self.cheight - 2*self.pady
        self.seekbarh = floor(self.cheight * 0.1)
        self.btnsize = self.twidth - 40
        
        self.padx = 0
        self.pady = 0
        
        # ==== LEFT TOOLBAR PANEL ====
        self.scroll_toolbar = ScrollBar(self.root, width=self.twidth, height=self.theight, padx=self.padx, pady=self.pady)
        self.scrollframe = self.scroll_toolbar.scrollframe
        
        buttons = [
            ("assets/open-video.png", self.openvideo),
            ("assets/axis.png", self.markaxes),
            ("assets/start.png", self.strack),
            ("assets/plot.png", self.plot),
            ("assets/back.png", self.tomenu)
        ]
        
        for imgpath, command in buttons:
            img = Image.open(abspath(imgpath)).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img)
            button = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                   image=img, command=command)
            button.pack(padx=5, pady=5)
            # Store the image reference to prevent garbage collection
            button.image = img
            
        # scroll_toolbar.pack()
        
        self.vidframe = ctk.CTkFrame(self.root, width=self.cwidth-self.twidth, height=self.theight, bg_color="#899fbd", fg_color="#5bdada")
        self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT)
        
        self.vwidth = self.cwidth - self.twidth
        self.vheight = self.theight-self.seekbarh-2*self.pady
        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="#4d535c")
        self.videoview.pack(side=ctk.TOP, expand=False)


    def openvideo(self):
        videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if videopath:
            self.load_video(videopath)
    
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
        self.plotx()

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
        self.videoview.delete("all")
        # self.root.update()
        # self.root.deiconify()