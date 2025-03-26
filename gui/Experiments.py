from tkinter import *
import customtkinter
from PIL import Image, ImageTk

from .SlidingFrictionApp import SlidingFrictionApp
from .CollisionApp import CollisionApp
# customtkinter.set_appearance_mode("dark")
# customtkinter.set_default_color_theme("dark-blue")

class Experiments:
    """
    Class for screen showing list of experiments.
    """
    def __init__(self):
        # self.master = master
        self.root = customtkinter.CTk()
        self.root.title("Experiments")

        self.root.geometry("960x640")

        # Load and display the logo, resized to fit the window
        # self.load_and_display_logo(master)

        sf_img = Image.open("assets/add-folder.png").resize((20, 20), Image.Resampling.LANCZOS)
        sf_img = ImageTk.PhotoImage(sf_img)
        butn_sf = customtkinter.CTkButton(master=self.root, image=sf_img, text="Sliding Friction",
                                          width=190, height=40, compound="left",
                                          command=self.sliding_friction)
        butn_sf.pack(pady=20, padx=20)

        sf_img2 = Image.open("assets/add-folder.png").resize((20, 20), Image.Resampling.LANCZOS)
        sf_img2 = ImageTk.PhotoImage(sf_img2)
        butn_sf2 = customtkinter.CTkButton(master=self.root, image=sf_img2, text="Collision",
                                          width=190, height=40, compound="left", fg_color="#D35B58",
                                          command=self.collision)
        
        butn_sf2.pack(pady=10, padx=20)
        butn_sf.pack(pady=20, padx=20)

        self.root.mainloop()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def collision(self):
        self.clear_screen()
        
        app = CollisionApp(self.root)

    def sliding_friction(self):
        self.clear_screen()

        app = SlidingFrictionApp(self.root)
        # Title label
        # tk.Label(master, text="Choose a tracking type:", font=("Helvetica", 16)).pack(pady=(20, 10))

        # # Buttons for menu options
        # ttk.Button(master, text="Rigid Object Tracking", command=self.on_rigid).pack(fill='x', padx=50, pady=5)
        # ttk.Button(master, text="Non-Rigid Object Tracking", command=self.on_non_rigid).pack(fill='x', padx=50, pady=5)
        # ttk.Button(master, text="Auto Tracking", command=self.on_auto).pack(fill='x', padx=50, pady=5)
        # self._restart = restart

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

    # def on_rigid(self):
    #     self.master.destroy()
    #     root = tk.Tk()
    #     root.geometry("960x640")

    #     app = VideoApp(root)
    #     root.mainloop()

    # def on_non_rigid(self):
    #     self.master.destroy()
    #     root = tk.Tk()
    #     root.geometry("960x640")
    #     app = VideoApp2(root)
    #     root.mainloop()

    # def on_auto(self):
    #     self.master.destroy()
    #     root = tk.Tk()
    #     root.geometry("960x640")
    #     app = VideoApp3(root)
    #     root.mainloop()


if __name__ == '__main__':
    Experiments()