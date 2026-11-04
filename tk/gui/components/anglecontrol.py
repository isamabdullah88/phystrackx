"""
anglecontrol.py

Shared rotation control: a labeled angle bar, a text box for exact angles, and a Reset button.
Used by the axes and scale tools.

Author: Isam Balghari
"""

from tkinter import ttk
import customtkinter as ctk


class AngleControl:
    """Angle bar with exact-value entry. Positive angles are clockwise on screen."""

    def __init__(self, parent, variable: ctk.DoubleVar, on_change, span: float = 30,
                 length: int = 500) -> None:
        """
        Args:
            parent: Widget to place the control in.
            variable (DoubleVar): Holds the angle in degrees.
            on_change (callable): Called with no arguments after the angle is changed by the user.
            span (float): The bar covers -span to +span. Typed values can go to +/-180.
            length (int): Bar length in pixels.
        """
        self.variable = variable
        self.on_change = on_change
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")

        ctk.CTkLabel(self.frame, text="Rotation (°)", font=("Arial", 14, "bold"), text_color="black").pack(
            side="left", padx=10)

        # Left of the middle rotates counterclockwise, right rotates clockwise
        self.slider = ttk.Scale(self.frame, from_=-span, to=span, orient="horizontal",
                                variable=variable, command=self._on_slider, length=length)
        self.slider.pack(side="left", padx=5)

        self.entry = ctk.CTkEntry(self.frame, width=70, justify="center")
        self.entry.pack(side="left", padx=5)
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)

        ctk.CTkButton(self.frame, text="Reset", width=60, command=self.reset).pack(
            side="left", padx=5)

        self.sync()

    def show(self, before) -> None:
        """Shows the control in a strip just above `before` (keeps it off the image)."""
        self.frame.pack(side="bottom", fill="x", before=before, pady=5)

    def hide(self) -> None:
        self.frame.pack_forget()

    def sync(self) -> None:
        """Show the current angle in the text box."""
        self.entry.delete(0, "end")
        self.entry.insert(0, f"{self.variable.get():.1f}")

    def reset(self) -> None:
        """Snap the picker and the angle back to the middle (0 degrees)."""
        self.variable.set(0)
        self.sync()
        self.on_change()

    def _on_slider(self, _value=None) -> None:
        self.sync()
        self.on_change()

    def _on_entry(self, _event=None) -> None:
        """Apply a typed angle. Invalid input restores the current angle."""
        try:
            value = float(self.entry.get())
        except ValueError:
            self.sync()
            return
        self.variable.set(min(max(value, -180.0), 180.0))
        self.sync()
        self.on_change()
