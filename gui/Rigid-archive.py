from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk

from .RigidApp import SlidingFrictionApp
from .CollisionApp import CollisionApp
from core import abspath
# customtkinter.set_appearance_mode("dark")
# customtkinter.set_default_color_theme("dark-blue")

class Rigid:
    """
    Class for screen showing list of Rigid body experiments.
    """    
    def __init__(self, root):
        # self.master = master
        # self.root = ctk.CTk()
        self.root = root
        self.root.title("Rigid Experiments")

        self.root.geometry("960x640")

        # === Center frame to hold the grid ===
        center_frame = ctk.CTkFrame(self.root)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")  # center the frame

        # === Create grid of icon buttons ===
        
        img = Image.open(abspath("assets/friction.png")).resize((80, 80), Image.Resampling.LANCZOS)
        # img = ImageTk.PhotoImage(img)
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
        butnsf = ctk.CTkButton(center_frame, image=img, text="",
                                          width=80, height=80, compound="left",
                                          command=self.friction)
        butnsf.grid(row=0, column=0, padx=10, pady=10)

        img = Image.open(abspath("assets/collision.png")).resize((80, 80), Image.Resampling.LANCZOS)
        # img = ImageTk.PhotoImage(img)
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
        butncls = ctk.CTkButton(center_frame, image=img, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.collision)
        butncls.grid(row=0, column=1, padx=10, pady=10)
        
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