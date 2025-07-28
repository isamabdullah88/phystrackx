"""
spinner.py

Displays a centered animated spinner on a CTkCanvas using a preloaded GIF.

Author: Isam Balghari
"""

from math import floor
from typing import Optional
import numpy as np
from PIL import Image, ImageTk, ImageSequence
import customtkinter as ctk
from customtkinter import CTkCanvas
from gui.plugins import Crop
from core import abspath


class Spinner:
    """
    A widget that shows a centered animated spinner overlay using a GIF.

    Args:
        canvas: The CTkCanvas to display the spinner on.
        crop: Optional Crop instance for positioning offset.
    """

    def __init__(self, canvas: CTkCanvas, crop: Optional[Crop] = None) -> None:
        self.running: bool = True
        self.canvas: CTkCanvas = canvas
        self.crop: Optional[Crop] = crop

        self.index: int = 0
        self.vwidth = self.canvas.winfo_width()
        self.vheight = self.canvas.winfo_height()

        gif_path = abspath("./assets/process.gif")
        self.frames = [ImageTk.PhotoImage(img.resize((200, 200), Image.Resampling.LANCZOS)) for img in \
            ImageSequence.Iterator(Image.open(gif_path))]

        # self.imgview = self.canvas.create_image(
        #     self.crop.fx if self.crop else 0,
        #     self.crop.fy if self.crop else 0,
        #     anchor="nw",
        #     image = self.frames[0]
        # )
        
        self.imgview = self.canvas.create_image(
            self.vwidth//2,
            self.vheight//2,
            image=self.frames[0],
            anchor="center")
        # self.canvas.itemconfigure(self.imgview, state="normal")
        self.animate()

    # def _process_frame(self, img: Image.Image) -> Image.Image:
    #     """
    #     Resizes the frame and centers it on a white canvas matching the canvas size.

    #     Args:
    #         img: Input GIF frame.

    #     Returns:
    #         Resized and padded image as PIL Image.
    #     """
    #     imgsize = 200
    #     resized = img.resize((imgsize, imgsize), Image.Resampling.LANCZOS)
    #     img_array = np.array(resized.convert("RGB"))

    #     canvas = np.ones((self.vheight, self.vwidth, 3), np.uint8) * 255

    #     xstart = floor(self.vwidth / 2) - floor(imgsize / 2)
    #     xend = xstart + imgsize
    #     ystart = floor(self.vheight / 2) - floor(imgsize / 2)
    #     yend = ystart + imgsize

    #     canvas[ystart:yend, xstart:xend, :] = img_array

    #     return Image.fromarray(canvas)

    def animate(self) -> None:
        """
        Animate the spinner frame-by-frame using `after` loop.
        """
        if not self.running:
            return

        self.index = (self.index + 1) % len(self.frames)
        self.canvas.itemconfig(self.imgview, image=self.frames[self.index])
        self.canvas.after(50, self.animate)

    def destroy(self) -> None:
        """
        Stop the animation and remove the spinner from canvas.
        """
        self.running = False
        self.canvas.delete(self.imgview)


# --- Minimal test app --- #

def main() -> None:
    """
    Launches a test window displaying the spinner animation.
    """
    root = ctk.CTk()
    root.geometry("900x600")
    root.title("Spinner Preview")

    canvas = ctk.CTkCanvas(root, width=900, height=600, bg="white")
    canvas.pack(fill="both", expand=True)

    # Wait for canvas to draw before showing spinner
    def launch_spinner():
        spinner = Spinner(canvas)
        # Auto-destroy after 5 seconds
        canvas.after(5000, spinner.destroy)

    canvas.after(100, launch_spinner)
    root.mainloop()


if __name__ == "__main__":
    main()
