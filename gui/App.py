from math import floor
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from tkinter import filedialog
from .components import ScrollBar
from core import abspath

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PhysTrackX")
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
        
        self._x = self.videoview.create_text(0, 0, text="x", fill="red", font=("Arial", 15, "bold"))
        self._y = self.videoview.create_text(0, 0, text="y", fill="blue", font=("Arial", 15, "bold"))
        
        def onmove(event):
            """ Update the axes to follow the mouse cursor. """
            self.videoview.delete("axes")  # Remove old axes
            x, y = event.x, event.y  # Get mouse position

            # Draw new axes centered on mouse position
            self.videoview.create_line(0, y, self.vwidth, y, fill="red", arrow=ctk.LAST, width=2, tags="axes")  # X-axis
            self.videoview.create_line(x, self.vheight, x, 0, fill="blue", arrow=ctk.LAST, width=2, tags="axes")  # Y-axis
            
            self.videoview.coords(self._x, self.vwidth-50, y+10)
            self.videoview.coords(self._y, x-10, self.vheight-50)

        def onclick(event):
            """ Store the clicked coordinates and draw a point. """
            x, y = event.x, event.y
            
            self.ox = x
            self.oy = y
            
            self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Button>")

        self.videoview.bind("<Motion>", onmove)
        self.videoview.bind("<Button>", onclick)


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