import customtkinter as ctk
from PIL import Image
from math import floor
from core import abspath

class SubToolbar:
    def __init__(self, canvas, width=150, height=100, btnsize=50):
        self.canvas = canvas

        self.enable = False
        self.btnsize = btnsize
        # Create the toolbar frame
        self.frame = ctk.CTkFrame(canvas, width=width, height=height, bg_color="#899fbd", fg_color="#5bdada")

        # Example content
        # Load your image using PIL
        img = Image.open("assets/plugin.png")  # Replace with your image path
        imgtk = ctk.CTkImage(light_image=img, dark_image=img, size=(floor(self.btnsize), floor(self.btnsize)))
        ctk.CTkLabel(self.frame, text="", image=imgtk).pack(pady=5)

        # Stick to top-left corner of canvas using create_window
        self.wid = self.canvas.create_window(5, 5, anchor="nw", window=self.frame)
        self.canvas.itemconfigure(self.wid, state="hidden")

    def destroy(self):
        self.frame.destroy()

    def toggle(self):
        if self.enable:
            self.canvas.itemconfigure(self.wid, state="hidden")
            self.enable = False
        else:
            self.canvas.itemconfigure(self.wid, state="normal")
            self.canvas.coords(self.wid, 5, 5)
            self.enable = True
        
    def button(self, imgpath, command):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(self.btnsize, self.btnsize))
        button = ctk.CTkButton(self.frame, text="", width=self.btnsize, height=self.btnsize,
                            image=img, command=command)
        button.pack(padx=10, pady=10)
        # Store the image reference to prevent garbage collection
        button.image = img
        
        return button


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x400")

        self.canvas = ctk.CTkCanvas(self, width=600, height=400, bg="white")
        self.canvas.pack()

        # Stick a sub-toolbar to canvas
        self.toolbar = SubToolbar(self.canvas)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
