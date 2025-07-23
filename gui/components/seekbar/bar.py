# from customtkinter import CTkCanvas
from core import SeekType
from math import floor
# import customtkinter as ctk
import tkinter as tk
from .seek import Seek

class Bar:
    """Implements and draws the bar of a seekbar. A vertical stick that can be dragged along a seek"""
    def __init__(self, canvas:tk.Canvas, x:float, x0:float, x1:float, y:float, fcount:int,
                color:str="#de459b", width=6, height=50):
        self.canvas = canvas
        
        self.x0 = x0
        self.x1 = x1
        self.y = y
        self.fcount = fcount
        self.whalf = width/2
        self.hhalf = height/2
        
        self.clicked = False
        
        self.x = x
        self.idx = self.x2fidx(self.x)
        
        self.tkrect = None
        self.color = color
        
        # self.seekcolor = seekcolor
        # self.label = label
        # self.callback = callback
        
        # self.seek = Seek(self.canvas, self.x0, self.x1, self.y, color=seekcolor)
        # self.seektype = seektype
        
    # def seekdraw(self, x0, x1):
    #     """Draws the seek bar"""
    #     if self.seektype == SeekType.FIXED:
    #         self.seek.draw(x0, x1)
    #     elif self.seektype == SeekType.LEFT:
    #         self.seek.draw(self.x-self.whalf, x1)
    #     elif self.seektype == SeekType.RIGHT:
    #         self.seek.draw(x0, self.x+self.whalf)
    
    def pack(self):
        """Draws the bar and the seek"""
        
        # self.seek.pack()
        
        self.tkrect = self.canvas.create_rectangle(self.x-self.whalf, self.y-self.hhalf,
                            self.x+self.whalf, self.y+self.hhalf, fill=self.color, outline="")
        self.canvas.tag_raise(self.tkrect)
        
    def clear(self):
        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)
    
        
    def onclick(self, event):
        x = event.x
        
        if self.contain(x):
            self.clicked = True
        else:
            self.clicked = False
            
    def x2fidx(self, x):
        """Position of bar to frame index"""
        x -= self.x0 - self.whalf
        return floor(x / (self.x1-self.x0 + 2*self.whalf) * self.fcount)
    
    def contain(self, x):
        """Checks if the x position is within the bar"""
        return abs(x - self.x) < self.whalf
    
    def inextents(self, x):
        """Checks if the x position is within the extents of the bar"""
        return self.x0 <= x <= self.x1
    
            
    def ondrag(self, event, func, xlim):
        """Updates the drag position by evaluating func with xlim."""
        x = event.x
        
        if not self.clicked:
            return
        
        # self.canvas.delete(self.tkrect)
        # self.seek.clear()
        
        # if self.contain(x):
        x = func(x, xlim)
        
        if x < self.x0:
            x = self.x0
        elif x > self.x1:
            x = self.x1
            
        self.x = x
        
        self.idx = self.x2fidx(self.x)
            # print("idx: ", self.idx)
            # self.callback(self.label, self.idx)
        # self.seekdraw(self.x0, self.x1)
        self.canvas.coords(self.tkrect, self.x-self.whalf, self.y-self.hhalf,
                        self.x+self.whalf, self.y+self.hhalf)
        
        # self.canvas.create_rectangle(self.x0, self.y - 3, self.x1, self.y + 3, fill="#888")
        
        # self.tkrect = self.canvas.create_rectangle(self.x-self.whalf, self.y-self.hhalf,
        #                     self.x+self.whalf, self.y+self.hhalf, fill="#0ef87f", outline="")
        
        # self.canvas.create_text((self.x0 + self.x1) // 2, self.y + 25,
        #                         text=f"Frame index: {self.x2fidx(x)}", fill="white")
            
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = tk.Frame(self, width=700, height=300)
        self.frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.frame, width=700, height=300, bg="#4d535c")
        self.canvas.pack()

        self.bar = Bar(self.canvas, 100, 0, 700, 100, 100, "leftbar", self.callback)
        self.bar.pack()
        
    # def print_range(self):
    #     start, end = self.seekbar.get_trim_range()
    #     print(f"Selected trim range: Frame {start} to {end}")
    
    def callback(self, label, idx):
        print('idx: ', self.bar.idx)

if __name__ == "__main__":
    # ctk.set_appearance_mode("dark")
    # ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()