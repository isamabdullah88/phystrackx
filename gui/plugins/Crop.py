from typing import Callable
import numpy as np
import customtkinter as ctk
from ..components.Rect import Rect
from core import PixelRect

class Crop(Rect):
    def __init__(self, videoview, vwidth, vheight, updateframe:Callable[[np.ndarray], None], updateparams:Callable):
        super().__init__(videoview, vwidth, vheight)
        
        self.updateframe = updateframe
        self.updateparams = updateparams
        self.applybtn = self.plcbutton("assets/apply.png", self.apply, 80)
        
    def drawrect(self, fwidth, fheight, fx, fy):
        """Draws rectangle with simple lines"""
        if fwidth is None:
            fwidth = self.vwidth
        if fheight is None:
            fheight = self.vheight
        
        def ondown(event):            
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            self.videoview.coords(self._ctkbox, sx, sy, ex, ey)
            
        def onrelease(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            
            self._ctkrects.append(self._ctkbox)
            self.videoview.itemconfig(self._ctkbox, outline="green")

            rect = PixelRect(sx-fx, sy-fy, ex-sx, ey-sy)
            self.rects.append(rect)
            
            self.videoview.unbind("<Button-1>")
            self.videoview.unbind("<B1-Motion>")
            self.videoview.unbind("<ButtonRelease-1>")
            
            self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            
            self.applybtn.place(x=self.vwidth-110, y=self.vheight-100)
            

        self.videoview.bind("<Button-1>", ondown)
        self.videoview.bind("<B1-Motion>", inrect)
        self.videoview.bind("<ButtonRelease-1>", onrelease)
        
        
    
    def apply(self):
        self.updateparams()
        self.updateframe()
        self.clearrects()
        self.button.place_forget()
        self.applybtn.place_forget()
        
        
        
    
    def appcrop(self, frame):
        if len(self.rects) > 0:
            rect = self.rects[0]
            
            cframe = frame[rect.ymin:rect.ymax, rect.xmin:rect.xmax]
            
            return cframe
        
        return frame