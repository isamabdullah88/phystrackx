import customtkinter as ctk
from customtkinter import CTkCanvas
from PIL import Image
from core import abspath
from core import PixelRect
from .Label import Label
import math

class Circle:
    def __init__(self, canvas:CTkCanvas, vwidth, vheight, toggle=None):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self._rcoords = None
        self._tkcircle = None
        self.circles = []
        self.canvascircles = []
        self._tkcircles = []
        
        self.toggle = toggle
        self.btnsize = 30
        self.button = self.plcbutton("assets/bin.png", self.clearrect, btnsize=self.btnsize)
        
        self.applybtn = self.plcbutton("assets/apply.png", self.onapply, btnsize=80)
        
    def plcbutton(self, imgpath, command, btnsize=30):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                            image=img, command=command)
        
        button.image = img
        
        return button
        
    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self._tkcircles:
            self.canvas.delete(self._tkcircles[-1])
            self.circles.pop()
            self._tkcircles.pop()
            if self._tkcircles:
                self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            else:
                self.button.place_forget()
                
    def clearrects(self):
        """Deletes all drawn rectangles"""
        for rect in self._tkcircles:
            self.canvas.delete(rect)
        self._tkcircles.clear()
        # self.button.place_forget()
        
    def cleardata(self):
        self.circles.clear()
    
    def drawcircle(self, fwidth, fheight, fx, fy):
        """Draws rectangle with simple lines"""
        if fwidth is None:
            fwidth = self.vwidth
        if fheight is None:
            fheight = self.vheight
        
        def ondown(event):            
            self._rcoords = (event.x, event.y)
            
            self._tkcircle = self.canvas.create_oval(event.x, event.y, event.x, event.y, width=3)
            
        def incircle(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            # rad = math.sqrt((ex-sx)**2 + (ey-sy)**2)

            self.canvas.coords(self._tkcircle, sx, sy, ex, ey)
            
        def onrelease(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            
            self._tkcircles.append(self._tkcircle)
            self.canvas.itemconfig(self._tkcircle, outline="green")

            self.canvascircles.append(PixelRect(sx, sy, ex-sx, ey-sy))

            rect = PixelRect(sx-fx, sy-fy, ex-sx, ey-sy)            
            self.circles.append(rect.pix2norm(fwidth, fheight))
            
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            
            self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            self.applybtn.place(x=self.vwidth-110, y=self.vheight-100)
            

        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", incircle)
        self.canvas.bind("<ButtonRelease-1>", onrelease)
        
    def onapply(self):
        self.button.destroy()
        self.applybtn.destroy()
        
        if self.toggle:
            self.toggle()
            
        for i,rect in enumerate(self.canvascircles):
            x, y, w, h = rect.totuple()
            text = f"Circle-{i+1}: x={x:.0f}, y={y:.0f}, width={w:.0f}, height={h:.0f}"
            Label(self.canvas, text=text).place(x=10, y=(i+1)*30)