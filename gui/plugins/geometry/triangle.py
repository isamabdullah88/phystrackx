"""
Triangle module for PhysTrackX.

This module defines the Triangle class used to create, manipulate, and display a triangle 
on a tkinter Canvas. It supports point addition, live drawing, interactive dragging, 
selection highlighting, side length labeling, and angle arc visualization.

Dependencies:
    - tkinter
    - point.Point
    - line.Line
    - arc.DrawAngles
"""

import tkinter as tk
from .point import Point
from .line import Line
from .arc import DrawAngles


class Triangle:
    """
    Class representing a triangle in 2D space.
    
    This class manages a collection of 3 points and 3 lines forming a triangle, allowing:
        - Point-by-point construction
        - Drawing lines and arcs on a tkinter Canvas
        - Area calculation
        - Angle labeling
        - Interactive selection
    """

    def __init__(self, canvas: tk.Canvas):
        """
        Initialize a new Triangle on the given tkinter Canvas.

        Args:
            canvas (tk.Canvas): The canvas on which to draw the triangle.
        """
        self.canvas = canvas
        self.points: list[Point] = []
        self.lines: list[Line] = []
        self.tkpt = None
        self.tkline = None
        self.numpts = 0
        self.selected = False
        self.complete = False

    def copy(self) -> "Triangle":
        """
        Create and return a deep copy of this triangle.

        Returns:
            Triangle: A new triangle instance with copied points and lines.
        """
        triangle = Triangle(self.canvas)
        triangle.points = [Point(p.x, p.y, p.tkpt) for p in self.points]
        triangle.lines = [Line(line.tkline, line.ptstart, line.ptend) for line in self.lines]
        triangle.tkpt = self.tkpt
        triangle.tkline = self.tkline
        return triangle

    def addpoint(self, point: Point) -> None:
        """
        Add a point to the triangle and draw it on the canvas.

        Once 3 points are added, the triangle is completed and angles/lengths are displayed.

        Args:
            point (Point): The point to be added.
        """
        if self.numpts == 3:
            if point.meets(self.points[0]):
                self.lines.append(Line(self.tkline, self.points[0], self.points[-1]))
                self.canvas.coords(
                    self.tkline, self.points[0].x, self.points[0].y, self.points[-1].x, self.points[-1].y
                )
                self.numpts += 1
                self.tkline = None
                self.complete = True

            return

        elif self.numpts < 3:
            self.points.append(point)
            self.numpts += 1

            if len(self.points) > 1:
                self.lines.append(Line(self.tkline, self.points[-2], self.points[-1]))

            self.tkline = self.canvas.create_line(
                point.x, point.y, point.x, point.y,
                fill="#3cd1df", width=2
            )
            
            self.tkpt = self.canvas.create_oval(
                point.x - 5, point.y - 5,
                point.x + 5, point.y + 5,
                fill="#d82995"
            )
            self.points[-1].settk(self.tkpt)

    def ondrag(self, event) -> None:
        """
        Update the temporary drawing line as the mouse moves.

        Args:
            event: A tkinter event containing the current mouse coordinates.
        """
        if self.tkline:
            self.canvas.coords(self.tkline, self.points[-1].x, self.points[-1].y, event.x, event.y)

    def area(self) -> float:
        """
        Compute the area of the triangle using the Shoelace formula.

        Returns:
            float: The computed area, or 0 if triangle is incomplete.
        """
        if len(self.points) < 3:
            return 0.0

        x1, y1 = self.points[0].x, self.points[0].y
        x2, y2 = self.points[1].x, self.points[1].y
        x3, y3 = self.points[2].x, self.points[2].y

        return abs((x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2)) / 2.0)

    def is_pt_ontriangle(self, point: Point) -> bool:
        """
        Check if the given point lies on any side of the triangle.

        Args:
            point (Point): The point to test.

        Returns:
            bool: True if point lies on a triangle side, False otherwise.
        """
        if len(self.lines) < 3:
            return False
        return any(line.is_pt_online(point) for line in self.lines)

    def select(self) -> None:
        """
        Toggle selection of the triangle, highlighting its sides when selected.
        """
        self.selected = not self.selected
        for line in self.lines:
            if self.selected:
                self.canvas.itemconfig(line.tkline, fill="#7f5fea", width=4)
            else:
                self.canvas.itemconfig(line.tkline, fill="#3cd1df", width=2)

    def label_lengths(self) -> None:
        """
        Display the length of each side of the triangle on the canvas.
        """
        for line in self.lines:
            line.label_length(self.canvas, color="#CCFFAE")
            
    def draw_angles(self) -> None:
            drawangles = DrawAngles(self.points[0], self.points[1], self.points[2])
            drawangles.draw(self.canvas, color="#27e586")
            
    def delete(self) -> None:
        """
        Remove the triangle from the canvas and clear its data.
        """
        for line in self.lines:
            self.canvas.delete(line.tkline)
        for point in self.points:
            self.canvas.delete(point.tkpt)
            
        self.lines.clear()
        self.points.clear()
        self.tkpt = None
        self.tkline = None
        self.numpts = 0
        self.selected = False
        self.complete = False
