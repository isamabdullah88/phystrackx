"""
datamanager.py

Manages and transforms tracking points and OCR data using user-defined axes.

Author: Isam Balghari
"""

import customtkinter as ctk
import numpy as np
from gui.components.visuals import TrackPoint
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
        self.ocrcount = ocrdata.datacount
        self.ocrsamplecount = ocrdata.samplecount
        self.maxcount = max(self.datacount, self.ocrsamplecount)
        self.timestamps = np.linspace(0, self.maxcount / self.fps, self.maxcount)

        # Pre-allocated container for transformed coordinates
        self.processed_points = [
            np.zeros((self.samplecount, self.rows, self.cols)) for _ in range(self.datacount)
        ]

    def transform(self) -> None:
        """
        Applies coordinate transformation to all tracked points.
        """
        for i, obj_points in enumerate(self.tpoints):
            for j, pt in enumerate(obj_points):
                tx, ty = self.transformxy(pt.x, pt.y)
                self.processed_points[i][j, :, 0] = tx
                self.processed_points[i][j, :, 1] = ty

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



def create_mock_data(root, canvas) -> tuple[list[list[TrackPoint]], OCRData, Axes]:
    """
    Creates mock tracking data, OCR data, and axes for testing.
    """
    # from gui.components.visuals import ContPoint
    # Mock TrackPoints: two objects, 5 frames each
    # tpoints = [
    #     [TrackPoint(x=10 + i, y=20 + i, fx=0, fy=0) for i in range(5)],  # object 1
    #     [TrackPoint(x=30 + i, y=40 + i, fx=0, fy=0) for i in range(5)],  # object 2
    # ]
    
    tpoints = [
        [TrackPoint(np.random.random((100,)), np.random.random((100,)), 0, 0) for _ in range(10)],
        [TrackPoint(np.random.random((100,)), np.random.random((100,)), 0, 0) for _ in range(10)]
    ]

    # Mock OCRData
    ocrdata = OCRData(data=["frame0", "frame1", "frame2", "frame3", "frame4"])

    # Minimal btnlist (needed by Axes)
    dummy_btn = ctk.CTkButton(canvas, text="dummy")
    btnlist = {"dummy": dummy_btn}

    # Create Axes object
    axes = Axes(
        root=root,
        canvas=canvas,
        vwidth=640,
        vheight=480,
        btnlist=btnlist,
        activebtn=dummy_btn
    )
    axes.ox = 0
    axes.oy = 480
    axes.theta.set(0)

    return tpoints, ocrdata, axes


def main() -> None:
    """
    Main entry point for testing DataManager.
    """
    # Setup hidden Tk root (we don’t need to run the mainloop)
    root = ctk.CTk()
    canvas = ctk.CTkCanvas(root, width=640, height=480)
    canvas.pack()

    # Create mock input data
    tpoints, ocrdata, axes = create_mock_data(root, canvas)

    # Initialize DataManager
    manager = DataManager(
        tpoints=tpoints,
        ocrdata=ocrdata,
        axes=axes,
        vwidth=640,
        vheight=480,
        fwidth=640,
        fheight=480,
        fps=30,
        scale=1.0
    )

    # Perform transformation
    manager.transform()

    # Print transformed results
    for i, obj_points in enumerate(manager.processed_points):
        print(f"Object {i} transformed points:")
        print(obj_points)


if __name__ == "__main__":
    main()