import customtkinter as ctk
from PIL import Image
from core import abspath
from .togglebutton import ToggleButton


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
        
    def undraw(self):
        """Undraws the point."""
        if hasattr(self, 'cpt'):
            self.canvas.delete(self.cpt)
            del self.cpt
        

class TPoints:
    """
    A class to manage tracked points on canvas, allowing for removing, and modifying points.
    """
    def __init__(self, canvas, vwidth, vheight):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self.tpts = []
        self.trsize = 15
        self.fidx = 0
        
        self.btnsize = 30
        self.delbtn = self.mkbutton("assets/bin.png", self.removept, btnsize=self.btnsize)
        # self.delbtn.configure(command=self.removept)
        self.togglebtn = ToggleButton(self.canvas, commandon=self.toggleon, commandoff=self.toggleoff)
        
        self.currpt = []
        self.sltdpt = {"tidx": None, "fidx": None, "cpt": None}
        
        self.canvas.tag_bind("points", "<Button-1>", self.onclick)
        
    
    def mkbutton(self, imgpath, command, btnsize=30):
        """
        Creates a button with an image and a command.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=btnsize, height=btnsize,
                        command=command, image=img)
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
                self.tpts[i].append(FPoint(self.canvas, pt, fx, fy, self.delbtn))
                
        self.togglebtn.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
                

    def drawpoint(self, fidx):
        """Draws a point by frame index."""
        if len(self.tpts) < 1:
            return
        
        self.fidx = fidx
        self.canvas.delete("points")
        for i,tpts in enumerate(self.tpts):
            
            # Draw previous multiple points
            for idx in range(max(self.fidx-self.trsize, 0), self.fidx+1):
                if tpts[idx] is None:
                    continue
            
                tpt = tpts[idx]
                tpt.draw()
            
                self.currpt.append([tpt.cpt, i, self.fidx])
            
    def matchid(self, id):
        for item in self.currpt:
            idp = item[0]
            
            if id == idp:
                return item
            
        return None

    def onclick(self, event):
        cid = self.canvas.find_withtag("current")[0]
        
        id, tidx, fidx = self.matchid(cid)
        
        print('fidx: ', fidx)
        self.sltdpt["cpt"] = cid
        self.sltdpt["tidx"] = tidx
        self.sltdpt["fidx"] = fidx

        sltdtpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
        
        for pt in sltdtpts:
            self.canvas.itemconfig(pt.cpt, fill='green', width=2)
            
        self.delbtn.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
        
    def toggleon(self):
        """Toggle button ON action."""
        self.delbtn.pack_forget()
        
        cid = self.canvas.find_withtag("current")[0]
        
        id, tidx, fidx = self.matchid(cid)

        sltdtpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
        
        for pt in sltdtpts:
            pt.draw()
            
    def toggleoff(self):
        """Toggle button ON action."""
        self.delbtn.pack_forget()
        
        cid = self.canvas.find_withtag("current")[0]
        
        id, tidx, fidx = self.matchid(cid)

        sltdtpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
        
        for pt in sltdtpts:
            pt.undraw()
        
    
    def removept(self):
        # cid = self.canvas.find_withtag("current")[0]
        
        # id, tidx, fidx = self.matchid(cid)
        tidx = self.sltdpt["tidx"]
        sltdtpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
        
        for pt in sltdtpts:
            # self.canvas.itemconfig(pt.cpt, fill='green', width=2)
            self.canvas.delete(pt.cpt)
            
        # self.canvas.delete(self.sltdpt["cpt"])
        self.delbtn.place_forget()
        self.tpts.pop(self.sltdpt["tidx"])
        
        self.delbtn.pack_forget()
        
    def clear(self):
        self.canvas.delete("points")
        self.tpts.clear()
        self.delbtn.place_forget()