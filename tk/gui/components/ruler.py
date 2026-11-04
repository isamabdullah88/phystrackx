"""
scaleruler.py

Interactive scale calibration overlay system built on top of CustomTkinter.
Enables real-world dimension mapping configurations for video frames.

Author: Isam Balghari
"""

import customtkinter as ctk
from math import floor, atan2, cos, sin, degrees, hypot, radians
from tkinter import messagebox
from typing import Dict, Any, Optional
from core.units import parse_length, unit_suffix
from core.autoruler import snap_ruler
from .dialogbox import DialogBox
from .buttons import SubmitButton
from .anglecontrol import AngleControl


class ScaleRuler:
    # Enterprise Configuration Matrix (Centralized Constants)
    RULER_TAG = "ruler"
    BUTTON_TAG = "ruler_button"  # 👈 FIXED: Isolated unique tag for the apply button
    MIN_RULER_LENGTH_PX = 10
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
        self.unit: str = ""  # Unit typed with the length, e.g. "cm" ("" when none)
        self.placed = False  # True once the user has shown the ruler
        self.view = None  # ViewTransform, set by the app so the ruler follows zoom and pan
        self.on_apply = None  # Optional callback after Apply (used to leave marking mode)
        self.on_cancel = None  # Optional callback after Cancel (used to leave marking mode)
        self.dragging: Optional[str] = None
        self.offset = [0, 0]

        # Rotation: the angle is read from the endpoints; the control writes it back
        self.theta = ctk.DoubleVar(value=0)
        self.angle = AngleControl(canvas.master, self.theta, self.on_angle_control)

        self.applybtn: Optional[ctk.CTkButton] = None
        self.btn_window_id: Optional[int] = None
        self.autobtn: Optional[ctk.CTkButton] = None
        self.undobtn: Optional[ctk.CTkButton] = None
        self._before_snap = None  # Ends before the last Auto Ruler, for Undo
        # Returns the frame being shown (BGR image in frame pixels), for Auto Ruler
        self.frame_source = None

    # ---------------------------------------------------------------------------------------------
    # Geometry helpers
    def _length(self) -> float:
        return hypot(self.p2[0] - self.p1[0], self.p2[1] - self.p1[1])

    def _midpoint(self):
        return (self.p1[0] + self.p2[0]) / 2, (self.p1[1] + self.p2[1]) / 2

    def _angle_deg(self) -> float:
        """Ruler angle in degrees. Positive is clockwise on screen, matching the axes."""
        return degrees(atan2(self.p2[1] - self.p1[1], self.p2[0] - self.p1[0]))

    def _sync_angle(self) -> None:
        self.theta.set(round(self._angle_deg(), 1))

    def _distance_to_segment(self, x: float, y: float) -> float:
        x1, y1 = self.p1
        x2, y2 = self.p2
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return hypot(x - (x1 + t * dx), y - (y1 + t * dy))

    # ---------------------------------------------------------------------------------------------
    def _picture_origin(self) -> tuple[float, float]:
        """Canvas position of the picture's top-left corner (the frame's pixel (0, 0))."""
        return self.view.origin if self.view is not None else (0, 0)

    def get_state(self) -> dict:
        """Ruler endpoints relative to the picture's top-left corner (in frame pixels), so they stay
        on the same part of the picture whatever the window size. Also the calibrated length."""
        ox, oy = self._picture_origin()
        return {"p1": [self.p1[0] - ox, self.p1[1] - oy], "p2": [self.p2[0] - ox, self.p2[1] - oy],
                "anchor": "picture", "real_world_length": self.real_world_length, "unit": self.unit,
                "canvas": [self.vwidth, self.vheight]}

    def unit_label(self) -> str:
        """The unit the measurements are in: the typed unit once calibrated, else pixels."""
        return self.unit if self.real_world_length is not None else "px"

    def shift(self, dx: float, dy: float) -> None:
        """Moves the ruler with the picture, when the picture is placed again after a resize."""
        self.p1 = [self.p1[0] + dx, self.p1[1] + dy]
        self.p2 = [self.p2[0] + dx, self.p2[1] + dy]
        if self.placed:
            self.draw()

    def set_canvas_size(self, vwidth: int, vheight: int) -> None:
        """The video area has a new size: the buttons stay in its bottom-right corner."""
        self.vwidth, self.vheight = vwidth, vheight
        for name, (x, y) in {"btn_window_id": (vwidth - 20, vheight - 20),
                             "autobtn_window_id": (vwidth - 90, vheight - 20),
                             "undobtn_window_id": (vwidth - 210, vheight - 20)}.items():
            wid = getattr(self, name, None)
            if wid is not None and self.canvas.type(wid):
                self.canvas.coords(wid, x, y)

    def restore_state(self, state: dict) -> None:
        """Re-places the ruler and its calibration. Older projects stored canvas positions, which
        are scaled if the window size has changed."""
        if state.get("anchor") == "picture":
            ox, oy = self._picture_origin()
            self.p1 = [state["p1"][0] + ox, state["p1"][1] + oy]
            self.p2 = [state["p2"][0] + ox, state["p2"][1] + oy]
        else:
            sx = self.vwidth / state["canvas"][0]
            sy = self.vheight / state["canvas"][1]
            self.p1 = [state["p1"][0] * sx, state["p1"][1] * sy]
            self.p2 = [state["p2"][0] * sx, state["p2"][1] * sy]
        self.real_world_length = state["real_world_length"]
        self.unit = state.get("unit", "")
        self.placed = True
        self._sync_angle()
        self.draw()

    def pack(self) -> None:
        """Maps canvas interaction hooks and locks outer UI layout states."""
        self.placed = True
        self._sync_angle()
        self.angle.show(before=self.canvas)
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

        # Snaps the ruler's ends to the object's ends, along its left edge
        self.autobtn = ctk.CTkButton(self.canvas, text="Auto Ruler", width=110, height=40,
                                     command=self.autosnap)
        self.autobtn_window_id = self.canvas.create_window(
            self.vwidth - 90, self.vheight - 20, window=self.autobtn, anchor="se", tags=self.BUTTON_TAG)

        # Puts the ruler back where it was before the last Auto Ruler
        self.undobtn = ctk.CTkButton(self.canvas, text="Undo", width=90, height=40,
                                     command=self.undo_autosnap, state="disabled")
        self.undobtn_window_id = self.canvas.create_window(
            self.vwidth - 210, self.vheight - 20, window=self.undobtn, anchor="se", tags=self.BUTTON_TAG)

    def undo_autosnap(self) -> None:
        """Puts the ruler's ends back to where they were before the last Auto Ruler."""
        if self._before_snap is None:
            return
        self.p1, self.p2 = [list(p) for p in self._before_snap]
        self._before_snap = None
        if self.undobtn:
            self.undobtn.configure(state="disabled")
        self._sync_angle()
        self.draw()

    def autosnap(self) -> None:
        """
        Moves the ruler's ends onto the edges of the object it lies on (see core/autoruler).

        The colour search takes a few hundredths of a second on a frame, so it runs here, on the
        UI thread, with the frame as a plain array.
        """
        image = self.frame_source() if self.frame_source else None
        if image is None:
            messagebox.showerror("Auto Ruler", "There is no picture to measure yet.")
            return
        ox, oy = self.view.origin if self.view is not None else (0, 0)
        start1 = (self.p1[0] - ox, self.p1[1] - oy)
        start2 = (self.p2[0] - ox, self.p2[1] - oy)
        half_width = self.height / 2
        try:
            q1, q2 = snap_ruler(image, start1, start2, side="left", half_width=half_width)
        except ValueError as e:
            messagebox.showerror("Auto Ruler", str(e))
            return
        self._apply_snap(q1, q2, ox, oy)

    def _apply_snap(self, q1, q2, ox: float, oy: float) -> None:
        """Moves the ends to the snapped points (frame pixels), keeping the old ones for Undo."""
        self._before_snap = ([list(self.p1), list(self.p2)])
        self.p1 = [q1[0] + ox, q1[1] + oy]
        self.p2 = [q2[0] + ox, q2[1] + oy]
        if self.undobtn:
            self.undobtn.configure(state="normal")
        self._sync_angle()
        self.draw()

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
        if self.on_apply:
            self.on_apply()

    def cancel(self) -> None:
        """Stops placing the ruler without applying it, when another tool is started. A ruler
        that was calibrated before is kept; one that was never calibrated is removed."""
        if self.applybtn is None:
            return
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.unbind("<Double-Button-1>")
        for btn in self.btnlist.values():
            btn.configure(state="normal")
        self.clear()
        if self.real_world_length is None:
            self.placed = False
        if self.on_cancel:
            self.on_cancel()

    def rotate_to(self, theta_deg: float) -> None:
        """Turns the ruler to `theta_deg` about its midpoint, keeping its length."""
        length = self._length()
        mx, my = self._midpoint()
        hx = length / 2 * cos(radians(theta_deg))
        hy = length / 2 * sin(radians(theta_deg))
        self.p1 = [mx - hx, my - hy]
        self.p2 = [mx + hx, my + hy]
        self.draw()

    def on_angle_control(self) -> None:
        """Called by the angle bar and text box."""
        self.rotate_to(self.theta.get())

    def _screen(self, p) -> tuple[float, float]:
        """Unzoomed (stored) point -> on-screen canvas point."""
        return self.view.to_canvas(p[0], p[1]) if self.view is not None else (p[0], p[1])

    def _base(self, x: float, y: float) -> tuple[float, float]:
        """On-screen canvas point -> unzoomed (stored) point."""
        return self.view.to_base(x, y) if self.view is not None else (x, y)

    def draw(self) -> None:
        """Re-renders complete scalar wire structures across pixel transforms."""
        self.canvas.delete(self.RULER_TAG)  # Now clears ONLY lines/text, keeps button safe!
        x1, y1 = self._screen(self.p1)
        x2, y2 = self._screen(self.p2)
        pixels = self._length()  # Calibration uses unzoomed frame pixels
        screen_len = hypot(x2 - x1, y2 - y1)
        if pixels == 0 or screen_len == 0:
            return

        # Unit vectors along the ruler (u) and across it, pointing "down" for a horizontal ruler (v)
        ux, uy = (x2 - x1) / screen_len, (y2 - y1) / screen_len
        vx, vy = -uy, ux
        h2 = self.height / 2

        # Wireframe Boundary Body Track
        corners = [
            x1 + vx * h2, y1 + vy * h2,
            x2 + vx * h2, y2 + vy * h2,
            x2 - vx * h2, y2 - vy * h2,
            x1 - vx * h2, y1 - vy * h2,
        ]
        self.canvas.create_polygon(*corners, fill="", outline="#000000", width=1,
                                   tags=self.RULER_TAG)

        # Segment Matrix Renders (Ticks)
        if screen_len > 50:
            for i in range(11):
                t = i / 10
                tx = x1 + (x2 - x1) * t
                ty = y1 + (y2 - y1) * t
                self.canvas.create_line(tx - 10 * vx, ty - 10 * vy, tx + 15 * vx, ty + 15 * vy,
                                        width=2, fill="black", tags=self.RULER_TAG)

        # Dynamic Value Mapping Logic (Preserves user calibration inputs over drags)
        if self.real_world_length is not None:
            self.scale = self.real_world_length / float(pixels)
            display_text = f"{self.real_world_length:.2f}{unit_suffix(self.unit)}"
        else:
            display_text = f"{self.scale * pixels:.2f}px"

        # Metric Core String Data Overlay, placed above the ruler
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(
            mx - 25 * vx, my - 25 * vy,
            text=display_text, font=self.FONT_LABEL,
            fill=self.COLOR_TEXT, tags=self.RULER_TAG
        )

        # Polished Grab Interactive Handle Elements
        for x, y in ((x1, y1), (x2, y2)):
            self.canvas.create_rectangle(
                x - self.handle_size, y - self.handle_size, x + self.handle_size, y + self.handle_size,
                fill=self.COLOR_HANDLE, outline="white", tags=self.RULER_TAG
            )

    def askscale(self) -> None:
        """Launches localized calibration parameters checking routine inputs."""
        pixels = self._length()
        if pixels == 0:
            return

        dialogbox = DialogBox(
            self.canvas, title="Scale Calibration",
            message="Enter the real-world length this ruler represents,\nwith its unit (e.g. 50 cm):",
            expected_type=str
        )
        if dialogbox.result is None:
            return
        try:
            value, unit = parse_length(dialogbox.result)
        except ValueError as e:
            messagebox.showerror("Scale Calibration", f"{e}.\nEnter a length such as 50 or 50 cm.")
            return

        self.real_world_length = value
        self.unit = unit
        self.scale = self.real_world_length / pixels
        self.draw()

    def onclick(self, event: Any) -> None:
        """Determines context target selection positions upon click events."""
        x, y = self._base(event.x, event.y)
        zoom = self.view.zoom if self.view is not None else 1.0
        tolerance = self.HIT_BOX_TOLERANCE / zoom  # Keep the grab area the same size on screen

        if hypot(x - self.p1[0], y - self.p1[1]) < tolerance:
            self.dragging = "resize1"
        elif hypot(x - self.p2[0], y - self.p2[1]) < tolerance:
            self.dragging = "resize2"
        elif self._distance_to_segment(x, y) < (self.height / 2 + 4) / zoom:
            self.dragging = "move"
            mx, my = self._midpoint()
            self.offset = [x - mx, y - my]

    def ondrag(self, event: Any) -> None:
        """Moves the grabbed end (or the whole ruler) freely. Ends never snap to each other."""
        x, y = self._base(event.x, event.y)
        if self.dragging == "resize1":
            if hypot(self.p2[0] - x, self.p2[1] - y) >= self.MIN_RULER_LENGTH_PX:
                self.p1 = [x, y]
        elif self.dragging == "resize2":
            if hypot(x - self.p1[0], y - self.p1[1]) >= self.MIN_RULER_LENGTH_PX:
                self.p2 = [x, y]
        elif self.dragging == "move":
            mx, my = self._midpoint()
            dx = x - self.offset[0] - mx
            dy = y - self.offset[1] - my
            self.p1 = [self.p1[0] + dx, self.p1[1] + dy]
            self.p2 = [self.p2[0] + dx, self.p2[1] + dy]

        self._sync_angle()
        self.draw()

    def onrelease(self, event: Any) -> None:
        """Releases track lock states safely."""
        self.dragging = None

    def clear(self) -> None:
        """Wipes layer maps cleanly out of scope registers."""
        self.canvas.delete(self.RULER_TAG)
        self.canvas.delete(self.BUTTON_TAG)  # Clear the button cleanly on completion
        self.angle.hide()
        if self.applybtn:
            self.applybtn.destroy()
            self.applybtn = None
        if self.autobtn:
            self.autobtn.destroy()
            self.autobtn = None
        if self.undobtn:
            self.undobtn.destroy()
            self.undobtn = None
        self._before_snap = None


if __name__ == "__main__":

    root = ctk.CTk()
    root.geometry("900x600")
    canvas = ctk.CTkCanvas(root, width=900, height=600)
    canvas.pack()
    ScaleRuler(canvas, 900, 600, {}, None).pack()
    root.mainloop()
