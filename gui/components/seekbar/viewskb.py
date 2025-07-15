from math import floor, ceil
import customtkinter as ctk
from .seek import Seek
from .bar import Bar

class ViewSeekBar:
    """Seekbar that is view only and act as a video viewer. It can't trim video."""
    def __init__(self, frame:ctk.CTkFrame, width, height, fcount=100, ondrag=None):
        """mode can be 'Trim' and 'View'."""
        self.canvas = ctk.CTkCanvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self.padx = 10
        self.width = width
        self.height = height
        
        self.ondrag = ondrag
        
        self.seek = None
        self.leftbar = None
        
        self.setparams()

    def setparams(self):
        self.idx = ceil(0.01*self.fcount)
        
        self.x0 = self.padx
        self.x1 = self.width - self.padx

        
        
    def callback(self, label, idx):
        self.idx = idx
        
        self.ondrag()
        
    def clear(self):
        if self.seek is not None:
            self.seek.clear()
            
        if self.leftbar is not None:
            self.leftbar.clear()

    def pack(self):
        
        self.clear()
        
        self.seek = Seek(self.canvas, self.x0, self.x1,  self.height/2)
        self.leftbar = Bar(self.canvas, self.x0, self.x1, self.height/2, self.fcount, "leftbar", self.callback)
        
        self.seek.pack()
        self.leftbar.pack()
        
        # if self.mode == "Trim":
        #     self.rightbar = Bar(self.canvas, self.x0, self.x1, self.height/2, self.fcount, "rightbar", self.callback)
        #     self.rightbar.pack()
        #     self.applybtn = self.plcbutton("assets/apply.png", self.onapply, btnsize=40)
        #     self.applybtn.place(x=self.width-60, y=self.height-60)
        # else:
        #     if self.applybtn:
        #         self.applybtn.place_forget()
        
    
    # def plcbutton(self, imgpath, command, btnsize=30):
    #     """
    #     Creates a button with an image and a command.
    #     """
    #     img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
    #     img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
    #     button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
    #                         image=img, command=command)
        
    #     button.image = img
        
    #     return button


    def set(self, fcount):
        self.fcount = fcount
        
        self.setparams()
        # self.x0 = ceil(0.01*self.width) + self.padx
        # self.x1 = floor(0.99*self.width) + self.padx
        # self.startidx = ceil(0.01*self.fcount)
        # self.endidx = floor(0.99*self.fcount)
        # self.idx = self.startidx
        # self.draw()
        # if trim:
        #     self.mode = "Trim"
        # else:
        #     self.mode = "View"
        #     self.x1 = self.width - self.padx
        
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.frame.pack(fill="both", expand=True)

        self.seekbar = ViewSeekBar(self.frame, 700, 100, fcount=100, ondrag=self.ondrag)
        self.seekbar.pack()
        
    # def print_range(self):
    #     start, end = self.seekbar.get_trim_range()
    #     print(f"Selected trim range: Frame {start} to {end}")
    
    def ondrag(self):
        print('idx: ', self.seekbar.idx)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()