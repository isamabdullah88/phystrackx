import customtkinter as ctk
from PIL import Image
from core import abspath
from core import PixelRect

class Rect:
    def __init__(self, canvas, vwidth, vheight, toggle=None):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self._rcoords = None
        self._ctkbox = None
        self.rects = []
        self._ctkrects = []
        
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
        if self._ctkrects:
            self.canvas.delete(self._ctkrects[-1])
            self.rects.pop()
            self._ctkrects.pop()
            if self._ctkrects:
                self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            else:
                self.button.place_forget()
                
    def clearrects(self):
        """Deletes all drawn rectangles"""
        for rect in self._ctkrects:
            self.canvas.delete(rect)
        self._ctkrects.clear()
        # self.button.place_forget()
        
    def cleardata(self):
        self.rects.clear()
    
    def drawrect(self, fwidth, fheight, fx, fy):
        """Draws rectangle with simple lines"""
        if fwidth is None:
            fwidth = self.vwidth
        if fheight is None:
            fheight = self.vheight
        
        def ondown(event):            
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            self.canvas.coords(self._ctkbox, sx, sy, ex, ey)
            
        def onrelease(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            
            self._ctkrects.append(self._ctkbox)
            self.canvas.itemconfig(self._ctkbox, outline="green")

            rect = PixelRect(sx-fx, sy-fy, ex-sx, ey-sy)
            
            self.rects.append(rect.pix2norm(fwidth, fheight))
            
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            
            self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            self.applybtn.place(x=self.vwidth-110, y=self.vheight-100)
            

        self.canvas.bind("<Button-1>", ondown)
        self.canvas.bind("<B1-Motion>", inrect)
        self.canvas.bind("<ButtonRelease-1>", onrelease)
        
    def onapply(self):
        self.button.destroy()
        self.applybtn.destroy()
        
        if self.toggle:
            self.toggle()