
import math
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
                self.display_triangle_with_angle_arcs(self.points[0], self.points[1], self.points[2])
                self.label_side_lengths(self.points[0], self.points[1], self.points[2])
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
                

    # def distance(p1, p2):
    #     return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def angle_from_sides(self, a, b, c):
        return math.degrees(math.acos((b**2 + c**2 - a**2) / (2 * b * c)))

    def vector_angle(self, p1:Point, vertex:Point, p2:Point):
        # Angle between vectors (vertex → p1) and (vertex → p2)
        v1 = (p1.x - vertex.x, p1.y - vertex.y)
        v2 = (p2.x - vertex.x, p2.y - vertex.y)
        
        # atan2 uses (Y, X), and we invert Y for canvas coordinate system
        a1 = math.degrees(math.atan2(-v1[1], v1[0])) % 360
        a2 = math.degrees(math.atan2(-v2[1], v2[0])) % 360

        # Angle from a1 to a2 (sweep)
        extent = (a2 - a1) % 360
        if extent > 180:
            # Flip to get interior angle
            a1, a2 = a2, a1
            extent = (a2 - a1) % 360
        return a1, extent

    def draw_angle_arc(self, vertex:Point, p1:Point, p2:Point, angle_deg, color):
        r = 30  # Radius of arc
        x, y = vertex.x, vertex.y
        bbox = (x - r, y - r, x + r, y + r)
        start, extent = self.vector_angle(p1, vertex, p2)
        self.canvas.create_arc(bbox, start=start, extent=extent, style="arc", outline=color, width=2)

        # Label the angle slightly outside the arc
        label_x = x + 1.2 * r * math.cos(math.radians(start + extent / 2))
        label_y = y + 1.2 * r * math.sin(math.radians(start + extent / 2))
        self.canvas.create_text(label_x, label_y, text=f"{angle_deg:.1f}°", fill=color, font=("Arial", 10, "bold"))

    def display_triangle_with_angle_arcs(self, A:Point, B:Point, C:Point):
        # Draw triangle
        # self.canvas.create_polygon([A, B, C], outline="black", fill="", width=2)

        # Compute side lengths
        a = B.distance(C)
        b = A.distance(C)
        c = A.distance(B)

        # Compute angles
        angle_A = self.angle_from_sides(a, b, c)
        angle_B = self.angle_from_sides(b, c, a)
        angle_C = self.angle_from_sides(c, a, b)

        # Draw arcs and labels
        self.draw_angle_arc(A, B, C, angle_A, "red")
        self.draw_angle_arc(B, A, C, angle_B, "red")
        self.draw_angle_arc(C, A, B, angle_C, "red")
        
        
    def label_side_lengths(self, A:Point, B:Point, C:Point):
        
        def label_length(p1:Point, p2:Point, color):
            mid_x = (p1.x + p2.x) / 2
            mid_y = (p1.y + p2.y) / 2
            length = p1.distance(p2)
            
            self.canvas.create_text(mid_x, mid_y, text=f"{length:.1f}", fill=color, font=("Arial", 9, "italic"))

        label_length(A, B, "green")  # side c
        label_length(B, C, "green")  # side a
        label_length(C, A, "green")  # side b


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
