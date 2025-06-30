import numpy as np
import tkinter as tk
from tkinter import ttk

class Axes:
    def __init__(self, root, canvas, vwidth, vheight):
        self.root = root
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.theta = tk.DoubleVar(value=0)  # Angle of rotation in degrees
        
        # Default frame is regular frame from bottom left corner
        self.ox = 0
        self.oy = self.vheight
        
        self.slider = ttk.Scale(self.root, from_=-180, to=0, orient='horizontal', variable=self.theta,
                            command=self.rotate)
        self.canvas.create_window(self.vwidth - 60, self.vheight - 20, window=self.slider, tags="slider")
        self.canvas.itemconfigure("slider", state="hidden")  # Hide the slider initially
        
    def clear(self):
        """Clear GUI elements"""
        self.canvas.delete("slider")
        self.canvas.delete("axes")
    
    def markaxes(self):
    
        self.canvas.delete("oval")  # Remove old oval if exists
        self.canvas.delete("axes")  # Remove old axes if exists
        
        self.canvas.bind("<Motion>", self.onmove)
        self.canvas.bind("<Button-1>", self.onclick)
        
    def drawaxes(self, startx, starty, xp, yp):
        """ Draws axes with simple lines. """
        sx0, sy0 = startx  # Starting point for the axes
        sx1, sy1 = starty  # Center point for the axes
        x0, y0 = xp  # X-axis end point
        x1, y1 = yp  # Y-axis end point
        
        if x0 < 0: x0 = 0
        if y0 < 0: y0 = 0
        if x1 < 0: x1 = 0
        if y1 < 0: y1 = 0
        
        if x0 > self.vwidth: x0 = self.vwidth
        if y0 > self.vheight: y0 = self.vheight
        if x1 > self.vwidth: x1 = self.vwidth
        if y1 > self.vheight: y1 = self.vheight
        
        self.canvas.create_line(sx0, sy0, x0, y0, fill="red", arrow=tk.LAST, width=2, tags="axes")  # X-axis
        self.canvas.create_line(sx1, sy1, x1, y1, fill="blue", arrow=tk.LAST, width=2, tags="axes")  # Y-axis

        self.canvas.create_text(x0-15, y0-15, text="x", fill="red", font=("Arial", 15, "bold"), tags="axes")
        self.canvas.create_text(x1+15, y1-15, text="y", fill="blue", font=("Arial", 15, "bold"), tags="axes")
        
    def canvas2reg (self, xc, yc, tx, ty):
        """ Transform coordinates from canvas coordinate-frame to regular frame.
        Args:
            xc (float): x-coordinate in canvas frame.
            yc (float): y-coordinate in canvas frame.
            tx (float): x-coordinate of canvas frame origin in canvas coordinates.
            ty (float): y-coordinate of canvas frame origin in canvas coordinates.
        """
        xr = xc - tx
        yr = -yc + ty
        return xr, yr
    
    def reg2canvas(self, xr, yr, tx, ty):
        """ Transform coordinates from regular frame to canvas coordinate-frame.
        Args:
            xr (float): x-coordinate in regular frame.
            yr (float): y-coordinate in regular frame.
            tx (float): x-coordinate of regular frame origin in canvas coordinates.
            ty (float): y-coordinate of regular frame origin in canvas coordinates.
        """
        xc = xr + tx
        yc = -yr + ty
        return xc, yc
    
    def rotatez(self, x, y, theta):
        """ Rotate a point (x, y) around the origin (z-axis) by angle theta in radians. 
        Args:
            x (float): x-coordinate of the point. 
            y (float): y-coordinate of the point.
            theta (float): angle of rotation in radians.
        """
        
        ctheta = np.cos(theta)
        stheta = np.sin(theta)
        xp = x * ctheta - y * stheta
        yp = x * stheta + y * ctheta
        return xp, yp
        
    def rotate(self, event):
        """ Rotate the axes by a given angle theta. """
        self.canvas.delete("axes")

        # X-axis point in regular frame
        x0 = self.vwidth
        y0 = 0
        
        # Y-axis point in regular frame
        x1 = 0
        y1 = self.vheight
        
        # Rotate x-axis point
        theta = np.deg2rad(self.theta.get())
        xp0, yp0 = self.rotatez(x0, y0, theta)
        
        # Rotate y-axis point
        xp1, yp1 = self.rotatez(x1, y1, theta)
        
        xp0, yp0 = self.reg2canvas(xp0, yp0, self.ox, self.oy)
        xp1, yp1 = self.reg2canvas(xp1, yp1, self.ox, self.oy)
        
        self.drawaxes((self.ox, self.oy), (self.ox, self.oy), (xp0, yp0), (xp1, yp1))
        
    
    def onmove(self, event):
        """ Update the axes to follow the mouse cursor. """
        self.canvas.delete("axes")  # Remove old axes
        tx, ty = event.x, event.y  # Get mouse position
        
        # Points in regular coordinates
        # X-axis point
        xf0 = self.vwidth
        yf0 = 0
        
        # Y-axis point
        xf1 = 0
        yf1 = self.vheight
        
        # Point in canvas coordinates
        # X-axis point
        xc0, yc0 = self.reg2canvas(xf0, yf0, tx, ty)
        
        # Y-axis point
        xc1, yc1 = self.reg2canvas(xf1, yf1, tx, ty)
        
        self.drawaxes((tx, ty), (tx, ty), (xc0, yc0), (xc1, yc1))

    def onclick(self, event):
        """ Store the clicked coordinates and draw a point. """
        x, y = event.x, event.y

        self.ox = x
        self.oy = y

        self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="red", tags="oval")  # Draw a small dot

        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<Button-1>")

        self.canvas.itemconfigure("slider", state="normal")  # Show the slider