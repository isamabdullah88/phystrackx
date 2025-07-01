from tqdm import tqdm
import cv2
import numpy as np
from .Experiment import Experiment
from core import NormalizedRect, PixelRect
from PIL import Image, ImageDraw, ImageFont


class Rigid(Experiment):
    def __init__(self, trackpath, vwidth=900, vheight=600):
        super().__init__(vwidth, vheight)
        
        self._trackpath = trackpath
        self.trackpts = []
        
    def ocr(self, frame, rect, pytesseract):            
        """Performs OCR detection on the specified rectangle in the frame."""
        x, y, w, h = rect.totuple()
        framep = frame.copy()[y:y+h, x:x+w]
        # Convert to grayscale
        gray = cv2.cvtColor(framep.copy(), cv2.COLOR_BGR2GRAY)

        # Optional: thresholding to improve contrast
        # plt.imshow(gray)
        # _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
        
        custom_config = r'--oem 3 --psm 6 outputbase digits'
        txt = pytesseract.image_to_string(gray, config=custom_config)
        
        cv2.putText(frame, txt, (100, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
    
    def track(self, rects:list[NormalizedRect], ocrrect:list[NormalizedRect], startidx=0, endidx=0, progress=None):
        """Tracks the specified rectangles in the video and performs OCR detection if specified."""
        
        # Import for OCR detection
        if len(ocrrect) > 0:
            import pytesseract
            import platform
            if platform.system() == 'Windows':
                pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
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
            
            p0 = cv2.goodFeaturesToTrack(fgray, maxCorners=100, qualityLevel=0.4, minDistance=5, blockSize=5, mask=mask)
            if p0 is None:
                continue
            
            p0 = np.array(p0, dtype=np.float32).reshape(-1, 1, 2)
        
            ptstrack.append(p0)
            
        fprev = None
        for i in tqdm(range(1, fcount-1), desc="Rigid", total=fcount-1):
            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if fprev is None:
                fprev = fgray.copy()
                continue

            for j,p0 in enumerate(ptstrack):
                p1, st, err = cv2.calcOpticalFlowPyrLK(fprev, fgray, p0, None)
                
                if p1 is not None:
                    p1p = p1.copy()[st == 1].reshape(-1,1,2)
                
                # for p in p1:
                #     a, b = p.ravel()
                #     cv2.circle(frame, (int(a), int(b)), radius=5, color=(0,255,0), thickness=2)
                    
                # for p in p1p:
                #     a, b = p.ravel()
                #     cv2.circle(frame, (int(a), int(b)), radius=5, color=(255,0,0), thickness=2)
                
                x, y = self.pts2pt(p1p)
                cv2.circle(frame, (x, y), radius=5, color=(0,0,255), thickness=2)
                ptstrack[j] = p1p
                
                self.trackpts[j].append([x,y])
            
            
            # Do OCR detection if specified
            for rect in ocrrect:
                rectp = rect.norm2pix(self.fwidth, self.fheight)
                self.ocr(frame, rectp, pytesseract)
            
            fprev = fgray.copy()
            
            self._videowriter.write(frame)
            
            if progress is not None:
                progress.set((i / (fcount - 1)) * 100)
            
        self._videowriter.release()

        for i in range(len(self.trackpts)):
            self.trackpts[i] = np.array(self.trackpts[i], dtype=np.float32).reshape(-1, 2)



if __name__ == '__main__':
    sliding_friction = Rigid('track-sfriction.mp4')
    sliding_friction.add_video("R1.mp4")
    
    rects = [PixelRect(284, 52, 23, 20)]
    sliding_friction.track(rects, 100, 450)
    sliding_friction.plot()
    
    