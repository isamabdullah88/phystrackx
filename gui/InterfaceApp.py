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
from core.Rect import PixelRect, Points

class InterfaceApp(App):
    def __init__(self, root):
        super().__init__(root)

        # For drawing ellipse over tracking area
        sfimg = Image.open("assets/line.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.linebd = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                      image=sfimg, command=self.drawline)
        self.linebd.pack(pady=10)
        
        # For drawing rectangle over text area
        sfimg = Image.open("assets/rectanglebd.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        self.rectbd = ctk.CTkButton(self.toolbarf, text="", width=80, height=80,
                                      image=sfimg, command=self.drawrect)
        self.rectbd.pack(pady=10)
        

        self.seekbar = CutSeekBar(self.video_frame, ondrag=self.updateframe)

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



    def load_video(self, videopath):
        self.interface.add_video(videopath)
        
        self.seekbar.pack(pady=10)
        self.seekbar.setcount(self.interface.fcount)

        frame1 = self.interface.frame(0)
        self.dispframe(frame1)

    def dispframe(self, frame):
        fwidth = self.interface.fwidth
        fheight = self.interface.fheight
        frame = self.resizeframe(frame, fwidth, fheight)

        img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=img)
        self._frame = frame
        self.fheight, self.fwidth = self._frame.shape[:2]

        self.fx = floor(self.cwidth/2 - frame.shape[1]/2)
        self.fy = floor(self.cheight/2 - frame.shape[0]/2)

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
                print('Line cleared')
            
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


    def start_tracking(self):
        """
        Detects and tracks radius for the main interface circle using classical techniques.
        """

        self.popup = SpinnerPopup(self.videoview, self.cwidth, self.cheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.interface.track(self._lcoords.pix2norm(self.fwidth, self.fheight), self._rect, startidx, endidx)
            
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