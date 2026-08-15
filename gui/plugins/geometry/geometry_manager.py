
from typing import List, Optional, Tuple
from .triangle import Triangle
from .point import Point

class GeometryManager:
    """Manages geometric entities, hit-testing, and measurements."""

    def __init__(self):
        self.triangles: List[Triangle] = []
        self.scale: float = 1.0

    def add_triangle(self, triangle: Triangle) -> None:
        self.triangles.append(triangle)

    def get_selected(self) -> List[Triangle]:
        return [t for t in self.triangles if t.selected]

    def hit_test(self, point: Point) -> Tuple[bool, Optional[Triangle]]:
        for triangle in self.triangles:
            if triangle.is_pt_ontriangle(point):
                return True, triangle
        return False, None

    def compute_angles(self) -> bool:
        selected = self.get_selected()
        if not selected:
            return False
        for triangle in selected:
            triangle.draw_angles()
            triangle.select()
        return True

    def compute_distances(self) -> bool:
        selected = self.get_selected()
        if not selected:
            return False
        for triangle in selected:
            triangle.label_lengths(self.scale)
            triangle.select()
        return True

    def delete_selected(self) -> bool:
        selected = self.get_selected()
        if not selected:
            return False
        for triangle in selected:
            triangle.delete()
        self.triangles = [t for t in self.triangles if not t.selected]
        return True

    def set_visibility(self, visible: bool) -> None:
        for triangle in self.triangles:
            triangle.unhide() if visible else triangle.hide()

    def clear(self) -> None:
        for triangle in self.triangles:
            triangle.delete()
        self.triangles.clear()