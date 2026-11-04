"""
view.py

Zoom and pan for the video view. Overlays (rectangles, points, axes, ruler) are stored in
"base" canvas coordinates, which are the unzoomed positions. ViewTransform maps between base
and on-screen canvas coordinates, so saved overlays stay valid at any zoom level.

Author: Isam Balghari
"""


class ViewTransform:
    MAX_ZOOM = 8.0

    def __init__(self) -> None:
        self.zoom = 1.0
        self.ox = 0.0  # Visible window's top-left, in crop-frame pixels
        self.oy = 0.0
        self.origin = (0, 0)  # Canvas position of the crop frame's top-left at zoom 1
        self.size = (1, 1)    # Crop frame size (width, height)
        self.fit = 1.0        # Upscale (or downscale) of the frame to fit the view; zoom is on top

    # ---------------------------------------------------------------------------------------------
    def configure(self, origin: tuple[int, int], size: tuple[int, int]) -> None:
        """Sets the crop frame placement and size, then keeps the window inside the frame."""
        self.origin = origin
        self.size = (max(1, size[0]), max(1, size[1]))
        self._clamp()

    def reset(self) -> None:
        self.zoom = 1.0
        self.ox = self.oy = 0.0
        self._clamp()

    def set_zoom(self, zoom: float) -> None:
        """Changes zoom around the current centre of the view."""
        w, h = self._window_size()
        cx, cy = self.ox + w / 2, self.oy + h / 2
        self.zoom = min(max(zoom, 1.0), self.MAX_ZOOM)
        w, h = self._window_size()
        self.ox, self.oy = cx - w / 2, cy - h / 2
        self._clamp()

    def zoom_at(self, x: float, y: float, zoom: float) -> None:
        """Changes zoom keeping the picture point under canvas position (x, y) where it is."""
        ox0, oy0 = self.origin
        m = self.zoom * self.fit
        fx = (x - ox0) / m + self.ox  # Crop-frame pixel under the pointer
        fy = (y - oy0) / m + self.oy
        self.zoom = min(max(zoom, 1.0), self.MAX_ZOOM)
        m = self.zoom * self.fit
        self.ox = fx - (x - ox0) / m
        self.oy = fy - (y - oy0) / m
        self._clamp()

    def pan(self, dx: float, dy: float) -> None:
        """Moves the picture by (dx, dy) canvas pixels: positive moves it right and down."""
        m = self.zoom * self.fit
        self.ox -= dx / m
        self.oy -= dy / m
        self._clamp()

    def set_fraction(self, fx: float, fy: float) -> None:
        """Pans using 0..1 fractions of the scrollable range (0 = left/top edge)."""
        w, h = self._window_size()
        self.ox = min(max(fx, 0.0), 1.0) * max(self.size[0] - w, 0)
        self.oy = min(max(fy, 0.0), 1.0) * max(self.size[1] - h, 0)
        self._clamp()

    def fractions(self) -> tuple[float, float]:
        w, h = self._window_size()
        fx = self.ox / (self.size[0] - w) if self.size[0] - w > 0 else 0.0
        fy = self.oy / (self.size[1] - h) if self.size[1] - h > 0 else 0.0
        return fx, fy

    def window(self) -> tuple[int, int, int, int]:
        """Integer crop window (x, y, width, height) in crop-frame pixels."""
        w, h = self._window_size()
        return int(round(self.ox)), int(round(self.oy)), int(round(w)), int(round(h))

    # ---------------------------------------------------------------------------------------------
    def to_canvas(self, x: float, y: float) -> tuple[float, float]:
        """Base (unzoomed) canvas point -> on-screen canvas point."""
        ox0, oy0 = self.origin
        m = self.zoom * self.fit
        return (ox0 + (x - ox0 - self.ox) * m,
                oy0 + (y - oy0 - self.oy) * m)

    def to_base(self, x: float, y: float) -> tuple[float, float]:
        """On-screen canvas point -> base (unzoomed) canvas point."""
        ox0, oy0 = self.origin
        m = self.zoom * self.fit
        return (ox0 + (x - ox0) / m + self.ox,
                oy0 + (y - oy0) / m + self.oy)

    # ---------------------------------------------------------------------------------------------
    def _window_size(self) -> tuple[float, float]:
        return self.size[0] / self.zoom, self.size[1] / self.zoom

    def _clamp(self) -> None:
        self.zoom = min(max(self.zoom, 1.0), self.MAX_ZOOM)
        w, h = self._window_size()
        self.ox = min(max(self.ox, 0.0), max(self.size[0] - w, 0.0))
        self.oy = min(max(self.oy, 0.0), max(self.size[1] - h, 0.0))
