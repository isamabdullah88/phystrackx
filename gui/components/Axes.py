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
        
        self.ox = 0
        self.oy = 0
        
        self.slider = ttk.Scale(self.root, from_=0, to=180, orient='horizontal', variable=self.theta,
                            command=self.rotate)
        self.canvas.create_window(self.vwidth - 60, self.vheight - 20, window=self.slider, tags="slider")
        self.canvas.itemconfigure("slider", state="hidden")  # Hide the slider initially
    
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
        
    def canvas2norm(self, x, y):
        """ Transform coordinates from canvas coordinate-frame to regular frame. """
        y = self.vheight - y
        return x, y
    
    def norm2canvas(self, x, y):
        """ Transform coordinates from regular frame to canvas coordinate-frame. """
        y = self.vheight - y
        return x, y
    
    def rotatez(self, x, y, theta):
        """ Rotate a point (x, y) around the origin (z-axis) by angle theta in radians. """
        ctheta = np.cos(theta)
        stheta = np.sin(theta)
        xp = x * ctheta - y * stheta
        yp = x * stheta + y * ctheta
        return xp, yp
        
    def rotate(self, event):
        """ Rotate the axes by a given angle theta. """
        self.canvas.delete("axes")

        theta = np.deg2rad(self.theta.get())  # Get the current angle from the slider
        
        x0 = self.vwidth
        y0 = self.oy
        
        x1 = self.ox
        y1 = self.vheight
        
        ox, oy = self.canvas2norm(self.ox, self.oy)  # Convert origin to regular coordinates
        x0, y0 = self.canvas2norm(x0, y0)  # Convert to regular coordinates
        x1, y1 = self.canvas2norm(x1, y1)  # Convert to regular coordinates
        
        x0 -= ox
        y0 -= oy
        x1 -= ox
        y1 -= oy
        
        # Rotate x-axis point
        xp0, yp0 = self.rotatez(x0, y0, theta)
        xp0 += ox
        yp0 += oy
        
        # Rotate y-axis point
        xp1, yp1 = self.rotatez(x1, y1, theta)
        xp1 += ox
        yp1 += oy
        
        def startpt(x, y):
            """ Calculate the starting point for the axes based on the center and end points. """
            if abs(x - self.ox) < 1e-3:  # Avoid division by zero
                sx = self.ox
                sy = 0
            else:
                m = -(y-self.oy)/(x-self.ox)
                b = m*self.ox - self.oy
                sx = 0
                sy = m*sx + b
            
            return sx, sy
        
        # Transforming back into tkinter coordinates
        ox, oy = self.norm2canvas(ox, oy)
        xp0, yp0 = self.norm2canvas(xp0, yp0)
        xp1, yp1 = self.norm2canvas(xp1, yp1)
        
        dot = (xp0-ox)*(xp1-ox) + (yp0-oy)*(yp1-oy)
        if abs(dot) > 1e-10:
            print('Dot: ', dot)

        
        self.drawaxes((ox, oy), (ox, oy), (xp0, yp0), (xp1, yp1))
        
    
    def onmove(self, event):
        """ Update the axes to follow the mouse cursor. """
        self.canvas.delete("axes")  # Remove old axes
        x, y = event.x, event.y  # Get mouse position

        self.drawaxes((0, y), (x, 0), (self.vwidth, y), (x, self.vheight))

    def onclick(self, event):
        """ Store the clicked coordinates and draw a point. """
        x, y = event.x, event.y

        self.ox = x
        self.oy = y

        self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="red", tags="oval")  # Draw a small dot

        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<Button-1>")

        self.canvas.itemconfigure("slider", state="normal")  # Show the slider