"""
mltracker.py

Deep learning single-object tracking engine utilizing OpenCV's DNN API.
Tracks a user-defined manual bounding box across fast-moving frames.

Author: Isam Balghari
"""

import cv2
import logging
import os
from core import abspath, PixelRect

class MLTracker:
    """Manages deep learning template tracking using lightweight ONNX models."""
    
    def __init__(self, tracking_type: str = "nanotrack") -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tracker = None
        self.tracking_type = tracking_type
        
    def initialize_tracker(self, initial_frame: cv2.Mat, rect: PixelRect) -> None:
        """
        Initializes the tracker using the user's manual bounding box.
        
        Args:
            initial_frame: The frame where the user drew the box.
            rect: A PixelRect object representing the bounding box.
        """
        if self.tracking_type == "nanotrack":
            
            param_path = abspath("models/nanotrack_backbone.onnx")
            model_path = abspath("models/nanotrack_head.onnx")
            
            params = cv2.TrackerNano_Params()
            params.backbone = param_path
            params.neckhead = model_path
            
            self.tracker = cv2.TrackerNano_create(params)
            
        elif self.tracking_type == "vittrack":
            param_path = abspath("models/vit_tracker_baseline.onnx")
            params = cv2.TrackerVit_Params()
            params.net = param_path
            
            self.tracker = cv2.TrackerVit_create(params)
            
        # Initialize the state tracker on frame
        bbox = (rect.xmin, rect.ymin, rect.width, rect.height)
        self.tracker.init(initial_frame, bbox)
        self.logger.info(f"Deep learning {self.tracking_type} engine successfully initialized on custom user ROI.")

    def update_tracker(self, frame: cv2.Mat) -> tuple[bool, PixelRect]:
        """
        Tracks the object in the current frame.
        
        Returns:
            success: Boolean indicating if tracker maintained lock.
            bbox: Updated PixelRect object representing the bounding box.
        """
            
        success, bbox = self.tracker.update(frame)
        if success:
            # Unpack and return cleanly cast standard Python integers
            return True, PixelRect(int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
        else:
            self.logger.warning("Deep Learning tracker lost tracking lock due to extreme degradation.")
            return False, PixelRect(0, 0, 0, 0)