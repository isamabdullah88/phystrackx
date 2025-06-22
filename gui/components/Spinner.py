
from math import floor
from PIL import Image, ImageTk, ImageSequence
import customtkinter as ctk
import numpy as np
from core import abspath

class SpinnerPopup:
    def __init__(self, canvas, width, height):
        self.running = True
        self.canvas = canvas


        # Load animated GIF
        self.frames = [ImageTk.PhotoImage(self.prsframe(img, width, height)) for img in \
            ImageSequence.Iterator(Image.open(abspath("./assets/process.gif")))]
        self.imgview = self.canvas.create_image(width//2, height//2, image=self.frames[0],
                                                anchor="center")

        self.index = 0
        self.animate()

    def animate(self):
        if not self.running:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.canvas.itemconfig(self.imgview, image=self.frames[self.index])
        self.canvas.after(50, self.animate)

    def destroy(self):
        self.running = False
        self.canvas.delete(self.imgview)

    def prsframe(self, img: Image, vwidth, vheight):
        
        imgsize = 200
        img = img.resize((imgsize, imgsize), Image.Resampling.LANCZOS)
        img = np.array(img.convert("RGB"))
        
        canvas = np.ones((vheight, vwidth, 3), np.uint8)*255
        
        xstart = floor(vwidth/2) - floor(imgsize/2)
        xend = floor(vwidth/2) + floor(imgsize/2)
        ystart = floor(vheight/2) - floor(imgsize/2)
        yend = floor(vheight/2) + floor(imgsize/2)
            
        canvas[ystart:yend, xstart:xend, :] = img
        
        return Image.fromarray(canvas)


if __name__ == '__main__':
    root = ctk.CTk()
    root.geometry("900x600")
    root.title("Spinner Popup Example")
    canvas = ctk.CTkCanvas(root, width=900, height=600, bg="white")
    canvas.pack(fill="both", expand=True)
    SpinnerPopup(canvas, 900, 600)