"""
phystrackx.py

Entry point for launching the PhysTrackX GUI application.

Author: Isam Balghari
"""

import customtkinter as ctk
from gui.menu import MenuScreen
from core import setup_logging


class GUI:
    """Main GUI launcher for PhysTrackX."""

    def __init__(self) -> None:
        self.width = 1280
        self.height = 720  # Corrected typo 'hegiht'

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

    def start(self) -> None:
        """Initializes and starts the main GUI loop."""
        root = ctk.CTk()
        root.geometry(f"{self.width}x{self.height}")
        MenuScreen(root)
        root.mainloop()


def main() -> None:
    """Runs the PhysTrackX GUI application."""
    setup_logging()
    program = GUI()
    program.start()


if __name__ == "__main__":
    main()
