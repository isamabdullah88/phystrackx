import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image
from typing import Callable
from core import FilterTypes

class Filters:
    def __init__(self, toolbar, updateframe:Callable[[[np.ndarray]], None]):
        self.toolbar = toolbar
        self.updateframe = updateframe
        
        self.ftypes = FilterTypes
        self.fvar = ctk.StringVar(value=self.ftypes.NONE.name)  # Default to None
        
    def spawnfilter(self):
        """
        Opens a popup to select a filter type and apply it to the video frame.
        """        
        self.fpopup = ctk.CTkToplevel(self.toolbar)
        self.fpopup.title("Select Filter")
        self.fpopup.geometry("250x300")

        
        for ftype in self.ftypes:
            radio = ctk.CTkRadioButton(self.fpopup, text=ftype.label, variable=self.fvar, value=ftype.name)
            radio.pack(pady=5)

        applybtn = ctk.CTkButton(self.fpopup, text="Apply", command=self.filter)
        applybtn.pack(pady=10)
        
    def filter(self):
        self.fpopup.destroy()
        self.updateframe()
        
        
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
        else:
            fltframe = frame

        return fltframe
        
    
    