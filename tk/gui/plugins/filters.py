import customtkinter as ctk
import cv2
from PIL import Image
from typing import Callable
from core import FilterTypes, abspath
from .slider import Slider
from .radiobox import Radiobox


def filter_frame(frame, ftype: str, value: float = 0):
    """Applies the filter named `ftype` to a frame. Takes plain values only, so it is safe to call
    from any thread. `value` is the brightness offset or the contrast factor."""
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
        fltframe = cv2.convertScaleAbs(frame, alpha=1, beta=value)
    elif ftype == FilterTypes.CONTRAST.name:
        fltframe = cv2.convertScaleAbs(frame, alpha=value, beta=1)
    else:
        fltframe = frame
    return fltframe


class FrozenFilter:
    """
    The filter chosen when a worker started, held as plain values. Tk variables may only be read on
    the UI thread: reading them from the tracking thread crashes Tk (a segmentation fault, at
    random). Workers take this snapshot instead of the live Filters plugin.
    """

    def __init__(self, ftype: str, value: float) -> None:
        self.ftype = ftype
        self.value = value

    def apply_filter(self, frame):
        return filter_frame(frame, self.ftype, self.value)


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
        
    def clear(self):
        self.fvar.set(FilterTypes.NONE.name)
        
        
    def _value(self, ftype: str) -> float:
        """The slider's value for brightness or contrast (a neutral value if there is no slider)."""
        if self.slider is not None:
            try:
                return self.slider.var.get()
            except Exception:  # The slider's window was closed
                pass
        return 1 if ftype == FilterTypes.CONTRAST.name else 0

    def apply_filter(self, frame):
        """
        Applies the selected filter to the current video frame. UI thread only (reads Tk
        variables); worker threads use snapshot().
        """
        ftype = self.fvar.get()
        return filter_frame(frame, ftype, self._value(ftype))

    def snapshot(self) -> FrozenFilter:
        """The current filter as plain values, for a worker thread. Call on the UI thread."""
        ftype = self.fvar.get()
        return FrozenFilter(ftype, self._value(ftype))