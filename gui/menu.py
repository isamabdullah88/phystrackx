# import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter

from .rigid.rigidapp import RigidApp
from .nonrigid.nonrigid import NonRigid
from core import abspath
import os

class MenuScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Select Tracking Type")

        dirpath = 'assets/logos'
        imgpaths = [os.path.join(dirpath, imgname) for imgname in ['astrolab.png', 'kss.png', 'qosain.png', 'physlab.png']]

        # Background image
        self.bg_img = self.loadimg("assets/logos/AIbackground1.jpg", 1280, 720)
        self.bg_label = ctk.CTkLabel(self.root, text="", image=self.bg_img)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Main PhysTrack logo (on top of bg)
        phystrack_img = self.loadimg('assets/logos/logo.png', 100, 100)
        self.phystrack_logo = ctk.CTkLabel(self.root, image=phystrack_img, text="", corner_radius=10)
        self.phystrack_logo.place(relx=0.3, rely=0.1, anchor="n")
        
        self.titlerect = ctk.CTkLabel(self.root,
            fg_color="#78e955", width=500, height=100, corner_radius=10
        )
        self.titlerect.place(relx=0.6, rely=0.1, anchor="n")
        
        # Styled title label: PhysTrack Rigid
        self.title_label = ctk.CTkLabel(
            self.root,
            text=" PhysTrack: Rigid ",
            font=("Segoe UI", 60, "bold"),
            text_color="#1010d6",
            bg_color="#78e955"
        )
        self.title_label.place(relx=0.6, rely=0.11, anchor="n")

        # Start button
        self.mkbutton(self.root, "assets/start.png", self.rigid, 200, 100, relx=0.5, rely=0.70)
        
        # Logos placed directly on background with styled labels
        self.logo_labels = []
        # positions = [0.2, 0.4, 0.6, 0.8]
        width = 1200*0.4
        xs = int((1200-width)/2)
        # for pos, imgpath in zip(positions, imgpaths):
        idx = 0
        for i in range(xs, int(width+xs), int(width/4)):
            imgpath = imgpaths[idx]
            idx += 1
            w = int(width/4)
            img = self.loadimg(imgpath, w-20, w-20)
            logo_container = ctk.CTkFrame(self.root, width=w, height=w, corner_radius=20, bg_color="#CA3737",
                                          border_color="#44B62A")
            logo_container.configure(fg_color=("#ffffff", "#111111"))
            # logo_container.place(relx=pos, rely=0.8, anchor="center")
            logo_container.place(x=i, y=700)
            lbl = ctk.CTkLabel(logo_container, image=img, text="")
            lbl.pack(padx=10, pady=10)
            self.logo_labels.append(logo_container)


        # Optional animation text
        # self.label = ctk.CTkLabel(self.root, text="Welcome to PhysTrackX", font=("Helvetica", 24))
        # self.label.place(relx=0.5, rely=0.9, anchor="center")
        # self._tid = self.root.after(500, self.texanim)

    def mkbutton(self, frame, imgpath, command, width, height, relx=0.5, rely=0.5):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((width, height), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(dark_image=img, size=(width, height))
        button = ctk.CTkButton(frame, image=img, text="", width=width, height=height,
                               compound="left", command=command, corner_radius=5, bg_color="transparent")
        button.place(relx=relx, rely=rely, anchor="center")
    # def mkbutton(self, frame, imgpath, command, width, height, relx=0.5, rely=0.5):
    #     """
    #     Creates a button with an image and a command, adding a simulated shadow and gradient background.
    #     """
    #     # Load and resize image
    #     img = Image.open(abspath(imgpath)).resize((width, height), Image.Resampling.LANCZOS)
    #     img = ctk.CTkImage(dark_image=img, size=(width, height))

    #     # Shadow layer (simulated)
    #     shadow = ctk.CTkFrame(frame, width=width + 20, height=height + 20, corner_radius=20)
    #     shadow.configure(fg_color="#222222")  # Dark background as shadow
    #     shadow.place(relx=relx, rely=rely + 0.01, anchor="center")  # Slight offset for shadow

    #     # Button frame with gradient-like bg
    #     btn_bg = ctk.CTkFrame(frame, width=width, height=height, corner_radius=20)
    #     btn_bg.configure(fg_color=("#ccccff", "#6666aa"))  # Light to dark simulated gradient
    #     btn_bg.place(relx=relx, rely=rely, anchor="center")

    #     # Actual button on top
    #     button = ctk.CTkButton(
    #         btn_bg,
    #         image=img,
    #         text="",
    #         width=width,
    #         height=height,
    #         compound="left",
    #         fg_color="transparent",  # Transparent to use bg from btn_bg
    #         hover_color="#444477",
    #         command=command
    #     )
    #     button.place(relx=0.5, rely=0.5, anchor="center")
        # return button


    def loadimg(self, imgpath, width, height):
        imgpath = abspath(imgpath)
        img = Image.open(imgpath).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
        return ctk.CTkImage(dark_image=img, size=img.size)

    def texanim(self):
        text = self.label.cget("text")
        if text.endswith("..."):
            self.label.configure(text="Welcome to PhysTrackX")
        else:
            self.label.configure(text=text + ".")
        self._tid = self.root.after(500, self.texanim)

    def rigid(self):
        self.root.after_cancel(self._tid)
        self.clear_screen()
        RigidApp(self.root)

    def nonrigid(self):
        self.root.after_cancel(self._tid)
        NonRigid(self.root)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
