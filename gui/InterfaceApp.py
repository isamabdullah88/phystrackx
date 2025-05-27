import os
import cv2
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from matplotlib import pyplot as plt
from tkinter import messagebox
from math import floor

from .App import App
from experiments.Interface import Interface
from .Core import circilize, fcrop_coords
from .components.Spinner import SpinnerPopup
from .components.Seekbar import CutSeekBar
from core.Rect import NormalizedRect, PixelRect

class InterfaceApp(App):
    def __init__(self, root):
        super().__init__(root)

        # For drawing ellipse over tracking area
        sfimg = Image.open("assets/line.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.linebd = ctk.CTkButton(self.toolbar_frame, text="", width=80, height=80,
                                      image=sfimg, command=self.drawline)
        self.linebd.pack(pady=10)
        
        # For drawing rectangle over text area
        sfimg = Image.open("assets/rectanglebd.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.rectbd = ctk.CTkButton(self.toolbar_frame, text="", width=80, height=80,
                                      image=sfimg, command=self.drawrect)
        self.rectbd.pack(pady=10)
        

        self.seekbar = CutSeekBar(self.video_frame, ondrag=self.update_frame)

        self.ccoords = (0, 0)

        # mask from user for tracking
        self._line = None
        # rect for text detection
        self._rect = None

        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        self._trackpath = os.path.join(tempdir, 'track-interface.mp4')

        self.interface = Interface(trackpath=self._trackpath)



    def load_video(self, videopath):
        self.interface.add_video(videopath)
        
        self.seekbar.pack(pady=10)
        self.seekbar.setcount(self.interface.fcount)

        frame1 = self.interface.frame(0)
        self.display_first_frame(frame1)

    def display_first_frame(self, frame):
        fwidth = self.interface.fwidth
        fheight = self.interface.fheight
        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame
        self.fheight, self.fwidth = self._frame.shape[:2]

        self.fx = floor(self.cwidth/2 - frame.shape[1]/2)
        self.fy = floor(self.cheight/2 - frame.shape[0]/2)

        self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
    def update_frame(self):
        
        frame = self.interface.frame(index=self.seekbar.idx)
        fwidth = self.interface.fwidth
        fheight = self.interface.fheight

        frame = self.resize_frame(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame

        self.videoview.itemconfig(self.imgview, image=self.photo)

    def mark_axes(self):

        def update_axes(event):
            """ Update the axes to follow the mouse cursor. """
            self.videoview.delete("axes")  # Remove old axes
            x, y = event.x, event.y  # Get mouse position

            # Draw new axes centered on mouse position
            self.videoview.create_line(0, y, self.cwidth, y, fill="red", width=2, tags="axes")  # X-axis
            self.videoview.create_line(x, 0, x, self.cheight, fill="blue", width=2, tags="axes")  # Y-axis

        def store_click(event):
            """ Store the clicked coordinates and draw a point. """
            x, y = event.x, event.y

            self.videoview.create_oval(x-3, y-3, x+3, y+3, fill="red", outline="black")  # Draw a small dot

            self.videoview.unbind("<Motion>")
            self.videoview.unbind("<Button>")

        self.videoview.bind("<Motion>", update_axes)
        self.videoview.bind("<Button>", store_click)

    def drawline(self):
        """Draws line with filled transparent image laid over region of interest"""
        self._ctkline = None

        def ondown(event):
            if self._ctkline is not None:
                self.videoview.delete(self._ctkline)
            
            self._lcoords = (event.x, event.y)
            
            self._ctkline = self.videoview.create_line(event.x, event.y, event.x, event.y, fill="magenta", width=3)
            
            
        def inline(event):
            sx, sy = self._lcoords
            ex, ey = (event.x, event.y)

            self.videoview.coords(self._ctkline, sx, sy, event.x, event.y)

            self._line = ((sx-self.fx)/self.fwidth, (sy-self.fy)/self.fheight), \
                ((ex-self.fx)/self.fwidth, (ey-self.fy)/self.fheight)
            
            print('Rect tr: ', self._line)

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inline)

    
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

            print('Rect Orig: ', (sx, sy, ex, ey))

            self.videoview.coords(self._ctkbox, sx, sy, event.x, event.y)

            self._rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy).pixel2normal(self.fwidth, self.fheight)
            print('Rect tr: ', self._rect.totuple())

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)


    def start_tracking(self):
        """
        Detects and tracks radius for the main interface circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.videoview, self.cwidth, self.cheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.interface.track(self._line, self._rect, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.load_video(self._trackpath)

            self.track_coords_button.configure(state=ctk.NORMAL)  # Enable coordinates button

        threading.Thread(target=trackbg, args=(self.popup,)).start()





    def plot_distances(self):
        if len(self.interface.tracked_pts) < 1:
            messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
            return

        num_tracks = len(self.interface.tracked_pts)
        _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

        for i in range(num_tracks):
            tracked_pts = self.interface.tracked_pts[i]
            xcoords = tracked_pts[0, :] - self.fx
            ycoords = tracked_pts[1, :] - self.fy

            axes[i][0].plot(xcoords)
            axes[i][0].set_title("x coordinates")
            axes[i][1].plot(ycoords)
            axes[i][1].set_title("y coordinates")

        plt.tight_layout()
        plt.show()