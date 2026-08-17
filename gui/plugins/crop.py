from typing import Callable
import logging
import customtkinter as ctk
from core import PixelRect
from math import floor
from gui.components.buttons import SubmitButton, BinButton

class Crop:
    def __init__(self, canvas, vwidth, vheight, updateframe:Callable):
        
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.fwidth = vwidth
        self.fheight = vheight
        self.cropwidth = vwidth
        self.cropheight = vheight

        # self.setsize : Callable = None
        self.updateframe = updateframe
        # self.toggle = toggle
        
        self.fx = self.fy = 0
        self.cropx = self.cropy = 0
        self.sx = self.sy = 0
        self._ctkbox = None
        self.croprect = None
        
        self.btnsize = 30
        self.apply_button = SubmitButton(self.canvas, command=self.apply, size=50)
        self.bin_button = BinButton(self.canvas, command=self.clearrect, size=self.btnsize)

        self.logger = logging.getLogger(__name__)
        
    def set(self, fwidth:int = 0, fheight:int = 0):
        if self.croprect is not None:
            self.logger.info("Crop rectangle exists. Ignoring new dimensions and using existing.")
            self.cropx = floor(self.vwidth/2 - self.croprect.width/2)
            self.cropy = floor(self.vheight/2 - self.croprect.height/2)
            self.cropwidth = self.croprect.width
            self.cropheight = self.croprect.height
            return
        
        if fwidth > 0 and fheight > 0:
            self.logger.info(f"Setting crop dimensions to: width={fwidth}, height={fheight}")
            self.fwidth = fwidth
            self.fheight = fheight
            self.cropwidth = fwidth
            self.cropheight = fheight
            
            self.fx = floor(self.vwidth/2 - self.fwidth/2)
            self.fy = floor(self.vheight/2 - self.fheight/2)
            self.cropx = self.fx
            self.cropy = self.fy
        
    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self._ctkbox is not None:
            self.canvas.delete(self._ctkbox)
            self.bin_button.pack_forget()
        
    def clear(self):
        self.croprect = None
        
        self.fx = floor(self.vwidth/2 - self.fwidth/2)
        self.fy = floor(self.vheight/2 - self.fheight/2)
        self.cropx = self.fx
        self.cropy = self.fy
        
        
    def drawrect(self, setsize:Callable):
        """Draws rectangle with simple lines"""
        self.setsize = setsize
        
        def ondown(event):
            self.sx, self.sy = (event.x, event.y)
            
            self._ctkbox = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            ex, ey = (event.x, event.y)

            self.canvas.coords(self._ctkbox, self.sx, self.sy, ex, ey)
            
        def onrelease(event):
            ex, ey = (event.x, event.y)
            
            self.canvas.itemconfig(self._ctkbox, outline="green")

            self.cropwidth = ex - self.sx
            self.cropheight = ey - self.sy
            
            self.croprect = PixelRect(self.sx-self.fx, self.sy-self.fy, self.cropwidth, self.cropheight)
            
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")

            self.bin_button.pack(anchor=ctk.N, pady=50)
            self.apply_button.pack(side="right", padx=10, pady=10, anchor="se")
            
            # self.cropx = floor(self.vwidth/2 - self.croprect.width/2)
            # self.cropy = floor(self.vheight/2 - self.croprect.height/2)
            

        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", inrect)
        self.canvas.bind("<ButtonRelease-1>", onrelease)
        
        
    
    def apply(self):
        self.clearrect()

        self.logger.info(f"Applying crop | Crop width: {self.cropwidth}, Crop height: {self.cropheight}")
        self.set()
        # self.setsize(self.cropwidth, self.cropheight)
        self.updateframe()

        self.bin_button.pack_forget()
        self.apply_button.pack_forget()
        
        
    def apply_crop(self, frame):
        if self.croprect is None:
            return frame
        
        cframe = frame[self.croprect.ymin:self.croprect.ymax, self.croprect.xmin:self.croprect.xmax]
        
        return cframe