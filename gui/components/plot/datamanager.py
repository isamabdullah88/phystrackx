"""
datamanager.py

Manages and transforms tracking points and OCR data using user-defined axes.

Author: Isam Balghari
"""

import numpy as np
from gui.components.tpoints import FPoint
from gui.components.axes import Axes
from experiments.components.ocr import OCRData


class DataManager:
    def __init__(self) -> None:
        """
        Initializes the data manager shell with default/empty values.
        Actual data population and computation happens in load_data().
        """
        self.tpoints: list[list[FPoint]] = []
        self.ocrdata: list = []  # Assuming ocrdata.data evaluates to a list/iterable
        self.axes: Axes | None = None

        self.vwidth: float = 0.0
        self.vheight: float = 0.0
        self.fwidth: float = 0.0
        self.fheight: float = 0.0
        self.fps: int = 1
        self.scale: float = 1.0
        self.scale_applied: bool = False

        self.datacount: int = 0
        self.samplecount: int = 0
        self.ocrcount: int = 0
        self.ocrsamplecount: int = 0
        self.maxcount: int = 0
        self.timestamps: np.ndarray = np.array([])

        # Pre-allocated container for transformed coordinates
        self.processed_points: list[np.ndarray] = []

    def load_data(self, tpoints: list[list[FPoint]], ocrdata: OCRData, axes: Axes, vwidth: float,
                 vheight: float, fwidth: float, fheight: float, fps: int, scale: float) -> bool:
        """
        Populates the tracking data and configuration settings.
        Handles internal exceptions to protect the main entry application.

        Args:
            tpoints (list[list[FPoint]]): Time-series tracking points for each object.
            ocrdata (OCRData): OCR result object containing frame-wise text.
            axes (Axes): Reference to the user-defined coordinate frame.
            vwidth (float): Width of the video view canvas.
            vheight (float): Height of the video view canvas.
            fwidth (float): Width of the image frame inside canvas.
            fheight (float): Height of the image frame inside canvas.
            fps (int): Frames per second of the video.
            scale (float): Pixel-to-real-world scale factor.
        
        Returns:
            bool: True if data was successfully loaded and setup without errors, False otherwise.
        """
        self.tpoints = tpoints
        self.ocrdata = ocrdata.data
        self.axes = axes

        self.vwidth = vwidth
        self.vheight = vheight
        self.fwidth = fwidth
        self.fheight = fheight
        self.fps = fps
        self.scale = scale
        self.scale_applied = False

        self.datacount = len(tpoints)
        self.samplecount = len([tpt for tpt in tpoints[0] if tpt.valid]) if tpoints else 0
        self.ocrcount = ocrdata.datacount
        self.ocrsamplecount = ocrdata.samplecount
        self.maxcount = max(self.samplecount, self.ocrsamplecount)
        self.timestamps = np.linspace(0, self.maxcount / self.fps, self.maxcount)

        # Pre-allocated container for transformed coordinates
        self.processed_points = [
            np.zeros((self.samplecount, 2), dtype=float) for _ in range(self.datacount)
        ]

        return True

    def transform(self) -> None:
        """
        Applies coordinate transformation to all tracked points.
        """
        for i, framepts in enumerate(self.tpoints):
            j = 0
            for pt in framepts:
                if not pt.valid:
                    continue
                self.processed_points[i][j, :] = np.array(self.transformxy(pt.x, pt.y))
                j += 1

        self.scale_applied = True

    def transformxy(self, x: float, y: float) -> tuple[float, float]:
        """
        Transforms a single point from raw canvas coordinates to rotated/scaled physical coordinates.

        Args:
            x (float): x-coordinate in canvas space.
            y (float): y-coordinate in canvas space.

        Returns:
            tuple[float, float]: Transformed (x, y) in regular space.
        """
        # Translate image offset in canvas
        frame_offset_x = (self.vwidth - self.fwidth) / 2
        frame_offset_y = (self.vheight - self.fheight) / 2
        x += frame_offset_x
        y += frame_offset_y

        # Convert to regular frame origin
        x, y = self.axes.canvas2reg(x, y, self.axes.ox, self.axes.oy)

        # Undo rotation (apply inverse of user-defined theta)
        theta_rad = -np.deg2rad(self.axes.theta.get()).item()

        x, y = self.axes.rotatez(x, y, theta_rad)
    
        # Apply scale
        if self.scale_applied is False:
            x = x * self.scale
            y = y * self.scale

        return x, y
    
    def clear(self) -> None:
        """
        Clears all stored tracking and OCR data.
        """
        self.tpoints.clear()
        self.ocrdata.clear()
        self.processed_points.clear()
