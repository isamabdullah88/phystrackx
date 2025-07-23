# from customtkinter import CTkCanvas
from math import floor
# import customtkinter as ctk
import tkinter as tk

class Bar:
    """Implements and draws the bar of a seekbar. A vertical stick that can be dragged along a seek"""
    def __init__(self, canvas:tk.Canvas, x:float, x0:float, x1:float, y:float, fcount:int, label, callback, width=6, height=50):
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
        self.label = label
        self.callback = callback
    
    def pack(self):
        self.canvas.create_rectangle(self.x-self.whalf, self.y-self.hhalf,
                            self.x+self.whalf, self.y+self.hhalf, fill="#0ef87f", outline="")
        
        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        
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
        
        self.canvas.delete("all")
        # if not self.clicked:
        #     return
        
        if self.x0-self.whalf < x < self.x1+self.whalf:
            self.x = x
            
            # self.idx = self.x2fidx(self.x)
            # self.callback(self.label, self.idx)
        # self.canvas.coords(self.tkrect, self.x-self.whalf, self.y-self.hhalf,
        #                 self.x+self.whalf, self.y+self.hhalf)
        self.canvas.create_rectangle(self.x-self.whalf, self.y-self.hhalf,
                            self.x+self.whalf, self.y+self.hhalf, fill="#0ef87f", outline="")
            
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