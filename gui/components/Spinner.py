import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk, ImageSequence

class SpinnerPopup:
    def __init__(self, parent, width, height):
        self.running = True
        self.parent = parent

        # Load animated GIF
        self.frames = [ImageTk.PhotoImage(img) for img in ImageSequence.Iterator(Image.open(
            "./assets/load-2765_128.gif"))]
        self.imgview = self.parent.create_image(width//2, height//2, image=self.frames[0],
                                                anchor="center")

        self.index = 0
        self.animate()

    def animate(self):
        if not self.running:
            print('after destroy')
            return
        self.index = (self.index + 1) % len(self.frames)
        self.parent.itemconfig(self.imgview, image=self.frames[self.index])
        self.parent.after(50, self.animate)

    def destroy(self):
        self.running = False
        self.parent.delete(self.imgview)
