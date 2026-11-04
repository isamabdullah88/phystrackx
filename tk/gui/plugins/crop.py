from typing import Callable
import logging
import customtkinter as ctk
from core import PixelRect
from math import floor
from gui.components.buttons import SubmitButton, BinButton

class Crop:
    def __init__(self, canvas, vwidth, vheight, updateframe:Callable):

        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.fwidth = vwidth
        self.fheight = vheight
        self.cropwidth = vwidth
        self.cropheight = vheight

        # self.setsize : Callable = None
        self.updateframe = updateframe
        # self.toggle = toggle

        self.fx = self.fy = 0
        self.cropx = self.cropy = 0
        self.sx = self.sy = 0
        self._ctkbox = None
        self._drawing = False  # True from Crop Region until the crop is applied or cancelled
        self.croprect = None
        self.on_apply = None  # Optional callback after a crop is applied

        # A applied crop (or a trim made with one) is shown upscaled to fit the view.
        # While a new crop is being drawn the full frame is shown at its own size.
        self.fitted = False
        self.fit = 1.0

        self.btnsize = 30
        self.apply_button = SubmitButton(self.canvas, command=self.apply, size=50)
        self.bin_button = BinButton(self.canvas, command=self.clearrect, size=self.btnsize)

        self.logger = logging.getLogger(__name__)

    def _fit_scale(self, w: float, h: float) -> float:
        """Scale that makes a w x h picture fill the view as far as its ratio allows."""
        if not self.fitted or w <= 0 or h <= 0:
            return 1.0
        return min(self.vwidth / w, self.vheight / h)

    def _place(self) -> None:
        """Works out the fit and where the picture sits, centred in the view."""
        self.fit = self._fit_scale(self.cropwidth, self.cropheight)
        self.cropx = floor(self.vwidth / 2 - self.cropwidth * self.fit / 2)
        self.cropy = floor(self.vheight / 2 - self.cropheight * self.fit / 2)
        # Full-frame placement at 1:1, used while drawing a new crop
        self.fx = floor(self.vwidth / 2 - self.fwidth / 2)
        self.fy = floor(self.vheight / 2 - self.fheight / 2)

    def relayout(self, vwidth: int, vheight: int) -> None:
        """The video area has a new size: the picture is placed again and fitted to it. A crop not
        being drawn is always fitted; the full frame is fitted too, so it fills a larger window."""
        self.vwidth, self.vheight = vwidth, vheight
        self.fitted = not self._drawing
        self._place()

    def set(self, fwidth:int = 0, fheight:int = 0):
        if self.croprect is not None:
            self.logger.info("Crop rectangle exists. Ignoring new dimensions and using existing.")
            self.cropwidth = self.croprect.width
            self.cropheight = self.croprect.height
            self._place()
            return

        if fwidth > 0 and fheight > 0:
            self.logger.info(f"Setting crop dimensions to: width={fwidth}, height={fheight}")
            self.fwidth = fwidth
            self.fheight = fheight
            self.cropwidth = fwidth
            self.cropheight = fheight
        self._place()

    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self._ctkbox is not None:
            self.canvas.delete(self._ctkbox)
            self.bin_button.pack_forget()

    def clear(self):
        self.croprect = None
        self.fitted = False
        self.cropwidth = self.fwidth
        self.cropheight = self.fheight
        self._place()

    def drawrect(self, setsize:Callable):
        """Draws rectangle with simple lines"""
        self.setsize = setsize

        # Drawing starts from the full frame at its own size, so the new crop is measured on it
        self.croprect = None
        self.fitted = False
        self.cropwidth = self.fwidth
        self.cropheight = self.fheight
        self._place()
        self.updateframe()

        def ondown(event):
            self.sx, self.sy = (event.x, event.y)

            self._ctkbox = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red")

        def inrect(event):
            ex, ey = (event.x, event.y)

            self.canvas.coords(self._ctkbox, self.sx, self.sy, ex, ey)

        def onrelease(event):
            ex, ey = (event.x, event.y)

            self.canvas.itemconfig(self._ctkbox, outline="green")

            self.cropwidth = ex - self.sx
            self.cropheight = ey - self.sy

            self.croprect = PixelRect(self.sx-self.fx, self.sy-self.fy, self.cropwidth, self.cropheight)

            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")

            self.bin_button.pack(anchor=ctk.N, pady=50)
            self.apply_button.pack(side="right", padx=10, pady=10, anchor="se")

        self._drawing = True
        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", inrect)
        self.canvas.bind("<ButtonRelease-1>", onrelease)

    def cancel(self):
        """Another tool was started: a crop that is not applied yet is dropped, so the frame is
        back to the full size, as before Crop Region."""
        if not self._drawing:
            return
        self._drawing = False
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.clearrect()
        self.bin_button.pack_forget()
        self.apply_button.pack_forget()
        self.clear()
        self.updateframe()
        if self.on_apply:
            self.on_apply()

    def apply(self):
        self._drawing = False
        self.clearrect()

        self.logger.info(f"Applying crop | Crop width: {self.cropwidth}, Crop height: {self.cropheight}")
        self.fitted = True
        self.set()
        self.updateframe()

        self.bin_button.pack_forget()
        self.apply_button.pack_forget()

        if self.on_apply:
            self.on_apply()


    def apply_crop(self, frame):
        if self.croprect is None:
            return frame

        cframe = frame[self.croprect.ymin:self.croprect.ymax, self.croprect.xmin:self.croprect.xmax]

        return cframe
