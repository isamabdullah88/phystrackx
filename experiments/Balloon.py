from math import floor
import cv2
import numpy as np
from tqdm import tqdm
from skimage.segmentation import active_contour
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
        if self.frame_height <= 360:
            return self.frame_width, self.frame_height
        
        self.aspratio = self.frame_width/self.frame_height

        self.frame_height = 360
        self.frame_width = floor(self.aspratio * self.frame_height)


    def preprocess(self, frame):
        """Preprocesses the frame to sharpen the edges"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
        gray = clahe.apply(gray)

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


    def track(self, mask, startidx=0, endidx=0):
        """Tracks the radius in marangoni effect

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.

        It first establishes a base ellipse model for the balloon, using preprocessing and then 
        applying ransac on sampled data to fit the model on outlier-free subset of data.
        It then tracks the ellipse in time to detect time evolving ellipse.
        Note: Make sure that the first frame has almost perfectly accurate detection.
        """
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.resize()
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, 24, (self.frame_width, self.frame_height))

        self._vidreader.seek(startidx)
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx

        # Filters for trajectory smoothing
        # smoothenx = Smoothen(tol=50)
        # smootheny = Smoothen(tol=50)
        # smoothenr = Smoothen(tol=100)

        mask = cv2.resize(mask, (self.frame_width, self.frame_height))
        
        ellipse = self.prepmask(mask)

        frame = self._vidreader.read()
        frame = cv2.resize(frame, (self.frame_width, self.frame_height))

        initpts = ptsellpise(ellipse)

        # Run active contour on this frame
        gray = self.preprocess(frame)
        snake = active_contour(gray, initpts)

        # Fit ellipse on the data
        snakecont = snake.copy().astype(np.float32).reshape(-1, 1, 2)
        ellipse = cv2.fitEllipse(snakecont[:, :,[1, 0]])

        for i in tqdm(range(fcount-1), desc="Balloon", total=fcount):

            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            gray = self.preprocess(frame)

            initpts = ptsellpise(ellipse, snake.shape[0])

            snakep = active_contour(gray, initpts, max_num_iter=100, gamma=0.5)
            snakecontp = snakep.copy().astype(np.float32).reshape(-1, 1, 2)
            ellipsep = cv2.fitEllipse(snakecontp[:,:,[1,0]])

            cv2.polylines(frame, [snakecontp[:,:,[1,0]].astype(np.int32)], isClosed=True,
                          color=(0, 255, 0), thickness=1)
            
            snakecont = snakecontp
            ellipse = ellipsep

            self._videowriter.write(frame)


        self._videowriter.release()



if __name__ == '__main__':
    balloon = Balloon("track.mp4")
    balloon.add_video("Balloon.mp4")

    mask = cv2.imread("mask-balloon.png", 0)
    balloon.track(None, 100, 500)
