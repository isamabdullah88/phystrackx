import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from gui.app import App
from experiments.nonrigid import Interface
from gui.components.spinner import Spinner
from gui.components.seekbar.seekbar import CutSeekBar
from gui.components.ruler import ScaleRuler
from core import PixelRect, Points, abspath

class InterfaceApp(App):
    def __init__(self, root):
        super().__init__(root)
        
        img = Image.open(abspath("assets/ruler.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.ruler = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.scale)
        self.ruler.pack(padx=5, pady=5)
        self.ruler.image = img

        # For drawing ellipse over tracking area
        img = Image.open(abspath("assets/line.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.linebd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawline)
        self.linebd.pack(padx=5, pady=5)
        
        # For drawing rectangle over text area
        img = Image.open(abspath("assets/rectanglebd.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        self.rectbd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
                                      image=img, command=self.drawrect)
        self.rectbd.pack(padx=5, pady=5)
        

        self.seekbar = CutSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
        # self.scroll_toolbar.pack()
        
        self.scruler = None

        self.ccoords = (0, 0)

        # Line coordinates for tracking
        self._lcoords = Points()
        # rect for text detection
        self._rect = None

        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        self._trackpath = os.path.join(tempdir, 'track-interface.mp4')

        self.interface = Interface(trackpath=self._trackpath)



    def loadvideo(self, videopath):
        self.interface.addvideo(videopath)
        
        self.seekbar.setcount(self.interface.fcount)

        frame1 = self.interface.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame):
        fwidth = self.interface.fwidth
        fheight = self.interface.fheight
        frame = self.resizeframe(frame, fwidth, fheight)
        self.fheight, self.fwidth = frame.shape[:2]

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.fx = floor(self.cwidth/2 - frame.shape[1]/2)
        self.fy = floor(self.cheight/2 - frame.shape[0]/2)

        # Default coordinate system
        if self.ox is None:
            self.ox = self.fx
        
        if self.oy is None:
            self.oy = self.fy + self.fheight

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
    def updateframe(self):
        
        frame = self.interface.frame(index=self.seekbar.idx)
        fwidth = self.interface.fwidth
        fheight = self.interface.fheight

        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def scale(self):
        self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

    def drawline(self):
        """Draws line with filled transparent image laid over region of interest"""
        self._ctkline = None

        def onclick(event):
            
            self._lcoords.addpt(event.x-self.fx, event.y-self.fy)
            
            for i in range(len(self._lcoords)):
                x0, y0 = self._lcoords[i]
                self.videoview.create_oval(x0+self.fx-2, y0+self.fy-2, x0+self.fx+2, y0+self.fy+2,
                                           fill="red", outline="black")
                
                if i > len(self._lcoords) - 2:
                    continue
                x1, y1 = self._lcoords[i+1]
                
                self.videoview.create_line(x0+self.fx, y0+self.fy, x1+self.fx, y1+self.fy,
                                           fill="magenta", width=3)
            
            
        def ondrag(event):
            if len(self._lcoords) < 1:
                return
            
            ex, ey = (event.x, event.y)
            
            if self._ctkline is None:
                x0, y0 = self._lcoords[-1]
                self._ctkline = self.videoview.create_line(x0+self.fx, y0+self.fy, ex+self.fx,
                                                           ey+self.fy, fill="magenta", width=3)
                return
            
            x1, y1 = self._lcoords[-1]
            self.videoview.coords(self._ctkline, x1+self.fx, y1+self.fy, event.x, event.y)
            
        def onescape(event):
            """Escape key to clear the drawn line"""
            if self._ctkline is not None:
                self.videoview.delete(self._ctkline)
                self._ctkline = None
                # self._lcoords = []
            
            self.videoview.unbind("<Button>")
            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Escape>")

        self.videoview.bind("<Button>", onclick)
        self.videoview.bind("<Motion>", ondrag)
        self.root.bind("<Escape>", onescape)

    
    def drawrect(self):
        """Draws rectangle with simple lines"""
        self._ctkbox = None
        
        def ondown(event):
            if self._ctkbox is not None:
                self.videoview.delete(self._ctkbox)
            
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            self.videoview.coords(self._ctkbox, sx, sy, event.x, event.y)

            self._rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy).pix2norm(self.fwidth, self.fheight)

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)


    def strack(self):
        """
        Detects and tracks radius for the main interface circle using classical techniques.
        """
        if self.interface.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return

        self.popup = Spinner(self.videoview, self.vwidth, self.vheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.interface.track(self._lcoords.pix2norm(self.fwidth, self.fheight), self._rect, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.loadvideo(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,)).start()


    def clear(self):
        """Clears almost everything"""
        super().clear()
        
        del self.interface
        self.interface = Interface(trackpath=self._trackpath)
        
        self.scruler = None
        self._rcoords = None
        self._rects = []
        
        self.seekbar.setcount(100)


    def plot_distances(self):
        if len(self.interface.trackpts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        num_tracks = len(self.interface.trackpts)
        _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

        for i in range(num_tracks):
            trackpts = self.interface.trackpts[i]
            xcoords = trackpts[0, :] - self.fx
            ycoords = trackpts[1, :] - self.fy

            axes[i][0].plot(xcoords)
            axes[i][0].set_title("x coordinates")
            axes[i][1].plot(ycoords)
            axes[i][1].set_title("y coordinates")

        plt.tight_layout()
        plt.show()