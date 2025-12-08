"""
videoapp.py

Defines the Video class which handles video display, frame manipulations, and tracking logic.

Author: Isam Balghari
"""

from typing import Optional, List
import os
import logging
import cv2
from PIL import Image, ImageTk
import numpy as np
from numpy.typing import NDArray

from customtkinter import CTkCanvas, IntVar
from experiments.rigid.rigid import Rigid
from gui.plugins.crop import Crop
from gui.plugins.filters import Filters
from gui.components.processanim import ProcessAnimation
from gui.components.rect import Rect
from core import filexists


class Video:
    """
    Video handler for loading, displaying, trimming, and tracking frames on a canvas.
    """

    def __init__(self, canvas: CTkCanvas, vwidth: int, vheight: int, crop: Crop, filters: Filters,
                 processanim: ProcessAnimation) -> None:
        """
        Initialize the Video app.

        Args:
            canvas (CTkCanvas): Canvas to render video frames.
            vwidth (int): Width of the video display area.
            vheight (int): Height of the video display area.
            crop (Crop): Crop handler.
            seekbar (TrimSeekBar): Seekbar for video navigation.
            filters (Filters): Filters to apply on video.
            processanim (Spinner): UI processanim to show progress or status.
        """
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.crop = crop
        self.filters = filters
        self.processanim = processanim

        self.frame: Optional[any] = None
        self.imgview = None
        self.tkimg = None

        tempdir = "temp"
        os.makedirs(tempdir, exist_ok=True)
        self.trimpath = os.path.join(tempdir, "Track_Rigid.mp4")

        self.rigid = Rigid(trimpath=self.trimpath, vwidth=self.vwidth, vheight=self.vheight-50,
                           tkqueue=self.processanim.queue)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Video App initialized")
        self.trimvideo = self.rigid.trim
        
        self.imgview = self.canvas.create_image(self.crop.fx, self.crop.fy, anchor="nw")

    @property
    def fcount(self) -> int:
        """Total number of frames in loaded video."""
        return self.rigid.fcount

    @property
    def trackpts(self) -> List[List[NDArray[np.float32]]]:
        """Tracking points recorded from video."""
        return self.rigid.trackpts
    
    @property
    def ocrdata(self) -> List[List[str]]:
        """OCR data extracted from video"""
        return self.rigid.texts

    # @property
    # def texts(self) -> List[List[str]]:
    #     """Text overlays on tracked frames."""
    #     return self.rigid.texts

    @property
    def fps(self) -> int:
        """Video frames per second."""
        return self.rigid.fps

    @property
    def fwidth(self) -> int:
        """Current video frame width."""
        return self.rigid.fwidth

    @property
    def fheight(self) -> int:
        """Current video frame height."""
        return self.rigid.fheight

    def loadvideo(self, videopath: str, istrim:bool=False) -> None:
        """
        Load a video from file or fallback to trimmed path.

        Args:
            videopath (str): Path to video file.
        """
        self.rigid.release()

        if istrim:
            self.logger.info("Loading trim video")
            if not filexists(self.trimpath):
                self.logger.error("Trim video not found!")
                return
            self.rigid.addvideo(self.trimpath, istrim)
            self.logger.info("Video added from: %s", self.trimpath)
        else:
            self.rigid.addvideo(videopath)
            self.logger.info("Video added from: %s", videopath)
        
        self.crop.set(self.fwidth, self.fheight)


    def showframe(self, idx: int) -> None:
        """
        Fetch and display a video frame on the canvas.

        Args:
            idx (int): Index of the frame to display.
        """
        frame = self.rigid.frame(index=idx)
        frame = self.filters.appfilter(frame)
        self.frame = self.crop.appcrop(frame)

        img = Image.fromarray(cv2.cvtColor(self.frame.copy(), cv2.COLOR_BGR2RGB))
        self.tkimg = ImageTk.PhotoImage(image=img)

        self.canvas.coords(self.imgview, self.crop.crpx, self.crop.crpy)
        self.canvas.itemconfig(self.imgview, image=self.tkimg)

    def track(self, trect: Rect, ocr: Rect, progress: IntVar) -> None:
        """
        Perform object tracking on the video using selected regions.

        Args:
            trect (Rect): Region to track.
            ocr (Rect): OCR target region.
            progress (IntVar): Variable for UI progress tracking.
        """
        self.rigid.track(trect.rects, ocr.rects, self.filters, self.crop, progress)

    def clear(self) -> None:
        """
        Clear stored tracking points from memory.
        """
        self.rigid.trackpts.clear()
