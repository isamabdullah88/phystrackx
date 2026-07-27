"""
scaleruler.py

Interactive scale calibration overlay system built on top of CustomTkinter.
Enables real-world dimension mapping configurations for video frames.

Author: Isam Balghari
"""

import customtkinter as ctk
from math import floor
from typing import Dict, Any, Optional
from .dialogbox import DialogBox
from .buttons import SubmitButton


class ScaleRuler:
    # Enterprise Configuration Matrix (Centralized Constants)
    RULER_TAG = "ruler"
    BUTTON_TAG = "ruler_button"  # 👈 FIXED: Isolated unique tag for the apply button
    MIN_RULER_WIDTH_PX = 40
    HIT_BOX_TOLERANCE = 14
    COLOR_HANDLE = "#EC17C5"
    COLOR_TEXT = "white"
    FONT_LABEL = ("Arial", 12, "bold")

    def __init__(self, canvas: ctk.CTkCanvas, vwidth: int, vheight: int,
                 btnlist: Dict[str, ctk.CTkButton], activebtn: Optional[ctk.CTkButton]) -> None:
        """Initializes the ScaleRuler shell overlay framework."""
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.btnlist = btnlist
        self.activebtn = activebtn
        
        # Geometry Boundaries
        self.width_offset = 50
        self.height = 30
        self.handle_size = 6

        # Standard Initial Coordinate Anchors (Centered layout)
        center_x = floor(vwidth / 2)
        center_y = floor(vheight / 2)
        self.p1 = [center_x - self.width_offset, center_y]
        self.p2 = [center_x + self.width_offset, center_y]

        # Calibration States
        self.scale: float = 1.0
        self.real_world_length: Optional[float] = None
        self.dragging: Optional[str] = None
        self.offset = [0, 0]
        
        self.applybtn: Optional[ctk.CTkButton] = None
        self.btn_window_id: Optional[int] = None

    def pack(self) -> None:
        """Maps canvas interaction hooks and locks outer UI layout states."""
        self.draw()
        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        self.canvas.bind("<ButtonRelease-1>", self.onrelease)
        self.canvas.bind("<Double-Button-1>", self.ondclick)
        
        # Intercept and isolate UI interactions
        for btn in self.btnlist.values():
            if btn != self.activebtn:
                btn.configure(state="disabled")
        
        # Create and draw the floating validation overlay action target
        self.applybtn = SubmitButton(self.canvas, command=self.onapply, size=50,
                                     tooltip="Apply Scale")
        
        # FIXED: Assigned BUTTON_TAG to prevent canvas deletion sweeps
        self.btn_window_id = self.canvas.create_window(
            self.vwidth - 20, 
            self.vheight - 20, 
            window=self.applybtn,
            anchor="se", 
            tags=self.BUTTON_TAG
        )

    def ondclick(self, event: Any) -> None:
        """Triggers the scale parameter dialog prompts upon registration."""
        self.askscale()
        
    def onapply(self) -> None:
        """Cleans event contexts and returns global system interaction properties to normal."""
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.unbind("<Double-Button-1>")
        
        for btn in self.btnlist.values():
            btn.configure(state="normal")

        self.clear()

    def draw(self) -> None:
        """Re-renders complete scalar wire structures across pixel transforms."""
        self.canvas.delete(self.RULER_TAG)  # Now clears ONLY lines/text, keeps button safe!
        x1, y = self.p1
        x2, _ = self.p2

        # Wireframe Boundary Body Track
        self.canvas.create_rectangle(
            x1, y - self.height // 2, x2, y + self.height // 2, 
            fill="", outline="#000000", width=1, tags=self.RULER_TAG
        )

        # Segment Matrix Renders (Ticks)
        pixels = abs(x2 - x1)
        if pixels > 50:
            for i in range(11):
                tx = x1 + i * pixels / 10
                self.canvas.create_line(tx, y - 10, tx, y + 15, width=2, fill="black",
                                        tags=self.RULER_TAG)

        # Dynamic Value Mapping Logic (Preserves user calibration inputs over drags)
        if self.real_world_length is not None:
            self.scale = self.real_world_length / float(pixels) if pixels > 0 else 1.0
            display_text = f"{self.real_world_length:.2f} units"
        else:
            display_text = f"{self.scale * pixels:.2f} units"

        # Metric Core String Data Overlay
        self.canvas.create_text(
            (x1 + x2) / 2, y - 25, 
            text=display_text, font=self.FONT_LABEL, 
            fill=self.COLOR_TEXT, tags=self.RULER_TAG
        )

        # Polished Grab Interactive Handle Elements
        self.canvas.create_rectangle(
            x1 - self.handle_size, y - 10, x1 + self.handle_size, y + 10, 
            fill=self.COLOR_HANDLE, outline="white", tags=self.RULER_TAG
        )
        self.canvas.create_rectangle(
            x2 - self.handle_size, y - 10, x2 + self.handle_size, y + 10, 
            fill=self.COLOR_HANDLE, outline="white", tags=self.RULER_TAG
        )

    def askscale(self) -> None:
        """Launches localized calibration parameters checking routine inputs."""
        pixels = abs(self.p2[0] - self.p1[0])
        if pixels == 0:
            return

        dialogbox = DialogBox(
            self.canvas, title="Scale Calibration", 
            message="Enter real-world length this ruler represents:", expected_type=float
        )
        
        if dialogbox.result is not None and dialogbox.result > 0:
            self.real_world_length = float(dialogbox.result)
            self.scale = self.real_world_length / float(pixels)
            self.draw()

    def onclick(self, event: Any) -> None:
        """Determines context target selection positions upon click events."""
        x, y = event.x, event.y

        if abs(x - self.p1[0]) < self.HIT_BOX_TOLERANCE and abs(y - self.p1[1]) < self.HIT_BOX_TOLERANCE:
            self.dragging = "resize1"
        elif abs(x - self.p2[0]) < self.HIT_BOX_TOLERANCE and abs(y - self.p2[1]) < self.HIT_BOX_TOLERANCE:
            self.dragging = "resize2"
        elif min(self.p1[0], self.p2[0]) < x < max(self.p1[0], self.p2[0]) and (self.p1[1] - self.height < y < self.p1[1] + self.height):
            self.dragging = "move"
            self.offset = [x - self.p1[0], y - self.p1[1]]

    def ondrag(self, event: Any) -> None:
        """Calculates transformation translations smoothly on motion tracking."""
        if self.dragging == "resize1":
            if (self.p2[0] - event.x) > self.MIN_RULER_WIDTH_PX:
                self.p1[0] = event.x
        elif self.dragging == "resize2":
            if (event.x - self.p1[0]) > self.MIN_RULER_WIDTH_PX:
                self.p2[0] = event.x
        elif self.dragging == "move":
            dx = event.x - self.p1[0] - self.offset[0]
            dy = event.y - self.p1[1] - self.offset[1]
            
            self.p1[0] += dx
            self.p2[0] += dx
            self.p1[1] += dy
            self.p2[1] += dy
        
        self.draw()

    def onrelease(self, event: Any) -> None:
        """Releases track lock states safely."""
        self.dragging = None
        
    def clear(self) -> None:
        """Wipes layer maps cleanly out of scope registers."""
        self.canvas.delete(self.RULER_TAG)
        self.canvas.delete(self.BUTTON_TAG)  # Clear the button cleanly on completion
        if self.applybtn:
            self.applybtn.destroy()
            self.applybtn = None

            
if __name__ == "__main__":
        
    root = ctk.CTk()
    root.geometry("900x600")
    canvas = ctk.CTkCanvas(root, width=900, height=600)
    canvas.pack()
    ScaleRuler(canvas, 900, 600, {}, None).pack()
    root.mainloop()
