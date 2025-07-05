from math import floor
import customtkinter as ctk
import cv2
from PIL import Image

from tkinter import filedialog
from .components import Axes
from core import abspath

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PhysTrackX")
        
        self.cwidth = 1200
        self.cheight = 800
        
        self.padx = floor(self.cwidth * 0.01)
        self.pady = floor(self.cheight * 0.01)
        
        self.root.geometry(f"{self.cwidth}x{self.cheight}")
        
        self.twidth = floor(self.cwidth * 0.1)
        self.theight = self.cheight
        self.seekbarh = floor(self.cheight * 0.1)
        self.btnsize = self.twidth - 40
        
        self.vwidth = self.cwidth - self.twidth
        self.vheight = self.theight-self.seekbarh
        
        # Video frame dimensions
        self.fwidth = self.vwidth
        self.fheight = self.vheight
        
        self.toolbar()
        
        self.axes = Axes(self.vidframe, self.videoview, self.vwidth, self.vheight)
        
        self.root.protocol("WM_DELETE_WINDOW", self.onclose)
        
    def button(self, imgpath, command):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(self.btnsize, self.btnsize))
        button = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                            image=img, command=command)
        button.pack(padx=5, pady=5)
        # Store the image reference to prevent garbage collection
        button.image = img
        
        return button

    def toolbar(self):
        """Toolbar frame"""
        
        self.scrollframe = ctk.CTkScrollableFrame(self.root, width=self.twidth-20, height=self.theight, bg_color="#899fbd", fg_color="#5bdada")
        self.scrollframe.pack(side=ctk.LEFT)
        
        buttons = [
            ("assets/video.png", self.openvideo),
            ("assets/axis.png", self.markaxes),
            ("assets/ruler.png", self.scale),
            ("assets/rectanglebd.png", self.drawrect),
            ("assets/start.png", self.strack),
            ("assets/plot.png", self.plot),
            ("assets/save.png", self.savedata),
            ("assets/clear.png", self.clear)
        ]
        
        for imgpath, command in buttons:
            self.button(imgpath, command)
        
        self.vidframe = ctk.CTkFrame(self.root, width=self.cwidth-self.twidth, height=self.theight, bg_color="#899fbd", fg_color="#5bdada")
        self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT)
        
        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="#4d535c")
        self.videoview.pack_propagate(False)
        self.videoview.pack(side=ctk.TOP, expand=False)


    def openvideo(self):
        videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if videopath:
            self.loadvideo(videopath)
    
    def markaxes(self):
        self.axes.markaxes()
        
    def scale(self):
        pass
    
    def drawrect(self):
        pass

    def strack(self):
        """
        Implements Lucas-Kanade optical flow tracking for marked points across video frames.
        This method processes the entire video sequence and tracks the motion of selected points.
        """
        pass
    
    def plot(self):
        pass
    
    def savedata(self):
        """
        Placeholder for saving data functionality.
        This method should implement the logic to save the tracked data.
        """
        pass

    def onclose(self):
        self.root.destroy()

    def clear(self):
        self.videoview.delete("all")
        
    
    def resize(self, fwidth, fheight):
        """Resizes shape to minimum of videoview height and width."""
        if (fwidth > self.vwidth):
            ratio = fheight/fwidth
            fwidth = self.vwidth
            fheight = floor(fwidth * ratio)

        if (fheight > self.vheight):
            ratio = fwidth/fheight
            fheight = self.vheight
            fwidth = floor(fheight*ratio)

        self.fwidth = fwidth
        self.fheight = fheight
        
    def resizef(self, frame, fwidth, fheight):
        """Resizes frame according to current fwidth and fheight"""
        frame = cv2.resize(frame, (fwidth, fheight))
        return frame