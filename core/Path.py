import os
import sys

def abspath(rpath):
    bpath = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(bpath, rpath)