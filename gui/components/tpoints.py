import customtkinter as ctk
from PIL import Image
from core import abspath
from .togglebutton import ToggleButton


class FPoint:
    """Class to manage single point clickable"""
    def __init__(self, pt, fx, fy, button):
        # self.canvas = canvas
        self.x, self.y = pt.copy()
        self.x += fx
        self.y += fy
        
        self.button = button
        
        self.cpt = None
        
    def draw(self, canvas):
        
        if self.cpt is not None:
            return
        
        self.cpt = canvas.create_oval(
            self.x - 6, self.y - 6, self.x + 6, self.y + 6,
            fill='magenta', outline='black', width=1, tags="points"
        )
        
    def undraw(self, canvas):
        """Undraws the point."""
        if self.cpt is not None:
            print('undrawing point: ', self.cpt)
            canvas.delete(self.cpt)
            self.cpt = None
        

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
        self.toggled = True
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
                self.tpts[i].append(FPoint(pt, fx, fy, self.delbtn))
                
        self.togglebtn.place(x=self.vwidth-50-30, y=self.btnsize + 60, anchor="nw")
                
    def undrawpoints(self):
        """Undraws all points."""
        for tpts in self.tpts:
            for pt in tpts:
                pt.undraw(self.canvas)
        

    def drawpoints(self, fidx):
        """Draws a point by frame index."""
        self.fidx = fidx
        if (len(self.tpts) < 1) or (not self.toggled):
            return
        
        # Undraw points
        self.undrawpoints()
        
        print('Drawing points at frame index: ', fidx)
        for i,tpts in enumerate(self.tpts):
            
            # Draw previous multiple points
            for idx in range(max(self.fidx-self.trsize, 0), self.fidx+1):
                if tpts[idx] is None:
                    continue
            
                tpt = tpts[idx]
                tpt.draw(self.canvas)
            
                self.currpt.append([tpt.cpt, i, self.fidx])
            
    def matchid(self, id):
        for item in self.currpt:
            idp = item[0]
            
            if id == idp:
                return item
            
        return None

    def onclick(self, event):
        cid = self.canvas.find_withtag("current")[0]
        print('cid: ', cid)
        
        id, tidx, fidx = self.matchid(cid)
        
        self.sltdpt["cpt"] = cid
        self.sltdpt["tidx"] = tidx
        self.sltdpt["fidx"] = fidx

        sltdtpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
        
        for pt in sltdtpts:
            self.canvas.itemconfig(pt.cpt, fill='green', width=2)
            
        self.delbtn.place(x=self.vwidth/2-self.btnsize/2, y=self.vheight-self.btnsize-20, anchor="nw")
        
    def toggleon(self):
        """Toggle button ON action."""
        print('tpts: ', len(self.tpts))
        
        print('fidx [ON]: ', self.fidx)
        for tidx,_ in enumerate(self.tpts):
            currpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
            print('currpts[ON]: ', len(currpts))
            for pt in currpts:
                pt.draw(self.canvas)
                
        self.toggled = True
            
    def toggleoff(self):
        """Toggle button ON action."""
        print('tpts: ', len(self.tpts))
        self.delbtn.pack_forget()
        
        print('fidx [OFF]: ', self.fidx)
        for tidx,tpts in enumerate(self.tpts):
            currpts = self.tpts[tidx][max(self.fidx-self.trsize, 0):self.fidx+1]
            # print('currpts: ', len(currpts))
            for pt in currpts:
                # pt.undraw(self.canvas)
                print('cpt: ', pt.cpt)
                # self.canvas.delete(pt.cpt)
                pt.undraw(self.canvas)
                
        self.toggled = False
        
    
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
        

import customtkinter as ctk
import random

def main():
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("800x600")
    root.title("TPoints Demo")

    canvas = ctk.CTkCanvas(root, width=800, height=600, bg="white")
    canvas.pack(fill="both", expand=True)

    # Instantiate TPoints
    tp = TPoints(canvas, vwidth=800, vheight=600)

    # Generate dummy tracked points (e.g. 2 trajectories with 5 points each)
    tpts = []
    for _ in range(2):  # 2 objects
        track = []
        x, y = random.randint(100, 300), random.randint(100, 300)
        for i in range(5):  # 5 frames
            track.append([x + i * 10, y + i * 5])
        tpts.append(track)

    tp.addpoints(tpts, fx=0, fy=0)
    tp.drawpoints(fidx=4)  # Draw up to frame 4

    root.mainloop()

if __name__ == "__main__":
    main()
