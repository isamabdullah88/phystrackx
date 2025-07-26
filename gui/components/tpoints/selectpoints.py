
import tkinter as tk
from .fpoint import FPoint

class SelectPoints:
    def __init__(self, trsize:int):
        self.selectedpoints = []
        self.tidx = None
        self.fidx = None
        self.tkid = None
        
        self.trsize = trsize
        self.selected = False
        self.toggled = True
        
        self.currpts = []  # To store currently selected points for toggling
        
    def select(self, canvas: tk.Canvas, points: list[FPoint], tidx:int, fidx:int):
        """
        Highlight the selected points on the canvas.

        Args:
            canvas (CTkCanvas): The canvas to highlight on.
        """
        if self.selectedpoints:
            for point in self.selectedpoints:
                point.deselect(canvas)
            self.selectedpoints.clear()
            self.selected = False
        else:
            self.tidx = tidx
            self.fidx = fidx
            self.selectedpoints = points[tidx][max(fidx - self.trsize, 0):fidx + 1]
            
            for point in self.selectedpoints:
                point.select(canvas)
            self.selected = True
            
    def toggleon(self, canvas:tk.Canvas, points:list[FPoint]):
        """Show all frames' trail of points."""
        for i,tpts in enumerate(points):
            for pt in tpts[max(self.fidx - self.trsize, 0):self.fidx + 1]:
                pt.draw(canvas)
                self.currpts.append([pt.cpt, i, self.fidx])
                
        self.toggled = True
        
    def toggleoff(self, canvas:tk.Canvas, points:list[FPoint]):
        """Hide all frames' trail of points."""
        for tpts in points:
            for pt in tpts[max(self.fidx - self.trsize, 0):self.fidx + 1]:
                pt.undraw(canvas)
        self.toggled = False