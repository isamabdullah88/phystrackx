from math import floor, ceil
import customtkinter as ctk
import tkinter as tk
from PIL import Image
from core import abspath

class CutSeekBar:
    def __init__(self, frame, width=200, height=40, fcount=100, ondrag=None, disable=True):
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self._rwidth = 4
        self._rheight = 10
        self._wpad = 10
        self.width = width - self._wpad
        self.height = height

        self.startidx = ceil(0.01*fcount)
        self.endidx = floor(0.99*fcount)
        self.active = None
        self.idx = self.startidx
        
        self._xoff = floor(self._wpad/2)
        self._xs = ceil(0.01*self.width) + self._xoff
        self._xe = floor(0.99*self.width) + self._xoff
        self._x = self._xs

        self._ondrag = ondrag
        self._disable = disable
        
        self.trimvideo = None
        self.loadvideo = None
        
    def settrim(self, trimvideo, loadvideo):
        self.trimvideo = trimvideo
        self.loadvideo = loadvideo

    def pack(self):
        self.draw()
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        
        self.applybtn = self.plcbutton("assets/apply.png", self.onapply, btnsize=40)
        self.applybtn.place(x=self.width-60, y=self.height-60)
        
    
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


    def setcount(self, fcount):
        self._disable = False
        self.fcount = fcount
        self._xs = ceil(0.01*self.width) + self._xoff
        self._xe = floor(0.99*self.width) + self._xoff
        self.startidx = ceil(0.01*self.fcount)
        self.endidx = floor(0.99*self.fcount)
        self.idx = self.startidx
        # self.draw()

    def x2fidx(self, x):
        x -= self._xoff
        return floor(x / self.width * self.fcount)

    def draw(self):
        self.canvas.delete("all")

        recth = floor(self.height/2)
        
        # Draw background bar
        self.canvas.create_rectangle(self._xoff, recth - 3, self.width+self._xoff, recth + 3,
                                     fill="#e2bcc5")

        # Draw selected range (trim region)
        self.canvas.create_rectangle(self._xs, recth - 4, self._xe, recth + 4, fill="#e74ce0",
                                     outline="")

        # Draw draggable handles
        w2 = floor(self._rwidth/2)
        self.canvas.create_rectangle(self._xs-w2, self._rheight, self._xs+w2, self.height-self._rheight,
                                     fill="#1eff00", outline="", tag="start")
        self.canvas.create_rectangle(self._xe-w2, self._rheight, self._xe+w2, self.height-self._rheight,
                                     fill="#1eff00", outline="", tag="end")

        # Optional: display current range
        self.canvas.create_text(self.width//2, recth+10, fill="#ffffff",
                                text=f"Trim Range: {self.startidx} - {self.endidx}")

    def click(self, event):
        x = event.x
        
        if abs(x - self._xs) < self._wpad/2:
            self.active = "start"
        elif abs(x - self._xe) < self._wpad/2:
            self.active = "end"
        else:
            self.active = None

    def drag(self, event):
        if self._disable:
            return
        
        x = event.x
        
        if self.active == "start":
            if (x >= self._xoff) and (x+self._wpad/2 < self._xe):
                self._xs = x
            self._x = self._xs
            
        elif self.active == "end":
            if (x <= self.width+self._xoff) and (x-self._wpad/2 > self._xs):
                self._xe = x
            self._x = self._xe

        self.startidx = self.x2fidx(self._xs)
        self.endidx = self.x2fidx(self._xe)
        self.idx = self.x2fidx(self._x)
        
        if (self._ondrag is not None) and (self.idx < self.fcount):
            self._ondrag()

        self.draw()

    def get_trim_range(self):
        return self.startidx, self.endidx
    
    def onapply(self):
        self.applybtn.place_forget()
        
        if self.trimvideo is not None:
            self.trimvideo(self.startidx, self.endidx)
            
        if self.loadvideo is not None:
            self.setcount(self.endidx-self.startidx)
            self.draw()
            self.loadvideo("")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.videoview = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.videoview.pack(pady=30)

        self.seekbar = CutSeekBar(self.videoview, width=600, fcount=2000, ondrag=self.ondrag,
                                  disable=False)

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
