from typing import Callable
import customtkinter as ctk
from ..buttons import ToggleButton, BinButton

class Label(ctk.CTkFrame):
    """Container frame holding the toggle button and the list of labels."""
    BIN_BUTTON_SIZE = 30  # Size of the bin button in pixels

    def __init__(self, parent, toggleon: Callable, toggleoff: Callable, **kwargs):
        kwargs.setdefault("fg_color", ("#ffffff", "#2b2b2b"))
        kwargs.setdefault("corner_radius", 6)
        super().__init__(parent, **kwargs)

        # --- Top Header with ToggleButton ---
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(side="top", fill="x", padx=6, pady=4)

        self.title = ctk.CTkLabel(self.header, text="Tracked Points",
                                        font=("Segoe UI", 14, "bold"))
        self.title.pack(side="left", padx=4)

        # Toggle button wired to expand/collapse callbacks
        self.toggleon = toggleon
        self.toggleoff = toggleoff
        self.tbutton = ToggleButton(self.header, commandon=self.toggleon, commandoff=self.toggleoff)
        self.tbutton.pack(side="right", padx=4)