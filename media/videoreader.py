import cv2
from math import floor

class VideoReader():
    def __init__(self, video_path):
        self._reader = cv2.VideoCapture(video_path)

        if not self._reader.isOpened():
            print("Video unable to open!")

        self.fcount = floor(self._reader.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = floor(self._reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = floor(self._reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = floor(self._reader.get(cv2.CAP_PROP_FPS))
        self._start_idx = 0

        self._idx = 0

    def read(self, index=None):
        self._idx += 1
        
        if index is not None:
            self.seek(index)
            self._idx = index

        ret, frame = self._reader.read()

        if not ret:
            print(f"Error reading frame returned {ret}")

        return frame
    
    def seek(self, index):
        self._reader.set(cv2.CAP_PROP_POS_FRAMES, index)