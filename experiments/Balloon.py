
# from stardist.models import StarDist2D
# from stardist.plot import render_label
# from csbdeep.utils import normalize
from math import floor
import cv2
import numpy as np
from tqdm import tqdm
from skimage.measure import EllipseModel, ransac
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from .Experiment import Experiment
from filters import Smoothen

class Balloon(Experiment):
    def __init__(self, trackpath):
        super().__init__()

        self._trackpath = trackpath
        # self.model = StarDist2D.from_pretrained("2D_versatile_fluo")

    def track(self, mask, startidx=0, endidx=0):
        """Tracks the radius in marangoni effect

        Args:
            mask (np.ndarray): A mask that specifies diameter inside which the experiment is
            happening. It has size of gui canvas.
        """

        # Create clean ellipse data (parametric equation of ellipse)
        np.random.seed(0)
        theta = np.linspace(0, 2 * np.pi, 100)
        x = 100 * np.cos(theta) + 250
        y = 50 * np.sin(theta) + 150

        # Add small Gaussian noise to simulate realistic conditions
        ellipse_points = np.column_stack((
            x + np.random.normal(0, 0.001, size=x.shape),
            y + np.random.normal(0, 0.001, size=y.shape)
        ))

        # Add outlier points (uniform noise)
        # outliers = np.random.rand(20, 2) * [600, 300]

        # Combine into one noisy dataset
        # data = np.vstack((ellipse_points, outliers))
        data = ellipse_points

        # Apply RANSAC
        model, inliers = ransac(
            data.copy(),              # noisy data
            EllipseModel,      # model class
            min_samples=5,     # minimum points to fit ellipse
            residual_threshold=5,  # how far a point can be from the model to be considered an inlier
            max_trials=1000    # number of RANSAC iterations
        )

        # Check if fitting succeeded
        if model is None:
            print("RANSAC failed to fit ellipse.")
        else:
            print("Ellipse parameters:", model.params)

            # Unpack ellipse parameters
            yc, xc, a, b, theta = model.params
            ellipse = plt.matplotlib.patches.Ellipse(
                (xc, yc), width=2 * a, height=2 * b, angle=np.rad2deg(theta),
                edgecolor='red', facecolor='none', linewidth=2, label='Fitted Ellipse'
            )

            # Plot the results
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.scatter(data[:, 0], data[:, 1], c='gray', s=10, label='All Points')
            ax.scatter(data[inliers, 0], data[inliers, 1], c='green', s=20, label='Inliers')
            ax.add_patch(ellipse)
            ax.set_aspect('equal')
            ax.set_xlim(-200, 600)
            ax.set_ylim(-100, 300)
            ax.legend()
            plt.title("Ellipse Fitting using RANSAC")
        plt.show()
        exit()
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        # print('Before video writer')
        self._videowriter = cv2.VideoWriter(self._trackpath, fourcc, 24, (self.frame_width, self.frame_height))

        # mask = cv2.resize(mask, (self.frame_width, self.frame_height))
        # print('Before video reader seek')
        self._vidreader.seek(startidx)
        
        if endidx == 0:
            fcount = self._vidreader.fcount - startidx
        else:
            fcount = endidx - startidx



        # Filters for trajectory smoothing
        smoothenx = Smoothen(tol=50)
        smootheny = Smoothen(tol=50)
        smoothenr = Smoothen(tol=100)
        backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)

        # print('before loop')
        for i in tqdm(range(fcount), desc="Balloon", total=fcount):

            frame = self._vidreader.read()

            framep = frame.copy()*0
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # framep[mask < 150] = 0
            framep[300:700, 420:800] = frame[300:700, 420:800].copy()
            fgMask = backSub.apply(framep)

            # Optional: Clean up the mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)

            # Find contours of the moving object (the balloon)
            contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # gray = np.sum(frame.copy(), axis=2)
            # gray = 1-gray/np.max(gray)
            # gray[gray > 0.75] = 0
            
            # gray *= 5.5
                        
            # gray[gray > 1] = 1
            # gray = (gray * 255).astype(np.uint8)
            # print('Before gray')
            # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Use Canny edge detection
            # print('Before canny')
            # edges = cv2.Canny(gray, 1, 150)

            # Find contours
            # contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # print('Before sort')
            # cv2.drawContours(framep, contours, -1, (0, 255, 255), thickness=1)
            
            # grayp = cv2.cvtColor(framep, cv2.COLOR_BGR2GRAY)
            # blurred = cv2.GaussianBlur(grayp, (5, 5), 0)
            # edges = cv2.Canny(grayp, 0, 100)
            # kernel = np.ones((3, 3), np.uint8)

            # Dilate edges to close gaps
            # edges = cv2.dilate(edges, kernel, iterations=1)

            # Find contours
            # contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # contourr = sorted(contours, key=cv2.contourArea, reverse=True)[0]  # Largest contour only
            # (x, y), r = cv2.minEnclosingCircle(contourr)
            # cv2.drawContours(frame, contours, -1, (0, 255, 255), thickness=1)

            # x = floor(smoothenx.smoothen(x))
            # y = floor(smootheny.smoothen(y))
            # r = floor(smoothenr.smoothen(r))

            # Draw the circle
            # cv2.circle(frame, (x, y), r, (0, 0, 255), 2)  # Green circle

            data = []
            for contour in contours:
                # Get the coordinates of the contour points
                for point in contour:
                    # print('point: ', point)
                    data.append(point[0])
                
            data = np.array(data)
            print('data: ', data.shape)
            
            # Synthetic Data
            np.random.seed(0)
            theta = np.linspace(0, 2 * np.pi, 100)
            x = 100 * np.cos(theta) + 200
            y = 50 * np.sin(theta) + 150
            data = np.column_stack((x + np.random.normal(0, 3, size=x.shape),
                                    y + np.random.normal(0, 3, size=y.shape)))
            
            
            model = EllipseModel()
            ransac_model, inliers = ransac(data, EllipseModel, min_samples=4,
                                        residual_threshold=5, max_trials=1000)

            print('inliers: ', inliers)
            # # Draw fitted ellipse
            yc, xc, a, b, theta = ransac_model.params
            ellipse = plt.matplotlib.patches.Ellipse((xc, yc), 2*a, 2*b, angle=np.rad2deg(theta),
                                                    edgecolor='red', facecolor='none', linewidth=2, label='RANSAC Ellipse')
            ax.add_patch(ellipse)

            ax.set_aspect('equal')
            ax.set_xlim(0, 400)
            ax.set_ylim(0, 300)
            ax.legend()
            plt.title("Ellipse Fitting using RANSAC")
            plt.show()
            self._videowriter.write(framep)


        self._videowriter.release()

        # Store tracked points for later analysis
        # self.processor.points_tracked = points_tracked



if __name__ == '__main__':
    balloon = Balloon("track.mp4")
    balloon.add_video("../Balloon.mp4")

    # balloon.crop_intime()
    balloon.track(None, 100, 150)
