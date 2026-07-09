import cv2
import platform
import logging
from core import abspath

class OcrEngine:
    """Manages framework initializations and string digitization from frame segments."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    def lazy_initialize(self) -> None:
        """Ensures platform-specific system drivers load cleanly exactly once."""
        if self._initialized:
            return
            
        import pytesseract
        self.pytesseract = pytesseract
        
        if platform.system() == "Windows":
            tesseract_path = abspath("Tesseract-OCR/tesseract.exe")
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            self.logger.info(f"Tesseract binary verified for Windows environments at: {tesseract_path}")
            
        self._initialized = True

    def extract_digits(self, frame: cv2.Mat, pixrect) -> str:
        """Processes bounded images converting pixel sub-matrices to string sequences."""
        self.lazy_initialize()
        
        crop_img = frame[pixrect.ymin:pixrect.ymax, pixrect.xmin:pixrect.xmax]
        if crop_img.size == 0:
            return ""
            
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        config = r'--oem 3 --psm 6 outputbase digits'
        
        text = self.pytesseract.image_to_string(gray, config=config).strip()
        cv2.putText(frame, text, (100, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return text