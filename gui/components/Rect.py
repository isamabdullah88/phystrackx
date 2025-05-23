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
        
    def pixel2normal(self, fwidth, fheight):
        """Convert pixel rect to normalized rect"""
        return NormalizedRect(self.xmin/fwidth, self.ymin/fheight, self.width/fwidth,
                              self.height/fheight)
    

    def totuple(self):
        """Converts to tuple"""
        return (self.xmin, self.ymin, self.width, self.height)


class NormalizedRect:
    """Normalized Rectangle Class"""
    def __init__(self, xmin, ymin, width, height):
        self.xmin = xmin
        self.ymin = ymin
        self.width = width
        self.height = height

        self.xmax = self.xmin + self.width
        self.ymax = self.ymin + self.height

    def normal2pixel(self, fwidth, fheight):
        """Convert normalized rect to pixel rect"""
        xmin = self.xmin * fwidth
        ymin = self.ymin * fheight
        width = self.width * fwidth
        height = self.height * fheight

        return PixelRect(xmin, ymin, width, height)
    
    def totuple(self):
        """Converts to tuple"""
        return (self.xmin, self.ymin, self.width, self.height)
