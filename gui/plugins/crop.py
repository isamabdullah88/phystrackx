from typing import Callable
import customtkinter as ctk
from core import PixelRect
from math import floor
from gui.components.buttons import SubmitButton, BinButton

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
        self.applybtn = SubmitButton(self.canvas, command=self.apply, size=50)
        self.binbtn = BinButton(self.canvas, command=self.clearrect, size=self.btnsize)
        
    def set(self, fwidth, fheight):
        self.fwidth = fwidth
        self.fheight = fheight
        self.crpwidth = fwidth
        self.crpheight = fheight
        
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)
        self.crpx = self.fx
        self.crpy = self.fy
        
    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self._ctkbox is not None:
            self.canvas.delete(self._ctkbox)
            self.binbtn.pack_forget()
        
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

            self.binbtn.pack(anchor=ctk.N, pady=50)
            self.applybtn.pack(side="right", padx=10, pady=10, anchor="se")
            
            self.crpx = floor(self.vwidth/2 - self.crpwidth/2)
            self.crpy = floor(self.vheight/2 - self.crpheight/2)
            

        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", inrect)
        self.canvas.bind("<ButtonRelease-1>", onrelease)
        
        
    
    def apply(self):
        self.clearrect()
        self.updateframe()
        self.binbtn.pack_forget()
        self.applybtn.pack_forget()
        self.toggle()
        
        
    def appcrop(self, frame):
        if self.crprect is None:
            return frame
        
        cframe = frame[self.crprect.ymin:self.crprect.ymax, self.crprect.xmin:self.crprect.xmax]
        
        return cframe