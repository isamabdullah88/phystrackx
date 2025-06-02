from tqdm import tqdm
import cv2
import numpy as np
from math import floor
import matplotlib.pyplot as plt
from .Experiment import Experiment
from core.Rect import NormalizedRect, PixelRect

class SlidingFriction(Experiment):
    def __init__(self, trackpath):
        super().__init__()
        
        self._trackpath = trackpath
        self.trackpts = []
        
    
    def resize(self):
        """Resize frame shape to lower"""
        if self.fheight <= 360:
            return self.fwidth, self.fheight
        
        self.aspratio = self.fwidth/self.fheight

        self.fheight = 360
        self.fwidth = floor(self.aspratio * self.fheight)
    
    
    def track(self, rects:NormalizedRect, startidx=0, endidx=0):
        
        # Tracking
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # self.resize()
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, 24, (self.fwidth, self.fheight))
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx
        print('fcount: ', fcount)

        # Define Lucas-Kanade optical flow parameters
        lk_params = dict(winSize=(15, 15), maxLevel=5,criteria=(cv2.TERM_CRITERIA_EPS | \
            cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        ptstrack = []
        
        self._vidreader.seek(startidx)
        
        for rect in rects:
            rect = rect.norm2pix(self.fwidth, self.fheight)
            
            frame = self._vidreader.read()
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            mask = np.zeros_like(fgray, dtype=np.uint8)
            mask[rect.ymin:rect.ymax, rect.xmin:rect.xmax] = 255
            
            p0 = cv2.goodFeaturesToTrack(fgray, maxCorners=5, qualityLevel=0.5, minDistance=10, blockSize=5, mask=mask)
            p0 = np.array(p0, dtype=np.float32).reshape(-1, 1, 2)
            
            ptstrack.append(p0)
            
        fprev = None
        for i in tqdm(range(1, fcount-1), desc="Sliding Friction", total=fcount):
            frame = self._vidreader.read()
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if fprev is None:
                fprev = fgray.copy()
                continue

            for i,p0 in enumerate(ptstrack):
                p1, st, err = cv2.calcOpticalFlowPyrLK(fprev, fgray, p0, None, **lk_params)
                x, y = pts2pt(p1)
                cv2.circle(frame, (x, y), radius=5, color=(0,255,0), thickness=2)
                ptstrack[i] = p1
            
            # plt.imshow(frame)
            # plt.plot(p1[:,:,0], p1[:,:,1], 'r.')
            # plt.show()
            fprev = fgray.copy()
            # p0 = p1
            
            self._videowriter.write(frame)
            
        self._videowriter.release()
            # Add the set of tracked points
            # self.tracked_pts.append(tracked_pts)


def pts2pt(pts):
    """Convert points to single mean point."""
    x, y = np.mean(np.squeeze(pts), axis=0)
    return floor(x), floor(y)

if __name__ == '__main__':
    sliding_friction = SlidingFriction('track-sfriction.mp4')
    sliding_friction.add_video("R1.mp4")

    # sliding_friction.crop_intime()

    rects = [PixelRect(284, 52, 23, 20)]
    sliding_friction.track(rects, 100, 450)