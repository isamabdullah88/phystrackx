from enum import Enum

class FilterTypes(Enum):
    MONOCHROME = ("Monochrome", "assets/plugins/gray.png")
    GAUSSIANBLUR = ("Gaussian Blur", "assets/plugins/gblur.png")
    MEDIANBLUR = ("Median Blur", "assets/plugins/mblur.png")
    BILATERALFILTER = ("Bilteral Filter", "assets/plugins/bfilter.png")
    CANNYEDGE = ("Canny Edge", "assets/plugins/canny.png")
    CONTRAST = ("Contrast", "assets/plugins/contrast.png")
    BRIGHTNESS = ("Brightness", "assets/plugins/brightness.png")
    NONE = ("None", "")
    
    def __init__(self, label, ipath):
        self.label = label
        self.ipath = ipath

