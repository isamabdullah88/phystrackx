import customtkinter as ctk
from PIL import Image
import numpy as np
from core import abspath


class FPoint:
    """Class to manage single point clickable"""
    def __init__(self, canvas, pt, fx, fy, vwidth, vheight, button, tidx, fidx, disable=False):
        self.canvas = canvas
        self.x, self.y = pt.copy()
        self.x += fx
        self.y += fy
        self.vwidth = vwidth
        self.vheight = vheight
        self.disable = disable
        self.button = button
        
        self.tidx = tidx
        self.fidx = fidx
        self.btnsize = 30
        
    def draw(self):
        
        if self.disable:
            return
        
        self.cpt = self.canvas.create_oval(
            self.x - 6, self.y - 6, self.x + 6, self.y + 6,
            fill='red', outline='black', width=1, tags="points"
        )
        
        self.canvas.tag_bind(self.cpt, '<Button-1>', self.selectpt)
        
    def selectpt(self, event):
        self.canvas.itemconfig(self.cpt, fill='green', width=2)
        self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
        
    
        

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
        # button.pack(padx=5, pady=5)
        # Store the image reference to prevent garbage collection
        button.image = img
        
        return button
        
    
    def addpoints(self, tpts, fx, fy):
        """Sets the tracked points."""
        if not isinstance(tpts, list):
            raise TypeError("tpts must be a list of points.")
        
        self.tpts = [[] for _ in range(len(tpts))]
        
        for i, tpt in enumerate(tpts):
            for j, pt in enumerate(tpt):
                x, y = pt.copy()
                self.tpts[i].append([x, y])
                
        self.fx = fx
        self.fy = fy

    def drawpoint(self, fidx):
        """Draws a point by frame index."""
        if len(self.tpts) < 1:
            return
        
        self.canvas.delete("points")
        for i,tpts in enumerate(self.tpts):
            if tpts[fidx] is None:
                continue
            
            x, y = tpts[fidx].copy()
            x += self.fx
            y += self.fy
            
            cpt = self.canvas.create_oval(
                x - 6, y - 6, x + 6, y + 6,
                fill='red', outline='black', width=1, tags="points"
            )
            
            # self.canvas.tag_bind(self.cpt, '<Button-1>', self.selectpt)
            self.currpt.append([cpt, i, fidx])
            
            # self.currpt["cpts"].append(cpt)
            # self.currpt["tidx"].append(i)
            # self.currpt["fidx"] = fidx
            
            
            
            
                
    def onclick(self, event):
        cid = self.canvas.find_withtag("current")
        print('cid: ', cid)
        if cid:
            self.sltdpt["cpt"] = cid[0]
        
        for item in self.currpt:
            id = item[0]
            if id == self.sltdpt["cpt"]:
                self.sltdpt["tidx"] = item[1]
                self.sltdpt["fidx"] = item[2]
                
                self.canvas.itemconfig(id, fill='green', width=2)
                self.button.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
    
    def removept(self):
        self.canvas.delete(self.sltdpt["cpt"])
        self.button.place_forget()
        self.tpts[self.sltdpt["tidx"]][self.sltdpt["fidx"]] = None
        
        self.button.pack_forget()
        
        