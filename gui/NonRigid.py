from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk

from .MarangoniApp import MarangoniApp
from .BalloonApp import BalloonApp
from .InterfaceApp import InterfaceApp
# customtkinter.set_appearance_mode("dark")
# customtkinter.set_default_color_theme("dark-blue")

class NonRigid:
    """
    Class for screen showing list of experiments.
    """
    def __init__(self):
        # self.master = master
        self.root = ctk.CTk()
        self.root.title("Non-Rigid Experiments")

        self.root.geometry("960x640")

        # === Center frame to hold the grid ===
        center_frame = ctk.CTkFrame(self.root)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")  # center the frame

        # === Create grid of icon buttons ===
        
        sfimg = Image.open("assets/marangoni.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        butnsf = ctk.CTkButton(center_frame, image=sfimg, text="",
                                          width=80, height=80, compound="left",
                                          command=self.marangoni)
        butnsf.grid(row=0, column=0, padx=10, pady=10)

        sfimg = Image.open("assets/balloon.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        butnsf = ctk.CTkButton(center_frame, image=sfimg, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.balloon)
        butnsf.grid(row=0, column=1, padx=10, pady=10)
        
        # Interface 
        sfimg = Image.open("assets/interface.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        butnsf = ctk.CTkButton(center_frame, image=sfimg, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.interface)
        butnsf.grid(row=0, column=2, padx=10, pady=10)

        self.root.mainloop()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def marangoni(self):
        self.clear_screen()
        
        app = MarangoniApp(self.root)

    def balloon(self):
        self.clear_screen()
        
        app = BalloonApp(self.root)

    
    def interface(self):
        self.clear_screen()

        app = InterfaceApp(self.root)

    # def load_and_display_logo(self, master):
    #     # Load the image
    #     image_path = "phys_track_logo.png"
    #     image = Image.open(image_path)

    #     # Resize the image to fit the window width while maintaining aspect ratio
    #     base_width = 700  # Set width smaller than the window width for padding considerations
    #     w_percent = (base_width / float(image.size[0]))
    #     h_size = int((float(image.size[1]) * float(w_percent)))
    #     image = image.resize((base_width, h_size), Image.Resampling.LANCZOS)

    #     photo = ImageTk.PhotoImage(image)

    #     # Create a label to display the image
    #     image_label = tk.Label(master, image=photo)
    #     image_label.image = photo  # Keep a reference, prevent GC
    #     image_label.pack(pady=(10, 0))
    


if __name__ == '__main__':
    NonRigid()