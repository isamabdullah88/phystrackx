
from typing import Dict, Callable
import customtkinter as ctk

from gui.components.buttons import (
    AngleButton,
    DistanceButton,
    ScreenshotButton,
    ExitButton,
    BinButton,
    ToggleButton
)

class GeometryToolbar:
    """Floating UI panel holding geometric action buttons."""

    def __init__(self, parent_canvas: ctk.CTkCanvas, actions: Dict[str, Callable]):
        self.canvas = parent_canvas

        # Toggle Button (show/hide primitives)
        self.toggle_button = ToggleButton(self.canvas, commandon=actions["unhide"],
                                       commandoff=actions["hide"])

        # Side Action Panel
        self.panel = ctk.CTkFrame(self.canvas, width=60, fg_color="teal", corner_radius=6)

        # Action Buttons
        self.toggle_button = ToggleButton(self.panel, commandon=actions["unhide"],
                                       commandoff=actions["hide"])
        self.angle_button = AngleButton(self.panel, actions["angle"], 40)
        self.dist_button = DistanceButton(self.panel, actions["distance"], 40)
        self.del_button = BinButton(self.panel, actions["delete"], 40)
        self.shot_button = ScreenshotButton(self.panel, actions["screenshot"], 40)
        self.exit_button = ExitButton(self.panel, actions["exit"], 40)

        for button in (self.toggle_button, self.angle_button, self.dist_button, self.del_button,
                       self.shot_button, self.exit_button):
            button.pack(padx=8, pady=6)

    def show(self) -> None:
        self.panel.place(relx=0.98, rely=0.5, anchor="e")

    def hide(self) -> None:
        self.panel.place_forget()