"""
tpoints.py

Tracked Points Visualization using CustomTkinter.

This module defines the `TPoints` class, which manages and displays tracked points (e.g., from 
motion tracking or video annotation) on a `customtkinter.CTkCanvas`. Features include toggling 
visibility of point trails, selecting individual trajectories, and deleting selected ones 
interactively.

Author: [Isam Balghari]
"""

from typing import Optional
import customtkinter as ctk
from PIL import Image
from core import abspath
from ..togglebutton import ToggleButton
from .fpoint import FPoint
from .selectpoints import SelectPoints


class TPoints:
    """
    Manages multiple tracked points on a canvas.

    Allows drawing points, toggling their visibility, selecting
    specific trajectories, and deleting them.
    """

    def __init__(self, canvas: ctk.CTkCanvas, vwidth: int, vheight: int) -> None:
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight

        self.tpts: list[list[FPoint]] = []
        self.currpts: list[list[int]] = []

        self.trsize: int = 15
        self.fidx: int = 0
        self.btnsize: int = 30
        self.toggled: bool = True

        self.delbtn: ctk.CTkButton = self._mkbutton("assets/bin.png", self.removept)
        self.togglebtn: ToggleButton = ToggleButton(
            canvas,
            commandon=self.toggleon,
            commandoff=self.toggleoff
        )

        self.selectpoints: SelectPoints = SelectPoints(trsize=self.trsize)

        self.canvas.tag_bind("points", "<Button-1>", self.onclick)

    def _mkbutton(self, imgpath: str, command: callable) -> ctk.CTkButton:
        """Creates a CTkButton with an image and command."""
        img = Image.open(abspath(imgpath)).resize(
            (self.btnsize, self.btnsize), Image.Resampling.LANCZOS
        )
        ctkimg = ctk.CTkImage(light_image=img, dark_image=img, size=(self.btnsize, self.btnsize))
        button = ctk.CTkButton(
            self.canvas, text="", width=self.btnsize, height=self.btnsize,
            command=command, image=ctkimg
        )
        button.image = ctkimg
        return button

    def addpoints(self, tpts: list[list[int]], fx: int, fy: int) -> None:
        """
        Adds tracked points and places toggle button.

        Args:
            tpts: 2D list of [x, y] points.
            fx: X offset to apply to all points.
            fy: Y offset to apply to all points.
        """
        if not isinstance(tpts, list) or len(tpts) == 0:
            return

        self.tpts = [[] for _ in range(len(tpts))]
        for i, tpt in enumerate(tpts):
            for pt in tpt:
                self.tpts[i].append(FPoint(pt[0], pt[1], fx, fy))

        self.togglebtn.pack(side=ctk.TOP, anchor=ctk.E, padx=10, pady=10)

    def undrawpoints(self) -> None:
        """Undraw all points from canvas."""
        for tpts in self.tpts:
            for pt in tpts:
                pt.undraw(self.canvas)

    def drawpoints(self, fidx: int) -> None:
        """
        Draws points on the canvas up to the given frame index.

        Args:
            fidx: Frame index to render points up to.
        """
        self.fidx = fidx
        self.selectpoints.fidx = fidx

        if (len(self.tpts) < 1) or not self.selectpoints.toggled:
            return

        self.undrawpoints()
        self.selectpoints.currpts.clear()

        for i, tpts in enumerate(self.tpts):
            for idx in range(max(self.fidx - self.trsize, 0), min(self.fidx + 1, len(tpts))):
                if tpts[idx] is None:
                    continue
                tpt = tpts[idx]
                tpt.draw(self.canvas)
                self.selectpoints.currpts.append([tpt.cpt, i, self.fidx])

    def matchid(self, cid: int) -> Optional[list[int]]:
        """
        Match canvas item ID to tracked point metadata.

        Args:
            cid: Canvas item ID.

        Returns:
            List with [cpt_id, tidx, fidx] or None if not found.
        """
        for item in self.selectpoints.currpts:
            if cid == item[0]:
                return item
        return None

    def onclick(self, event: object) -> None:
        """Handle click on canvas point and show delete button if valid."""
        cid = self.canvas.find_withtag("current")[0]
        match = self.matchid(cid)
        if not match:
            return

        _, tidx, fidx = match
        self.selectpoints.select(self.canvas, self.tpts, tidx, fidx)

        if self.selectpoints.selected:
            self.delbtn.pack(anchor=ctk.N, pady=10)
        else:
            # self.delbtn.place_forget()
            self.delbtn.pack_forget()

    def toggleon(self) -> None:
        """Toggle on: show currently active trail of points."""
        self.selectpoints.toggleon(self.canvas, self.tpts)

    def toggleoff(self) -> None:
        """Toggle off: hide current trail of points and hide delete button."""
        self.selectpoints.toggleoff(self.canvas, self.tpts)
        self.delbtn.pack_forget()

    def removept(self) -> None:
        """Remove selected point trail from canvas and internal list."""
        tidx = self.selectpoints.tidx
        sltdtpts = self.tpts[tidx][max(self.fidx - self.trsize, 0):self.fidx + 1]

        for pt in sltdtpts:
            pt.undraw(self.canvas)

        self.tpts.pop(tidx)
        self.delbtn.pack_forget()

        if len(self.tpts) == 0:
            # self.togglebtn.place_forget()
            self.togglebtn.pack_forget()

    def clear(self) -> None:
        """Remove all points from canvas and clear all data."""
        self.canvas.delete("points")
        self.tpts.clear()
        self.delbtn.pack_forget()
        self.togglebtn.pack_forget()


# === Demo App ===

def main() -> None:
    """Sample GUI to demonstrate tracked point visualization."""
    import random
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("800x600")
    root.title("TPoints Demo")

    canvas = ctk.CTkCanvas(root, width=800, height=600, bg="white")
    canvas.pack(fill="both", expand=True)

    tp = TPoints(canvas, vwidth=800, vheight=600)

    # Generate dummy tracked points: 2 objects, each with 5 points
    tracks: list[list[float]] = []
    for _ in range(2):
        track = []
        x, y = random.randint(100, 300), random.randint(100, 300)
        for i in range(5):
            track.append([x + i * 10, y + i * 5])
        tracks.append(track)

    tp.addpoints(tracks, fx=0, fy=0)
    tp.drawpoints(fidx=4)

    root.mainloop()


if __name__ == "__main__":
    main()