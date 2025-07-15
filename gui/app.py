from math import floor
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image

from core import abspath
from .components.titlebar import TitleBar
from .components.axes import Axes
from .components.tooltip import ToolTip
# from .components.seekbar import CutSeekBar

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
        
        self.btnlist = {}
        
        self.toolbar()
        
        self.root.protocol("WM_DELETE_WINDOW", self.onclose)
        
    def mkbutton(self, imgpath, command):
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
            ("assets/video.png", self.openvideo, "Load Video File"),
            ("assets/seek.png", self.loadseek, "Trim Video"),
            ("assets/axis.png", self.markaxes, "Setup Coordinate Axes"),
            ("assets/ruler.png", self.scale, "Add Scale"),
            ("assets/rectanglebd.png", self.drawrect, "Mark Objects"),
            ("assets/start.png", self.strack, "Start Tracking"),
            ("assets/plot.png", self.plot, "Plot Tracked Data"),
            ("assets/save.png", self.savedata, "Save Tracked Data"),
            ("assets/reset.png", self.reset, "Clear Everything")
        ]
        
        for imgpath, command, tooltip in buttons:
            self.btn = self.mkbutton(imgpath, command)
            ToolTip(self.btn, tooltip)
            self.btnlist[imgpath.split('/')[-1][:-4]] = self.btn
        
        self.vidframe = ctk.CTkFrame(self.root, width=self.cwidth-self.twidth, height=self.theight, bg_color="#899fbd", fg_color="#5bdada")
        self.vidframe.pack_propagate(False)
        self.vidframe.pack(side=ctk.LEFT)
        
        self.videoview = ctk.CTkCanvas(self.vidframe, width=self.vwidth, height=self.vheight, bg="#4d535c")
        self.videoview.pack_propagate(False)
        self.videoview.pack(side=ctk.TOP, expand=False)
        
        # Title
        self.title = TitleBar(self.videoview, self.vwidth, "Welcome!")
        
        # Axes
        self.axes = Axes(self.vidframe, self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist["axis"])
        
        


    def openvideo(self):
        self.videopath = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4")])
        if self.videopath:
            self.loadvideo(self.videopath)
            
    def loadseek(self):
        pass
    
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

    def reset(self):
        pass
        
    def updateframe(self):
        pass
    
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
        
    # def resizef(self, frame, fwidth, fheight):
    #     """Resizes frame according to current fwidth and fheight"""
    #     frame = cv2.resize(frame, (fwidth, fheight))
    #     return frame