

class Line:
    def __init__(self, tkline, line, selected=False):
        # line: selected line consisting of two points
        # tkline: Tkinter line used to display
        self.tkline = tkline
        self.line = line
        self.selected = selected