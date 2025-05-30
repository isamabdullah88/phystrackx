import cv2
import numpy as np
import matplotlib.pyplot as plt
from itertools import groupby
from media import VideoReader

class SlidingFriction():
    def __init__(self):
        self._vidreader = None
        self.fwidth = None
        self.fheight = None
        self.frame_count = 0
        # self._clip_start = 0
        
        self.active_duration = []
        self.tracked_pts = []

    def add_video(self, video_path):
        self._vidreader = VideoReader(video_path)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.frame_count = self._vidreader.frame_count


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
            if sum(group) < 0.8*len(group):
                idx += len(group)
                continue
            groups.append((idx, len(group)+idx))
            idx += len(group)

        groups = sorted(groups, key=lambda x: x[1]-x[0], reverse=True)
        # print(g)
        print(groups)
        # plt.plot(scores_bin)
        # plt.plot(scores_filtered)
        # plt.show()
        start, end = groups[0]

        start = max(start-20, 0)
        end = min(end+20, self._vidreader.frame_count)

        self.active_duration = list(range(start, end, 1))
        # self._vidreader.seek(max_group[0])
        # self._vidreader.frame_count = max_group[1] - max_group[0]
        # self._vidreader.set_extents(start, end-start)

        # self._clip_start = start
        self.frame_count = len(self.active_duration)


    def track(self, points):

        # Define Lucas-Kanade optical flow parameters
        lk_params = dict(
            winSize=(10, 10),      # Size of search window for each pyramid level
            maxLevel=5,            # Number of pyramid levels (0 means single level)
            criteria=(             # Termination criteria for iterative algorithm
                cv2.TERM_CRITERIA_EPS |      # Stop if accuracy is reached
                cv2.TERM_CRITERIA_COUNT,     # Stop if max iterations reached
                10,                          # Maximum iterations
                0.03                         # Minimum accuracy/epsilon
            )
        )


        for point in points:
            p0 = np.array(point, dtype=np.float32).reshape(-1, 1, 2)
            # Convert first frame to grayscale if necessary
            # OpenCV optical flow requires grayscale images
            # if self.processor.frames[0].ndim == 3 and self.processor.frames[0].shape[2] == 3:
            #     old_gray = cv2.cvtColor(self.processor.frames[0], cv2.COLOR_BGR2GRAY)
            # else:
            #     old_gray = self.processor.frames[0]  # Frame is already grayscale

            # Initialize dictionary to store tracking history
            # Keys: point indices, Values: lists of (x,y) coordinates
            # points_tracked = {i: [p] for i, p in enumerate(points)}
            tracked_pts = np.zeros((2, self.frame_count))

            # Process all frames after the first one
            fprev = None
            # self._vidreader.seek(self._clip_start)
            for i in range(self.frame_count):
                # Convert current frame to grayscale if necessary
                # if frame.ndim == 3 and frame.shape[2] == 3:
                #     frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # else:
                #     frame_gray = frame
                fidx = self.active_duration[i]
                frame = self._vidreader.read(fidx)
                fgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Calculate optical flow using Lucas-Kanade method
                # p1: calculated new positions of input points
                # st: status array (1 = point found, 0 = point lost)
                # err: array of error measures for each point
                if fprev is None:
                    fprev = fgray.copy()
    
                # cv2.imwrite(f"gray-{i:03d}.png", fgray)

                p1, st, err = cv2.calcOpticalFlowPyrLK(fprev, fgray, p0, None, **lk_params)
                # print('p1: ', type(p1))
                # print('p1: ', p1)
                # print('err: ', err)

                tracked_pts[:, i] = p1.reshape(2,)
                ptmp = p1.reshape(2,)

                cv2.circle(fgray, (int(ptmp[0]), int(ptmp[1])), radius=7, color=(255,0,0), thickness=2)
                # cv2.imwrite(f"gray-{i}.png", fgray)
                # Select good points by checking status array
                # good_new = p1[st == 1]  # New positions of successfully tracked points
                # good_old = p0[st == 1]  # Previous positions of successfully tracked points

                # Update tracking history for successfully tracked points
                # for i, (new, old) in enumerate(zip(good_new, good_old)):
                #     a, b = new.ravel()  # Extract x,y coordinates from array
                #     points_tracked[i].append((a, b))  # Add new position to tracking history

                # Update for next iteration
                # old_gray = frame_gray.copy()
                # p0 = good_new.reshape(-1, 1, 2)  # Update previous points
                fprev = fgray.copy()
                p0 = p1

            # Add the set of tracked points
            self.tracked_pts.append(tracked_pts)

        # Visualize tracked points on all frames
        # for i, frame in enumerate(self.processor.frames):
        #     for j, point in points_tracked.items():
        #         if i < len(point):  # Check if point was tracked in this frame
        #             x, y = point[i]
        #             # Draw green circle at tracked point position
        #             cv2.circle(frame, (int(x), int(y)), 3, (0, 255, 0), -1)

        # Store tracked points for later analysis
        # self.processor.points_tracked = points_tracked



if __name__ == '__main__':
    sliding_friction = SlidingFriction()
    sliding_friction.add_video("/home/isam/MSPhysics/Projects/PhysTrack/phystrackx/R1.MP4")

    sliding_friction.crop_intime()

    sliding_friction.track(np.array([[298, 60]]))