"""
axes.py

Defines the Axes class that manages coordinate transformations and GUI-based axis selection.

Author: Isam Balghari
"""

from tkinter import ttk
import numpy as np
import customtkinter as ctk
from PIL import Image
from core import abspath


class Axes:
    def __init__(self, root, canvas, vwidth: int, vheight: int, btnlist: dict, activebtn: ctk.CTkButton):
        self.root = root
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.theta = ctk.DoubleVar(value=0)

        self.ox = 0
        self.oy = self.vheight

        self.btnlist = btnlist
        self.activebtn = activebtn
        self.applybtn = self.mkbutton("assets/apply.png", self.onapply, btnsize=80)

    def clear(self):
        """Clear all canvas drawings related to sliders and axes."""
        self.canvas.itemconfigure("slider", state="hidden")
        self.slider.pack_forget()
        self.canvas.delete("axes")

    def markaxes(self):
        """Enable interactive marking of axes with mouse events."""
        self.canvas.delete("oval")
        self.canvas.delete("axes")
        self.canvas.bind("<Motion>", self.onmove)
        self.canvas.bind("<Button-1>", self.onclick)

        for k, btn in self.btnlist.items():
            if btn != self.activebtn:
                btn.configure(state="disabled")

    def drawaxes(self, startx, starty, xp, yp):
        """Draw x and y axes lines with arrow heads and labels."""
        sx0, sy0 = startx
        sx1, sy1 = starty
        x0, y0 = xp
        x1, y1 = yp

        x0 = min(max(x0, 0), self.vwidth)
        y0 = min(max(y0, 0), self.vheight)
        x1 = min(max(x1, 0), self.vwidth)
        y1 = min(max(y1, 0), self.vheight)

        self.canvas.create_line(sx0, sy0, x0, y0, fill="red", arrow=ctk.LAST,
                                width=2, tags="axes")
        self.canvas.create_line(sx1, sy1, x1, y1, fill="blue", arrow=ctk.LAST,
                                width=2, tags="axes")

        self.canvas.create_text(x0 - 15, y0 - 15, text="x", fill="red",
                                font=("Arial", 15, "bold"), tags="axes")
        self.canvas.create_text(x1 + 15, y1 - 15, text="y", fill="blue",
                                font=("Arial", 15, "bold"), tags="axes")

    def canvas2reg(self, xc, yc, tx, ty):
        """Convert canvas coordinates to regular (math) frame."""
        return xc - tx, -yc + ty

    def reg2canvas(self, xr, yr, tx, ty):
        """Convert regular (math) coordinates to canvas frame."""
        return xr + tx, -yr + ty

    def rotatez(self, x, y, theta):
        """Rotate a point (x, y) by angle `theta` (radians) around the origin."""
        c, s = np.cos(theta), np.sin(theta)
        return x * c - y * s, x * s + y * c

    def rotate(self, event=None):
        """Redraw axes based on the current rotation angle."""
        self.canvas.delete("axes")

        x0, y0 = self.vwidth, 0
        x1, y1 = 0, self.vheight

        theta_rad = np.deg2rad(self.theta.get())

        xp0, yp0 = self.rotatez(x0, y0, theta_rad)
        xp1, yp1 = self.rotatez(x1, y1, theta_rad)

        xp0, yp0 = self.reg2canvas(xp0, yp0, self.ox, self.oy)
        xp1, yp1 = self.reg2canvas(xp1, yp1, self.ox, self.oy)

        self.drawaxes((self.ox, self.oy), (self.ox, self.oy), (xp0, yp0), (xp1, yp1))

    def onmove(self, event):
        """Update axes preview to follow mouse position."""
        self.canvas.delete("axes")

        xf0, yf0 = self.vwidth, 0
        xf1, yf1 = 0, self.vheight

        xc0, yc0 = self.reg2canvas(xf0, yf0, event.x, event.y)
        xc1, yc1 = self.reg2canvas(xf1, yf1, event.x, event.y)

        self.drawaxes((event.x, event.y), (event.x, event.y), (xc0, yc0), (xc1, yc1))

    def onclick(self, event):
        """Finalize axis origin selection and show slider for rotation."""
        self.ox, self.oy = event.x, event.y
        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<Button-1>")

        self.slider = ttk.Scale(
            self.root,
            from_=-180,
            to=0,
            orient="horizontal",
            variable=self.theta,
            command=self.rotate
        )

        self.canvas.create_window(self.vwidth - 180, self.vheight - 20,
                                  window=self.slider, tags="slider")

        self.applybtn.pack(side="right", padx=10, pady=10, anchor="se")

    def onapply(self):
        """Finalize axis placement and restore other UI buttons."""
        self.canvas.itemconfigure("slider", state="hidden")
        self.applybtn.pack_forget()

        for btn in self.btnlist.values():
            btn.configure(state="normal")

    def mkbutton(self, imgpath, command, btnsize=30):
        """Create a CTkButton with image loaded from `imgpath`."""
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))

        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                               image=img, command=command)
        button.image = img
        return button
