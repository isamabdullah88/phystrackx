import customtkinter as ctk
import cv2
from PIL import Image
from typing import Callable
from core import FilterTypes, abspath
from .slider import Slider
from .radiobox import Radiobox

class Filters:
    def __init__(self, toolbar, canvas, vwidth, vheight, updateframe:Callable, toggle:Callable):
        self.toolbar = toolbar
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.updateframe = updateframe
        self.toggle = toggle
        
        self.ftypes = FilterTypes
        self.fvar = ctk.StringVar(value=self.ftypes.NONE.name)  # Default to None
        self.bcvalue = ctk.IntVar(value=0) # Brightness and contrast value
        
        self.slider = None
        
        self.btnsize = 30
        self.applybtn = self.plcbutton("assets/apply.png", self.onapplybtn, 80)
        
    def spawnfilter(self):
        """
        Opens a popup to select a filter type and apply it to the video frame.
        """
        self.radiobox = Radiobox(self.canvas, self.vwidth, self.vheight, "Select Filter", 
            FilterTypes, self.onapply, self.onselect)
    
    
    def onselect(self):
        if self.slider:
            self.slider.destroy()
            self.slider = None
            
        filter = self.radiobox.selected.get()
        
        if filter == FilterTypes.BRIGHTNESS.name:
            self.slider = Slider(self.radiobox, 0, 100, self.onupdate)
        elif filter == FilterTypes.CONTRAST.name:
            self.slider = Slider(self.radiobox, 0, 10, self.onupdate)
            
    
    def onupdate(self, event):
        filter = self.radiobox.selected.get()
        self.fvar.set(filter)
        self.updateframe()
    
    def onapply(self, event):
        filter = self.radiobox.selected.get()
        self.fvar.set(filter)
        
        self.updateframe()
        self.radiobox.destroy()
        
        # Apply button
        self.applybtn.place(x=self.vwidth-110, y=self.vheight-100)
        
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
            fltframe = cv2.cvtColor(fltframe, cv2.COLOR_GRAY2BGR)
        elif ftype == FilterTypes.BRIGHTNESS.name:
            fltframe = cv2.convertScaleAbs(frame, alpha=1, beta=self.slider.var.get())
        elif ftype == FilterTypes.CONTRAST.name:
            fltframe = cv2.convertScaleAbs(frame, alpha=self.slider.var.get(), beta=1)
        else:
            fltframe = frame

        return fltframe
        
    
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
    
    def onapplybtn(self):
        self.applybtn.place_forget()
        # self.toggle()