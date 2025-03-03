import cv2

class VideoReader():
    def __init__(self, video_path):
        self._reader = cv2.VideoCapture(video_path)

        if not self._reader.isOpened():
            print("Video unable to open!")

        self.frame_count = int(self._reader.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self._reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._start_idx = 0

        self._idx = 0

    # def set_extents(self, start_idx, frame_count):
    #     """
    #     Set the start index where video starts and ends (using frame count). This is to enable
    #     cropping in time for start and ending of experiments.
    #     """
    #     self._start_idx = start_idx
    #     self.frame_count = frame_count
    #     self._idx = start_idx
    #     self.seek(self._idx)

    def read(self, index=None):
        self._idx += 1
        print('idx: ', self._idx)

        # if self._idx > (self._start_idx + self.frame_count):
        #     self.seek(self._start_idx)
        #     self._idx = self._start_idx

        # if index is not None:
        #     self.seek(index+self._start_idx)
        #     self._idx = index+self._start_idx
        if index is not None:
            self.seek(index)
            self._idx = index

        ret, frame = self._reader.read()

        if not ret:
            print(f"Error reading frame returned {ret}")

        return frame
    
    def seek(self, index):
        self._reader.set(cv2.CAP_PROP_POS_FRAMES, index)