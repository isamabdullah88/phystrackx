"""
togglebutton.py

A CustomTkinter-based toggle button with customizable ON/OFF callbacks and image states.

Author: [Isam Balghari]
"""

from typing import Callable, Optional
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from core import abspath


class ToggleButton(ctk.CTkButton):
    """
    A toggle button that switches between ON and OFF states with custom image icons
    and user-defined callback functions.
    """

    def __init__(
        self,
        master: tk.Widget,
        commandon: Optional[Callable[[], None]] = None,
        commandoff: Optional[Callable[[], None]] = None,
        width: int = 40,
        height: int = 40,
        **kwargs
    ) -> None:
        """
        Initialize the toggle button.

        Args:
            master: The parent widget.
            commandon: Callback when toggled ON.
            commandoff: Callback when toggled OFF.
            width: Width of the button.
            height: Height of the button.
            **kwargs: Additional arguments passed to CTkButton.
        """
        super().__init__(master, **kwargs)

        self.imgon = ctk.CTkImage(
            dark_image=Image.open(abspath("assets/switch-on.png")),
            size=(50, 20)
        )
        self.imgoff = ctk.CTkImage(
            dark_image=Image.open(abspath("assets/switch-off.png")),
            size=(50, 20)
        )

        self.commandon = commandon
        self.commandoff = commandoff
        self.ison = True

        self.configure(
            image=self.imgon,
            text="",
            width=width,
            height=height,
            command=self.toggle
        )

    def toggle(self) -> None:
        """
        Toggle the button state and call the corresponding callback.
        """
        self.ison = not self.ison
        self.configure(image=self.imgon if self.ison else self.imgoff)

        if self.ison and self.commandon:
            self.commandon()
        elif not self.ison and self.commandoff:
            self.commandoff()


if __name__ == "__main__":
    def on_toggle() -> None:
        print("Switched ON")

    def off_toggle() -> None:
        print("Switched OFF")

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("300x200")
    root.title("CustomTkinter Toggle Button")

    toggle = ToggleButton(
        root,
        commandon=on_toggle,
        commandoff=off_toggle
    )
    toggle.pack(pady=50)

    root.mainloop()
