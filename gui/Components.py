import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk, ImageSequence

class SpinnerPopup:
    def __init__(self, parent):
        # super().__init__(parent)
        # self.geometry("256x256")
        # self.title("Loading...")
        # self.resizable(False, False)
        # self.attributes("-topmost", True)
        self.parent = parent

        # Load animated GIF
        self.frames = [ImageTk.PhotoImage(img) for img in ImageSequence.Iterator(Image.open("./assets/load-2765_256.gif"))]
        self.label = Label(self.parent, image=self.frames[0], bg="black", borderwidth=0)
        self.label.pack(expand=True)

        self.index = 0
        self.animate()

    def animate(self):
        self.index = (self.index + 1) % len(self.frames)
        self.label.config(image=self.frames[self.index])
        self.parent.after(50, self.animate)

    def destroy(self):
        self.label.destroy()
        self.label = None