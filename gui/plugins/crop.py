from typing import Callable
import customtkinter as ctk
from core import PixelRect, abspath
from PIL import Image
from math import floor

class Crop:
    def __init__(self, canvas, vwidth, vheight, updateframe:Callable, toggle:Callable):
        
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.fwidth = vwidth
        self.fheight = vheight
        self.crpwidth = vwidth
        self.crpheight = vheight
        
        self.updateframe = updateframe
        self.toggle = toggle
        
        self.fx = self.fy = 0
        self.crpx = self.crpy = 0
        self.sx = self.sy = 0
        self._ctkbox = None
        self.crprect = None
        
        self.btnsize = 30
        self.clearbtn = self.mkbutton("assets/bin.png", self.clearrect, width=30, height=30)
        self.applybtn = self.mkbutton("assets/apply.png", self.apply, width=80, height=40)
        
    def set(self, fwidth, fheight):
        self.fwidth = fwidth
        self.fheight = fheight
        self.crpwidth = fwidth
        self.crpheight = fheight
        
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)
        self.crpx = self.fx
        self.crpy = self.fy
        
    def mkbutton(self, imgpath, command, width=30, height=30):
        """Create a CTkButton with image loaded from `imgpath`."""
        img = Image.open(abspath(imgpath)).resize((width, height), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))

        button = ctk.CTkButton(self.canvas, text="", width=width, height=height,
                               image=img, command=command)
        button.image = img
        return button
        
    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self._ctkbox is not None:
            self.canvas.delete(self._ctkbox)
            self.clearbtn.place_forget()
        
    def clear(self):
        self.crprect = None
        
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)
        self.crpx = self.fx
        self.crpy = self.fy
        
        
    def drawrect(self):
        """Draws rectangle with simple lines"""
        
        def ondown(event):
            self.sx, self.sy = (event.x, event.y)
            
            self._ctkbox = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            ex, ey = (event.x, event.y)

            self.canvas.coords(self._ctkbox, self.sx, self.sy, ex, ey)
            
        def onrelease(event):
            ex, ey = (event.x, event.y)
            
            self.canvas.itemconfig(self._ctkbox, outline="green")

            self.crpwidth = ex - self.sx
            self.crpheight = ey - self.sy
            
            self.crprect = PixelRect(self.sx-self.fx, self.sy-self.fy, self.crpwidth, self.crpheight)
            
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            
            self.clearbtn.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            
            self.applybtn.place(x=self.vwidth-110, y=self.vheight-55)
            
            self.crpx = floor(self.vwidth/2 - self.crpwidth/2)
            self.crpy = floor(self.vheight/2 - self.crpheight/2)
            

        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", inrect)
        self.canvas.bind("<ButtonRelease-1>", onrelease)
        
        
    
    def apply(self):
        self.clearrect()
        self.updateframe()
        self.clearbtn.place_forget()
        self.applybtn.place_forget()
        self.toggle()
        
        
    def appcrop(self, frame):
        if self.crprect is None:
            return frame
        
        cframe = frame[self.crprect.ymin:self.crprect.ymax, self.crprect.xmin:self.crprect.xmax]
        
        return cframe