

class Circle:
    """Basic circle unit class."""
    def __init__(self, **kwargs):
        self.cx = kwargs.get('cx', 0)
        self.cy = kwargs.get('cy', 0)
        self.rad = kwargs.get('rad', 0)
