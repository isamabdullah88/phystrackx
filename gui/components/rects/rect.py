from typing import Tuple
from dataclasses import dataclass

import customtkinter as ctk
import tkinter as tk
from core import PixelRect, NormalizedRect
from .label import Labels
from ..buttons import SubmitButton, BinButton


@dataclass
class BoundingBox:
    """Encapsulates canvas graphical ID and spatial coordinates in one place."""
    tkrect: int
    pixelrect: PixelRect
    normrect: NormalizedRect


class Rect:
    """Manages interactive bounding-box drawing, canvas styling, and coordinates."""
    OUTLINE_DRAWING = "red"
    OUTLINE_PENDING = "magenta"
    OUTLINE_APPLIED = "#2ecc71"
    LINE_WIDTH = 2
    BIN_BUTTON_SIZE = 30
    APPLY_BUTTON_SIZE = 50

    def __init__(self, canvas, vwidth, vheight, button_list, active_button):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self._rcoords = None
        self._ctkbox = 0
        # self.rects = []
        # self.pixelrects = []
        # self._ctkrects = []
        self.boxes: list[BoundingBox] = []
        
        self.labels = Labels(self.canvas)

        self.bin_button = BinButton(self.canvas, command=self.clearrect, size=self.BIN_BUTTON_SIZE,
                                tooltip="Delete Last Rect")
        
        self.apply_button = SubmitButton(self.canvas, command=self.onapply, size=self.APPLY_BUTTON_SIZE,
                                     tooltip="Apply Rects")
        
        self.button_list = button_list
        self.active_button = active_button
        
    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self.boxes:
            box = self.boxes.pop()
            self.canvas.delete(box.tkrect)
            if self.boxes:
                self.bin_button.pack(anchor=tk.N, pady=50)
            else:
                self.bin_button.pack_forget()
                
    # def cleartkrects(self):
    #     """Deletes all drawn rectangles"""
    #     for box in self.boxes:
    #         self.canvas.delete(box.tkrect)
        
    #     self.boxes.clear()

        
    def clear(self):
        self.labels.clear()
        self.labels.destroy()
    
        # self.cleartkrects()
        # self.pixelrects.clear()
        # self.rects.clear()
        self.boxes.clear()
    
    def drawrect(self, fwidth, fheight, fx, fy):
        """Draws rectangle with simple lines"""
        # Disable other buttons
        for k,btn in self.button_list.items():
            if btn != self.active_button:
                btn.configure(state="disabled")
                
        if fwidth is None:
            fwidth = self.vwidth
        if fheight is None:
            fheight = self.vheight
        
        def ondown(event):           
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline=self.OUTLINE_DRAWING, width=self.LINE_WIDTH)
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            self.canvas.coords(self._ctkbox, sx, sy, ex, ey)
            
        def onrelease(event):
            self.canvas.itemconfig(self._ctkbox, outline=self.OUTLINE_PENDING)
            
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            
            self.apply_button.pack(side=tk.BOTTOM, anchor=tk.E, padx=10, pady=10)
            self.bin_button.pack(anchor=tk.N, pady=10)

            # Storing rectangle details
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            xmin = min(sx, ex) - fx
            ymin = min(sy, ey) - fy
            width = abs(ex - sx)
            height = abs(ey - sy)
            prect = PixelRect(xmin, ymin, width, height)
            nrect = prect.pix2norm(fwidth, fheight)

            self.boxes.append(BoundingBox(self._ctkbox, prect, nrect))

        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", inrect)
        self.canvas.bind("<ButtonRelease-1>", onrelease)
        
    def onapply(self):
        """Finalize rects and colors on apply"""
        for box in self.boxes:
            print("Box: ", box)
            print(f"Box: tkrect {box.tkrect}, Pixel: {box.pixelrect}, Normalized: {box.normrect}")
            self.canvas.itemconfig(box.tkrect, outline=self.OUTLINE_APPLIED, width=self.LINE_WIDTH)

        self.bin_button.pack_forget()
        self.apply_button.pack_forget()

        self.labels.pack(side=tk.TOP, anchor=tk.NW, padx=10, pady=60)
        self.labels.add_labels([box.pixelrect for box in self.boxes], color=self.OUTLINE_APPLIED)
        
        # Activate all buttons
        for k,btn in self.button_list.items():
            btn.configure(state="normal")



# =====================================================================
# Main Testing Function
# =====================================================================

def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Testing Interactive Rect Selection")
    root.geometry("850x600")

    # 1. Top Control Toolbar
    toolbar = ctk.CTkFrame(root, height=50)
    toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))

    btn_dict = {}

    btn_draw = ctk.CTkButton(toolbar, text="Draw Rectangle", width=130)
    btn_draw.pack(side=tk.LEFT, padx=5, pady=5)
    btn_dict["draw"] = btn_draw

    btn_other = ctk.CTkButton(toolbar, text="Other Action (Test Lock)", width=160)
    btn_other.pack(side=tk.LEFT, padx=5, pady=5)
    btn_dict["other"] = btn_other

    btn_clear_all = ctk.CTkButton(
        toolbar,
        text="Clear All",
        fg_color="#e03131",
        hover_color="#c92a2a",
        width=100
    )
    btn_clear_all.pack(side=tk.RIGHT, padx=5, pady=5)

    # 2. Canvas Area
    canvas_width, canvas_height = 800, 500
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="#1e1e1e", highlightthickness=0)
    canvas.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 3. Instantiate Rect Tool
    rect_tool = Rect(
        canvas=canvas,
        vwidth=canvas_width,
        vheight=canvas_height,
        button_list=btn_dict,
        active_button=btn_draw
    )

    # 4. Attach Callbacks
    btn_draw.configure(command=lambda: rect_tool.drawrect(canvas_width, canvas_height, 0, 0))
    btn_clear_all.configure(command=rect_tool.clear)

    root.mainloop()


if __name__ == "__main__":
    main()