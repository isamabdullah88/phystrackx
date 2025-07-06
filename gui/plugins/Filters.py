import customtkinter as ctk
from tkinter import ttk
import cv2
import numpy as np
from typing import Callable
from core import FilterTypes
from gui.components import Radiobox, Slider

class Filters:
    def __init__(self, toolbar, canvas, vwidth, vheight, updateframe:Callable):
        self.toolbar = toolbar
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.updateframe = updateframe
        
        self.ftypes = FilterTypes
        self.fvar = ctk.StringVar(value=self.ftypes.NONE.name)  # Default to None
        self.bcvalue = ctk.IntVar(value=0) # Brightness and contrast value
        
        self.slider = None
        
    def spawnfilter(self):
        """
        Opens a popup to select a filter type and apply it to the video frame.
        """
        self.radiobox = Radiobox(self.canvas, self.vwidth, self.vheight, "Select Filter", 
            FilterTypes, self.onapply, self.onselect) #[FilterTypes.BRIGHTNESS.name, FilterTypes.CONTRAST.name])
        # self.fpopup = ctk.CTkToplevel(self.toolbar)
        # self.fpopup.title("Select Filter")
        # self.fpopup.geometry("250x300")

        
        # for ftype in self.ftypes:
        #     radio = ctk.CTkRadioButton(self.fpopup, text=ftype.label, variable=self.fvar, value=ftype.name, command=self.onselect)
        #     radio.pack(pady=5)

        # applybtn = ctk.CTkButton(self.fpopup, text="Apply", command=self.filter)
        # applybtn.pack(pady=10)
    
    
    def onselect(self):
        if self.slider:
            self.slider.destroy()
            self.slider = None
            
        filter = self.radiobox.selected.get()
        # print('filter: ', filter)
        if filter == FilterTypes.BRIGHTNESS.name:
            # self.slider = ttk.Scale(self.canvas, from_=1, to=100, orient='horizontal', variable=self.bcvalue, command=lambda: self.bcupdate(filter))
            # self.canvas.create_window(self.vwidth - 60, self.vheight - 20, window=self.slider)
            self.slider = Slider(self.radiobox, 0, 100, self.onupdate)
            
        
        elif filter == FilterTypes.CONTRAST.name:
            # self.slider = ttk.Scale(self.canvas, from_=1, to=10, orient='horizontal', variable=self.bcvalue, command=lambda: self.bcupdate(filter))
            # self.canvas.create_window(self.vwidth - 60, self.vheight - 20, window=self.slider)
            self.slider = Slider(self.radiobox, 0, 10, self.onupdate)
            
    
    def onupdate(self, event):
        filter = self.radiobox.selected.get()
        self.fvar.set(filter)
        self.updateframe()
    
    def onapply(self, event):
        filter = self.radiobox.selected.get()
        print('filter: ', filter)
        self.fvar.set(filter)
        
        # print('alpha/beta: ', self.slider.var.get())
        # if self.slider:
        #     self.slider.destroy()
        # self.fpopup.destroy()
        self.updateframe()
        self.radiobox.destroy()
        
    def clear(self):
        self.fvar.set(FilterTypes.NONE.name)
        
        
    def appfilter(self, frame):
        """
        Applies the selected filter to the current video frame.
        """
        ftype = self.fvar.get()

        if ftype == FilterTypes.MONOCHROME.name:
            fltframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fltframe = cv2.cvtColor(fltframe, cv2.COLOR_GRAY2BGR)
        elif ftype == FilterTypes.GAUSSIANBLUR.name:
            fltframe = cv2.GaussianBlur(frame, (5, 5), 0)
        elif ftype == FilterTypes.MEDIANBLUR.name:
            fltframe = cv2.medianBlur(frame, 5)
        elif ftype == FilterTypes.BILATERALFILTER.name:
            fltframe = cv2.bilateralFilter(frame, 9, 75, 75)
        elif ftype == FilterTypes.CANNYEDGE.name:
            fltframe = cv2.Canny(frame, 100, 200)
        elif ftype == FilterTypes.BRIGHTNESS.name:
            fltframe = cv2.convertScaleAbs(frame, alpha=1, beta=self.slider.var.get())
        elif ftype == FilterTypes.CONTRAST.name:
            fltframe = cv2.convertScaleAbs(frame, alpha=self.slider.var.get(), beta=1)
        else:
            fltframe = frame

        return fltframe
        
    
    