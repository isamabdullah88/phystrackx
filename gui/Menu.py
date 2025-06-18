# import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from PIL import Image, ImageTk

from .Rigid import Rigid
from .NonRigid import NonRigid
from core import abspath

class MenuScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Select Tracking Type")
        self.root.geometry("960x640")
        
        # Title label
        self.label = ctk.CTkLabel(root, text="Welcome to PhysTrackX", font=("Helvetica", 24))
        self.label.pack(pady=(20, 0))

        # Subtitle label
        subtlabel = ctk.CTkLabel(root, text="A Project By Dr. Sabieh, Isam", font=("Helvetica", 18))
        subtlabel.pack(pady=(10, 0))
        
        # Load and display the logo, resized to fit the window
        self.displogo(root)
        
        self.texanim()
        
        # === Center frame to hold the grid ===
        center_frame = ctk.CTkFrame(self.root)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")  # center the frame

        # === Create grid of icon buttons ===
        
        img = Image.open(abspath("assets/rigid.png")).resize((80, 80), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        butnsf = ctk.CTkButton(center_frame, image=img, text="",
                                          width=80, height=80, compound="left",
                                          command=self.rigid)
        butnsf.grid(row=0, column=0, padx=10, pady=10)

        img = Image.open(abspath("assets/nonrigid.png")).resize((80, 80), Image.Resampling.LANCZOS)
        img = ImageTk.PhotoImage(img)
        butnsf = ctk.CTkButton(center_frame, image=img, text="",
                                          width=80, height=80, compound="left", fg_color="#D35B58",
                                          command=self.nonrigid)
        butnsf.grid(row=0, column=1, padx=10, pady=10)

    def displogo(self, root):
        # Load the image
        imgpath = abspath("assets/logo.png")
        image = Image.open(imgpath)

        # Resize the image to fit the window width while maintaining aspect ratio
        base_width = 700  # Set width smaller than the window width for padding considerations
        w_percent = (base_width / float(image.size[0]))
        h_size = int((float(image.size[1]) * float(w_percent)))
        image = image.resize((base_width, h_size), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(image)

        # Create a label to display the image
        image_label = ctk.CTkLabel(root, image=photo, text="")
        image_label.image = photo  # Keep a reference, prevent GC
        image_label.pack(pady=(10, 0))
        
    def texanim(self):
        text = self.label.cget("text")
        if text.endswith("..."):
            self.label.configure(text="Welcome to PhysTrackX")
        else:
            self.label.configure(text=text + ".")
        self.root.after(500, self.texanim)

    def rigid(self):
        self.root.destroy()
        
        rigid = Rigid()
        

    def nonrigid(self):
        self.root.destroy()
        
        NonRigid()