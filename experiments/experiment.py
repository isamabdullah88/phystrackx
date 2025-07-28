
import sys
import os
import re

from itertools import groupby
from math import floor

import cv2
import numpy as np
from media.videoreader import VideoReader
from media import proxyvideo, trimvideo

class Experiment:
    def __init__(self, trimpath, vwidth, vheight):
        
        if not sys.stdout or not sys.stdout.isatty():
            # Create a logs directory if it doesn't exist
            if not os.path.exists("logs"):
                os.makedirs("logs")

            # Redirect standard output and standard error to log files
            sys.stdout = open("logs/stdout.log", "a")
            sys.stderr = open("logs/stderr.log", "a")
        
        self._vidreader = None
        self.fwidth = None
        self.fheight = None
        self.fcount = 0
        
        self.vwidth = vwidth
        self.vheight = vheight
        
        self.active_duration = []
        
        self.videopath = None
        self.proxypath = None
        self.trimpath = trimpath

        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")
        
    

    def addvideo(self, videopath):
        self.videopath = videopath
        self._vidreader = VideoReader(videopath)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        self.fps = self._vidreader.fps
        
        self.resize()
        
    
    def resize(self):
        """Resize frame shape to minimum of videoview height and width."""
        proxy = False
        if (self.fwidth > self.vwidth):
            ratio = self.fheight/self.fwidth
            self.fwidth = self.vwidth
            self.fheight = floor(self.fwidth * ratio)
            proxy = True

        if (self.fheight > self.vheight):
            ratio = self.fwidth/self.fheight
            self.fheight = self.vheight
            self.fwidth = floor(self.fheight*ratio)
            proxy = True
            
        if proxy:
            self.proxymize()
            
    def proxymize(self):
        """Resizes video into lower resolution video if needed"""
        tempdir = "./temp"
        os.makedirs(tempdir, exist_ok=True)
        
        self.videopath = proxyvideo(self.videopath, self.fwidth)
        self._vidreader = VideoReader(self.videopath)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        self.fps = self._vidreader.fps
        
        
        
    def trim(self, startidx:int=0, endidx:int=0):
        """Trims the video between the frame indices"""
        
        # self.resize()
        # print('startidx, endidx: ', startidx, endidx)
            
        trimvideo(self.videopath, self.trimpath, startidx, endidx, self.fps)
        # fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # videowriter = cv2.VideoWriter(self.trimpath, fourcc, self._vidreader.fps,
        #                                     (self.fwidth, self.fheight))
        
        # print('before count: ', self.fcount)
        # if endidx == 0:
        #     self.fcount = self._vidreader.fcount - startidx
        # else:
        #     self.fcount = endidx - startidx
            
        # self._vidreader.seek(startidx)
        # for i in range(self.fcount):
        #     frame = self._vidreader.read()
        #     frame = cv2.resize(frame, (self.fwidth, self.fheight))
            
        #     videowriter.write(frame)
        # print('after count: ', self.fcount)
        # videowriter.release()
        
    def release(self):
        self._vidreader.release()


    def frame(self, index=None):
        if (index is None):
            return self._vidreader.read()
        
        if (len(self.active_duration) == 0):
            f = self._vidreader.read(index)
        else:
            f = self._vidreader.read(self.active_duration[index])

        return f

    def crop_intime(self):
        """
        Finds the duration where the experiment happens.
        """
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16,
                                                                detectShadows=True)
        
        motion_scores = []

        for i in  range(self.fcount):
            frame = self._vidreader.read()

            mask = self.bg_subtractor.apply(frame)

            if i == 0:
                motion_scores.append(0)
                continue

            score = np.sum(mask) / 255
            motion_scores.append(score)

        motion_scores = np.array(motion_scores)
        motion_scores = motion_scores / np.max(motion_scores)
        
        win_len = 15

        scores_bin = []
        for i in range(1, self.fcount+1):
            idx = i-win_len
            if idx < 0: idx = 0

            score = motion_scores[idx:i]

            if np.mean(score) > 0.4:
                scores_bin.append(1)
            else:
                scores_bin.append(0)

        self._vidreader.seek(0)
    
        groups = []
        idx = 0
        for _, group_ in groupby(scores_bin):
            group = list(group_)
            if sum(group) < 0.8*len(group):
                idx += len(group)
                continue
            groups.append((idx, len(group)+idx))
            idx += len(group)

        groups = sorted(groups, key=lambda x: x[1]-x[0], reverse=True)
        
        start, end = groups[0]
        
        start = max(start-20, 0)
        end = min(end+20, self._vidreader.fcount)

        self.active_duration = list(range(start, end, 1))

        self.fcount = len(self.active_duration)
        
    
    def pts2pt(self, pts:np.ndarray):
        """Convert points to single mean point. pts should have have (x, y) coordinates"""
        pts = pts.reshape(-1, 2)
        
        x, y = np.mean(pts, axis=0)
        return floor(x), floor(y)