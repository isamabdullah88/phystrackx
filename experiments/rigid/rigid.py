from tqdm import tqdm
import cv2
import numpy as np
from experiments.experiment import Experiment
from customtkinter import IntVar
from core import NormalizedRect, PixelRect
from gui.plugins import Crop, Filters
from queue import Queue


class Rigid(Experiment):
    def __init__(self, trimpath, vwidth, vheight, tkqueue:Queue=None):
        super().__init__(vwidth, vheight)
        
        self.trimpath = trimpath
        self.trackpts = []
        self.texts = []
        
        self.tkqueue = tkqueue
        
    # TODO: Major reconstruction needed for OCR
    def ocr(self, frame, rect, pytesseract):
        """Performs OCR detection on the specified rectangle in the frame."""
        
        framep = frame.copy()[rect.ymin:rect.ymax, rect.xmin:rect.xmax]
        
        # Convert to grayscale
        gray = cv2.cvtColor(framep, cv2.COLOR_BGR2GRAY)
        
        custom_config = r'--oem 3 --psm 6 outputbase digits'
        text = pytesseract.image_to_string(gray, config=custom_config)
        
        cv2.putText(frame, text, (100, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return text
    
    
    def trim(self, startidx:int=0, endidx:int=0):
        """Trims the video between the frame indices"""
        
        self.resize()
        print('startidx, endidx: ', startidx, endidx)
            
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        videowriter = cv2.VideoWriter(self.trimpath, fourcc, self._vidreader.fps,
                                            (self.fwidth, self.fheight))
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx
            
        self._vidreader.seek(startidx)
        for i in range(fcount):
            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            
            videowriter.write(frame)
            
            if i%100 == 0:
                print('i: ', i)
            
        videowriter.release()    
        
    
    def track(self, rects:list[NormalizedRect], ocrrect:list[NormalizedRect], filters:Filters, crop:Crop, startidx=0, endidx=0, progress:IntVar=None):
        """Tracks the specified rectangles in the video and performs OCR detection if specified."""
        
        
        # Import for OCR detection
        if len(ocrrect) > 0:
            import pytesseract
            import platform
            if platform.system() == 'Windows':
                pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        self.resize()
        
        crwidth = self.fwidth
        crheight = self.fheight
        if crop.crprect is not None:
            crwidth = crop.crprect.width
            crheight = crop.crprect.height
        
        # Tracking
        # fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # self._videowriter = cv2.VideoWriter(self.trimpath, fourcc, self._vidreader.fps,
        #                                     (crwidth, crheight))
        
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
        self.texts = [[] for _ in ocrrect]
        
        frame = self._vidreader.read()
        frame = cv2.resize(frame, (self.fwidth, self.fheight))
        
        # Apply transformations to frame
        frame = filters.appfilter(frame)
        frame = crop.appcrop(frame)
        
        fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # TODO: Major reconstruction needed for Track
        for rect in rects:
            rect = rect.norm2pix(crwidth, crheight)

            mask = np.zeros_like(fgray, dtype=np.uint8)
            mask[rect.ymin:rect.ymax, rect.xmin:rect.xmax] = 255
            
            p0 = cv2.goodFeaturesToTrack(fgray, maxCorners=100, qualityLevel=0.4, minDistance=5, blockSize=5, mask=mask)
            if p0 is None:
                continue
            
            p0 = np.array(p0, dtype=np.float32).reshape(-1, 1, 2)
        
            ptstrack.append(p0)
            
        fprev = None
        for i in tqdm(range(0, fcount-1), desc="Rigid", total=fcount-1):
            frame = self._vidreader.read()
            frame = cv2.resize(frame, (self.fwidth, self.fheight))
            
            # Apply transformations to frame
            frame = filters.appfilter(frame)
            frame = crop.appcrop(frame)
            
            fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if fprev is None:
                fprev = fgray.copy()
                continue

            for j,p0 in enumerate(ptstrack):
                p1, st, err = cv2.calcOpticalFlowPyrLK(fprev, fgray, p0, None)
                
                if p1 is not None:
                    p1p = p1.copy()[st == 1].reshape(-1,1,2)
                    if p1p.size == 0:
                        p1p = p0.copy()
                else:
                    p1p = p0.copy()
                
                x, y = self.pts2pt(p1p)
                ptstrack[j] = p1p
                
                self.trackpts[j].append([x,y])
            
            
            # Do OCR detection if specified
            for j,rect in enumerate(ocrrect):
                rectp = rect.norm2pix(crwidth, crheight)
                text = self.ocr(frame, rectp, pytesseract)
                self.texts[j].append(text)
            
            fprev = fgray.copy()
            
                
            
            tkframe = frame.copy()
            for pts in self.trackpts:
                for j in range(max(0, i-30), i):
                    x, y = pts[j]
                    tkframe = cv2.circle(tkframe, (x, y), 5, (0,0,255), 1)
            # Frontend variables
            if self.tkqueue and (not self.tkqueue.full()):
                self.tkqueue.put(tkframe)
                
            if progress is not None:
                progress.set((i / (fcount - 1)) * 100)

            # self._videowriter.write(frame)
            
        # self._videowriter.release()

        for i in range(len(self.trackpts)):
            self.trackpts[i] = np.array(self.trackpts[i], dtype=np.float32).reshape(-1, 2)



if __name__ == '__main__':
    sliding_friction = Rigid('track-sfriction.mp4')
    sliding_friction.addvideo("R1.mp4")
    
    rects = [PixelRect(284, 52, 23, 20)]
    sliding_friction.track(rects, 100, 450)
    sliding_friction.plot()
    
    