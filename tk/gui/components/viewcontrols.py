"""
viewcontrols.py

Strip below the video with zoom, X/Y scrollers (to pan a zoomed view), and the shape choice for
the next object drawn (rectangle or circle).

Author: Isam Balghari
"""

from tkinter import ttk
import customtkinter as ctk
from .view import ViewTransform


class ViewControls:
    SHAPE_VALUES = {"Rectangle": "rect", "Circle": "circle"}

    def __init__(self, parent, view: ViewTransform, on_change, on_shape) -> None:
        """
        Args:
            parent: Widget to place the strip in.
            view (ViewTransform): The view being controlled.
            on_change (callable): Called after zoom or pan changes.
            on_shape (callable): Called with "rect" or "circle" when the shape changes.
        """
        self.view = view
        self.on_change = on_change
        self.on_shape = on_shape
        self.zoomvar = ctk.DoubleVar(value=1.0)
        self.xvar = ctk.DoubleVar(value=0.0)
        self.yvar = ctk.DoubleVar(value=0.0)

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")

        # Dark text: the strip sits on the cyan background
        ctk.CTkLabel(self.frame, text="Zoom", font=("Arial", 14, "bold"), text_color="black").pack(
            side="left", padx=5)
        ttk.Scale(self.frame, from_=1, to=ViewTransform.MAX_ZOOM, orient="horizontal",
                  variable=self.zoomvar, command=self._on_zoom, length=180).pack(side="left", padx=5)

        ctk.CTkLabel(self.frame, text="X", font=("Arial", 14, "bold"), text_color="black").pack(
            side="left", padx=(12, 2))
        ttk.Scale(self.frame, from_=0, to=1, orient="horizontal", variable=self.xvar,
                  command=self._on_pan, length=180).pack(side="left", padx=5)

        ctk.CTkLabel(self.frame, text="Y", font=("Arial", 14, "bold"), text_color="black").pack(
            side="left", padx=(12, 2))
        ttk.Scale(self.frame, from_=0, to=1, orient="horizontal", variable=self.yvar,
                  command=self._on_pan, length=180).pack(side="left", padx=5)

        ctk.CTkButton(self.frame, text="Reset View", width=90, command=self.reset).pack(
            side="left", padx=10)

        self.shape_switch = ctk.CTkSegmentedButton(self.frame, values=list(self.SHAPE_VALUES),
                                                   command=self._on_shape_change)
        self.shape_switch.set("Rectangle")
        self.shape_switch.pack(side="left", padx=10)

        self.sync()

    def show(self, before, with_shape: bool = True) -> None:
        """Shows the strip just above `before` (below the video). The shape choice is only
        relevant when marking objects, so it can be hidden for axes and scale."""
        if with_shape:
            self.shape_switch.pack(side="left", padx=10)
        else:
            self.shape_switch.pack_forget()
        self.frame.pack(side="bottom", fill="x", before=before, pady=5)

    def hide(self) -> None:
        self.frame.pack_forget()

    def shape(self) -> str:
        return self.SHAPE_VALUES[self.shape_switch.get()]

    def sync(self) -> None:
        """Copies the view's zoom and pan into the controls."""
        self.zoomvar.set(self.view.zoom)
        fx, fy = self.view.fractions()
        self.xvar.set(fx)
        self.yvar.set(fy)

    def reset(self) -> None:
        self.view.reset()
        self.sync()
        self.on_change()

    def _on_zoom(self, _value=None) -> None:
        self.view.set_zoom(self.zoomvar.get())
        self.sync()
        self.on_change()

    def _on_pan(self, _value=None) -> None:
        self.view.set_fraction(self.xvar.get(), self.yvar.get())
        self.on_change()

    def _on_shape_change(self, _value=None) -> None:
        self.on_shape(self.shape())
