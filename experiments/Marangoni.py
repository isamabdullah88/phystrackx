import cv2
import numpy as np
import matplotlib.pyplot as plt
import trackpy as tp
from math import floor
# from stardist.models import StarDist2D
from stardist.plot import render_label
from csbdeep.utils import normalize
from itertools import groupby
from media import VideoReader

class Marangoni():
    def __init__(self):
        self._vidreader = None
        self.frame_width = None
        self.frame_height = None
        self.frame_count = 0
        # self._clip_start = 0
        
        self.active_duration = []
        self.tracked_pts = []

        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")
        # print('model: ', self.model)

    def add_video(self, video_path):
        self._vidreader = VideoReader(video_path)
        self.frame_width = self._vidreader.width
        self.frame_height = self._vidreader.height
        self.frame_count = self._vidreader.frame_count
        self._vidreader.seek(250)


    def frame(self, index=None):
        if (index is None) or (self.active_duration is None):
            f = self._vidreader.read()
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
            # The group has to be valid group having 80% 1's atleast
            # print('sum: ', sum(group))
            # print('group: ', group)
            if sum(group) < 0.8*len(group):
                idx += len(group)
                continue
            groups.append((idx, len(group)+idx))
            idx += len(group)

        groups = sorted(groups, key=lambda x: x[1]-x[0], reverse=True)
        # print(g)
        print(groups)
        start, end = groups[0]
        
        start = max(start-20, 0)
        end = min(end+20, self._vidreader.frame_count)

        self.active_duration = list(range(start, end, 1))
        # self._vidreader.seek(max_group[0])
        # self._vidreader.frame_count = max_group[1] - max_group[0]
        # self._vidreader.set_extents(start, end-start)

        # self._clip_start = start
        # self.frame_count = self._vidreader.frame_count
        # print('start: ', self._clip_start)
        # print('frame count: ', self.frame_count)
        self.frame_count = len(self.active_duration)

        # plt.plot(scores_bin)
        # plt.plot(motion_scores)
        # plt.show()


    def track(self):

        self._vidreader.seek(200)
        
        for i in range(self.frame_count):

            frame = self._vidreader.read()
            frame = frame[:, 200:1750]
            h, w = frame.shape[:2]
            h = floor(h/3)
            w = floor(w/3)
            
            gray = np.sum(frame.copy(), axis=2)
            gray = 1-gray/np.max(gray)
            gray[gray > 0.75] = 0
            
            gray *= 5.5
                        
            gray[gray > 1] = 1
            gray = (gray * 255).astype(np.uint8)
            
            # Use Canny edge detection
            edges = cv2.Canny(gray*255, 25, 250)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            framep = frame.copy()
            cv2.drawContours(framep, contours, -1, (0, 255, 255), thickness=1)
            
            grayp = cv2.cvtColor(framep, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(grayp, 50, 250)
            kernel = np.ones((3, 3), np.uint8)

            # Dilate edges to close gaps
            edges = cv2.dilate(edges, kernel, iterations=1)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]  # Largest contour only
            cv2.drawContours(frame, contours, -1, (0, 255, 255), thickness=1)
            
            for contour in contours:
                (x, y), radius = cv2.minEnclosingCircle(contour)
                center = (int(x), int(y))
                radius = int(radius)

                # Draw the circle
                cv2.circle(frame, center, radius, (255, 0, 0), 3)  # Green circle

            cv2.waitKey(0)
            if i%10==0:
                print('Processed: ', i)
            
        cv2.destroyAllWindows()
            
        # Store tracked points for later analysis
        # self.processor.points_tracked = points_tracked



if __name__ == '__main__':
    marangoni = Marangoni()
    marangoni.add_video("../Marangoni.MOV")

    # marangoni.crop_intime()
    marangoni.track()