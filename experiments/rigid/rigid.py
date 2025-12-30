"""
rigid.py

Implements rigid body tracking using optical flow and optional OCR from video frames.

Author: Isam Balghari
"""

from typing import Optional, List
from queue import Queue
import cv2
import numpy as np
from numpy.typing import NDArray
import logging

from tqdm import tqdm
from customtkinter import IntVar
from experiments.experiment import Experiment
from experiments.components import OCRData
from core import NormalizedRect, abspath
from gui.plugins import Crop, Filters


class Rigid(Experiment):
    """
    Tracks rigid objects using Lucas-Kanade optical flow,
    and optionally performs OCR within user-defined regions.
    """

    def __init__(self, trimpath: str, vwidth: int, vheight: int, tkqueue: Queue = None) -> None:
        """
        Initialize the rigid tracker.

        Args:
            trimpath: Path to save trimmed/tracked video.
            vwidth: Maximum viewer width.
            vheight: Maximum viewer height.
            tkqueue: Optional Tkinter queue for live frame updates.
        """
        super().__init__(trimpath, vwidth, vheight)
        self.tkqueue = tkqueue
        self.trackpts: List[List[NDArray[np.float32]]] = []
        self.texts: List[List[str]] = []
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Rigid(Exp) initialized")

    def ocr(self, frame: cv2.Mat, rect: 'PixelRect', pytesseract) -> str:
        """
        Extract text using OCR from the selected rectangular region.

        Args:
            frame: Frame from which to extract.
            rect: Rectangle to crop before OCR.
            pytesseract: pytesseract module reference.

        Returns:
            Extracted text.
        """
        crop_img = frame[rect.ymin:rect.ymax, rect.xmin:rect.xmax]
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        config = r'--oem 3 --psm 6 outputbase digits'
        text = pytesseract.image_to_string(gray, config=config)
        cv2.putText(frame, text, (100, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return text

    def track(self, rects: list[NormalizedRect], ocrrects: list[NormalizedRect], filters: Filters,
              crop: Crop, progress: Optional[IntVar] = None) -> None:
        """
        Perform optical flow tracking and optional OCR detection.

        Args:
            rects: Rectangles to track.
            ocrrects: Rectangles for OCR.
            filters: Filters to apply to each frame.
            crop: Cropper to apply to each frame.
            progress: Optional variable to report GUI progress.
        """
        if ocrrects:
            import pytesseract
            import platform
            if platform.system() == "Windows":
                tesseract_path = abspath("Tesseract-OCR/tesseract.exe")
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.logger.info("Tesseract OCR initialized for Windows at path: %s", tesseract_path)
            

        crwidth = crop.crprect.width if crop.crprect else self.fwidth
        crheight = crop.crprect.height if crop.crprect else self.fheight

        self._vidreader.seek(0)
        frame = self._vidreader.read()
        frame = cv2.resize(frame, (self.fwidth, self.fheight))
        frame = filters.appfilter(crop.appcrop(frame))
        fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        self.trackpts = [[] for _ in rects]
        self.texts = [[] for _ in ocrrects]
        ptstrack = []

        # Initial good features to track
        for rect in rects:
            pixrect = rect.norm2pix(crwidth, crheight)
            mask = np.zeros_like(fgray, dtype=np.uint8)
            mask[pixrect.ymin:pixrect.ymax, pixrect.xmin:pixrect.xmax] = 255
            p0 = cv2.goodFeaturesToTrack(
                fgray, maxCorners=100, qualityLevel=0.4,
                minDistance=5, blockSize=5, mask=mask
            )
            if p0 is not None:
                ptstrack.append(p0.astype(np.float32).reshape(-1, 1, 2))
            else:
                ptstrack.append(np.empty((0, 1, 2), dtype=np.float32))

        fprev = fgray.copy()
        fcount = self._vidreader.fcount

        lk_params = dict(
            winSize=(15, 15),
            maxLevel=5,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )

        for i in tqdm(range(fcount - 1)):
            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            frame = filters.appfilter(crop.appcrop(frame))
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            for j, p0 in enumerate(ptstrack):
                if p0.size == 0:
                    continue
                p1, st, _ = cv2.calcOpticalFlowPyrLK(fprev, fgray, p0, None, **lk_params)
                if p1 is not None and st is not None:
                    p1p = p1[st == 1].reshape(-1, 1, 2)
                    ptstrack[j] = p1p if p1p.size > 0 else p0
                else:
                    ptstrack[j] = p0
                x, y = self.pts2pt(ptstrack[j])
                self.trackpts[j].append([x, y])

            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(crwidth, crheight)
                text = self.ocr(frame, pixrect, pytesseract)
                self.texts[j].append(text)

            fprev = fgray.copy()

            # Optional live GUI update
            if self.tkqueue and not self.tkqueue.full():
                tkframe = frame.copy()
                for pts in self.trackpts:
                    for k in range(max(0, i - 30), i):
                        x, y = pts[k]
                        tkframe = cv2.circle(tkframe, (x, y), 5, (0, 0, 255), 1)
                self.tkqueue.put(tkframe)

            if progress is not None:
                progress.set((i / (fcount - 1)) * 100)

        # Final formatting
        for i in range(len(self.trackpts)):
            self.trackpts[i] = np.array(self.trackpts[i], dtype=np.float32).reshape(-1, 2)
            
        self.texts = OCRData(self.texts)


if __name__ == "__main__":
    from core import PixelRect
    rigid = Rigid("track-sfriction.mp4", 900, 600)
    rigid.addvideo("R1.mp4")
    rects = [PixelRect(284, 52, 23, 20)]
    rigid.track(rects, [], Filters(), Crop())
