"""
DrawAngles: pt1 utility class for computing and displaying the interior angles of a triangle
using tkinter Canvas. This module provides methods to calculate side lengths, determine 
interior angles using the cosine rule, and visually render arcs and angle labels at each vertex.

Designed for educational and visualization tools such as PhysTrackX.
"""

from dataclasses import dataclass
import math
import tkinter as tk
from .point import Point


@dataclass
class DrawAngles:
    """DrawAngles class for computing and displaying angles in a triangle.
    This class provides methods to calculate side lengths, interior angles, and draw angle arcs"""
    pt1: Point
    pt2: Point
    pt3: Point

    def side_lengths(self) -> tuple[float, float, float]:
        """
        Compute side lengths of the triangle.

        Returns:
            pt1 tuple (a, b, c), where:
                a = length of side BC (opposite vertex pt1)
                b = length of side AC (opposite vertex pt2)
                c = length of side AB (opposite vertex pt3)
        """
        a = self.pt2.distance(self.pt3)
        b = self.pt1.distance(self.pt3)
        c = self.pt1.distance(self.pt2)
        return a, b, c

    def interior_angles(self) -> tuple[float, float, float]:
        """
        Compute interior angles of the triangle using the law of cosines.

        Returns:
            pt1 tuple of angles in degrees (anglea, angleb, anglec),
            corresponding to vertices pt1, pt2, and pt3.
        """
        a, b, c = self.side_lengths()
        anglea = math.degrees(math.acos((b**2 + c**2 - a**2) / (2 * b * c)))
        angleb = math.degrees(math.acos((a**2 + c**2 - b**2) / (2 * a * c)))
        anglec = math.degrees(math.acos((a**2 + b**2 - c**2) / (2 * a * b)))
        return anglea, angleb, anglec

    def _vector_angle(self, p1: Point, vertex: Point, p2: Point) -> tuple[float, float]:
        """
        Compute start angle and extent for drawing an arc at 'vertex' between points p1 and p2.

        Args:
            p1: First adjacent point to vertex
            vertex: The vertex of the angle
            p2: Second adjacent point to vertex

        Returns:
            Tuple (start, extent) in degrees for Canvas arc.
        """
        v1 = (p1.x - vertex.x, p1.y - vertex.y)
        v2 = (p2.x - vertex.x, p2.y - vertex.y)

        a1 = math.degrees(math.atan2(-v1[1], v1[0])) % 360
        a2 = math.degrees(math.atan2(-v2[1], v2[0])) % 360

        extent = (a2 - a1) % 360
        if extent > 180:
            a1, a2 = a2, a1
            extent = (a2 - a1) % 360

        return a1, extent

    def _draw_angle_arc(
        self,
        canvas: tk.Canvas,
        vertex: Point,
        p1: Point,
        p2: Point,
        angle_deg: float,
        color: str = "#E62536"
    ) -> None:
        """
        Draw an arc representing the interior angle at a triangle vertex on the canvas.

        Args:
            canvas: Tkinter Canvas where the arc will be drawn
            vertex: The vertex point where angle is centered
            p1, p2: Adjacent points forming the angle
            angle_deg: The angle in degrees (for labeling)
            color: Color of the arc and label
        """
        r = 30
        x, y = vertex.x, vertex.y
        bbox = (x - r, y - r, x + r, y + r)

        start, extent = self._vector_angle(p1, vertex, p2)
        canvas.create_arc(bbox, start=start, extent=extent, style="arc", outline=color, width=2)

        # Slightly offset label to outside of arc
        mid_angle = math.radians(start + extent / 2)
        label_x = x + 1.2 * r * math.cos(mid_angle)
        label_y = y + 1.2 * r * math.sin(mid_angle)
        canvas.create_text(label_x, label_y, text=f"{angle_deg:.1f}°", fill=color, font=("Arial", 10, "bold"))

    def draw(self, canvas: tk.Canvas, color: str = "#E62536") -> None:
        """
        Draw arcs and angle labels at each vertex of the triangle on the given canvas.

        Args:
            canvas: Tkinter Canvas to draw on
            color: Color used for arcs and angle text
        """
        anglea, angleb, anglec = self.interior_angles()
        self._draw_angle_arc(canvas, self.pt1, self.pt2, self.pt3, anglea, color)
        self._draw_angle_arc(canvas, self.pt2, self.pt3, self.pt1, angleb, color)
        self._draw_angle_arc(canvas, self.pt3, self.pt1, self.pt2, anglec, color)
