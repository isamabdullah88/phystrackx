from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk

from .marangoniapp import MarangoniApp
from .balloonapp import BalloonApp
from .interfaceapp import InterfaceApp
from core import abspath
# customtkinter.set_appearance_mode("dark")
# customtkinter.set_default_color_theme("dark-blue")

class NonRigid:
    """
    Class for screen showing list of experiments.
    """
    def __init__(self, root):
        # self.master = master
        # self.root = ctk.CTk()
        self.root = root
        self.root.title("Non-Rigid Experiments")

        # self.root.geometry("960x640")

        # === Center frame to hold the grid ===
        center_frame = ctk.CTkFrame(self.root)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")  # center the frame

        # === Create grid of icon buttons ===
        
        img = Image.open(abspath("assets/marangoni.png")).resize((80, 80), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(80, 80))
        butnsf = ctk.CTkButton(center_frame, image=img, text="",
                                          width=80, height=80, compound="left",
                                          command=self.marangoni)
        butnsf.grid(row=0, column=0, padx=10, pady=10)

        img = Image.open(abspath("assets/balloon.png")).resize((80, 80), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(80, 80))
        butnsf = ctk.CTkButton(center_frame, image=img, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.balloon)
        butnsf.grid(row=0, column=1, padx=10, pady=10)
        
        # Interface 
        img = Image.open(abspath("assets/interface.png")).resize((80, 80), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(80, 80))
        butnsf = ctk.CTkButton(center_frame, image=img, text="",
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
    


if __name__ == '__main__':
    NonRigid()