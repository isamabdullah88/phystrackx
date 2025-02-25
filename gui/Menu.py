# import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from PIL import Image, ImageTk

from .Experiments import Experiments

class MenuScreen:
    def __init__(self, master, restart=None):
        self.master = master
        self.master.title("Select Tracking Type")
        self.master.geometry("960x640")

        # Load and display the logo, resized to fit the window
        self.load_and_display_logo(master)

        # Title label
        ctk.CTkLabel(master, text="Choose a tracking type:", font=("Helvetica", 16)).pack(pady=(20, 10))

        # Buttons for menu options
        ttk.Button(master, text="Rigid Object Tracking", command=self.on_rigid).pack(fill='x', padx=50, pady=5)
        ttk.Button(master, text="Non-Rigid Object Tracking", command=self.on_non_rigid).pack(fill='x', padx=50, pady=5)
        # ttk.Button(master, text="Auto Tracking", command=self.on_auto).pack(fill='x', padx=50, pady=5)
        # self._restart = restart

    def load_and_display_logo(self, master):
        # Load the image
        image_path = "phys_track_logo.png"
        image = Image.open(image_path)

        # Resize the image to fit the window width while maintaining aspect ratio
        base_width = 700  # Set width smaller than the window width for padding considerations
        w_percent = (base_width / float(image.size[0]))
        h_size = int((float(image.size[1]) * float(w_percent)))
        image = image.resize((base_width, h_size), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(image)

        # Create a label to display the image
        image_label = ctk.CTkLabel(master, image=photo)
        image_label.image = photo  # Keep a reference, prevent GC
        image_label.pack(pady=(10, 0))

    def on_rigid(self):
        self.master.destroy()
        # root = tk.Tk()
        # root.geometry("960x640")

        # app = VideoApp(root)
        experiments = Experiments()
        # root.mainloop()

    def on_non_rigid(self):
        self.master.destroy()
        root = tk.Tk()
        root.geometry("960x640")
        app = VideoApp2(root)
        root.mainloop()

    def on_auto(self):
        self.master.destroy()
        root = tk.Tk()
        root.geometry("960x640")
        app = VideoApp3(root)
        root.mainloop()