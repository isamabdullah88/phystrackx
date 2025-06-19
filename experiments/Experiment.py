
import sys
import os

from itertools import groupby
from math import floor
import cv2
import numpy as np

from media import VideoReader

class Experiment:
    def __init__(self):
        
        # if not sys.stdout or not sys.stdout.isatty():
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
        
        self.active_duration = []

        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")

    def add_video(self, video_path):
        self._vidreader = VideoReader(video_path)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.fcount = self._vidreader.fcount
        print('frame count: ', self.fcount)


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
        
        if pts.shape[0] == 1:
            return np.squeeze(pts).astype(np.int32)
        
        x, y = np.mean(np.squeeze(pts), axis=0)
        return floor(x), floor(y)