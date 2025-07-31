"""
spinner.py

Displays a centered animated spinner on a CTkCanvas using a preloaded GIF.

Author: Isam Balghari
"""

from typing import Optional
from PIL import Image, ImageTk, ImageSequence
import customtkinter as ctk
from customtkinter import CTkCanvas
from gui.plugins import Crop
from core import abspath


class Spinner:
    """
    A widget that shows a centered animated spinner overlay using a GIF.

    Args:
        canvas (CTkCanvas): The canvas to display the spinner on.
        crop (Optional[Crop]): Optional crop object for offset positioning.
    """

    def __init__(self, canvas: CTkCanvas, imgview, crop: Optional[Crop] = None) -> None:
        self.running: bool = True
        self.canvas: CTkCanvas = canvas
        self.crop: Optional[Crop] = crop
        self.index: int = 0

        self.imgview = imgview
        self.vwidth: int = self.canvas.winfo_width()
        self.vheight: int = self.canvas.winfo_height()

        gif_path: str = abspath("./assets/process.gif")
        raw_frames = ImageSequence.Iterator(Image.open(gif_path))
        self.frames: list[ImageTk.PhotoImage] = [
            ImageTk.PhotoImage(
                img.resize((200, 200), Image.Resampling.LANCZOS)
            )
            for img in raw_frames
        ]

        self.canvas.coords(self.imgview, self.vwidth // 2 - 100, self.vheight // 2 - 100)
        self.canvas.itemconfig(self.imgview, image=self.frames[0], anchor="nw")

        self.animate()

    def animate(self) -> None:
        """
        Animate the spinner frame-by-frame using the canvas `.after()` method.
        """
        if not self.running:
            return

        self.index = (self.index + 1) % len(self.frames)
        self.canvas.itemconfig(self.imgview, image=self.frames[self.index])
        self.canvas.after(50, self.animate)

    def destroy(self) -> None:
        """
        Stop animation and remove spinner from the canvas.
        """
        self.running = False


def main() -> None:
    """
    Launch a demo window displaying the spinner animation for 5 seconds.
    """
    root: ctk.CTk = ctk.CTk()
    root.geometry("900x600")
    root.title("Spinner Preview")

    canvas: CTkCanvas = ctk.CTkCanvas(root, width=900, height=600, bg="grey")
    canvas.pack(fill="both", expand=True)
    imgview = canvas.create_image(0, 0)

    def launch_spinner() -> None:
        spinner = Spinner(canvas, imgview)
        canvas.after(5000, spinner.destroy)

    canvas.after(100, launch_spinner)
    root.mainloop()


if __name__ == "__main__":
    main()
