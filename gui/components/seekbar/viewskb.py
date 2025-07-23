from math import floor, ceil
import tkinter as tk
from .seek import Seek
from .bar import Bar
from core import SeekType

class ViewSeekBar:
    """Seekbar that is view only and act as a video viewer. It can't trim video."""
    def __init__(self, frame:tk.Frame, width, height, fcount=100,  callback=None):
        """mode can be 'Trim' and 'View'."""
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self.padx = 10
        self.width = width
        self.height = height
        
        self.callback = callback
        
        self.fixedseek = None
        self.leftbar = None
        
        self.setparams()
        

    def setparams(self):
        self.idx = ceil(0.01*self.fcount)
        
        self.x0 = self.padx
        self.x1 = self.width - self.padx

    # def callback(self, label, idx):
    #     self.idx = idx
        
    #     self.callback()
        
    def clear(self):
        # if self.seek is not None:
        #     self.seek.clear()
            
        if self.leftbar is not None:
            self.leftbar.clear()

    def pack(self):
        
        self.clear()
        
        self.fixedseek = Seek(self.canvas, self.x0, self.x1, self.height/2, color="#9c97d6")
        self.fixedseek.pack()
        self.leftbar = Bar(self.canvas, self.x0, self.x0, self.x1, self.height/2, self.fcount,
                        callback=self.callback)
        self.leftbar.pack()
        
        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        
    def set(self, fcount):
        self.fcount = fcount
        
        self.setparams()
        
    def onclick(self, event):
        self.leftbar.onclick(event)
        # self.callback()
        
    def ondrag(self, event):
        func = lambda x, xlim: min(x, xlim)
        self.leftbar.ondrag(event, func, self.x1)
        self.fixedseek.draw(self.leftbar.x0, self.leftbar.x1)
        # self.callback()
        

import time
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = tk.Frame(self, width=700, height=300)
        self.frame.pack(fill="both", expand=True)

        self.seekbar = ViewSeekBar(self.frame, 700, 100, fcount=100, callback=self.callback)
        self.seekbar.pack()
        
    # def print_range(self):
    #     start, end = self.seekbar.get_trim_range()
    #     print(f"Selected trim range: Frame {start} to {end}")
    
    def callback(self):
        print('callback called: ' + str(time.time()))

if __name__ == "__main__":
    app = App()
    app.mainloop()