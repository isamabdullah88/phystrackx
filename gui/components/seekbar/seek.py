"""
Seek Class for Seekbar Component
This module defines the Seek class which implements and draws the seek part of a seekbar.
"""
from core import SeekType
import tkinter as tk

class Seek:
    """Implements and draws the seek part of a seekbar. A horizontal bar of seek"""
    def __init__(self, canvas:tk.Canvas, x0:float, x1: float, y: float, color:str="#ee7ae8", height: float=8):
        self.canvas = canvas
        
        self.hhalf = height/2
        self.x0 = x0
        self.x1 = x1
        self.y = y
        
        self.color = color
        self.tkrect = None
        
    def pack(self):
        """Draws the seek bar"""
        self.tkrect = self.canvas.create_rectangle(self.x0+1, self.y-self.hhalf-1, self.x1, self.y+self.hhalf+1, fill=self.color, outline="")
        self.canvas.tag_lower(self.tkrect)
        
    def draw(self, x0, x1):
        # Draw background bar
        # self.tkrectb = self.canvas.create_rectangle(self.x0, self.y-self.hhalf, self.x1, self.y+self.hhalf, fill="#e2bcc5")

        # Draw selected range
        self.tkrect = self.canvas.create_rectangle(x0+1, self.y-self.hhalf-1, x1, self.y+self.hhalf+1, fill=self.color, outline="")
        # if self.tkrect is not None:
        #     self.canvas.coords(self.tkrect, x0+1, self.y-self.hhalf-1, x1, self.y+self.hhalf+1)
        
    def clear(self):
        # if self.tkrectb is not None:
        #     self.canvas.delete(self.tkrectb)
            
        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)