
import cv2
import numpy as np
from tqdm import tqdm
from skimage.measure import EllipseModel, ransac
from skimage.filters import gaussian
from skimage.segmentation import (active_contour, morphological_geodesic_active_contour,
                                  inverse_gaussian_gradient)
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from .Experiment import Experiment
from filters import Smoothen
from .Utils import ptsellpise

class Balloon(Experiment):
    def __init__(self, trackpath):
        super().__init__()

        self._trackpath = trackpath
        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")

    def preprocess(self, cframe, i):
        """Preprocesses the cropped frame in multiple steps to reliably detect balloon boundary"""
        framep = cframe.copy()

        gray = cv2.cvtColor(framep, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(f"gray-plain-{i}.png", gray)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
        gray = clahe.apply(gray)
        cv2.imwrite(f"gray-enhanced-{i}.png", gray)
        edges = cv2.Canny(gray, 50, 150)
        cv2.imwrite(f"edges-enhanced-{i}.png", edges)
        # edgesp = edges.copy()*0
        # edgesp[300:750, 420:800] = edges[300:750, 420:800]

        # Find contours of the moving object (the balloon)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        cv2.drawContours(gray, contours, -1, (0, 0, 0), thickness=5)
        cv2.imwrite(f"gray-contour-{i}.png", gray)

        return gray
    

    def fit_ransac(self, contours, xoff, yoff):
        """Fits ellipse on data while using ransac to reject outliers"""
        data = np.vstack([cont.reshape(-1, 2) for cont in contours])
        
        model, inliers = ransac(data, EllipseModel, min_samples=300,
                                    residual_threshold=25, max_trials=10)

        if model is None:
            print("RANSAC failed to fit ellipse.")
            return None
        # else:
        # print("Ellipse parameters:", model.params)
        # print('inliers: ', inliers)
            # # Draw fitted ellipse
        xc, yc, a, b, theta = model.params
        ellipse = plt.matplotlib.patches.Ellipse((xc, yc), 2*a, 2*b, angle=np.rad2deg(theta),
                                                edgecolor='red', facecolor='none', linewidth=2, label='RANSAC Ellipse')
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.add_patch(ellipse)
        ax.plot(data[:,0], data[:,1], '.')

        ax.set_aspect('equal')
        # ax.set_xlim(0, 400)
        # ax.set_ylim(0, 300)
        ax.legend()
        plt.title("Ellipse Fitting using RANSAC")
        plt.show()
        return xc + xoff, yc+yoff, a, b, theta


    def track(self, mask, startidx=0, endidx=0):
        """Tracks the radius in marangoni effect

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.

        It first establishes a base ellipse model for the balloon, using preprocessing and then 
        applying ransac on sampled data to fit the model on outlier-free subset of data.
        It then tracks the ellipse in time to detect time evolving ellipse.
        Note: Make sure that the first frame has almost perfectly accurate detection.
        """
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, 24, (self.frame_width, self.frame_height))
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, 24, (640, 360))

        self._vidreader.seek(startidx)
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx

        # Filters for trajectory smoothing
        # smoothenx = Smoothen(tol=50)
        # smootheny = Smoothen(tol=50)
        # smoothenr = Smoothen(tol=100)
        # mask = np.zeros((self.frame_height, self.frame_width))
        # mask[300:700, 420:800] = 255

        # mask = cv2.resize(mask, (self.frame_width, self.frame_height))
        mask = cv2.imread("mask-balloon.png", 0)
        mask = cv2.resize(mask, (640, 360))
        points = cv2.findNonZero(mask)

        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(points)

        frame = self._vidreader.read()
        frame = cv2.resize(frame, (640, 360))

        # RANSAC based ellipse fitting -----------------
        """
        gray = self.preprocess(frame, 0)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        ellipse = self.fit_ransac(contours, x, y)
        """

        # Active contour fitting ------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
        gray = clahe.apply(gray)
        # smoothed = gaussian(gray, 3)

        _, thresh = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contour = max(contours, key=cv2.contourArea)
        ellipse = cv2.fitEllipse(contour)
        cv2.ellipse(frame, ellipse, (0, 255, 0), 1)

        print('ellipse: ', ellipse)

        # Show
        # plt.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cmap="gray")
        # plt.title("Fitted Ellipse")
        # plt.axis('off')
        # plt.show()
        # exit()
        # initpts = contour.reshape(-1, 2)[:, [1, 0]]
        initpts = ptsellpise(ellipse)[:, [1,0]]

        # Run active contour on this frame
        snake = active_contour(gray, initpts)
        snakecont = snake.copy().astype(np.float32).reshape(-1, 1, 2)
        ellipse = cv2.fitEllipse(snakecont[:,:,[1, 0]])
        # cv2.ellipse(frame, balloon, (0, 255, 0), 2)
        print('snake: ', snake.shape)
        print('ellipse: ', ellipse)

        # snakelvl = np.zeros_like(gray)
        # snakelvl[snake] = 1

        # Draw snake
        # fig, ax = plt.subplots(figsize=(7, 7))
        # ax.imshow(frame, cmap=plt.cm.gray)
        # ax.plot(initpts[:, 1], initpts[:, 0], '-r', lw=1)
        # ax.plot(snake[:, 1], snake[:, 0], '-b', lw=1)
        # ax.set_xticks([]), ax.set_yticks([])
        # ax.axis([0, frame.shape[1], frame.shape[0], 0])

        # plt.show()

        for i in tqdm(range(fcount-1), desc="Balloon", total=fcount):

            frame = self._vidreader.read()
            frame = cv2.resize(frame, (640, 360))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
            gray = clahe.apply(gray)

            # M = cv2.moments(snakecont)
            # cx = int(M["m10"] / M["m00"])
            # cy = int(M["m01"] / M["m00"])
            # center = np.array([cx, cy])

            # Expand each point away from the center
            # scale = 1.1  # Expand by 10%
            # snakecont = (snakecont - center) * scale + center
            # snakecont = np.round(snakecont).astype(np.int32)
            (cx, cy), (a, b), angle = ellipse
            # a = a*0.9
            # b = b*0.9
            ellipse = (cx, cy), (a, b), angle
            # print('reduced ellipse: ', ellipse)
            initpts = ptsellpise(ellipse, snake.shape[0])[:, [1, 0]]

            snakep = active_contour(gray, initpts, max_num_iter=100, gamma=0.5)
            snakecontp = snakep.copy().astype(np.float32).reshape(-1, 1, 2)
            ellipsep = cv2.fitEllipse(snakecontp[:,:,[1,0]])
            # gimg = inverse_gaussian_gradient(gray)
            # cv2.imwrite('gimg.png', gimg)
            
            # snakelvl = morphological_geodesic_active_contour(gimg, 50, snakelvl, balloon=1)
            # cv2.ellipse(frame, ellipse, (0, 255, 0), 1)
            # fig, ax = plt.subplots(figsize=(7, 7))
            # ax.imshow(frame, cmap=plt.cm.gray)
            # ax.plot(snakecont[:,:, 1], snakecont[:,:, 0], '--r', lw=1)
            # ax.plot(snakecontp[:,:, 1], snakecontp[:,:, 0], '-b', lw=1)
            # ax.plot(initpts[:, 1], initpts[:, 0], '-m', lw=1)
            # ax.set_xticks([]), ax.set_yticks([])
            # ax.axis([0, frame.shape[1], frame.shape[0], 0])

            # plt.show()
            cv2.drawContours(frame, snakecontp[:,:,[1,0]].astype(np.int32), -1, (0, 255, 0), thickness=2)

            # snake = snakep
            snakecont = snakecontp
            ellipse = ellipsep

            self._videowriter.write(frame)


        self._videowriter.release()

        # Store tracked points for later analysis
        # self.processor.points_tracked = points_tracked



if __name__ == '__main__':
    balloon = Balloon("track.mp4")
    balloon.add_video("../Dataset/Balloon/Balloon.mp4")

    # balloon.crop_intime()
    balloon.track(None, 100, 1550)
