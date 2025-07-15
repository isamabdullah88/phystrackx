import customtkinter as ctk
from PIL import Image
from core import abspath
from core import PixelRect
from .label import Label

class Rect:
    def __init__(self, canvas, vwidth, vheight, btnlist, activebtn, toggle=None):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self._rcoords = None
        self._ctkbox = None
        self.rects = []
        self.canvasrects = []
        self._ctkrects = []
        
        self.labels = []
        
        self.toggle = toggle
        self.btnsize = 30
        self.button = self.plcbutton("assets/bin.png", self.clearrect, btnsize=self.btnsize)
        
        self.applybtn = self.plcbutton("assets/apply.png", self.onapply, btnsize=80)
        self.applied = False
        
        self.btnlist = btnlist
        self.activebtn = activebtn
        
        
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
        
    def clear(self):
        for label in self.labels:
            label.clear()
            
        self.labels.clear()
            
        self.clearrects()
        self.rects.clear()
        self.canvasrects.clear()
    
    def drawrect(self, fwidth, fheight, fx, fy):
        """Draws rectangle with simple lines"""
        # Disable other buttons
        for k,btn in self.btnlist.items():
            if btn != self.activebtn:
                btn.configure(state="disabled")
                
        if fwidth is None:
            fwidth = self.vwidth
        if fheight is None:
            fheight = self.vheight
        
        def ondown(event):           
            self._rcoords = (event.x, event.y)
            
            self._ctkbox = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red", width=3)
            
        def inrect(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)

            self.canvas.coords(self._ctkbox, sx, sy, ex, ey)
            
        def onrelease(event):
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            
            self._ctkrects.append(self._ctkbox)
            self.canvas.itemconfig(self._ctkbox, outline="magenta")

            self.canvasrects.append(PixelRect(sx, sy, ex-sx, ey-sy))

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
        """Finalize rects and colors on apply"""
        for tkrect in self._ctkrects:
            self.canvas.itemconfig(tkrect, outline="green", width=2)
        
        self.button.place_forget()
        self.applybtn.place_forget()
        
        self.applied = True
        
        # if self.toggle:
        #     self.toggle()
            
        for i,rect in enumerate(self.canvasrects):
            x, y, w, h = rect.totuple()
            text = f"Rect-{i+1}: x={x:.0f}, y={y:.0f}, width={w:.0f}, height={h:.0f}"
            label = Label(self.canvas, text=text)
            label.place(x=10, y=80 + (i+1)*30)
            self.labels.append(label)
        
        # Activate all buttons
        for k,btn in self.btnlist.items():
            btn.configure(state="normal")