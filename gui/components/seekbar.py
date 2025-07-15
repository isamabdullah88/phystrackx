from math import floor, ceil
import customtkinter as ctk
import tkinter as tk
from PIL import Image
from core import abspath


class Seek:
    """Implements and draws the seek part of a seekbar. A horizontal bar of seek"""
    def __init__(self, canvas, x0, x1, y, height=10):
        self.canvas = canvas
        
        self.hhalf = height/2
        self.x0 = x0
        self.x1 = x1
        self.y = y
        
        self.tkrectb = None
        self.tkrects = None
        
    def pack(self):
        # Draw background bar
        self.tkrectb = self.canvas.create_rectangle(self.x0, self.y-self.hhalf, self.x1, self.y+self.hhalf, fill="#e2bcc5")

        # Draw selected range (trim region)
        self.tkrects = self.canvas.create_rectangle(self.x0+1, self.y-self.hhalf-1, self.x1, self.y+self.hhalf+1, fill="#e74ce0", outline="")
        
    def clear(self):
        if self.tkrectb is not None:
            self.canvas.delete(self.tkrectb)
            
        if self.tkrects is not None:
            self.canvas.delete(self.tkrects)
        
class Bar:
    """Implements and draws the bar of a seekbar. A vertical stick that can be dragged along a seek"""
    def __init__(self, canvas:ctk.CTkCanvas, x0:float, x1:float, y:float, fcount:int, label, callback, xs=10, width=10, height=50):
        self.canvas = canvas
        
        self.x0 = x0
        self.x1 = x1
        self.y = y
        self.fcount = fcount
        self.whalf = width/2
        self.hhalf = height/2
        
        self.clicked = False
        
        self.x = self.x0 + xs
        self.idx = self.x2fidx(self.x)
        
        self.tkrect = None
        self.label = label
        self.callback = callback
    
    def pack(self):
        self.tkrect = self.canvas.create_rectangle(self.x-self.whalf, self.y-self.hhalf,
                            self.x+self.whalf, self.y+self.hhalf, fill="#1b930b", outline="")
        
        self.canvas.tag_bind(self.tkrect, "<Button-1>", self.onclick)
        self.canvas.tag_bind(self.tkrect, "<B1-Motion>", self.ondrag)
        
    def clear(self):
        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)
    
        
    def onclick(self, event):
        x = event.x
        
        if abs(x - self.x) < self.whalf:
            self.clicked = True
        else:
            self.clicked = False
            
    def x2fidx(self, x):
        """Position of bar to frame index"""
        x -= self.x0 - self.whalf
        return floor(x / (self.x1-self.x0 + 2*self.whalf) * self.fcount)
            
    def ondrag(self, event):
        x = event.x
        
        if not self.clicked:
            return
        
        if self.x0-self.whalf < x < self.x1+self.whalf:
            self.x = x
            self.canvas.coords(self.tkrect, self.x-self.whalf, self.y-self.hhalf,
                            self.x+self.whalf, self.y+self.hhalf)
            
            self.idx = self.x2fidx(self.x)
            self.callback(self.label, self.idx)

        
        

class CutSeekBar:
    def __init__(self, frame, width=200, height=40, fcount=100, ondrag=None, disable=True, mode="Trim"):
        """mode can be 'Trim' and 'View'."""
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        # self._rwidth = 4
        # self._rheight = 10
        self.padx = 10
        self.width = width - self.padx
        self.height = height

        self.startidx = ceil(0.01*fcount)
        self.endidx = floor(0.99*fcount)
        self.active = None
        self.idx = self.startidx
        
        # self._xoff = floor(self._wpad/2)
        self.x0 = ceil(0.01*self.width) + self.padx
        self.x1 = floor(0.99*self.width) - self.padx
        self.x = self.x0

        self._ondrag = ondrag
        # self._disable = disable
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
            
        print('label: ', label)
        print('idx: ', self.idx)
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
            

        # self.pack()

    # def x2fidx(self, x):
    #     x -= self._xoff
    #     return floor(x / self.width * self.fcount)

    # def draw(self):
    #     self.canvas.delete("all")

    #     recth = floor(self.height/2)
        
    #     # Draw background bar
    #     self.canvas.create_rectangle(self._xoff, recth - 3, self.width+self._xoff, recth + 3,
    #                                 fill="#e2bcc5")

    #     # Draw draggable handles
    #     w2 = floor(self._rwidth/2)
    #     self.canvas.create_rectangle(self._xs-w2, self._rheight, self._xs+w2, self.height-self._rheight,
    #                                 fill="#1eff00", outline="", tag="start")
        
    #     if self.mode == "Trim":
    #         # Draw selected range (trim region)
    #         self.canvas.create_rectangle(self._xs, recth - 4, self._xe, recth + 4, fill="#e74ce0",
    #                                     outline="")
        
    #         self.canvas.create_rectangle(self._xe-w2, self._rheight, self._xe+w2, self.height-self._rheight,
    #                                     fill="#1eff00", outline="", tag="end")

    #         # Optional: display current range
    #         self.canvas.create_text(self.width//2, recth+10, fill="#ffffff",
    #                                 text=f"Trim Range: {self.startidx} - {self.endidx}")

    # def click(self, event):
    #     x = event.x
        
    #     if abs(x - self._xs) < self._wpad/2:
    #         self.active = "start"
    #     elif abs(x - self._xe) < self._wpad/2:
    #         self.active = "end"
    #     else:
    #         self.active = None

    # def drag(self, event):
    #     if self._disable:
    #         return
        
    #     x = event.x
        
    #     if self.active == "start":
    #         if (x >= self._xoff) and (x+self._wpad/2 < self._xe):
    #             self._xs = x
    #         self._x = self._xs
            
    #     elif (self.mode == "Trim") and (self.active == "end"):
    #         if (x <= self.width+self._xoff) and (x-self._wpad/2 > self._xs):
    #             self._xe = x
    #         self._x = self._xe

    #     self.startidx = self.x2fidx(self._xs)
    #     self.endidx = self.x2fidx(self._xe)
    #     self.idx = self.x2fidx(self._x)
        
    #     if (self._ondrag is not None) and (self.idx < self.fcount):
    #         self._ondrag()

    #     self.draw()

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
        # Seek(self.canvas, 100, 600, 50)
        # bar1 = Bar(self.canvas, 100, 600, 50, 100, "left", None)
        # bar2 = Bar(self.canvas, 110, 600, 50, 100, "right", None)

        # self.print_button = ctk.CTkButton(self, text="Print Cut Range", command=self.print_range)
        # self.print_button.pack()

    # def print_range(self):
    #     start, end = self.seekbar.get_trim_range()
    #     print(f"Selected trim range: Frame {start} to {end}")
    
    def ondrag(self):
        pass

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
