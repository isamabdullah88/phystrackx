"""
This module implements the Balloon experiment, which tracks the boundary of balloon-like objects
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

from core import PixelRect
from experiments.experiment import Experiment
from filters import Smoothen
from .utils import ptsellpise

class Balloon(Experiment):
    def __init__(self, trimpath, vwidth, vheight, tkqueue):
        super().__init__(trimpath, vwidth, vheight)

        self.tkqueue = tkqueue
        self.trackpts: list[list[int]] = []
        self.texts: list[list[str]] = []

    # def resize(self):
    #     """Resize frame shape to lower"""
    #     if self.fheight <= 360:
    #         return self.fwidth, self.fheight
        
    #     self.aspratio = self.fwidth/self.fheight

    #     self.fheight = 360
    #     self.fwidth = floor(self.aspratio * self.fheight)


    def preprocess(self, frame, mask=None):
        """Preprocesses the frame to sharpen the edges"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
        gray = clahe.apply(gray)
        
        # edges = cv2.Canny(gray, 100, 150)
        # Apply mask to the edges
        # if mask is not None:
        #     edges = cv2.bitwise_and(edges, edges, mask=mask)
        # contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        # contour = max(contours, key=cv2.contourArea) if contours else None
        # if len(contours) > 0:
        #     cv2.drawContours(gray, contours, -1, (255, 255, 255), 5)
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
        """offsets ellipse by the rectangle"""
        (cx, cy), (a, b), angle = ellipse
        
        x, y, w, h = rect.totuple()

        if (x-val >= 0) and (cx-a/2 < val):
            x = x-val
            cx += val
            w += val

        if (y-val >= 0) and (cy-b/2 < val):
            y = y-val
            cy += val
            h += val

        if (w+val < self.fwidth) and (a+val > w-val):
            w += val

        if (h+val < self.fheight) and (b+val > h-val):
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



    def track(self, mask, ocrrects, filters, crop, progress):
        """Tracks boundary of balloon like objects and optionally text area.

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.

        It first establishes a base ellipse model for the balloon, using preprocessing and then 
        applying ransac on sampled data to fit the model on outlier-free subset of data.
        It then tracks the ellipse in time to detect time evolving ellipse.
        Note: Make sure that the first frame has almost perfectly accurate detection.
        """
        if ocrrects:
            import pytesseract
            import platform
            if platform.system() == "Windows":
                pytesseract.pytesseract.tesseract_cmd = (
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                )

        self.resize()

        # Tracking
        # fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # # self.resize()
        # self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, self._vidreader.fps,
        #                                     (self.fwidth, self.fheight))

        crwidth = crop.crprect.width if crop.crprect else self.fwidth
        crheight = crop.crprect.height if crop.crprect else self.fheight

        # self._vidreader.seek(0)
        # frame = self._vidreader.read()
        # frame = cv2.resize(frame, (self.fwidth, self.fheight))
        # frame = filters.appfilter(crop.appcrop(frame))

        mask = cv2.resize(mask, (self.fwidth, self.fheight))
        
        rect = self.mask2rect(mask)
        mask = mask[rect.ymin:rect.ymax, rect.xmin:rect.xmax]
        ellipse = self.prepmask(mask)

        # initpts = ptsellpise(ellipse)

        alpha = 0.01
        beta = 1
        gamma = 0.01
        w_edge = 50
        w_line = 0
        maxiters = 1000

        asp = []
        bs = []
        angles = []
        
        # Filters for trajectory smoothing
        smoothena = Smoothen(tol=50, winlen=5)
        smoothenb = Smoothen(tol=50, winlen=5)

        fcount = self._vidreader.fcount
        startrect = rect
        self.trackpts = [[]]
        for i in tqdm(range(fcount-1), desc="Balloon", total=fcount):

            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            frame = filters.appfilter(crop.appcrop(frame))

            rectp, ellipse = self.offellipse(ellipse, rect, 100)
            initpts = ptsellpise(ellipse, 100)
            
            framep = frame.copy()[rectp.ymin:rectp.ymax, rectp.xmin:rectp.xmax]
            
            gray = self.preprocess(framep, None)
            gray = gaussian(gray, 3)

            initpts = active_contour(gray, initpts, max_num_iter=maxiters, alpha=alpha, beta=beta,
                                    gamma=gamma, w_edge=w_edge, w_line=w_line)
            

            (cx, cy), (a, b), angle = ellipse
            # snakecontp = initpts.copy().astype(np.float32).reshape(-1, 1, 2)
            ellipse = cv2.fitEllipse(initpts.copy()[:,[1,0]].reshape(-1, 1, 2).astype(np.float32))

            (cx, cy), (a, b), angle = ellipse

            asp.append(a)
            bs.append(b)
            angles.append(angle)

            if startrect.xmin != rectp.xmin:
                cx -= (startrect.xmin - rectp.xmin)
            if startrect.ymin != rectp.ymin:
                cy -= (startrect.ymin-rectp.ymin)
                
            ellipse = (cx, cy), (a, b), angle
            
            a = smoothena.smoothen(a)
            b = smoothenb.smoothen(b)
            
            ellipse = (cx, cy), (a, b), angle

            (cx, cy), (a, b), angle = ellipse
            if startrect.xmin != rectp.xmin:
                cx += (startrect.xmin - rectp.xmin)
            if startrect.ymin != rectp.ymin:
                cy += (startrect.ymin-rectp.ymin)
                
            ellipse = (cx, cy), (a, b), angle

            rect = rectp
            snakecont = initpts.copy()[:,[1,0]].astype(np.int32).reshape(-1, 1, 2)
            snakecont[:, :, 0] += rect.xmin
            snakecont[:, :, 1] += rect.ymin
            (cx, cy), (a, b), angle = ellipse
            cv2.polylines(frame, [snakecont], isClosed=True, color=(0, 255, 0), thickness=1)
            cv2.ellipse(frame, center=(floor(cx+rect.xmin), floor(cy+rect.ymin)), axes=(floor(b/2), floor(a/2)), angle=angle, color=(0,0,255), startAngle=0,
                        endAngle=360, thickness=2)
            
            self.trackpts[0].append(snakecont.reshape(-1, 2))

            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(crwidth, crheight)
                text = self.ocr(frame, pixrect, pytesseract)
                self.texts[j].append(text)

            if progress is not None:
                progress.set((i / (fcount - 1)) * 100)

            # self._videowriter.write(frame)
        # self._vidreader.release()

        print('video reader released')


        # self._videowriter.release()




if __name__ == '__main__':
    balloon = Balloon("balloon-track.mp4")
    balloon.addvideo("Balloon.mp4")
    mask = cv2.imread("mask-balloon.png", 0)
    balloon.track(mask, None, 100, 500)
    
    balloon = Balloon("bubble-track.mp4")
    balloon.addvideo("Bubble-Laplace-Pressure.mp4")
    mask = cv2.imread("bubble-mask.png", 0)
    balloon.track(mask, None, 925, 3200)
