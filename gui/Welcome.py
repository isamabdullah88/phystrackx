import tkinter as tk
import customtkinter
from PIL import ImageTk, Image
# from video_processing import VideoProcessor
# from utils import resize_frame
# import cv2
# import numpy as np
# from tkinter import ttk
# import csv
# from nonrigid import VideoApp2
# from rigid import VideoApp
# from auto import VideoApp3

class WelcomeScreen:
    def __init__(self, master):
        self.master = master
        self.master.title("Welcome")
        self.master.geometry("960x640")

        # Title label
        self.label = tk.Label(master, text="Welcome to PhysTrackX", font=("Helvetica", 24))
        self.label.pack(pady=(20, 0))

        # Subtitle label
        subtitle_label = tk.Label(master, text="A Project By", font=("Helvetica", 18))
        subtitle_label.pack(pady=(10, 0))

        # Load and display the image
        self.load_and_display_image(master)

        self.animate_text()

    def load_and_display_image(self, master):
        # Load the image
        image_path = "assets/physlab_logo.png"
        image = Image.open(image_path)
        photo = ImageTk.PhotoImage(image)

        # Create a label to display the image
        image_label = tk.Label(master, image=photo)
        image_label.image = photo  # Keep a reference, prevent GC
        image_label.pack(pady=(10, 20))

    def animate_text(self):
        text = self.label.cget("text")
        if text.endswith("..."):
            self.label.config(text="Welcome to PhysTrackX")
        else:
            self.label.config(text=text + ".")
        self.master.after(500, self.animate_text)

