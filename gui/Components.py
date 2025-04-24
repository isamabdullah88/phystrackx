import customtkinter as ctk
from tkinter import Label
from PIL import Image, ImageTk, ImageSequence

class SpinnerPopup:
    def __init__(self, parent, width, height):
        # super().__init__(parent)
        # self.geometry("256x256")
        # self.title("Loading...")
        # self.resizable(False, False)
        # self.attributes("-topmost", True)
        self.running = True
        self.parent = parent
        print('Spinner created!')

        # Load animated GIF
        self.frames = [ImageTk.PhotoImage(img) for img in ImageSequence.Iterator(Image.open("./assets/load-2765_256.gif"))]
        # self.label = ctk.CTkLabel(self.parent, image=self.frames[0])
        self.imgview = self.parent.create_image(width//2, height//2, image=self.frames[0], anchor="center")
        # self.label.pack(expand=True)

        self.index = 0
        self.animate()

    def animate(self):
        if not self.running:
            print('after destroy')
            # self.label.destroy()
            return
        self.index = (self.index + 1) % len(self.frames)
        # self.label.configure(image=self.frames[self.index])
        self.parent.itemconfig(self.imgview, image=self.frames[self.index])
        self.parent.after(50, self.animate)

    def destroy(self):
        self.running = False
        print('At destroy')
        self.parent.delete(self.imgview)
        # self.label.destroy()
        print('At destroy2')
        # self.label = None
        print('At destroy3')
        # self.parent.destroy()