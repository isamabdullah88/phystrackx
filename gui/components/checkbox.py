import customtkinter as ctk
from enum import Enum

class Checkbox(ctk.CTkToplevel):
    def __init__(self, parent, options:Enum, callback=None):
        super().__init__(parent)
        self.title("Select Filters")
        self.geometry("480x280")
        self.resizable(False, False)
        self.grab_set()  # Make popup modal

        self.optionsvar = {}
        self.callback = callback

        # Header
        ctk.CTkLabel(self, text="Choose Filters", font=("Segoe UI", 18, "bold")).pack(pady=(15, 5))

        # Grid frame (3 columns)
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(padx=20, pady=10)

        cols = 3
        for idx, option in enumerate(options):
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(self.grid_frame, text=option.name, variable=var)
            row = idx // cols
            col = idx % cols
            cb.grid(row=row, column=col, padx=15, pady=10, sticky="w")
            self.optionsvar[option.name] = var

        # Confirm button
        ctk.CTkButton(self, text="✓ Apply", command=self.on_apply, width=120).pack(pady=15)

    def on_apply(self):
        selected = [k for k, v in self.optionsvar.items() if v.get()]
        if self.callback:
            self.callback(selected)
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("400x300")
        self.title("Main App")

        ctk.CTkButton(self, text="Open Filter Options", command=self.open_popup).pack(pady=50)

    def open_popup(self):
        filters = Enum("Filters", ["Grayscale", "Sepia", "Invert", "Blur", "Sharpen", "Edge", "Contrast", "Brightness", "Threshold"])
        Checkbox(self, options=filters, callback=self.handle_selection)

    def handle_selection(self, selected):
        print("Selected filters:", selected)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
