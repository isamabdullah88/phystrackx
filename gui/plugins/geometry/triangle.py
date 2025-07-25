
import tkinter as tk
from .point import Point
from .line import Line
from .arc import DrawAngles

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
        self.numpts = 0
        
    def copy(self):
        """Create a copy of the triangle."""
        triangle = Triangle(self.canvas)
        triangle.points = [Point(p.x, p.y) for p in self.points]
        triangle.lines = [Line(line.tkline, line.ptstart, line.ptend) for line in self.lines]
        triangle.tkpt = self.tkpt
        triangle.tkline = self.tkline
        return triangle
    
    def addpoint(self, point):
        """Add a point to the triangle."""
        # Implementation for adding a point to the triangle
        # if len(self.points) == 4:
            # return {'complete': False, 'exist': True}
            # self.complete = True
            
        if self.numpts == 3:
            if point.meets(self.points[0]):
                self.lines.append(Line(self.tkline, self.points[0], self.points[-1]))
                self.canvas.coords(self.tkline, self.points[0].x, self.points[0].y, self.points[-1].x, self.points[-1].y)
                # self.points.append(point)
                self.numpts += 1
                self.tkline = None
                # print('lines: ', len(self.lines))
                self.complete = True
                # self.display_triangle_with_angle_arcs(self.points[0], self.points[1], self.points[2])
                drawangles = DrawAngles(self.points[0], self.points[1], self.points[2])
                drawangles.draw(self.canvas, color="#27e586")
                # self.label_side_lengths(self.points[0], self.points[1], self.points[2])
                self.label_lengths()
            #     return {'complete': True, 'exist': False}
            # else:
            #     return {'complete': False, 'exist': False}
        
        elif self.numpts < 3:
            # if not any(p.meets(point) for p in self.points):
            # print('Adding point:', len(self.points))
            self.points.append(point)
            self.numpts += 1
                
            if len(self.points) > 1:
                # print('points: ', len(self.points))
                self.lines.append(Line(self.tkline, self.points[-2], self.points[-1]))
                # print('lines2: ', len(self.lines))
                
            self.tkpt = self.canvas.create_oval(point.x-5, point.y-5, point.x+5, point.y+5, fill="#d82995")
            self.tkline = self.canvas.create_line(point.x, point.y, point.x, point.y, fill="#3cd1df", width=2)
            self.canvas.tag_lower(self.tkline)
        # else:
            
                
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
    
    
    def is_pt_ontriangle(self, point: Point) -> bool:
        if len(self.lines) < 3:
            return False
        
        for line in self.lines:
            if line.is_pt_online(point):
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
                

    # def distance(p1, p2):
    #     return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        
        
    def label_lengths(self):
        for line in self.lines:
            line.label_length(self.canvas, color="#CCFFAE")
    # def label_side_lengths(self, A:Point, B:Point, C:Point):
        
    #     def label_length(p1:Point, p2:Point, color):
    #         mid_x = (p1.x + p2.x) / 2
    #         mid_y = (p1.y + p2.y) / 2
    #         length = p1.distance(p2)
            
    #         self.canvas.create_text(mid_x, mid_y, text=f"{length:.1f}", fill=color, font=("Arial", 9, "italic"))

    #     label_length(A, B, "green")  # side c
    #     label_length(B, C, "green")  # side a
    #     label_length(C, A, "green")  # side b


# # Tkinter setup
# root = tk.Tk()
# root.title("Triangle Angles with Arcs")
# canvas = tk.Canvas(root, width=400, height=400, bg="white")
# canvas.pack()

# # Triangle points (manually defined)
# A = (100, 300)
# B = (300, 300)
# C = (200, 100)

# # Display triangle and angles
# display_triangle_with_angle_arcs(canvas, A, B, C)

# root.mainloop()
