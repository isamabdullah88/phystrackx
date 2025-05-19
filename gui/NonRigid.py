from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk

from .MarangoniApp import MarangoniApp
from .BalloonApp import BalloonApp
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

        # === Load a sample icon (use your own PNG path) ===
        # icon_image = ctk.CTkImage(light_image=Image.open("icon.png"), size=(40, 40))

        # === Create grid of icon buttons ===
        
        sfimg = Image.open("assets/marangoni.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        butn_sf = ctk.CTkButton(center_frame, image=sfimg, text="",
                                          width=80, height=80, compound="left",
                                          command=self.marangoni)
        
        butn_sf.grid(row=0, column=0, padx=10, pady=10)

        sf_img = Image.open("assets/balloon.png").resize((80, 80), Image.Resampling.LANCZOS)
        sf_img = ImageTk.PhotoImage(sf_img)
        butn_sf = ctk.CTkButton(center_frame, image=sf_img, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.balloon)
        
        # btn = ctk.CTkButton(center_frame, text="", image=icon_image, width=60, height=60, command=lambda r=r, c=c: self.icon_action(r, c))
        butn_sf.grid(row=0, column=1, padx=10, pady=10)
        # Load and display the logo, resized to fit the window
        # self.load_and_display_logo(master)

        # butn_sf.pack(pady=20, padx=20)

        
        # butn_sf2.pack(pady=10, padx=20)
        # butn_sf.pack(pady=20, padx=20)

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