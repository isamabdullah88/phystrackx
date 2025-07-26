

class SelectPoints:
    def __init__(self, trsize):
        self.selectedpoints = []
        self.tidx = None
        self.fidx = None
        self.tkid = None
        
        self.trsize = trsize
        self.selected = False
        
    def select(self, canvas, points, tidx, fidx):
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