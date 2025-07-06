import customtkinter as ctk
from enum import Enum

class OptionsPopup(ctk.CTkToplevel):
    def __init__(self, parent, options:Enum, callback=None):
        super().__init__(parent)
        self.title("Select Options")
        self.geometry("300x300")
        self.grab_set()  # Make it modal
        self.optionsvar = {}
        self.callback = callback

        # Create checkboxes for each option
        for option in options:
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(self, text=option.name, variable=var)
            cb.pack(anchor="w", pady=4, padx=10)
            self.optionsvar[option.name] = var

        # Confirm button
        ctk.CTkButton(self, text="Apply", command=self.onapply).pack(pady=10)

    def onapply(self):
        selected = []
        for k,v in self.optionsvar.items():
            if v.get() is True:
                selected.append(k)
        
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
        # options = ["Grayscale", "Blur", "Edge Detect", "Sharpen", "Invert"]
        
        
        options = Enum("PlotTypes", ["X", "Y", "DX"])
        OptionsPopup(self, options=options, callback=self.handle_selection)

    def handle_selection(self, selected_options):
        print("Selected filters:", [k for k, v in selected_options.items() if v])

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
