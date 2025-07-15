
from math import floor
from PIL import Image, ImageTk
import customtkinter as ctk
from customtkinter import CTkCanvas
import numpy as np
from gui.plugins import Crop
from queue import Queue, Empty
import cv2

class Spinner:
    def __init__(self, canvas:CTkCanvas, crop:Crop=None):
        self.running = True
        self.canvas = canvas
        self.queue = Queue(maxsize=5)
        self.crop = crop

        # Load animated GIF
        # self.frames = [ImageTk.PhotoImage(self.prsframe(img, vwidth, vheight)) for img in \
        #     ImageSequence.Iterator(Image.open(abspath("./assets/process.gif")))]
        self.imgview = self.canvas.create_image(self.crop.fx, self.crop.fy, anchor="nw")
        # self.canvas.itemconfigure(self.imgview, state="normal")

        self.index = 0

    def pack(self):
        if not self.running:
            return
        
        try:
            frame = self.queue.get_nowait()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            
            self.imgtk = ImageTk.PhotoImage(img)
            self.canvas.itemconfigure(self.imgview, image=self.imgtk)
            self.canvas.coords(self.imgview, self.crop.crpx, self.crop.crpy)
        except Empty:
            pass
        
        self.canvas.after(50, self.pack)

    def destroy(self):
        self.running = False
        self.canvas.delete(self.imgview)

    # def prsframe(self, img: Image, vwidth, vheight):
        
    #     imgsize = 200
    #     img = img.resize((imgsize, imgsize), Image.Resampling.LANCZOS)
    #     img = np.array(img.convert("RGB"))
        
    #     canvas = np.ones((vheight, vwidth, 3), np.uint8)*255
        
    #     xstart = floor(vwidth/2) - floor(imgsize/2)
    #     xend = floor(vwidth/2) + floor(imgsize/2)
    #     ystart = floor(vheight/2) - floor(imgsize/2)
    #     yend = floor(vheight/2) + floor(imgsize/2)
            
    #     canvas[ystart:yend, xstart:xend, :] = img
        
    #     return Image.fromarray(canvas)


if __name__ == '__main__':
    root = ctk.CTk()
    root.geometry("900x600")
    root.title("Spinner Popup Example")
    canvas = ctk.CTkCanvas(root, width=900, height=600, bg="white")
    canvas.pack(fill="both", expand=True)
    Spinner(canvas, 900, 600)