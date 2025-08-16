from math import floor

class PixelRect:
    """Pixel Rectangle Class"""
    def __init__(self, xmin, ymin, width, height):
        self.xmin = floor(xmin)
        self.ymin = floor(ymin)
        self.width = floor(width)
        self.height = floor(height)

        self.xmax = self.xmin + self.width
        self.ymax = self.ymin + self.height
        
    def pix2norm(self, fwidth, fheight):
        """Convert pixel rect to normalized rect"""
        return NormalizedRect(self.xmin/fwidth, self.ymin/fheight, self.width/fwidth,
                              self.height/fheight)
    

    def totuple(self):
        """Converts to tuple"""
        return (self.xmin, self.ymin, self.width, self.height)
    
    
    def topt(self):
        """Converts to center point"""
        x = floor((self.xmin+self.xmax)/2)
        y = floor((self.ymin+self.ymax)/2)
        
        return (x, y)


class NormalizedRect:
    """Normalized Rectangle Class"""
    def __init__(self, xmin, ymin, width, height):
        self.xmin = xmin
        self.ymin = ymin
        self.width = width
        self.height = height

        self.xmax = self.xmin + self.width
        self.ymax = self.ymin + self.height

    def norm2pix(self, fwidth, fheight):
        """Convert normalized rect to pixel rect"""
        xmin = self.xmin * fwidth
        ymin = self.ymin * fheight
        width = self.width * fwidth
        height = self.height * fheight

        return PixelRect(xmin, ymin, width, height)
    
    def totuple(self):
        """Converts to tuple"""
        return (self.xmin, self.ymin, self.width, self.height)
    
    def topt(self):
        """Converts to center point"""
        x = (self.xmin+self.xmax)/2
        y = (self.ymin+self.ymax)/2
        
        return (x, y)


class Points:
    """Multiple 2d points class"""
    def __init__(self, x=[], y=[]):
        self.x = x
        self.y = y
        
    def addpt(self, x, y):
        """Add a point to the list"""
        self.x.append(x)
        self.y.append(y)
        
    def __getitem__(self, idx):
        """Get a point by index"""
        if idx < -len(self.x) or idx >= len(self.x):
            raise IndexError("Index out of range")
        return (self.x[idx], self.y[idx])
        
    def pix2norm(self, fwidth, fheight):
        """Normalize points"""
        x = [xi / fwidth for xi in self.x]
        y = [yi / fheight for yi in self.y]
        return Points(x, y)
        
    def norm2pix(self, fwidth, fheight):
        """Denormalize points"""
        x = [xi * fwidth for xi in self.x]
        y = [yi * fheight for yi in self.y]
        
        return Points(x, y)
    
    def pts2rect(self, xoff=0, yoff=0, fwidth=1, fheight=1):
        """Convert points to rectangle"""
        if len(self.x) == 0 or len(self.y) == 0:
            raise ValueError("No points to convert to rectangle")
        
        xmin = max(0, min(self.x)-xoff)
        xmax = min(max(self.x)+xoff, fwidth)
        ymin = max(0, min(self.y)-yoff)
        ymax = min(max(self.y)+yoff, fheight)
        
        return PixelRect(xmin, ymin, xmax - xmin, ymax - ymin)

    def pop(self):
        self.x.pop()
        self.y.pop()

    def __len__(self):
        """Length of points"""
        return len(self.x)
    
    def __str__(self):
        """String representation of points"""
        return f"Points(x={self.x}, y={self.y})"
       