"""
tpoints.py

Tracked Points Visualization using CustomTkinter.

This module defines the `TrackPoints` class, which manages and displays tracked points (e.g., from 
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
from .trackpoint import TrackPoint
from .selectpoints import SelectPoints


class TrackPoints:
    """
    Manages multiple tracked points on a canvas.

    Allows drawing points, toggling their visibility, selecting
    specific trajectories, and deleting them.
    """

    def __init__(self, canvas: ctk.CTkCanvas, vwidth: int, vheight: int, tether: bool = True) -> None:
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.tether = tether

        self.tpoints: list[list[TrackPoint]] = []
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

        self.selectpoints: SelectPoints = SelectPoints(trsize=self.trsize, tether=self.tether)

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

    def addpoints(self, tpoints: list[list[int]], fx: int, fy: int) -> None:
        """
        Adds tracked points and places toggle button.

        Args:
            tpoints: 2D list of [x, y] points.
            fx: X offset to apply to all points.
            fy: Y offset to apply to all points.
        """
        if not isinstance(tpoints, list) or len(tpoints) == 0:
            return

        self.tpoints = [[] for _ in range(len(tpoints))]
        for oidx, tpoint in enumerate(tpoints):
            for fidx, point in enumerate(tpoint):
                self.tpoints[oidx].append(TrackPoint(point[:, 0], point[:, 1], fx, fy))

        self.togglebtn.place(
            x=self.vwidth - 80,
            y=self.btnsize + 60,
            anchor="nw"
        )

    def undrawpoints(self) -> None:
        """Undraw all points from canvas."""
        for tpoints in self.tpoints:
            for point in tpoints:
                point.undraw(self.canvas)

    def drawpoints(self, fidx: int) -> None:
        """
        Draws points on the canvas up to the given frame index.

        Args:
            fidx: Frame index to render points up to.
        """
        self.fidx = fidx
        self.selectpoints.fidx = fidx

        if len(self.tpoints) < 1 or not self.selectpoints.toggled:
            return

        self.undrawpoints()
        self.selectpoints.currpts.clear()

        for i, tpoints in enumerate(self.tpoints):
            if self.tether:
                for idx in range(max(self.fidx - self.trsize, 0), self.fidx + 1):
                    if tpoints[idx] is None:
                        continue
                    tpoint = tpoints[idx]
                    tpoint.draw(self.canvas)
                    self.selectpoints.currpts.append([tpoint.cpt, i, self.fidx])
            else:
                if (self.fidx >= len(tpoints)) or (tpoints[self.fidx] is None):
                    continue
                tpoint = tpoints[self.fidx]
                tpoint.draw(self.canvas)
                self.selectpoints.currpts.append([tpoint.cpt, i, self.fidx])

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
        self.selectpoints.select(self.canvas, self.tpoints, tidx, fidx)

        if self.selectpoints.selected:
            self.delbtn.place(
                x=self.vwidth / 2 - self.btnsize / 2,
                y=self.vheight - self.btnsize - 20,
                anchor="nw"
            )
        else:
            self.delbtn.place_forget()

    def toggleon(self) -> None:
        """Toggle on: show currently active trail of points."""
        self.selectpoints.toggleon(self.canvas, self.tpoints)

    def toggleoff(self) -> None:
        """Toggle off: hide current trail of points and hide delete button."""
        self.selectpoints.toggleoff(self.canvas, self.tpoints)
        self.delbtn.place_forget()

    def removept(self) -> None:
        """Remove selected point trail from canvas and internal list."""
        tidx = self.selectpoints.tidx

        if self.tether:
            sltdtpoints = self.tpoints[tidx][max(self.fidx - self.trsize, 0):self.fidx + 1]
        else:
            sltdtpoints = self.tpoints[tidx][self.fidx]

        for point in sltdtpoints:
            point.undraw(self.canvas)

        self.tpoints.pop(tidx)
        self.delbtn.place_forget()

        if len(self.tpoints) == 0:
            self.togglebtn.place_forget()

    def clear(self) -> None:
        """Remove all points from canvas and clear all data."""
        self.canvas.delete("points")
        self.tpoints.clear()
        self.delbtn.place_forget()


# === Demo App ===

def main() -> None:
    """Sample GUI to demonstrate tracked point visualization."""
    import random
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("800x600")
    root.title("TrackPoints Demo")

    canvas = ctk.CTkCanvas(root, width=800, height=600, bg="white")
    canvas.pack(fill="both", expand=True)

    tp = TrackPoints(canvas, vwidth=800, vheight=600)

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