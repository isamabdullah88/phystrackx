from math import floor, ceil
import customtkinter as ctk
from .seek import Seek
from .bar import Bar

class ViewSeekBar:
    """Seekbar that is view only and act as a video viewer. It can't trim video."""
    def __init__(self, frame:ctk.CTkFrame, width, height, fcount=100,  callback=None):
        """mode can be 'Trim' and 'View'."""
        self.canvas = ctk.CTkCanvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self.padx = 10
        self.width = width
        self.height = height
        
        self.callback = callback
        
        self.seek = None
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
        if self.seek is not None:
            self.seek.clear()
            
        if self.leftbar is not None:
            self.leftbar.clear()

    def pack(self):
        
        self.clear()
        
        self.seek = Seek(self.canvas, self.x0, self.x1,  self.height/2)
        self.leftbar = Bar(self.canvas, self.x0, self.x0, self.x1, self.height/2, self.fcount, "leftbar", self.callback)
        
        self.seek.pack()
        self.leftbar.pack()
        
        self.canvas.tag_bind(self.leftbar.tkrect, "<Button-1>", self.onclick)
        self.canvas.tag_bind(self.leftbar.tkrect, "<B1-Motion>", self.ondrag)
        
    def set(self, fcount):
        self.fcount = fcount
        
        self.setparams()
        
    def onclick(self, event):
        self.leftbar.onclick(event)
        # x = event.x
        
        # if abs(x - self.leftbar.x) < self.leftbar.whalf:
        #     self.leftbar.clicked = True
        # else:
        #     self.leftbar.clicked = False
        
    def ondrag(self, event):
        self.leftbar.ondrag(event)
        
        # x = event.x
        
        # if not self.leftbar.clicked:
        #     return
        
        # if self.leftbar.x0-self.leftbar.whalf < x < self.leftbar.x1+self.leftbar.whalf:
        #     self.leftbar.x = x
            
        #     self.canvas.delete(self.leftbar.tkrect)
        #     self.leftbar.tkrect = self.canvas.create_rectangle(self.leftbar.x-self.leftbar.whalf, self.leftbar.y-self.leftbar.hhalf,
        #                     self.leftbar.x+self.leftbar.whalf, self.leftbar.y+self.leftbar.hhalf, fill="#0ef87f", outline="")
            
        #     self.leftbar.idx = self.leftbar.x2fidx(self.leftbar.x)
        #     self.callback(self.leftbar.label, self.leftbar.idx)
        
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.frame.pack(fill="both", expand=True)

        self.seekbar = ViewSeekBar(self.frame, 700, 100, fcount=100, callback=self.callback)
        self.seekbar.pack()
        
    # def print_range(self):
    #     start, end = self.seekbar.get_trim_range()
    #     print(f"Selected trim range: Frame {start} to {end}")
    
    def callback(self, label, idx):
        print('idx: ', self.seekbar.idx)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()