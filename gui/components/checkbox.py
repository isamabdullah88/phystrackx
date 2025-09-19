"""
checkbox.py

Implements a modal checkbox window using customtkinter for selecting Enum-based options.

Author: Isam Balghari
"""

from enum import Enum
import customtkinter as ctk


class Checkbox(ctk.CTkToplevel):
    """
    A modal popup that displays checkboxes for each Enum option
    and passes selected options to a callback on confirmation.
    """
    def __init__(self, parent: ctk.CTk, options: Enum, text="Choose", callback=None):
        super().__init__(parent)
        self.title("Select Options")
        self.geometry("480x280")
        self.resizable(False, False)
        self.grab_set()  # Modal popup

        self.callback = callback
        self.optionsvar = {}

        ctk.CTkLabel(
            self, text=text, font=("Segoe UI", 18, "bold")
        ).pack(pady=(15, 5))

        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(padx=20, pady=10)

        self._populate_options(options)

        ctk.CTkButton(self, text="✓ Apply", command=self.onapply,
                      width=120).pack(pady=15)

    def _populate_options(self, options: Enum, cols: int = 3):
        """
        Add Enum options as checkboxes in a grid layout.
        """
        for idx, option in enumerate(options):
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(self.grid_frame, text=option.name, variable=var)
            row, col = divmod(idx, cols)
            cb.grid(row=row, column=col, padx=15, pady=10, sticky="w")
            self.optionsvar[option.name] = var

    def onapply(self):
        """
        Collect selected options and pass to callback before destroying the window.
        """
        selected = [name for name, var in self.optionsvar.items() if var.get()]
        if self.callback:
            self.callback(selected)
        self.destroy()


class App(ctk.CTk):
    """
    Sample application to demonstrate Checkbox usage.
    """
    def __init__(self):
        super().__init__()
        self.geometry("400x300")
        self.title("Main App")

        ctk.CTkButton(self, text="Open Filter Options",
                      command=self.open_popup).pack(pady=50)

    def open_popup(self):
        filters = Enum("Filters", [
            "Grayscale", "Sepia", "Invert", "Blur",
            "Sharpen", "Edge", "Contrast", "Brightness", "Threshold"
        ])
        Checkbox(self, options=filters, callback=self.handle_selection)

    def handle_selection(self, selected: list[str]):
        print("Selected filters:", selected)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
