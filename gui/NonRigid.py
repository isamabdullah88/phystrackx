from tkinter import *
import customtkinter
from PIL import Image, ImageTk

from .MarangoniApp import MarangoniApp
# customtkinter.set_appearance_mode("dark")
# customtkinter.set_default_color_theme("dark-blue")

class NonRigid:
    """
    Class for screen showing list of experiments.
    """
    def __init__(self):
        # self.master = master
        self.root = customtkinter.CTk()
        self.root.title("Non-Rigid Experiments")

        self.root.geometry("960x640")

        # Load and display the logo, resized to fit the window
        # self.load_and_display_logo(master)

        sf_img = Image.open("assets/add-folder.png").resize((20, 20), Image.Resampling.LANCZOS)
        sf_img = ImageTk.PhotoImage(sf_img)
        butn_sf = customtkinter.CTkButton(master=self.root, image=sf_img, text="Marangoni",
                                          width=190, height=40, compound="left",
                                          command=self.marangoni)
        butn_sf.pack(pady=20, padx=20)

        sf_img2 = Image.open("assets/add-folder.png").resize((20, 20), Image.Resampling.LANCZOS)
        sf_img2 = ImageTk.PhotoImage(sf_img2)
        butn_sf2 = customtkinter.CTkButton(master=self.root, image=sf_img2, text="Balloon",
                                          width=190, height=40, compound="left", fg_color="#D35B58",
                                          command=self.balloon)
        
        butn_sf2.pack(pady=10, padx=20)
        butn_sf.pack(pady=20, padx=20)

        self.root.mainloop()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def marangoni(self):
        self.clear_screen()
        
        app = MarangoniApp(self.root)

    def balloon(self):
        self.clear_screen()
        pass

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