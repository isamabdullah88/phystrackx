"""
datamanager.py

Manages and transforms tracking points and OCR data using user-defined axes.

Author: Isam Balghari
"""

import numpy as np
from gui.components.tpoints import TrackPoint
from gui.components.axes import Axes
from experiments.components.ocr import OCRData


class DataManager:
    def __init__(
        self,
        tpoints: list[list[TrackPoint]],
        ocrdata: OCRData,
        axes: Axes,
        vwidth: int,
        vheight: int,
        fwidth: int,
        fheight: int,
        fps: int,
        scale: float
    ) -> None:
        """
        Initializes the data manager with tracking points and transformation settings.

        Args:
            tpoints (list[list[TrackPoint]]): Time-series tracking points for each object.
            ocrdata (OCRData): OCR result object containing frame-wise text.
            axes (Axes): Reference to the user-defined coordinate frame.
            vwidth (int): Width of the video view canvas.
            vheight (int): Height of the video view canvas.
            fwidth (int): Width of the image frame inside canvas.
            fheight (int): Height of the image frame inside canvas.
            fps (int): Frames per second of the video.
            scale (float): Pixel-to-real-world scale factor.
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

        self.datacount = len(tpoints)
        self.samplecount = len(tpoints[0]) if tpoints else 0
        self.timestamps = np.linspace(0, self.samplecount / self.fps, self.samplecount)
        self.ocrcount = ocrdata.datacount

        # Pre-allocated container for transformed coordinates
        self.processed_points = [
            np.zeros((self.samplecount, 2)) for _ in range(self.datacount)
        ]

    def transform(self) -> None:
        """
        Applies coordinate transformation to all tracked points.
        """
        for i, obj_points in enumerate(self.tpoints):
            for j, pt in enumerate(obj_points):
                self.processed_points[i][j, :] = np.array(
                    self.transformxy(pt.x, pt.y)
                )

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
        theta_rad = -np.deg2rad(self.axes.theta.get())
        x, y = self.axes.rotatez(x, y, theta_rad)

        # Apply scale if needed
        if self.scale is not None:
            x *= self.scale
            y *= self.scale

        return x, y
