from math import floor, ceil
import customtkinter as ctk
import tkinter as tk
from PIL import Image
from core import abspath


class CutSeekBar:
    def __init__(self, frame, width=200, height=40, fcount=100, ondrag=None, disable=True, mode="Trim"):
        """mode can be 'Trim' and 'View'."""
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self.padx = 10
        self.width = width - self.padx
        self.height = height

        self.startidx = ceil(0.01*fcount)
        self.endidx = floor(0.99*fcount)
        self.active = None
        self.idx = self.startidx
        
        self.x0 = ceil(0.01*self.width) + self.padx
        self.x1 = floor(0.99*self.width) - self.padx
        self.x = self.x0

        self._ondrag = ondrag
        self.mode = mode
        
        self.trimvideo = None
        self.loadvideo = None
        
        self.seek = None
        self.leftbar = None
        self.rightbar = None
        
        
    def callback(self, label, idx):
        if label == "leftbar":
            self.startidx = idx
            self.idx = idx
        
        if label == "rightbar":
            self.endidx = idx
            self.idx = idx
            
        self._ondrag()
        
        
    def settrim(self, trimvideo, loadvideo):
        self.trimvideo = trimvideo
        self.loadvideo = loadvideo

    def pack(self):
        
        if self.seek is not None:
            self.seek.clear()
        if self.leftbar is not None:
            self.leftbar.clear()
        if self.rightbar is not None:
            self.rightbar.clear()
        
        self.seek = Seek(self.canvas, self.x0, self.x1,  self.height/2)
        self.leftbar = Bar(self.canvas, self.x0, self.x1, self.height/2, self.fcount, "leftbar", self.callback)
        
        self.seek.pack()
        self.leftbar.pack()
        
        if self.mode == "Trim":
            self.rightbar = Bar(self.canvas, self.x0, self.x1, self.height/2, self.fcount, "rightbar", self.callback)
            self.rightbar.pack()
            self.applybtn = self.plcbutton("assets/apply.png", self.onapply, btnsize=40)
            self.applybtn.place(x=self.width-60, y=self.height-60)
        else:
            if self.applybtn:
                self.applybtn.place_forget()
        
    
    def plcbutton(self, imgpath, command, btnsize=30):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                            image=img, command=command)
        
        button.image = img
        
        return button


    def set(self, fcount, trim=True):
        self._disable = False
        self.fcount = fcount
        self.x0 = ceil(0.01*self.width) + self.padx
        self.x1 = floor(0.99*self.width) + self.padx
        self.startidx = ceil(0.01*self.fcount)
        self.endidx = floor(0.99*self.fcount)
        self.idx = self.startidx
        # self.draw()
        if trim:
            self.mode = "Trim"
        else:
            self.mode = "View"
            self.x1 = self.width - self.padx
    

    def get_trim_range(self):
        return self.startidx, self.endidx
    
    def onapply(self):
        self.applybtn.place_forget()
        
        if self.trimvideo is not None:
            self.trimvideo(self.startidx, self.endidx)
            
        if self.loadvideo is not None:
            self.set(self.endidx-self.startidx, trim=False)
            # self.draw()
            self.pack()
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

        self.seekbar = CutSeekBar(self.frame, width=600, fcount=2000, ondrag=self.ondrag,
                            disable=False)
    
    def ondrag(self):
        pass

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
