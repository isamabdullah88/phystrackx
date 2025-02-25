import cv2
import numpy as np
import matplotlib.pyplot as plt
from itertools import groupby
from media import VideoReader

class SlidingFriction():
    def __init__(self):
        # if video_path is not None:
            # self._vidreader = VideoReader(video_path)
        self._vidreader = None
        self.frame_width = None
        self.frame_height = None
        self.frame_count = 0

    def add_video(self, video_path):
        self._vidreader = VideoReader(video_path)
        self.frame_width = self._vidreader.width
        self.frame_height = self._vidreader.height
        self.frame_count = self._vidreader.frame_count


    def frame(self, index=None):
        return self._vidreader.read(index=index)

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

        # plt.plot(motion_scores)
        # plt.show()
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
            groups.append((idx, len(group)+idx))
            idx += len(group)

        groups = sorted(groups, key=lambda x: x[1]-x[0], reverse=True)
        # print(g)
        print(groups)
        # plt.plot(scores_bin)
        # plt.plot(scores_filtered)
        # plt.show()
        start, end = groups[0]
        # self._vidreader.seek(max_group[0])
        # self._vidreader.frame_count = max_group[1] - max_group[0]
        self._vidreader.set_extents(start, end-start)

        self.frame_count = self._vidreader.frame_count



if __name__ == '__main__':
    sliding_friction = SlidingFriction()
    sliding_friction.add_video("/home/isam/MSPhysics/Projects/PhysTrack/phystrackx/R1.MP4")

    sliding_friction.crop_intime()