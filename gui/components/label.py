
import customtkinter as ctk

class Label(ctk.CTkFrame):
    def __init__(self, parent, text="Label", color="blue", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Colored box
        self.colorbox = ctk.CTkLabel(self, text="", width=15, height=15, fg_color=color, corner_radius=3)
        self.colorbox.pack(side="left", padx=(0, 8))

        # Text label
        self.label = ctk.CTkLabel(self, width=150, text=text, font=("Segoe UI", 16))
        self.label.pack(side="left")

    def set_text(self, text):
        self.label.configure(text=text)

    def set_color(self, color):
        self.colorbox.configure(fg_color=color)
        
    def clear(self):
        self.colorbox.destroy()
        self.label.destroy()
