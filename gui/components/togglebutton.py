import customtkinter as ctk
import tkinter as tk
from PIL import Image

class ToggleButton(ctk.CTkButton):
    def __init__(self, master, commandon=None, commandoff=None, width=40, height=40, **kwargs):
        super().__init__(master, **kwargs)
        
        self.imgon = ctk.CTkImage(dark_image=Image.open("assets/switch-on.png"), size=(50, 20))
        self.imgoff = ctk.CTkImage(dark_image=Image.open("assets/switch-off.png"), size=(50, 20))
        self.commandon = commandon
        self.commandoff = commandoff
        self.is_on = False

        self.configure(image=self.imgoff, text="", width=width, height=height, command=self.toggle)

    def toggle(self):
        self.is_on = not self.is_on
        self.configure(image=self.imgon if self.is_on else self.imgoff)
        
        if self.is_on and self.commandon:
            self.commandon()
        elif not self.is_on and self.commandoff:
            self.commandoff()


# Example usage
if __name__ == "__main__":
    def on_toggle():
        print("Switched ON")

    def off_toggle():
        print("Switched OFF")

    # Init app
    ctk.set_appearance_mode("light")  # or "dark"
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
