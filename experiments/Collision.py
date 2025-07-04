from tqdm import tqdm
import cv2
import numpy as np
from math import floor
from .Experiment import Experiment
from core.Rect import NormalizedRect

class Collision(Experiment):
    def __init__(self, trackpath, vwidth=900, vheight=600):
        super().__init__(vwidth, vheight)
        
        self._trackpath = trackpath
        self.trackpts = []
    
    def track(self, rects:list[NormalizedRect], startidx=0, endidx=0):
        
        # Tracking
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.resize()
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, self._vidreader.fps,
                                            (self.fwidth, self.fheight))
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx

        # Define Lucas-Kanade optical flow parameters
        lk_params = dict(winSize=(15, 15), maxLevel=5,criteria=(cv2.TERM_CRITERIA_EPS | \
            cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        ptstrack = []
        
        self._vidreader.seek(startidx)
        
        self.trackpts = [[] for _ in rects]
        
        frame = self._vidreader.read()
        fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
        for rect in rects:
            rect = rect.norm2pix(self.fwidth, self.fheight)

            mask = np.zeros_like(fgray, dtype=np.uint8)
            mask[rect.ymin:rect.ymax, rect.xmin:rect.xmax] = 255
            
            p0 = cv2.goodFeaturesToTrack(fgray, maxCorners=5, qualityLevel=0.5, minDistance=10, blockSize=5, mask=mask)
            p0 = np.array(p0, dtype=np.float32).reshape(-1, 1, 2)
            
            ptstrack.append(p0)
            
        fprev = None
        for i in tqdm(range(1, fcount-1), desc="Sliding Friction", total=fcount-1):
            frame = self._vidreader.read()
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if fprev is None:
                fprev = fgray.copy()
                continue

            for j,p0 in enumerate(ptstrack):
                p1, st, err = cv2.calcOpticalFlowPyrLK(fprev, fgray, p0, None, **lk_params)
                x, y = self.pts2pt(p1)
                cv2.circle(frame, (x, y), radius=5, color=(0,255,0), thickness=2)
                ptstrack[j] = p1
                
                self.trackpts[j].append([x,y])
            
            fprev = fgray.copy()
            
            self._videowriter.write(frame)
            
        self._videowriter.release()

        for i in range(len(self.trackpts)):
            self.trackpts[i] = np.array(self.trackpts[i], dtype=np.float32).reshape(-1, 2)


if __name__ == '__main__':
    collision = Collision('track-collision.mp4')
    collision.addvideo("HeadOn.MP4")
    
    rects = [
        NormalizedRect(3/320, 48/240, 27/320, 27/240),
        NormalizedRect(137/320, 73/240, 28/320, 27/240)
    ]
    collision.track(rects, startidx=135, endidx=270)
    # collision.plotdrv()
    from gui.Plot import Plot
    plot = Plot(collision.trackpts)
    plot.plotx()
    plot.plotdrv()
    plot.show()