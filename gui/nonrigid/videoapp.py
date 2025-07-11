from customtkinter import CTkCanvas, IntVar
from experiments import Marangoni
from gui.plugins import Crop, Filters
from gui.components.seekbar import CutSeekBar
from gui.components.spinner import Spinner
from gui.components.rect import Rect

import os
import cv2
from PIL import Image, ImageTk


class Video:
    """Class to handle video viewing, frame manipulations"""
    def __init__(self, canvas:CTkCanvas, vwidth:int, vheight:int, crop:Crop, seekbar:CutSeekBar, filters:Filters, spinner:Spinner):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.crop = crop
        self.seekbar = seekbar
        self.filters = filters
        # self.fcount = 0
        self.frame = None
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self.trackpath = os.path.join(tempdir, 'track-rigid.mp4')
        self.rigid = Marangoni(trackpath=self.trackpath, vwidth=self.vwidth, vheight=self.vheight, tkqueue=spinner.queue)
        
        self.imgview = self.canvas.create_image(self.crop.fx, self.crop.fy, anchor="nw")
    
    @property
    def fcount(self):
        return self.rigid.fcount
    
    @property
    def trackpts(self):
        return self.rigid.trackpts
    
    @property
    def texts(self):
        return self.rigid.texts
    
    @property
    def fps(self):
        return self.rigid.fps
    
    @property
    def fwidth(self):
        return self.rigid.fwidth
    
    @property
    def fheight(self):
        return self.rigid.fheight
    
    def loadvideo(self, videopath):
        self.rigid.addvideo(videopath)
        
        
        
    def resizef(self, frame, fwidth, fheight):
        """Resizes frame according to current fwidth and fheight"""
        frame = cv2.resize(frame, (fwidth, fheight))
        return frame
        
        
    def showframe(self):
        """Updates and shows the frame to video view"""
        
        frame = self.rigid.frame(index=self.seekbar.idx)
        frame = self.resizef(frame, self.fwidth, self.fheight)
        
        # Apply filter
        frame = self.filters.appfilter(frame)
        
        # Apply crop
        self.frame = self.crop.appcrop(frame)
        
        img = Image.fromarray(cv2.cvtColor(self.frame.copy(), cv2.COLOR_BGR2RGB))
        self.tkimg = ImageTk.PhotoImage(image=img)
        
        self.canvas.coords(self.imgview, self.crop.crpx, self.crop.crpy)
        self.canvas.itemconfig(self.imgview, image=self.tkimg)
        
    def track(self, trect:Rect, ocr:Rect, progress:IntVar):
        startidx = self.seekbar.startidx
        endidx = self.seekbar.endidx
        self.rigid.track(trect.rects, ocr.rects, self.filters, self.crop, startidx, endidx, progress)
        
        
        
        