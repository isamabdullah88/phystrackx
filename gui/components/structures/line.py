import customtkinter as ctk
from PIL import Image
from core import abspath, PixelRect, Points
from ..label import Label

class Line:
    def __init__(self, canvas, vwidth, vheight, btnlist, activebtn, toggle=None):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self._rcoords = None
        self._ctkline = None
        self.line = Points()
        self.canvaslines = []
        self.tklines = []
        self.tkpts = []
        
        self.labels = []
        
        self.toggle = toggle
        self.btnsize = 30
        self.button = self.mkbutton("assets/bin.png", self.clearline, btnsize=self.btnsize)
        
        self.applybtn = self.mkbutton("assets/apply.png", self.onapply, btnsize=80)
        # self.applied = False
        
        self.btnlist = btnlist
        self.activebtn = activebtn
        
        
    def mkbutton(self, imgpath, command, btnsize=30):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                            image=img, command=command)
        
        button.image = img
        
        return button
        
    # def clearrect(self):
    #     """Deletes the last drawn rectangle"""
    #     if self.tklines:
    #         self.canvas.delete(self.tklines[-1])
    #         self.line.pop()
    #         self.tklines.pop()
    #         if self.tklines:
    #             self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
    #         else:
    #             self.button.place_forget()
                
    def clearline(self):
        """Deletes all drawn points in line"""
        for tkline in self.tklines:
            self.canvas.delete(tkline)
        self.tklines.clear()

        for tkpt in self.tkpts:
            self.canvas.delete(tkpt)
        self.tkpts.clear()
        
    def clear(self):
        for label in self.labels:
            label.clear()
            
        self.labels.clear()
            
        self.clearline()
        self.line.clear()
        self.canvaslines.clear()
    
    def drawline(self, fwidth, fheight, fx, fy):
        """Draws series of lines"""
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
            
            self.line.addpt(event.x-fx, event.y-fy)

            for i in range(len(self.line)):
                x0, y0 = self.line[i]
                tkpt = self.canvas.create_oval(x0+fx-2, y0+fy-2, x0+fx+2, y0+fy+2,
                                           fill="red", outline="black")
                self.tkpts.append(tkpt)
                
                if i > len(self.line) - 2:
                    continue

                x1, y1 = self.line[i+1]
                
                tkline = self.canvas.create_line(x0+fx, y0+fy, x1+fx, y1+fy,
                                           fill="magenta", width=3)
                
                self.tklines.append(tkline)
            
        def inrect(event):

            if len(self.line) < 1:
                return
            
            ex, ey = (event.x, event.y)
            
            if self._ctkline is None:
                x0, y0 = self.line[-1]
                self._ctkline = self.canvas.create_line(x0+fx, y0+fy, ex+fx,
                                                           ey+fy, fill="magenta", width=3)
                
                return
            
            x1, y1 = self.line[-1]
            self.canvas.coords(self._ctkline, x1+fx, y1+fy, event.x, event.y)
            
        def onescape(event):
            """Escape key to clear the drawn line"""
            if self._ctkline is not None:
                self.canvas.delete(self._ctkline)
                self._ctkline = None
                # self._lcoords = []
            
            self.line = self.line.pix2norm(fwidth, fheight)
            
            self.canvas.unbind("<Button>")
            self.canvas.unbind("<Motion>")
            self.canvas.unbind("<Escape>")

            print('lines: ', self.line)

            
            self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
            self.applybtn.place(x=self.vwidth-110, y=self.vheight-100)
            

        self.canvas.bind("<Button>", ondown)
        self.canvas.bind("<Motion>", inrect)
        self.canvas.bind("<Escape>", onescape)
        self.canvas.focus_set()
        
    def onapply(self):
        """Finalize lines and colors on apply"""
        for tkline in self.tklines:
            self.canvas.itemconfig(tkline, fill="green", width=2)

        for tkpt in self.tkpts:
            self.canvas.itemconfig(tkpt, fill="green", width=2)
        
        self.button.place_forget()
        self.applybtn.place_forget()
        
        # self.applied = True
        
        # for i,rect in enumerate(self.canvaslines):
        #     x, y, w, h = rect.totuple()
        #     text = f"Rect-{i+1}: x={x:.0f}, y={y:.0f}, width={w:.0f}, height={h:.0f}"
        #     label = Label(self.canvas, text=text)
        #     label.place(x=10, y=80 + (i+1)*30)
        #     self.labels.append(label)
        
        # Activate all buttons
        for k,btn in self.btnlist.items():
            btn.configure(state="normal")