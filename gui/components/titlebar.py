import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk
from core import abspath

class TitleBar:
    def __init__(self, canvas, vwidth, text, height=70):
        self.canvas = canvas


        self.draw_gradient_bar(0, 0, vwidth, height, "#b733f4", "#ba76da", steps=100)
        self.draw_shadow(0, height, vwidth)
        
        # === Add logo ===
        self.logo = ImageTk.PhotoImage(Image.open(abspath("./assets/logo.png")).resize((50, 50)))
        self.canvas.create_image(20, 10, image=self.logo, anchor="nw")

        # === Add title text (left aligned) ===
        self.canvas.create_text(
            90, height // 2, anchor="w",
            text=text,
            fill="#ffffff",
            font=font.Font(family="Segoe UI", size=20, weight="bold")
        )

    def draw_gradient_bar(self, x1, y1, x2, y2, color1, color2, steps=100):
        r1, g1, b1 = self.hex_to_rgb(color1)
        r2, g2, b2 = self.hex_to_rgb(color2)

        for i in range(steps):
            ratio = i / steps
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            y = y1 + ((y2 - y1) * ratio)
            self.canvas.create_line(x1, y, x2, y, fill=hex_color)

    def draw_shadow(self, x1, y_start, x2, height=10):
        for i in range(height):
            alpha = int(80 * (1 - i / height))
            color = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
            self.canvas.create_line(x1, y_start + i, x2, y_start + i, fill=color)

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    # 🔧 Usage
    root = tk.Tk()
    root.geometry("900x800")
    # Continue your app below
    canvas = tk.Canvas(root, width=700, height=400)
    canvas.pack()
    print('canvas: ', canvas)
    canvas.create_text(100,100, text="HELLOO", width=200)
    title_bar = TitleBar(canvas, 500, "Example Toolbar")


    root.mainloop()
