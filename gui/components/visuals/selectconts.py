"""
selectpoints.py

This module defines the SelectConts class, which provides functionality
for selecting and toggling the visibility of tracked points (TrackPoint instances)
on a tkinter or CustomTkinter canvas.

It is typically used to:
- Highlight specific trajectories based on user interaction (e.g., mouse clicks),
- Toggle visibility of point trails for a given frame window,
- Manage the selection state for deletion or visual feedback.

Intended for use in interactive visualizations involving motion tracking,
trajectory labeling, or point annotation tasks.

Author: [Isam Balghari]
"""

import tkinter as tk
from typing import List, Optional
from .contpoint import ContPoint


class SelectConts:
    """
    Handles selection and toggling of point trajectories on a canvas.
    """
    def __init__(self, trsize: int) -> None:
        """
        Args:
            trsize: Number of trailing frames to include in selection and visibility.
        """
        self.trsize: int = trsize

        self.selectedpoints: List[ContPoint] = []
        self.currpts: List[List[int]] = []  # Format: [canvas_id, traj_index, frame_index]

        self.tidx: Optional[int] = None  # Selected trajectory index
        self.fidx: Optional[int] = None  # Current frame index
        self.tkid: Optional[int] = None  # Placeholder for future use (e.g. tag or timer ID)

        self.selected: bool = False
        self.toggled: bool = True

    def select(self, canvas: tk.Canvas, points: List[List[ContPoint]], tidx: int, fidx: int) -> None:
        """
        Toggle selection for a trajectory. Highlights the selected trail on the canvas.

        Args:
            canvas: The canvas to draw on.
            points: List of all trajectories (each a list of FPoints).
            tidx: Index of trajectory to select.
            fidx: Current frame index.
        """
        if self.selectedpoints:
            for pt in self.selectedpoints:
                pt.deselect(canvas)
            self.selectedpoints.clear()
            self.selected = False
        else:
            self.tidx = tidx
            self.fidx = fidx
            self.selectedpoints = points[tidx][fidx]
            for pt in self.selectedpoints:
                pt.select(canvas)
            self.selected = True

    def toggleon(self, canvas: tk.Canvas, points: List[List[ContPoint]]) -> None:
        """
        Show all currently valid points (within trail size) on the canvas.

        Args:
            canvas: The canvas to draw on.
            points: List of all trajectories.
        """
        if self.fidx is None:
            return

        for i, tpts in enumerate(points):
            pt = tpts[self.fidx]
            pt.draw(canvas)
            self.currpts.append([pt.cpt, i, self.fidx])

        self.toggled = True

    def toggleoff(self, canvas: tk.Canvas, points: List[List[ContPoint]]) -> None:
        """
        Hide all points for the current frame's trail from the canvas.

        Args:
            canvas: The canvas to remove drawings from.
            points: List of all trajectories.
        """
        if self.fidx is None:
            return

        for tpts in points:
            # for pt in tpts[max(self.fidx - self.trsize, 0):self.fidx + 1]:
            pt = tpts[self.fidx]
            pt.undraw(canvas)

        self.toggled = False
