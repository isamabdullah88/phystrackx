"""
This module implements the Interface experiment, which tracks the boundary of balloon-like objects
and optionally performs OCR on a specified rectangle in the video frames.

Notes:
Following points must be considered while using this:
* The video containing balloon like object must have a plain background with least texture.
* The camera should not be moving while balloon is being inflated.
* The video should be of high resolution.s
"""
from math import floor
import cv2
import numpy as np
from tqdm import tqdm
from skimage.segmentation import active_contour
from skimage.filters import gaussian
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

from .Experiment import Experiment
from filters import Smoothen
from .Utils import ptsline
from core import PixelRect, Points

class Interface(Experiment):
    def __init__(self, trackpath):
        super().__init__()

        self._trackpath = trackpath

    def resize(self):
        """Resize frame shape to lower"""
        if self.fheight <= 360:
            return self.fwidth, self.fheight
        
        self.aspratio = self.fwidth/self.fheight

        self.fheight = 360
        self.fwidth = floor(self.aspratio * self.fheight)


    def preprocess(self, frame, mask=None):
        """Preprocesses the frame to sharpen the edges"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
        gray = clahe.apply(gray)
        
        edges = cv2.Canny(gray, 100, 150)
        # Apply mask to the edges
        if mask is not None:
            edges = cv2.bitwise_and(edges, edges, mask=mask)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        # contour = max(contours, key=cv2.contourArea) if contours else None
        if len(contours) > 0:
            cv2.drawContours(gray, contours, -1, (255, 255, 255), 3)
        
        # plt.imshow(edges, cmap='gray')
        # plt.imshow(gray, cmap='gray')
        # plt.show()

        return gray
    
    def prepmask(self, mask):
        """Preprocess and convert user defined mask to ellipse. Also convert from opencv
        (x,y) to (r,c)"""
        _, thresh = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contour = max(contours, key=cv2.contourArea)
        ellipse = cv2.fitEllipse(contour)
        (xc, yc), (a, b), angle = ellipse

        return (xc, yc), (a, b), angle
    

    def offset(self, initpts, rect: PixelRect, val: int):
        xmin = max(0, floor(np.min(initpts[:, 1])))
        xmax = floor(np.max(initpts[:, 1]))
        ymin = max(0, floor(np.min(initpts[:, 0])))
        ymax = floor(np.max(initpts[:, 0]))
        
        x, y, w, h = rect.totuple()

        if xmin < val:
            x = x-val
            initpts[:, 1] = initpts[:, 1] + val
        if ymin < val:
            y = y-val
            initpts[:, 0] = initpts[:, 0] + val
        if xmax+val > w:
            w += val
        if ymax + val > h:
            h += val        

        return PixelRect(x, y, w, h)
    
    def offellipse(self, ellipse, rect: PixelRect, val: int):
        (cx, cy), (a, b), angle = ellipse
        
        x, y, w, h = rect.totuple()

        if cx-a/2 < val:
            x = x-val
            cx += val
            w += val

        if cy-b/2 < val:
            y = y-val
            cy += val
            h += val

        if a+val > w-val:
            w += val

        if b+val > h-val:
            h += val

        ellipse = (cx, cy), (a, b), angle

        return PixelRect(x, y, w, h), ellipse
    

    def mask2rect(self, mask):

        coords = cv2.findNonZero(mask)
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(coords)

        return PixelRect(x, y, w, h)


    def ocr(self, rect, startidx=0, endidx=0):
        import pytesseract
        # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        self._vidreader.seek(startidx)
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx

        x, y, w, h = rect.totuple()
        print('rect: ', rect.totuple())
        print('fw, fh: ', (self.fwidth, self.fheight))
            
        for i in range(fcount):

            frame = self._vidreader.read()
            frame = frame[y:y+h, x:x+w]
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Optional: thresholding to improve contrast
            # plt.imshow(gray)
            # _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
            
            custom_config = r'--oem 3 --psm 6 outputbase digits'
            numbers = pytesseract.image_to_string(gray, config=custom_config)
            print("Number:", numbers)



    def track(self, lcoords: Points, rect, startidx=0, endidx=0):
        """Tracks boundary of balloon like objects and optionally text area.

        Args:
            lcoords (np.ndarray): Line coordinates that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.

        It first establishes a base ellipse model for the balloon, using preprocessing and then 
        applying ransac on sampled data to fit the model on outlier-free subset of data.
        It then tracks the ellipse in time to detect time evolving ellipse.
        Note: Make sure that the first frame has almost perfectly accurate detection.
        """
        # Do OCR detection
        if rect is not None:
            rectp = rect.norm2pix(self.fwidth, self.fheight)
            self.ocr(rectp, startidx=startidx, endidx=endidx)

        # Tracking
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # self.resize()
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, 24, (self.fwidth, self.fheight))

        self._vidreader.seek(startidx)
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx

        alpha = 1
        beta = 1
        gamma = 0.01
        w_edge = 5
        w_line = 15
        maxiters = 1000
        
        lcoords = lcoords.norm2pix(self.fwidth, self.fheight)
        rect = lcoords.pts2rect()
        
        initpts = ptsline(lcoords, numpts=100, xoff=rect.xmin, yoff=rect.ymin)

        for i in tqdm(range(fcount-1), desc="Interface", total=fcount):

            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))

            framep = frame.copy()[rect.ymin:rect.ymax, rect.xmin:rect.xmax]
            
            gray = self.preprocess(framep, None)
            gray = gaussian(gray, 3)

            initpts = active_contour(gray, initpts, max_num_iter=maxiters, alpha=alpha, beta=beta,
                                    gamma=gamma, w_edge=w_edge, w_line=w_line, 
                                    boundary_condition='fixed')
            
            cv2.polylines(framep, [initpts[:, [1, 0]].astype(np.int32)], isClosed=False,
                          color=(0, 255, 0), thickness=2)

            frame[rect.ymin:rect.ymax, rect.xmin:rect.xmax] = framep

            self._videowriter.write(frame)


        self._videowriter.release()




if __name__ == '__main__':
    balloon = Interface("interface-track.mp4")
    balloon.add_video("Candle1.mp4")
    # mask = cv2.imread("mask-balloon.png", 0)
    balloon.track(None, None, 100, 3500)
