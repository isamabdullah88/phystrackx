from customtkinter import CTkCanvas, IntVar
from experiments.rigid.rigid import Rigid
from gui.plugins.crop import Crop
from gui.plugins.filters import Filters
from gui.components.spinner import Spinner
from gui.components.seekbar import TrimSeekBar
from gui.components.rect import Rect
from core import filexists

import logging
import os
import cv2
from PIL import Image, ImageTk


class Video:
    """Class to handle video viewing, frame manipulations"""
    def __init__(self, canvas:CTkCanvas, vwidth:int, vheight:int, crop:Crop, seekbar:TrimSeekBar, filters:Filters, spinner:Spinner):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.crop = crop
        self.seekbar = seekbar
        self.filters = filters
        self.spinner = spinner
        # self.fcount = 0
        self.frame = None
        
        tempdir = './temp'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        self.trimpath = os.path.join(tempdir, 'track-rigid.mp4')
        self.rigid = Rigid(trimpath=self.trimpath, vwidth=self.vwidth, vheight=self.vheight, tkqueue=self.spinner.queue)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Video App initializedyes")
        
        self.trimvideo = self.rigid.trim
        
    # @property
    # def tkqueue(self):
    #     return self.spinner.queue
    
    # @property
    # def fidx(self):
    #     return self.seekbar.idx
    
    # @property
    # def sfidx(self):
    #     return self.seekbar.startidx
    
    # @property
    # def efidx(self):
    #     return self.seekbar.endidx
    
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
    
    def loadvideo(self, videopath:str):
        if not filexists(videopath):
            self.logger.warning("Loading trim video")
            if not filexists(self.trimpath):
                self.logger.error("Trim video not found!")
            else:
                self.rigid.addvideo(self.trimpath)
        else:    
            self.rigid.addvideo(videopath)
            self.logger.info("Video added from: %s", videopath)
        
        self.imgview = self.canvas.create_image(self.crop.fx, self.crop.fy, anchor="nw")
        
        
    def resizef(self, frame, fwidth, fheight):
        """Resizes frame according to current fwidth and fheight"""
        frame = cv2.resize(frame, (fwidth, fheight))
        return frame
        
        
    def showframe(self, idx):
        """Updates and shows the frame to video view"""
        
        frame = self.rigid.frame(index=idx)
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
        # startidx = self.seekbar.startidx
        # endidx = self.seekbar.endidx
        self.canvas.tag_lower(self.imgview)
        
        self.rigid.track(trect.rects, ocr.rects, self.filters, self.crop, progress)
        
    def clear(self):
        self.rigid.trackpts.clear()
        
        