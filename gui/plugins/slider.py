import customtkinter as ctk
from tkinter import ttk

class Slider:
    def __init__(self, canvas, start=0, end=100, callback=None):
        self.canvas = canvas
        self.start = start
        self.end = end
        self.callback = callback
        
        self.var = ctk.IntVar(value=self.start)
        self.slider = ttk.Scale(self.canvas, from_=self.start, to=self.end, orient='horizontal', variable=self.var, command=self.callback)
        self.slider.pack(side="bottom", pady=10)
        
        
    def destroy(self):
        self.slider.destroy()