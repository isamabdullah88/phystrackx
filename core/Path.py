import os
import sys

def abspath(rpath):
    bpath = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(bpath, rpath)

def filexists(filepath):
    """Check if a file exists."""
    return os.path.isfile(filepath)