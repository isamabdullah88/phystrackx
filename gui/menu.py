# import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from PIL import Image, ImageTk

from .rigid.rigidapp import RigidApp
from .nonrigid.nonrigid import NonRigid
from core import abspath

class MenuScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Select Tracking Type")
        # self.root.geometry("960x640")
        
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
        
        self.button(center_frame, "assets/rigid.png", self.rigid, 0, 0)
        
        self.button(center_frame, "assets/nonrigid.png", self.nonrigid, 0, 1)

    def button(self, frame, imgpath, command, row, col, btnsize=80):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(frame, image=img, text="", width=btnsize, height=btnsize,
                               compound="left", command=command)
        button.grid(row=row, column=col, padx=10, pady=10)

    def displogo(self, root):
        # Load the image
        imgpath = abspath("assets/logo.png")
        img = Image.open(imgpath)

        # Resize the img to fit the window width while maintaining aspect ratio
        base_width = 700  # Set width smaller than the window width for padding considerations
        w_percent = (base_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

        # photo = ImageTk.PhotoImage(img)
        photo = ctk.CTkImage(dark_image=img, size=(base_width, h_size))

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
            
        self._tid = self.root.after(500, self.texanim)

    def rigid(self):
        self.root.after_cancel(self._tid)  # Stop the text animation
        # self.root.destroy()
        self.clear_screen()
        
        rigid = RigidApp(self.root)
        

    def nonrigid(self):
        self.root.after_cancel(self._tid)  # Stop the text animation
        # self.root.destroy()
        
        NonRigid(self.root)
        
    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()