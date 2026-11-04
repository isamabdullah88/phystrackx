"""
videoapp.py

Defines the Video class which handles video display, frame manipulations, and tracking logic.

Author: Isam Balghari
"""

from typing import Optional, List
import math
import os
import logging
import threading
from typing import NamedTuple
import cv2
import numpy as np
from PIL import Image, ImageTk

from customtkinter import CTkCanvas, IntVar
from experiments.components import OCRData
from experiments.rigid.rigid import Rigid, FullResSource
from gui.plugins.crop import Crop
from gui.plugins.filters import Filters
from gui.components.rects.rect import Rect
from core import filexists


class NativePart(NamedTuple):
    """A piece of the full-resolution copy, with where it sits, so it is drawn exactly in place."""
    image: any
    x0: int        # Top-left of the image, in the copy's pixels
    y0: int
    sx: float      # Copy pixels per proxy pixel
    sy: float
    off_x: float   # Where the frame being shown starts in the proxy (trim origin plus crop)
    off_y: float


class Video:
    """
    Video handler for loading, displaying, trimming, and tracking frames on a canvas.
    """

    def __init__(self, canvas: CTkCanvas, vwidth: int, vheight: int, crop: Crop, filters: Filters) -> None:
        """
        Initialize the Video app.

        Args:
            canvas (CTkCanvas): Canvas to render video frames.
            vwidth (int): Width of the video display area.
            vheight (int): Height of the video display area.
            crop (Crop): Crop handler.
            filters (Filters): Filters to apply on video.
        """
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.crop = crop
        self.filters = filters

        self.frame: Optional[any] = None
        self.on_native_ready = None  # Called (from a worker thread) once the full-resolution copy exists
        self._native_busy = False
        self.imgview = None
        self.tkimg = None
        self.drawn = None      # The picture last drawn (BGR array)
        self._raw = None       # Last decoded frame and its index: panning and zooming do not
        self._raw_idx = None   # change the frame, so it is not decoded again
        self._filtered = None  # The filtered frame and (index, filter, value) it was made from:
        self._filtered_key = None  # zoom and pan redraw without filtering again

        tempdir = "temp"
        os.makedirs(tempdir, exist_ok=True)
        self.trimpath = os.path.join(tempdir, "Track_Rigid.mp4")

        self.rigid = Rigid(trimpath=self.trimpath, vwidth=self.vwidth, vheight=self.vheight-50)
        self.frameidx = 0
        # Where the trimmed clip sits in the proxy: first proxy frame, and crop origin in proxy pixels
        self.trimstart = 0
        self.trimorigin = (0, 0)
        self.istrimmed = False  # True while the loaded clip is a trim (not the full proxy)

        self.logger = logging.getLogger(__name__)
        self.logger.info("Video App initialized")
        self.trimvideo = self.rigid.trim
        
        self.imgview = self.canvas.create_image(self.crop.fx, self.crop.fy, anchor="nw")

    @property
    def fcount(self) -> int:
        """Total number of frames in loaded video."""
        return self.rigid.fcount

    @property
    def trackpts(self) -> List[List[List[float]]]:
        """Tracking points recorded from video."""
        return self.rigid.trackpts
    
    @property
    def ocrdata(self) -> OCRData:
        """OCR data extracted from video"""
        return self.rigid.texts

    @property
    def fps(self) -> int:
        """Video frames per second."""
        return self.rigid.fps

    @property
    def fwidth(self) -> int:
        """Current video frame width."""
        return self.rigid.fwidth

    @property
    def fheight(self) -> int:
        """Current video frame height."""
        return self.rigid.fheight

    def set_size(self, fwidth: int, fheight: int) -> None:
        """
        Set the size of the video frame.

        Args:
            fwidth (int): New width for the video frame.
            fheight (int): New height for the video frame.
        """
        self.rigid.set(fwidth, fheight)

    def loadvideo(self, videopath: str, istrim:bool=False, on_progress=None) -> None:
        """
        Load a video from file or fallback to trimmed path.

        Args:
            videopath (str): Path to video file.
            on_progress (callable, optional): Receives proxy encoding progress (0.0 to 1.0).
        """
        self.rigid.release()
        # A new clip: the cached frames are no longer valid
        self._raw = self._raw_idx = self._filtered = self._filtered_key = None

        if istrim:
            self.logger.info("Loading trim video")
            if not filexists(self.trimpath):
                self.logger.error("Trim video not found!")
                return
            self.rigid.addvideo(self.trimpath, istrim, self.crop.fwidth, self.crop.fheight)
            self.istrimmed = True
            self.logger.info("Video added from: %s", self.trimpath)
        else:
            self.set_trim_map(0, (0, 0))
            self.istrimmed = False
            self.crop.fitted = False  # The full video is shown at its own size
            self.rigid.addvideo(videopath, on_progress=on_progress)
            self.logger.info("Video added from: %s", videopath)
            self.crop.set(self.fwidth, self.fheight)

        # Until the proxy was ready the reader pointed at the source file, so a frame drawn in
        # the meantime would be cached at the source's size
        self._raw = self._raw_idx = self._filtered = self._filtered_key = None
        self.logger.info(f"Video loaded: {videopath}, Frame count: {self.fcount}, FPS: {self.fps},"
                         f"Width: {self.crop.cropwidth}, Height: {self.crop.cropheight}")


    def set_trim_map(self, start: int, origin: tuple[int, int]) -> None:
        """
        Records where the trimmed clip sits in the proxy, so full-resolution tracking reads the
        same frames and the same area.

        Args:
            start (int): Proxy frame that the clip's first frame comes from.
            origin (tuple[int, int]): Top-left of the crop in proxy pixels (0, 0 if not cropped).
        """
        self.trimstart = start
        self.trimorigin = origin

    def showframe(self, idx: int, view=None) -> None:
        """
        Fetch and display a video frame on the canvas.

        Args:
            idx (int): Index of the frame to display.
            view (ViewTransform, optional): Zoom and pan. When zoomed in, only the visible
                window of the frame is shown, stretched to fill the frame area.
        """
        self.frameidx = idx
        if self._raw is None or self._raw_idx != idx:
            self._raw = self.rigid.frame(index=self.frameidx)
            self._raw_idx = idx
        flt = self.filters.snapshot()
        key = (idx, flt.ftype, flt.value)
        if self._filtered is None or self._filtered_key != key:
            self._filtered = flt.apply_filter(self._raw)
            self._filtered_key = key
        self.frame = self.crop.apply_crop(self._filtered)

        if view is not None:
            view.configure(view.origin, (self.frame.shape[1], self.frame.shape[0]))
        self.show_array(self.frame, view, native=self._native_view(view))

    def _native_picture(self, view) -> Optional[any]:
        """The image of _native_view, or None (the proxy is shown instead)."""
        part = self._native_view(view)
        return None if part is None else part.image

    def _native_view(self, view) -> Optional[NativePart]:
        """
        When the view enlarges the picture, the shown pixels come from the full-resolution copy
        (the proxy has fewer pixels, so enlarging it looks blurred). Returns the visible part of the
        frame at full resolution, with a margin so it can be placed at a fraction of a pixel, or
        None to show the proxy. The copy is made in the background the first time it is needed;
        until then the proxy is shown.
        """
        if view is None or view.zoom * view.fit <= 1:
            return None
        if self.rigid.nativepath is None:
            self._prepare_native()
            return None
        frame_h, frame_w = self.frame.shape[:2]
        # The visible window of the frame, widened to whole pixels
        x0 = max(0, int(math.floor(view.ox)))
        y0 = max(0, int(math.floor(view.oy)))
        x1 = min(frame_w, int(math.ceil(view.ox + frame_w / view.zoom)))
        y1 = min(frame_h, int(math.ceil(view.oy + frame_h / view.zoom)))
        # The clip is cut from the proxy: its frame i is source frame trimstart + i (when trimmed),
        # and its pixels start at trimorigin in the proxy, plus any crop shown on top of it
        ox, oy = self.trimorigin
        if self.crop.croprect is not None:
            ox, oy = ox + self.crop.croprect.xmin, oy + self.crop.croprect.ymin
        source_frame = self.frameidx + (self.trimstart if self.istrimmed else 0)
        if not self.istrimmed and self.rigid.active_duration:
            source_frame = self.rigid.active_duration[self.frameidx]
        found = self.rigid.native_region_at(source_frame, (ox + x0, oy + y0, x1 - x0, y1 - y0))
        if found is None:
            return None
        image, nx0, ny0, sx, sy = found
        return NativePart(self.filters.apply_filter(image), nx0, ny0, sx, sy, ox, oy)

    def _prepare_native(self) -> None:
        """Builds the full-resolution copy on a worker thread, then tells the app it is ready."""
        if self._native_busy:
            return
        self._native_busy = True

        def work():
            try:
                self.rigid.ensure_native()
            except Exception:
                self.logger.exception("Could not make the full-resolution copy for zoomed views")
            finally:
                self._native_busy = False
            if self.on_native_ready is not None and self.rigid.nativepath is not None:
                self.on_native_ready()

        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _scale(img, size: tuple[int, int]):
        """Resizes without smoothing when enlarging (pixels stay sharp, like macOS zoom), and
        averages when shrinking (so detail is not lost to aliasing)."""
        enlarging = size[0] >= img.shape[1] and size[1] >= img.shape[0]
        return cv2.resize(img, size, interpolation=cv2.INTER_NEAREST if enlarging else cv2.INTER_AREA)

    @staticmethod
    def _place(img, size: tuple[int, int], ax: float, ay: float, tx: float, ty: float):
        """
        Draws img enlarged without smoothing, mapping its pixel index (i, j) to canvas (ax*i + tx,
        ay*j + ty). The map is exact, to a fraction of a pixel, so the picture and the overlays
        (which use the same numbers) agree at any zoom and pan.
        """
        matrix = np.array([[ax, 0.0, tx], [0.0, ay, ty]], np.float64)
        return cv2.warpAffine(img, matrix, size, flags=cv2.INTER_NEAREST,
                              borderMode=cv2.BORDER_REPLICATE)

    def show_array(self, frame, view=None, native: Optional[NativePart] = None) -> None:
        """Draws a processed (cropped) frame on the canvas, through the zoom and pan view.

        The picture occupies the frame's size times the fit, showing the part of the frame inside
        the view's window. Frame point u (a pixel k spans [k, k+1)) is drawn at
        (u - window_origin) * zoom * fit, which is the transform the overlays use.

        native: the visible part of the frame at full resolution (see _native_view), which is
        drawn instead of the proxy's pixels.
        """
        # An empty frame comes from a clip that failed to load. Drawing it raises inside the Tk
        # callback, so skip this redraw and keep the last picture on screen.
        if frame is None or frame.size == 0:
            self.logger.warning("Skipping redraw: the frame is empty")
            return

        fit = view.fit if view is not None else 1.0
        out = (max(1, round(frame.shape[1] * fit)), max(1, round(frame.shape[0] * fit)))
        shown = frame
        if view is not None:
            view.configure(view.origin, (frame.shape[1], frame.shape[0]))
            m = view.zoom * fit
            if native is not None and native.image.size > 0:
                # Pixel i of the part is at (x0 + i + 0.5) / sx in the proxy, which is that minus
                # the frame's offset in the frame; the canvas position follows from the view
                ax, ay = m / native.sx, m / native.sy
                tx = ax * (native.x0 + 0.5) - m * (native.off_x + view.ox) - 0.5
                ty = ay * (native.y0 + 0.5) - m * (native.off_y + view.oy) - 0.5
                shown = self._place(native.image, out, ax, ay, tx, ty)
            elif m >= 1 and (m != 1 or view.ox or view.oy):
                shown = self._place(frame, out, m, m, m * (0.5 - view.ox) - 0.5,
                                    m * (0.5 - view.oy) - 0.5)
            elif view.zoom > 1:  # Shrunk and zoomed: average a whole-pixel window
                x, y, w, h = view.window()
                part = frame[y:y + h, x:x + w]
                if part.size == 0:
                    self.logger.warning("Skipping redraw: the zoom window is outside the frame")
                    return
                shown = self._scale(part, out)
            elif fit != 1:
                shown = self._scale(frame, out)

        self.drawn = shown  # What is on the canvas (BGR), for tests that check overlays against it
        img = Image.fromarray(cv2.cvtColor(shown.copy(), cv2.COLOR_BGR2RGB))
        self.tkimg = ImageTk.PhotoImage(image=img)  # Making a new one is faster than paste()

        self.canvas.coords(self.imgview, self.crop.cropx, self.crop.cropy)
        self.canvas.itemconfig(self.imgview, image=self.tkimg)

    def track(self, track_rects: Rect, ocr_rects: Rect, progress: IntVar, on_frame=None,
              should_stop=None, fullres: bool = False, on_tracking=None, filters=None,
              assist: bool = False) -> None:
        """
        Perform object tracking on the video using selected regions.

        Args:
            track_rects (Rect): Region to track.
            ocr_rects (Rect): OCR target region.
            progress (IntVar): Variable for UI progress tracking.
            fullres (bool): Track at the source's full size. The full-size copy is made first
                if it does not exist yet; progress covers that step.
            on_tracking (callable, optional): Called once the tracker starts reading frames.
            filters (optional): The filter to apply, taken on the UI thread (Filters.snapshot()).
                This runs on a worker thread, where the live Filters plugin (Tk variables) must
                not be read.
            assist (bool): Use Segment Anything on hard frames (see experiments/rigid/assist.py).
        """
        self.logger.info("Starting tracking at frame index: %d", self.frameidx)
        self.logger.info("Tracking rectangles: ")
        for rect in track_rects.rects:
            pixelrect = rect.norm2pix(self.crop.cropwidth, self.crop.cropheight)
            self.logger.info("Track Rect: (x=%.02f, y=%.02f, w=%.02f, h=%.02f)", pixelrect.xmin,
                             pixelrect.ymin, pixelrect.width, pixelrect.height)

        self.logger.info("OCR rectangles: ")
        for rect in ocr_rects.rects:
            pixelrect = rect.norm2pix(self.crop.cropwidth, self.crop.cropheight)
            self.logger.info("OCR Rect: (x=%.02f, y=%.02f, w=%.02f, h=%.02f)", pixelrect.xmin,
                             pixelrect.ymin, pixelrect.width, pixelrect.height)

        source = None
        if fullres:
            path = self.rigid.ensure_native(on_progress=lambda f: progress.set(int(f * 100)))
            source = FullResSource(path, start=self.trimstart, origin=self.trimorigin)
        if on_tracking is not None:
            on_tracking()

        engine = None
        if assist:
            from media.segmenter import default_segmenter
            from experiments.rigid.assist import HardEngine
            segmenter = default_segmenter()
            if segmenter is None:
                self.logger.warning("Assist is on, but the Segment Anything model is not installed "
                                    "(run phystrackx.py --download-models); tracking without it.")
            else:
                engine = HardEngine(segmenter)
        self.rigid.track(self.frameidx, track_rects.rects, ocr_rects.rects,
                         filters if filters is not None else self.filters,
                         self.crop, progress, on_frame=on_frame, should_stop=should_stop,
                         fullres=source, assist=engine)

    def clear(self) -> None:
        """
        Clear stored tracking points and OCR readings from memory (the video stays loaded).
        """
        self.rigid.trackpts.clear()
        self.rigid.texts = OCRData([])
        self.logger.info("Tracking points cleared from memory.")
