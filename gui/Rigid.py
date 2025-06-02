from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk

from .SlidingFrictionApp import SlidingFrictionApp
from .CollisionApp import CollisionApp
# customtkinter.set_appearance_mode("dark")
# customtkinter.set_default_color_theme("dark-blue")

class Rigid:
    """
    Class for screen showing list of experiments.
    """
    # def __init__(self):
    #     # self.master = master
    #     self.root = customtkinter.CTk()
    #     self.root.title("Rigid")

    #     self.root.geometry("960x640")

    #     # Load and display the logo, resized to fit the window
    #     # self.load_and_display_logo(master)

    #     sf_img = Image.open("assets/slidingfriction.png").resize((20, 20), Image.Resampling.LANCZOS)
    #     sf_img = ImageTk.PhotoImage(sf_img)
    #     butn_sf = customtkinter.CTkButton(master=self.root, image=sf_img, text="Sliding Friction",
    #                                       width=190, height=40, compound="left",
    #                                       command=self.sliding_friction)
    #     butn_sf.pack(pady=20, padx=20)

    #     sf_img2 = Image.open("assets/collision.png").resize((20, 20), Image.Resampling.LANCZOS)
    #     sf_img2 = ImageTk.PhotoImage(sf_img2)
    #     butn_sf2 = customtkinter.CTkButton(master=self.root, image=sf_img2, text="Collision",
    #                                       width=190, height=40, compound="left", fg_color="#D35B58",
    #                                       command=self.collision)
        
    #     butn_sf2.pack(pady=10, padx=20)
    #     butn_sf.pack(pady=20, padx=20)

    #     self.root.mainloop()

    # def clear_screen(self):
    #     for widget in self.root.winfo_children():
    #         widget.destroy()

    # def collision(self):
    #     self.clear_screen()
        
    #     app = CollisionApp(self.root)

    # def sliding_friction(self):
    #     self.clear_screen()

    #     app = SlidingFrictionApp(self.root)
    
    def __init__(self):
        # self.master = master
        self.root = ctk.CTk()
        self.root.title("Rigid Experiments")

        self.root.geometry("960x640")

        # === Center frame to hold the grid ===
        center_frame = ctk.CTkFrame(self.root)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")  # center the frame

        # === Create grid of icon buttons ===
        
        sfimg = Image.open("assets/friction.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        butnsf = ctk.CTkButton(center_frame, image=sfimg, text="",
                                          width=80, height=80, compound="left",
                                          command=self.friction)
        butnsf.grid(row=0, column=0, padx=10, pady=10)

        sfimg = Image.open("assets/collision.png").resize((80, 80), Image.Resampling.LANCZOS)
        sfimg = ImageTk.PhotoImage(sfimg)
        butnsf = ctk.CTkButton(center_frame, image=sfimg, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.collision)
        butnsf.grid(row=0, column=1, padx=10, pady=10)
        

        self.root.mainloop()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def friction(self):
        self.clear_screen()
        
        app = SlidingFrictionApp(self.root)

    def collision(self):
        self.clear_screen()
        
        app = CollisionApp(self.root)
    


if __name__ == '__main__':
    Rigid()