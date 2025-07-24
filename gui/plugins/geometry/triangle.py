
import tkinter as tk
from .point import Point
from .line import Line

class Triangle:
    """Class representing a triangle in a 2D space.
    It can hold three points and provides methods to add points and check if a point is within the triangle."""
    def __init__(self, canvas:tk.Canvas):
        self.canvas = canvas
        self.points: list[Point] = []
        self.tkpt = None
        self.tkline = None
        self.lines: list[Line] = []
        
        self.selected = False
        self.complete = False
        
        self.payload = {}
        
    def copy(self):
        """Create a copy of the triangle."""
        triangle = Triangle(self.canvas)
        triangle.points = [Point(p.x, p.y) for p in self.points]
        triangle.lines = [Line(line.tkline, (line.line[0], line.line[1])) for line in self.lines]
        triangle.tkpt = self.tkpt
        triangle.tkline = self.tkline
        return triangle
    
    def addpoint(self, point):
        """Add a point to the triangle."""
        # Implementation for adding a point to the triangle
        if len(self.points) == 4:
            # return {'complete': False, 'exist': True}
            self.complete = True
            
        elif len(self.points) == 3:
            if point.meets(self.points[0]):
                self.lines.append(Line(self.tkline, (self.points[0], self.points[-1])))
                self.canvas.coords(self.tkline, self.points[0].x, self.points[0].y, self.points[-1].x, self.points[-1].y)
                self.points.append(point)
                self.tkline = None
                # print('lines: ', len(self.lines))
                self.complete = True
                
            #     return {'complete': True, 'exist': False}
            # else:
            #     return {'complete': False, 'exist': False}
        
        else:
            # if not any(p.meets(point) for p in self.points):
            # print('Adding point:', len(self.points))
            self.points.append(point)
                
            if len(self.points) > 1:
                # print('points: ', len(self.points))
                self.lines.append(Line(self.tkline, (self.points[-2], self.points[-1])))
                # print('lines2: ', len(self.lines))
                
            self.tkpt = self.canvas.create_oval(point.x-5, point.y-5, point.x+5, point.y+5, fill="#d82995")
            self.tkline = self.canvas.create_line(point.x, point.y, point.x, point.y, fill="#3cd1df", width=2)
            self.canvas.tag_lower(self.tkline)
                
            # return {'complete': False, 'exist': False}
    
    def ondrag(self, event):
        """Handle dragging of the triangle points."""
        if self.tkline:
            self.canvas.coords(self.tkline, self.points[-1].x, self.points[-1].y, event.x, event.y)
            
    def area(self) -> float:
        """Calculate the area of the triangle using the shoelace formula."""
        if len(self.points) < 3:
            return 0.0
        
        x1, y1 = self.points[0].x, self.points[0].y
        x2, y2 = self.points[1].x, self.points[1].y
        x3, y3 = self.points[2].x, self.points[2].y
        
        return abs((x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2.0)
    
    
    def ptontriangle(self, point: Point) -> bool:
        print('lines: ', len(self.lines))
        if len(self.lines) < 3:
            return False
        
        for line in self.lines:
            if line.ptonline(point):
                return True
        
    def select(self):
        """Select the triangle by highlighting its points and lines."""
        if self.selected:
            # for point in self.points:
            #     self.canvas.itemconfig(point.tkpt, fill="#d82995")
            self.selected = False
            for line in self.lines:
                self.canvas.itemconfig(line.tkline, fill="#3cd1df", width=2)
        else:
            self.selected = True
            # for point in self.points:
            #     self.canvas.itemconfig(point.tkpt, fill="#d82995", width=2)
            print('lines select: ', len(self.lines))
            for line in self.lines:
                self.canvas.itemconfig(line.tkline, fill="#7f5fea", width=3)