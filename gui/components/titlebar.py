"""
titlebar.py

This module defines the TitleBar class used to render a stylized gradient title bar
with a logo and shadow effect at the top of a tkinter Canvas.

Author: Isam Balghari
"""

import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk
from core import abspath


class TitleBar:
    """
    Renders a gradient title bar with a logo and title text on a tkinter Canvas.
    """

    def __init__(self, canvas: tk.Canvas, width: int, text: str, height: int = 70) -> None:
        """
        Initialize and draw the title bar.

        Args:
            canvas (tk.Canvas): The canvas on which to draw the title bar.
            width (int): Width of the title bar.
            text (str): Title text to display.
            height (int): Height of the title bar.
        """
        self.canvas = canvas
        self.height = height

        self._draw_gradient_bar(0, 0, width, height, "#b733f4", "#ba76da", steps=100)
        self._draw_shadow(0, height, width)

        # Logo image
        logo_path = abspath("./assets/logos/logo.png")
        logo_img = Image.open(logo_path).resize((50, 50), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(logo_img)

        self.canvas.create_image(20, 10, image=self.logo, anchor="nw")

        # Title text
        self.canvas.create_text(
            90, height // 2,
            anchor="w",
            text=text,
            fill="#ffffff",
            font=font.Font(family="Segoe UI", size=20, weight="bold")
        )

    def _draw_gradient_bar(self, x1: int, y1: int, x2: int, y2: int, color1: str, color2: str, steps: int = 100) -> None:
        """Draw a vertical gradient between two colors."""
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)

        for i in range(steps):
            ratio = i / steps
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            y = y1 + ((y2 - y1) * ratio)
            self.canvas.create_line(x1, y, x2, y, fill=hex_color)

    def _draw_shadow(self, x1: int, y_start: int, x2: int, height: int = 10) -> None:
        """Draw a shadow gradient beneath the title bar."""
        for i in range(height):
            alpha = int(80 * (1 - i / height))
            shade = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
            self.canvas.create_line(x1, y_start + i, x2, y_start + i, fill=shade)

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert a hex color string to an (R, G, B) tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# === Example standalone usage ===
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x800")

    canvas = tk.Canvas(root, width=700, height=400)
    canvas.pack()

    TitleBar(canvas, 700, "Example Toolbar")
    root.mainloop()
