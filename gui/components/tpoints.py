import customtkinter as ctk
from PIL import Image
from core import abspath


class FPoint:
    """Class to manage single point clickable"""
    def __init__(self, canvas, pt, fx, fy, button, disable=False):
        self.canvas = canvas
        self.x, self.y = pt.copy()
        self.x += fx
        self.y += fy
        
        self.disable = disable
        self.button = button
        
        self.btnsize = 30
        
    def draw(self):
        
        if self.disable:
            return
        
        self.cpt = self.canvas.create_oval(
            self.x - 6, self.y - 6, self.x + 6, self.y + 6,
            fill='magenta', outline='black', width=1, tags="points"
        )
        

class TPoints:
    """
    A class to manage tracked points on canvas, allowing for removing, and modifying points.
    """
    def __init__(self, canvas, vwidth, vheight):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self.tpts = []
        
        self.btnsize = 30
        self.button = self.plcbutton("assets/bin.png", btnsize=self.btnsize)
        self.button.configure(command=self.removept)
        
        self.currpt = []
        self.sltdpt = {"tidx": None, "fidx": None, "cpt": None}
        
        self.canvas.tag_bind("points", "<Button-1>", self.onclick)
        
    
    def plcbutton(self, imgpath, btnsize=30):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                            image=img)
        button.image = img
        
        return button
        
    
    def addpoints(self, tpts, fx, fy):
        """Sets the tracked points."""
        if not isinstance(tpts, list):
            raise TypeError("tpts must be a list of points.")
        
        if len(tpts) == 0:
            return
        
        self.tpts = [[] for _ in range(len(tpts))]
        
        for i, tpt in enumerate(tpts):
            for j, pt in enumerate(tpt):
                self.tpts[i].append(FPoint(self.canvas, pt, fx, fy, self.button))
                

    def drawpoint(self, fidx):
        """Draws a point by frame index."""
        if len(self.tpts) < 1:
            return
        
        self.canvas.delete("points")
        for i,tpts in enumerate(self.tpts):
            if tpts[fidx] is None:
                continue
            
            tpt = tpts[fidx]
            tpt.draw()
            
            self.currpt.append([tpt.cpt, i, fidx])
            
    def matchid(self, id):
        for item in self.currpt:
            idp = item[0]
            
            if id == idp:
                return item
            
        return None

    def onclick(self, event):
        cid = self.canvas.find_withtag("current")[0]
        
        id, tidx, fidx = self.matchid(cid)
        
        self.sltdpt["cpt"] = cid
        self.sltdpt["tidx"] = tidx
        self.sltdpt["fidx"] = fidx

        self.canvas.itemconfig(id, fill='green', width=2)
        self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
    
    def removept(self):
        self.canvas.delete(self.sltdpt["cpt"])
        self.button.place_forget()
        self.tpts.pop(self.sltdpt["tidx"])
        
        self.button.pack_forget()
        
    def clear(self):
        self.canvas.delete("points")
        self.tpts.clear()
        self.button.place_forget()