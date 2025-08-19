
# from stardist.models import StarDist2D
# from stardist.plot import render_label
# from csbdeep.utils import normalize
from math import floor
import cv2
import numpy as np
from tqdm import tqdm

from experiments.experiment import Experiment
from experiments.components.ocr import OCRData
from filters.smoothen import Smoothen
from core.circle import Circle
from gui.plugins.filters import Filters 
from gui.plugins.crop import Crop
from customtkinter import IntVar
from queue import Queue

class Marangoni(Experiment):
    def __init__(self, trimpath, vwidth, vheight, tkqueue:Queue=None):
        super().__init__(trimpath, vwidth, vheight)

        self.tkqueue = tkqueue
        self.trackpts: list[list[np.ndarray]] = []
        self.texts: list[list[str]] = []

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


    def track(self, mask, ocrrects, filters:Filters, crop:Crop, progress: IntVar=None):
        """Tracks the radius in marangoni effect

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.
        """
        if ocrrects:
            import pytesseract
            import platform
            if platform.system() == "Windows":
                pytesseract.pytesseract.tesseract_cmd = (
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                )

        self.resize()

        crwidth = crop.crprect.width if crop.crprect else self.fwidth
        crheight = crop.crprect.height if crop.crprect else self.fheight

        mask = cv2.resize(mask, (self.fwidth, self.fheight))

        # self._vidreader.seek(startidx)
        
        # if endidx == 0:
        #     fcount = self._vidreader.fcount - startidx
        # else:
        #     fcount = endidx - startidx

        # Filters for trajectory smoothing
        smoothenx = Smoothen(tol=50)
        smootheny = Smoothen(tol=50)
        smoothenr = Smoothen(tol=100)

        fcount = self._vidreader.fcount
        self.trackpts = [[]]
        for i in tqdm(range(fcount-1), desc="Marangoni", total=fcount-1):

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
            
            self.trackpts[0].append(contourr.reshape(-1, 2).astype(np.float32))

            for j, rect in enumerate(ocrrects):
                pixrect = rect.norm2pix(crwidth, crheight)
                text = self.ocr(frame, pixrect, pytesseract)
                self.texts[j].append(text)
            
            if progress is not None:
                progress.set((i / (fcount - 1)) * 100)
        
        self.texts = OCRData(self.texts)



if __name__ == '__main__':
    marangoni = Marangoni()
    marangoni.addvideo("../Dataset/Marangoni/Green_Marangoni_Bursting_1.mov")

    # marangoni.crop_intime()
    marangoni.track()
