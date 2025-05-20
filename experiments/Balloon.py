
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

        model = None

        # Filters for trajectory smoothing
        # smoothenx = Smoothen(tol=50)
        # smootheny = Smoothen(tol=50)
        # smoothenr = Smoothen(tol=100)

        # print('before loop')
        for i in tqdm(range(fcount), desc="Balloon", total=fcount):

            frame = self._vidreader.read()
            frame = frame[300:700, 420:800]
            # frame = cv2.resize(frame, (640, 360))

            framep = frame.copy()

            gray = cv2.cvtColor(framep, cv2.COLOR_BGR2GRAY)
            # cv2.imwrite(f"gray-plain-{i}.png", gray)
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
            gray = clahe.apply(gray)
            # cv2.imwrite(f"gray-enhanced-{i}.png", gray)
            edges = cv2.Canny(gray, 50, 150)
            # cv2.imwrite(f"edges-enhanced-{i}.png", edges)
            # edgesp = edges.copy()*0
            # edgesp[300:750, 420:800] = edges[300:750, 420:800]

            # Find contours of the moving object (the balloon)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            cv2.drawContours(gray, contours, -1, (0, 0, 0), thickness=5)
            # cv2.imwrite(f"gray-contour-{i}.png", gray)
            # clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4,4))
            # gray = clahe.apply(gray)
            # cv2.imwrite(f'gray-cont-enhanced{i}.png', gray)
            
            edges = cv2.Canny(gray, 50, 150)
            # cv2.imwrite(f"edges-cont-{i}.png", edges)
            # edgesp[300:750, 420:800] = edges[300:750, 420:800]
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            data = np.vstack([cont.reshape(-1, 2) for cont in contours])
            # for contour in contours:
            #     # Get the coordinates of the contour points
            #     for point in contour:
            #         # print('point: ', point)
            #         data.append(point[0])
                
            # data = np.array(data)
            # print('data: ', data.shape)
            
            # plt.plot(data[:,0], data[:,1], '.')
            # plt.axis("equal")
            # plt.show()
            
            
            # model = EllipseModel()
            # model.estimate(data)
            model, inliers = ransac(data, EllipseModel, min_samples=300,
                                        residual_threshold=25, max_trials=10)

            # # Check if fitting succeeded
            if model is None:
                print("RANSAC failed to fit ellipse.")
                exit()
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
            

            cv2.drawContours(framep, contours, -1, (0, 255, 255), thickness=1)
            cv2.imwrite(f"frame{i}.png", framep)
            self._videowriter.write(framep)
            # exit()


        self._videowriter.release()

        # Store tracked points for later analysis
        # self.processor.points_tracked = points_tracked



if __name__ == '__main__':
    balloon = Balloon("track.mp4")
    balloon.add_video("../Dataset/Balloon/Balloon.mp4")

    # balloon.crop_intime()
    balloon.track(None, 100, 150)
