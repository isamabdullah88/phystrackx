import cv2
import numpy as np
import matplotlib.pyplot as plt
import trackpy as tp
from stardist.models import StarDist2D
from stardist.plot import render_label
from csbdeep.utils import normalize
from itertools import groupby
from media import VideoReader

class NonRigid():
    def __init__(self):
        self._vidreader = None
        self.fwidth = None
        self.fheight = None
        self.frame_count = 0
        # self._clip_start = 0
        
        self.active_duration = []
        self.tracked_pts = []

        self.model = StarDist2D.from_pretrained("2D_versatile_fluo")

    def addvideo(self, video_path):
        self._vidreader = VideoReader(video_path)
        self.fwidth = self._vidreader.width
        self.fheight = self._vidreader.height
        self.frame_count = self._vidreader.frame_count
        self._vidreader.seek(550)


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

        # Define Lucas-Kanade optical flow parameters
        # lk_params = dict(
        #     winSize=(15, 15),      # Size of search window for each pyramid level
        #     maxLevel=2,            # Number of pyramid levels (0 means single level)
        #     criteria=(             # Termination criteria for iterative algorithm
        #         cv2.TERM_CRITERIA_EPS |      # Stop if accuracy is reached
        #         cv2.TERM_CRITERIA_COUNT,     # Stop if max iterations reached
        #         10,                          # Maximum iterations
        #         0.03                         # Minimum accuracy/epsilon
        #     )
        # )


        # for point in points:
        #     p0 = np.array(point, dtype=np.float32).reshape(-1, 1, 2)
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
            frame = self._vidreader.read()
            # fgray = 255 - cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            labels, details = self.model.predict_instances(normalize(frame))


            # Calculate optical flow using Lucas-Kanade method
            # p1: calculated new positions of input points
            # st: status array (1 = point found, 0 = point lost)
            # err: array of error measures for each point
            # if fprev is None:
            #     fprev = fgray.copy()
            
                # Apply Gaussian Blur
            # blurred = cv2.GaussianBlur(fgray, (1, 1), 0)

            # Use Canny edge detection
            # edges = cv2.Canny(fgray, 0, 50)

            # Find contours
            # contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Define a size threshold for small contours
            # min_area = 100  # Adjust this value as needed

            # Filter and draw small contours
            # for contour in contours:
            #     if cv2.contourArea(contour) < min_area:
            #         cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)


            plt.subplot(1,2,1)
            plt.imshow(frame, cmap="gray")
            plt.axis("off")
            plt.title("input image")

            plt.subplot(1,2,2)
            plt.imshow(render_label(labels, img=frame))
            plt.axis("off")
            plt.title("prediction + input overlay")
            print('yup!')
            # f = tp.locate(fgray, 31, invert=False, maxsize=15)
            # print('after locate')
            # print('after annotate')
            # fig, ax = plt.subplots()
            # ax.hist(f['mass'], bins=20)

            # Optionally, label the axes.
            # ax.set(xlabel='mass', ylabel='count')
            # plt.figure()
            # tp.annotate(f, fgray)
            # plt.show()

            # Show the image
            # cv2.imshow("Small Contours", fgray)
            # cv2.imshow("edge", edges)
            # cv2.imshow("blurred", blurred)

            cv2.waitKey(0)
        cv2.destroyAllWindows()
            # p0 = good_new.reshape(-1, 1, 2)  # Update previous points
            # fprev = fgray.copy()
            # p0 = p1

            # Add the set of tracked points
            # self.tracked_pts.append(tracked_pts)

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
    nonrigid = NonRigid()
    nonrigid.addvideo("../Marangoni.MOV")

    # nonrigid.crop_intime()
    nonrigid.track()