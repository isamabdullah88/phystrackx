
# from stardist.models import StarDist2D
# from stardist.plot import render_label
# from csbdeep.utils import normalize
from math import floor
import cv2
import numpy as np
from tqdm import tqdm

from .Experiment import Experiment
from filters import Smoothen
from core import Circle

class Marangoni(Experiment):
    def __init__(self, trackpath):
        super().__init__()

        self._trackpath = trackpath
        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")
        self.trackpts = []

    def track(self, mask, startidx=0, endidx=0):
        """Tracks the radius in marangoni effect

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.
        """
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, self._vidreader.fps,
                                            (self.fwidth, self.fheight))

        mask = cv2.resize(mask, (self.fwidth, self.fheight))

        self._vidreader.seek(startidx)
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx

        # Filters for trajectory smoothing
        smoothenx = Smoothen(tol=50)
        smootheny = Smoothen(tol=50)
        smoothenr = Smoothen(tol=100)


        for i in tqdm(range(fcount), desc="Marangoni", total=fcount):

            frame = self._vidreader.read()

            frame[mask < 150] = 0
            
            gray = np.sum(frame.copy(), axis=2)
            gray = 1-gray/np.max(gray)
            gray[gray > 0.75] = 0
            
            gray *= 5.5
                        
            gray[gray > 1] = 1
            gray = (gray * 255).astype(np.uint8)
            
            # Use Canny edge detection
            edges = cv2.Canny(gray*255, 25, 250)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            framep = frame.copy()
            cv2.drawContours(framep, contours, -1, (0, 255, 255), thickness=1)
            
            grayp = cv2.cvtColor(framep, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(grayp, 50, 250)
            kernel = np.ones((3, 3), np.uint8)

            # Dilate edges to close gaps
            edges = cv2.dilate(edges, kernel, iterations=1)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            contourr = sorted(contours, key=cv2.contourArea, reverse=True)[0]  # Largest contour only
            (x, y), r = cv2.minEnclosingCircle(contourr)
            cv2.drawContours(frame, [contourr], -1, (0, 255, 255), thickness=1)

            x = floor(smoothenx.smoothen(x))
            y = floor(smootheny.smoothen(y))
            r = floor(smoothenr.smoothen(r))

            # Draw the circle
            cv2.circle(frame, (x, y), r, (0, 0, 255), 2)  # Green circle

            # Store data
            self.trackpts.append(Circle(r, x, y))

            self._videowriter.write(frame)

        self._videowriter.release()

        # Store tracked points for later analysis
        # self.processor.points_tracked = points_tracked



if __name__ == '__main__':
    marangoni = Marangoni()
    marangoni.addvideo("../Dataset/Marangoni/Green_Marangoni_Bursting_1.mov")

    # marangoni.crop_intime()
    marangoni.track()
