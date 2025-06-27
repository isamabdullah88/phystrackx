import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image
from typing import Callable

class Filters:
    def __init__(self, toolbar, updateframe:Callable[[[np.ndarray]], None]):
        self.toolbar = toolbar
        self.updateframe = updateframe
        # self.vidview = vidview
        
        self.ftypes = [
            ("Gray", "assets/plugins/gray.png"),
            ("Gaussian Blur", "assets/plugins/gblur.png"),
            ("Median Blur", "assets/plugins/mblur.png"),
            ("Bilateral Filter", "assets/plugins/bfilter.png"),
            ("Canny Edge Detection", "assets/plugins/canny.png"),
        ]
        
    def spawnfilter(self, frame:np.ndarray):
        """
        Opens a popup to select a filter type and apply it to the video frame.
        """
        self.frame = frame
        
        self.fpopup = ctk.CTkToplevel(self.toolbar)
        self.fpopup.title("Select Filter")
        self.fpopup.geometry("300x200")

        self.fvar = ctk.StringVar(value=self.ftypes[0][0])  # Default to the first filter type
        
        for ftype in self.ftypes:
            radio = ctk.CTkRadioButton(self.fpopup, text=ftype[0], variable=self.fvar, value=ftype[0])
            radio.pack(pady=5)
                
            # icon = ctk.CTkImage(Image.open(ftype[1]), size=(20, 20))
            # self.radioicon(self.fpopup, icon, ftype[0], ftype[0])

        applybtn = ctk.CTkButton(self.fpopup, text="Apply", command=self.filter)
        applybtn.pack(pady=10)
        
    # def radioicon(self, frame, image, text, value):
    #     row = ctk.CTkFrame(frame)
    #     row.pack(pady=5, anchor="w")

    #     icon = ctk.CTkLabel(row, image=image, text="")
    #     icon.pack(side="left", padx=5)

    #     radio = ctk.CTkRadioButton(row, text=text, variable=self.fvar, value=value)
    #     radio.pack(side="left")
        
    def filter(self):
        """
        Applies the selected filter to the current video frame.
        """
        ftype = self.fvar.get()

        if ftype == "Gray":
            fltframe = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            fltframe = cv2.cvtColor(fltframe, cv2.COLOR_GRAY2BGR)
        elif ftype == "Gaussian Blur":
            fltframe = cv2.GaussianBlur(self.frame, (5, 5), 0)
        elif ftype == "Median Blur":
            fltframe = cv2.medianBlur(self.frame, 5)
        elif ftype == "Bilateral Filter":
            fltframe = cv2.bilateralFilter(self.frame, 9, 75, 75)
        elif ftype == "Canny Edge Detection":
            fltframe = cv2.Canny(self.frame, 100, 200)
        else:
            fltframe = self.frame

        self.updateframe(fltframe)

        self.fpopup.destroy()
        
    
    