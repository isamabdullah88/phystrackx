

class Seek:
    """Implements and draws the seek part of a seekbar. A horizontal bar of seek"""
    def __init__(self, canvas, x0, x1, y, height=8):
        self.canvas = canvas
        
        self.hhalf = height/2
        self.x0 = x0
        self.x1 = x1
        self.y = y
        
        self.tkrectb = None
        self.tkrect = None
        
    def draw(self, x0, x1):
        # Draw background bar
        # self.tkrectb = self.canvas.create_rectangle(self.x0, self.y-self.hhalf, self.x1, self.y+self.hhalf, fill="#e2bcc5")

        # Draw selected range
        self.tkrect = self.canvas.create_rectangle(x0+1, self.y-self.hhalf-1, x1, self.y+self.hhalf+1, fill="#ee7ae8", outline="")
        
    def clear(self):
        if self.tkrectb is not None:
            self.canvas.delete(self.tkrectb)
            
        if self.tkrect is not None:
            self.canvas.delete(self.tkrect)