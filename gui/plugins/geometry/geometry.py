"""
Geometry plugin for PhysTrackX.

Modular architecture separating UI overlay, geometry state management,
and interactive canvas controllers.
"""

from typing import Dict, Optional
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab

from .geometry_manager import GeometryManager
from .geometry_toolbar import GeometryToolbar
from .triangle import Triangle
from .point import Point

class Geometry:
    """Main plugin controller handling canvas interactions and coordinating UI & Model."""

    def __init__(self, canvas: ctk.CTkCanvas, vwidth: int, vheight: int, 
                 button_list: Optional[Dict[str, ctk.CTkButton]] = None,
                 active_button: Optional[ctk.CTkButton] = None
    ):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.button_list = button_list or {}
        self.active_button = active_button

        self.model = GeometryManager()
        self.active_triangle: Optional[Triangle] = Triangle(self.canvas)

        # Wire up Toolbar callbacks
        actions = {
            "angle": self._on_angle,
            "distance": self._on_distance,
            "delete": self._on_delete,
            "screenshot": self._on_screenshot,
            "exit": self.onexit,
            "hide": lambda: self.model.set_visibility(False),
            "unhide": lambda: self.model.set_visibility(True),
        }
        self.toolbar = GeometryToolbar(self.canvas, actions)

    def set_scale(self, scale: float) -> None:
        self.model.scale = scale

    def pack(self) -> None:
        """Enables interactive mode."""
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_drag)
        self.canvas.config(cursor="crosshair")
        self._set_external_toolbar_state(disabled=True)

    def _on_click(self, event: tk.Event) -> None:
        point = Point(event.x, event.y)

        # In-progress triangle creation
        if self.active_triangle and not self.active_triangle.complete:
            self.active_triangle.addpoint(point)
            if self.active_triangle.complete:
                self.model.add_triangle(self.active_triangle)
                self.active_triangle = None
                self.toolbar.show()
            return

        # Hit-testing existing shapes
        found, hit_triangle = self.model.hit_test(point)
        if found and hit_triangle:
            hit_triangle.select()
        else:
            self.active_triangle = Triangle(self.canvas)
            self.active_triangle.addpoint(point)

    def _on_drag(self, event: tk.Event) -> None:
        if self.active_triangle and not self.active_triangle.complete:
            self.active_triangle.ondrag(event)

    # ---------------- Tool Actions ----------------

    def _on_angle(self) -> None:
        if not self.model.compute_angles():
            messagebox.showerror("Error", "No triangles selected. Please select at least one triangle.")

    def _on_distance(self) -> None:
        if not self.model.compute_distances():
            messagebox.showerror("Error", "No triangles selected. Please select at least one triangle.")

    def _on_delete(self) -> None:
        if not self.model.delete_selected():
            messagebox.showerror("Error", "No triangles selected. Please select at least one triangle.")
            return

        if not self.model.triangles:
            self.toolbar.hide()

    def _on_screenshot(self) -> None:
        filepath = ctk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if not filepath:
            return

        self.canvas.update()
        x, y = self.canvas.winfo_rootx(), self.canvas.winfo_rooty()
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()

        try:
            ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(filepath)
            messagebox.showinfo("Success", "Screenshot saved successfully.")
        except Exception as err:
            messagebox.showerror("Error", f"Failed to save screenshot:\n{err}")

    def onexit(self) -> None:
        self.toolbar.hide()
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<Motion>")
        self.canvas.config(cursor="arrow")
        self._set_external_toolbar_state(disabled=False)

    def reset(self) -> None:
        self.model.clear()
        if self.active_triangle:
            self.active_triangle.delete()
        self.active_triangle = Triangle(self.canvas)
        self.toolbar.hide()

    def _set_external_toolbar_state(self, disabled: bool) -> None:
        state = "disabled" if disabled else "normal"
        for btn in self.button_list.values():
            if btn != self.active_button:
                btn.configure(state=state)