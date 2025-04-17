
from itertools import groupby
import cv2
import numpy as np

from media import VideoReader

class Experiment:
    def __init__(self):
        self._vidreader = None
        self.frame_width = None
        self.frame_height = None
        self.frame_count = 0
        
        self.active_duration = []
        self.tracked_pts = []

        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")

    def add_video(self, video_path):
        self._vidreader = VideoReader(video_path)
        self.frame_width = self._vidreader.width
        self.frame_height = self._vidreader.height
        self.frame_count = self._vidreader.frame_count
        print('frame count: ', self.frame_count)


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

        for i in  range(self.frame_count):
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
        for i in range(1, self.frame_count+1):
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
        end = min(end+20, self._vidreader.frame_count)

        self.active_duration = list(range(start, end, 1))

        self.frame_count = len(self.active_duration)