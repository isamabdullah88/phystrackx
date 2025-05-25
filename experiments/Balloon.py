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
import matplotlib.pyplot as plt

from .Experiment import Experiment
from filters import Smoothen
from .Utils import ptsellpise

class Balloon(Experiment):
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
        if mask is None:
            edges = cv2.bitwise_and(edges, edges, mask=mask)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        # contour = max(contours, key=cv2.contourArea) if contours else None
        # if len(contours) > 0:
        #     cv2.drawContours(gray, contours, -1, (255, 255, 255), 5)
        
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



    def track(self, mask, rect, startidx=0, endidx=0):
        """Tracks boundary of balloon like objects and optionally text area.

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.

        It first establishes a base ellipse model for the balloon, using preprocessing and then 
        applying ransac on sampled data to fit the model on outlier-free subset of data.
        It then tracks the ellipse in time to detect time evolving ellipse.
        Note: Make sure that the first frame has almost perfectly accurate detection.
        """
        # Do OCR detection
        if rect is not None:
            rectp = rect.normal2pixel(self.fwidth, self.fheight)
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

        # Filters for trajectory smoothing
        # smoothenx = Smoothen(tol=50)
        # smootheny = Smoothen(tol=50)
        # smoothenr = Smoothen(tol=100)

        mask = cv2.resize(mask, (self.fwidth, self.fheight))
        # cv2.imwrite("bubble-mask.png", mask)
        
        coords = cv2.findNonZero(mask)
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(coords)
        mask = mask[y:y+h, x:x+w]
        
        ellipse = self.prepmask(mask)

        frame = self._vidreader.read()
        frame = cv2.resize(frame, (self.fwidth, self.fheight))

        frame = frame[y:y+h, x:x+w]

        initpts = ptsellpise(ellipse)

        alpha = 0.1
        beta = 5
        gamma = 0.01
        w_edge = 50
        w_line = 0
        # Run active contour on this frame
        gray = self.preprocess(frame, mask)
        gray = gaussian(gray, 3)
        snake = active_contour(gray, initpts, max_num_iter=2000, alpha=alpha, beta=beta,
                                    gamma=gamma, w_edge=w_edge, w_line=w_line)
        # snake = active_contour(gray, initpts)

        # Fit ellipse on the data
        snakecont = snake.copy().astype(np.float32).reshape(-1, 1, 2)
        ellipse = cv2.fitEllipse(snakecont[:, :,[1, 0]])

        plt.imshow(gray, cmap='gray')
        plt.plot(snakecont[:,:,1], snakecont[:,:,0], '--b')
        plt.plot(initpts[:,1], initpts[:,0], '--r')
        plt.show()

        for i in tqdm(range(fcount-1), desc="Balloon", total=fcount):

            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            xmin = max(0, floor(np.min(initpts[:, 1])))
            xmax = floor(np.max(initpts[:, 1]))
            ymin = max(0, floor(np.min(initpts[:, 0])))
            ymax = floor(np.max(initpts[:, 0]))
            # print('xmin, xmax, ymin, ymax: ', xmin, xmax, ymin, ymax)
            # frame = frame[ymin+y:y+ymax, x+xmin:x+xmax]
            if xmin < 100:
                x = x-100
                initpts[:, 1] = initpts[:, 1] + 100
            if ymin < 100:
                y = y-100
                initpts[:, 0] = initpts[:, 0] + 100
            if xmax+100 > w:
                w += 100
            if ymax + 100 > h:
                h += 100
            
            print('x, y, w, h: ', x, y, w, h)
            frame = frame[y:y+h, x:x+w]
            
            gray = self.preprocess(frame, None)
            gray = gaussian(gray, 3)

            (cx, cy), (a, b), angle = ellipse
            ellipse = (cx, cy), (a*0.8, b*0.8), angle
            
            # initpts = ptsellpise(ellipse, 100)

            snakep = active_contour(gray, initpts, max_num_iter=2000, alpha=alpha, beta=beta,
                                    gamma=gamma, w_edge=w_edge, w_line=w_line)
            
            # snakep = active_contour(gray, initpts)
            
            snakecontp = snakep.copy().astype(np.float32).reshape(-1, 1, 2)
            ellipse = cv2.fitEllipse(snakecontp[:,:,[1,0]])

            cv2.polylines(frame, [snakecontp[:,:,[1,0]].astype(np.int32)], isClosed=True,
                          color=(0, 255, 0), thickness=1)
            

            plt.figure(figsize=(12, 8))
            plt.imshow(gray, cmap='gray')
            plt.plot(initpts[:,1], initpts[:,0], '--b')
            plt.plot(snakecontp[:,:,1], snakecontp[:,:,0], 'g')
            plt.show()

            # ellipse = ellipsep
            initpts = snakep
            snakecont = snakecontp

            self._videowriter.write(frame)


        self._videowriter.release()




if __name__ == '__main__':
    balloon = Balloon("balloon-track.mp4")
    balloon.add_video("Balloon.mp4")
    mask = cv2.imread("mask-balloon.png", 0)
    balloon.track(mask, None, 100, 500)
    
    # balloon = Balloon("bubble-track.mp4")
    # balloon.add_video("Bubble-Laplace-Pressure.mp4")
    # mask = cv2.imread("bubble-mask.png", 0)
    # balloon.track(mask, None, 925, 3254)
