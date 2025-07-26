"""
Tracked Points Visualization using CustomTkinter.

This script provides classes to visualize, toggle, and delete 
tracked points on a canvas using CustomTkinter.
"""

import customtkinter as ctk
from PIL import Image
from core import abspath
from ..togglebutton import ToggleButton
from .fpoint import FPoint

class TPoints:
    """
    Manages multiple tracked points on a canvas, allowing drawing,
    toggling visibility, selection, and deletion.
    """
    def __init__(self, canvas, vwidth, vheight):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight

        self.tpts = []
        self.currpts = []
        self.trsize = 15
        self.fidx = 0
        self.btnsize = 30
        self.toggled = True

        self.sltdpt = {"tidx": None, "fidx": None, "cpt": None}

        self.delbtn = self._mkbutton("assets/bin.png", self.removept)
        self.togglebtn = ToggleButton(canvas, commandon=self.toggleon, commandoff=self.toggleoff)

        self.canvas.tag_bind("points", "<Button-1>", self.onclick)

    def _mkbutton(self, imgpath, command):
        """Creates a CTkButton with an image and command."""
        img = Image.open(abspath(imgpath)).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(self.btnsize, self.btnsize))
        button = ctk.CTkButton(self.canvas, text="", width=self.btnsize, height=self.btnsize,
                               command=command, image=img)
        button.image = img
        return button

    def addpoints(self, tpts, fx, fy):
        """Add points (2D list of coords) and place toggle button."""
        if not isinstance(tpts, list) or len(tpts) == 0:
            return

        self.tpts = [[] for _ in range(len(tpts))]
        for i, tpt in enumerate(tpts):
            for pt in tpt:
                self.tpts[i].append(FPoint(pt, fx, fy, self.delbtn))

        self.togglebtn.place(x=self.vwidth - 80, y=self.btnsize + 60, anchor="nw")

    def undrawpoints(self):
        """Undraw all points from canvas."""
        for tpts in self.tpts:
            for pt in tpts:
                pt.undraw(self.canvas)

    def drawpoints(self, fidx):
        """Draw points up to a given frame index."""
        self.fidx = fidx
        if len(self.tpts) < 1 or not self.toggled:
            return

        self.undrawpoints()
        self.currpts.clear()

        for i, tpts in enumerate(self.tpts):
            for idx in range(max(self.fidx - self.trsize, 0), self.fidx + 1):
                if tpts[idx] is None:
                    continue
                tpt = tpts[idx]
                tpt.draw(self.canvas)
                self.currpts.append([tpt.cpt, i, self.fidx])

    def matchid(self, cid):
        """Find matching tracked point by canvas ID."""
        for item in self.currpts:
            if cid == item[0]:
                return item
        return None

    def onclick(self, event):
        """Handle canvas point click and show delete button."""
        cid = self.canvas.find_withtag("current")[0]
        match = self.matchid(cid)
        if not match:
            return

        _, tidx, fidx = match
        self.sltdpt.update({"cpt": cid, "tidx": tidx, "fidx": fidx})

        sltdtpts = self.tpts[tidx][max(self.fidx - self.trsize, 0):self.fidx + 1]
        for pt in sltdtpts:
            self.canvas.itemconfig(pt.cpt, fill='green', width=2)

        self.delbtn.place(x=self.vwidth / 2 - self.btnsize / 2, y=self.vheight - self.btnsize - 20, anchor="nw")

    def toggleon(self):
        """Show current frame's trail of points."""
        for i,tpts in enumerate(self.tpts):
            for pt in tpts[max(self.fidx - self.trsize, 0):self.fidx + 1]:
                pt.draw(self.canvas)
                self.currpts.append([pt.cpt, i, self.fidx])
        self.toggled = True

    def toggleoff(self):
        """Hide current frame's trail of points."""
        for tpts in self.tpts:
            for pt in tpts[max(self.fidx - self.trsize, 0):self.fidx + 1]:
                pt.undraw(self.canvas)
        self.delbtn.place_forget()
        self.toggled = False

    def removept(self):
        """Remove selected trajectory from canvas and list."""
        tidx = self.sltdpt["tidx"]
        sltdtpts = self.tpts[tidx][max(self.fidx - self.trsize, 0):self.fidx + 1]

        for pt in sltdtpts:
            self.canvas.delete(pt.cpt)

        self.tpts.pop(tidx)
        self.delbtn.place_forget()

    def clear(self):
        """Clear all tracked points."""
        self.canvas.delete("points")
        self.tpts.clear()
        self.delbtn.place_forget()


def main():
    """Run a sample app with random tracked points."""
    import random
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("800x600")
    root.title("TPoints Demo")

    canvas = ctk.CTkCanvas(root, width=800, height=600, bg="white")
    canvas.pack(fill="both", expand=True)

    tp = TPoints(canvas, vwidth=800, vheight=600)

    # Create 2 objects with 5 points each
    tpts = []
    for _ in range(2):
        track = []
        x, y = random.randint(100, 300), random.randint(100, 300)
        for i in range(5):
            track.append([x + i * 10, y + i * 5])
        tpts.append(track)

    tp.addpoints(tpts, fx=0, fy=0)
    tp.drawpoints(fidx=4)

    root.mainloop()


if __name__ == "__main__":
    main()
