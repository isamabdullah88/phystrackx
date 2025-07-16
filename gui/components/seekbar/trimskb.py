from math import floor, ceil
import customtkinter as ctk
import tkinter as tk
from PIL import Image
from core import abspath
from .bar import Bar
from .viewskb import ViewSeekBar


class TrimSeekBar(ViewSeekBar):
    def __init__(self, frame, width, height, fcount=100, ondrag=None):
        super().__init__(frame, width, height, fcount, self.leftcb)

        self.startidx = ceil(0.01*fcount)
        self.endidx = floor(0.99*fcount)
        self.idx = self.startidx

        self.ondrag = ondrag
        
        self.rightbar = None
        
    def pack(self):
        super().pack()
        
        self.rightbar = Bar(self.canvas, self.x1-self.padx, self.x0, self.x1, self.height/2, self.fcount, "rightbar", self.rightcb)
        self.rightbar.pack()
        
        self.applybtn = self.mkbutton("assets/apply.png", self.onapply, btnsize=40)
        self.applybtn.place(x=self.width-60, y=self.height-60)
        
    def leftcb(self, label, idx):
        self.startidx = idx
        self.idx = idx
            
        print('left idx: ', self.startidx)
        self.ondrag()
        
    def rightcb(self, label, idx):
        self.endidx = idx
        self.idx = idx
        
        print('right idx: ', self.endidx)
        self.ondrag()
        
        
    def settrim(self, trimvideo, loadvideo):
        self.trimvideo = trimvideo
        self.loadvideo = loadvideo
        
    def clearright(self):
        if self.rightbar is not None:
            self.rightbar.clear()
        
    def clear(self):
        super().clear()
        self.clearright()
    
    def mkbutton(self, imgpath, command, btnsize=30):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                            image=img, command=command)
        
        button.image = img
        
        return button
    
    
    def onapply(self):
        print('on apply')
        self.applybtn.place_forget()
        print('after place forget')
        
        if self.trimvideo is not None:
            self.trimvideo(self.startidx, self.endidx)
            
        print('after trim video')
        if self.loadvideo is not None:
            self.set(self.endidx-self.startidx)
            # self.draw()
            self.clearright()
            super().pack()
            self.loadvideo("")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.frame.pack(fill="both", expand=True)
        self.canvas = ctk.CTkCanvas(self.frame)
        self.canvas.pack(fill="both", expand=True)

        self.tseekbar = TrimSeekBar(self.frame, 600, 100, 2000, ondrag=self.ondrag)
        self.tseekbar.pack()
    
    def ondrag(self):
        pass

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
