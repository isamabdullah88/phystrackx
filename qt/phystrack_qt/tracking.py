"""
Tracking for the Qt spike: the parent repo's trackers run over a frame range on a worker thread.
The method is picked before the run (track_methods.py):

- "nanotrack": the parent's MLTracker (OpenCV NanoTrack, as the Tk app uses), frame by frame.
- "blob": the parent's blob tracker (experiments/rigid/blobtracker.py), frame by frame; with the
  still background, that is taken first from frames spread over the range.
- "offline": the parent's whole-clip engine (experiments/rigid/cliptrack.py): it reads the range,
  then picks the ball's path over all of it, so the positions arrive at the end.
The blob and whole-clip methods can end with the physics fit (experiments/rigid/physics.py).

The worker opens its own reader on the proxy, so the UI can keep scrubbing while it runs (the Tk
app has to block scrubbing, because both share one reader). Results reach the UI through queued
signals; the worker never touches a widget.

Positions are box centres in proxy pixels (the picture's own pixels), keyed by frame.
"""

import logging
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, Signal

from core import PixelRect
from media import VideoReader

from .parent_imports import import_light
from .track_methods import BY_KEY, DEFAULT, engine_settings

MLTracker = import_light("experiments.rigid.mltracker").MLTracker

Box = tuple[float, float, float, float]  # x, y, width, height in proxy pixels


SHOW_INTERVAL = 0.1  # Seconds between the frames the view is sent (about 10 a second)


class Stopped(Exception):
    """Raised inside a parent engine (through its progress callback) when the run is stopped."""


class ReaderFrames:
    """Frames start..end of a reader as a sequence (frames[i] is frame start + i), for the parent's
    engines. The last frame read is kept. A short jump forward is read through (decoding a few
    frames is cheaper than a seek)."""

    READ_THROUGH = 24  # Frames

    def __init__(self, reader, start: int, end: int) -> None:
        self.reader, self.start, self.count = reader, start, end - start + 1
        self.last = (None, None)

    def __len__(self) -> int:
        return self.count

    def __getitem__(self, i: int):
        if i < 0:
            i += self.count
        if not 0 <= i < self.count:
            raise IndexError(i)
        at = self.last[0]
        if at != i:
            if at is not None and at < i <= at + self.READ_THROUGH:
                for j in range(at + 1, i):
                    self.reader.read(self.start + j)   # Sequential: no seeking
            self.last = (i, self.reader.read(self.start + i))
        return self.last[1]


def _outline_points(box: Box, outline) -> np.ndarray | None:
    """An Auto Object outline (fractions of its box) as points in proxy pixels."""
    if not outline:
        return None
    x, y, w, h = box
    return np.array([(x + u * w, y + v * h) for u, v in outline], float)


class TrackJob(QObject):
    tracked = Signal(int, list)   # Frame index, a Box (or None if lost) per object
    shown = Signal(int, object)   # Frame index and its picture (BGR), for the view to draw as it is
    progress = Signal(str, int, float)  # What it is doing, the frame it is on (the video's own number),
                                        # and the share of the whole run done (all objects and passes)
    path = Signal(int, list)      # Whole clip: an object's best path so far (a Box or None per frame)
    finished = Signal(bool)       # True if it ran to the end, False if stopped
    failed = Signal(str)

    def __init__(self, proxy_path: str, boxes: list[Box], start: int, end: int,
                 method: str = DEFAULT, options: dict | None = None, outlines: list | None = None) -> None:
        super().__init__()
        self.proxy_path, self.boxes, self.start, self.end = proxy_path, boxes, start, end
        self.method = BY_KEY[method]
        self.settings = engine_settings(self.method, options or {})
        self.outlines = outlines or [None] * len(boxes)
        self._stop = threading.Event()
        self._sent = (0.0, None)     # When the progress was last sent, and its stage
        self.logger = logging.getLogger(__name__)

    def run(self) -> None:
        threading.Thread(target=self._work, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _progress(self, stage: str, frame: int, fraction: float) -> None:
        """Sends the progress at most 10 times a second (and always a stage's first)."""
        now = time.perf_counter()
        if now - self._sent[0] >= 0.1 or stage != self._sent[1]:
            self._sent = (now, stage)
            self.progress.emit(stage, frame, fraction)

    def _work(self) -> None:
        reader = None
        try:
            reader = VideoReader(self.proxy_path)
            t0 = time.perf_counter()
            if self.method.engine == "nanotrack":
                done = self._live_nanotrack(reader)
            elif self.method.engine == "blob":
                done = self._live_blob(reader)
            else:
                done = self._whole_clip(reader)
            if not done:
                self.finished.emit(False)
                return
            self.logger.info(f"Tracked {self.end - self.start} frames with {self.method.key} in "
                             f"{time.perf_counter() - t0:.1f} s")
            self.finished.emit(True)
        except Stopped:
            self.finished.emit(False)
        except Exception as e:  # Reported to the user rather than lost on the worker thread
            self.logger.exception("Tracking failed")
            self.failed.emit(f"Tracking failed: {e}")
        finally:
            if reader is not None:
                reader.release()

    # --- Live: a position per frame as it goes -----------------------------------------------------
    def _live(self, reader, trackers, centres, share=(0.0, 1.0)) -> bool:
        """Runs the frame-by-frame trackers over the range, filling `share` of the progress.
        `centres` (blob tracker) collects each object's sub-pixel centre per frame. False if stopped."""
        self.tracked.emit(self.start, list(self.boxes))
        lo, hi = share
        shown_at = 0.0
        frame = None
        for index in range(self.start + 1, self.end + 1):
            if self._stop.is_set():
                return False
            frame = reader.read(index)  # Sequential, so no seeking
            found = []
            for k, tracker in enumerate(trackers):
                ok, rect = tracker.update_tracker(frame)
                if ok and centres is not None:
                    cx, cy = tracker.centre
                    _, _, w, h = self.boxes[k]
                    centres[k][index - self.start] = (cx, cy)
                    found.append((cx - w / 2, cy - h / 2, w, h))
                else:
                    found.append((rect.xmin, rect.ymin, rect.width, rect.height) if ok else None)
            self.tracked.emit(index, found)
            self._progress("Tracking", index, lo + (hi - lo) * (index - self.start) / max(1, self.end - self.start))
            # The view draws the tracker's own frames, so the UI thread never decodes during a run
            if time.perf_counter() - shown_at >= SHOW_INTERVAL:
                shown_at = time.perf_counter()
                self.shown.emit(index, frame.copy())
        if frame is not None:
            self.shown.emit(self.end, frame.copy())
        return True

    def _live_nanotrack(self, reader) -> bool:
        first = reader.read(self.start)
        trackers = []
        for x, y, w, h in self.boxes:
            tracker = MLTracker("nanotrack")
            tracker.initialize_tracker(first, PixelRect(int(x), int(y), int(w), int(h)))
            trackers.append(tracker)
        return self._live(reader, trackers, None)

    def _live_blob(self, reader) -> bool:
        blob = import_light("experiments.rigid.blobtracker")
        settings = blob.BlobSettings.from_dict(self.settings)
        background = None
        ring = bool(self.settings.get("ring_centre"))
        if settings.background_mix > 0:
            self.progress.emit("Taking the still background", self.start, 0.0)
            background = import_light("experiments.rigid.background").estimate_background(
                ReaderFrames(reader, self.start, self.end))
        first = reader.read(self.start)
        trackers = []
        for box, outline in zip(self.boxes, self.outlines):
            tracker = blob.BlobTracker(settings)
            tracker.background = background
            x, y, w, h = box
            tracker.initialize_tracker(first, PixelRect(int(round(x)), int(round(y)), int(round(w)), int(round(h))),
                                       _outline_points(box, outline))
            trackers.append(tracker)
        n = self.end - self.start + 1
        centres = [np.full((n, 2), np.nan) for _ in trackers]
        for k, tracker in enumerate(trackers):
            centres[k][0] = tracker.centre
        if not self._live(reader, trackers, centres, (0.05 if background is not None else 0.0,
                                                      0.9 if ring else 1.0)):
            return False
        if ring or self.settings.get("physics"):
            self._refine(centres, reader, background, ring)
        return True

    def _refine(self, centres, reader, background, ring) -> None:
        """Each object's track moved to the ball's round outline (ring) and/or put through the
        physics fit, sent again as the final positions."""
        physics = import_light("experiments.rigid.physics")
        ringfit = import_light("experiments.rigid.ringfit")
        frames = ReaderFrames(reader, self.start, self.end)
        results = []
        for k, c in enumerate(centres):
            status = np.where(np.isfinite(c).all(axis=1), physics.MEASURED, physics.LOST)
            _, _, w, h = self.boxes[k]
            fixed = np.nan_to_num(c)
            if ring:
                def report(i, n, k=k):
                    if self._stop.is_set():
                        raise Stopped()
                    self._progress("Finding the centres", self.start + i,
                                   0.9 + 0.1 * (k + i / max(1, n)) / len(centres))
                fixed, _, _ = ringfit.ring_refine(frames, fixed, status, max(w, h) / 2.0, background,
                                                  physics.MEASURED, report)
            if self.settings.get("physics"):
                fixed, status = physics.refine(fixed, status, max(w, h) / 2.0)
            results.append((fixed, status))
        self._send_all(results)

    # --- Whole clip: read the range, then the best path over all of it -----------------------------
    def _whole_clip(self, reader) -> bool:
        cliptrack = import_light("experiments.rigid.cliptrack")
        frames = ReaderFrames(reader, self.start, self.end)
        results = []
        count = len(self.boxes)
        for k, (box, outline) in enumerate(zip(self.boxes, self.outlines)):
            which = f"Object {k + 1} of {count}: " if count > 1 else ""
            shown_at = [0.0]

            def report(fraction, done, stage, which=which, k=k, shown_at=shown_at):
                if self._stop.is_set():
                    raise Stopped()
                # Each object is an equal part of the bar; its passes fill its part in turn
                self._progress(which + stage, self.start + done, (k + fraction) / count)
                now = time.perf_counter()
                if now - shown_at[0] >= SHOW_INTERVAL and frames.last[0] is not None:
                    shown_at[0] = now   # The view follows the frames as they are read
                    self.shown.emit(self.start + frames.last[0], frames.last[1].copy())

            def partial(centre, status, k=k, box=box):
                self.path.emit(k, self._boxes(centre, status, box))

            x, y, w, h = box
            rect = PixelRect(int(round(x)), int(round(y)), int(round(w)), int(round(h)))
            out = cliptrack.track_frames(frames, rect, "offline", self.settings,
                                         outline=_outline_points(box, outline), progress=report,
                                         partial=partial)
            results.append((out.centre, out.status))
            self.path.emit(k, self._boxes(out.centre, out.status, box))
        self.shown.emit(self.end, reader.read(self.end).copy())
        return True

    @staticmethod
    def _boxes(centre, status, box) -> list:
        """One object's boxes for every frame of the range (None where lost)."""
        _, _, w, h = box
        return [None if st == 0 else (float(c[0]) - w / 2, float(c[1]) - h / 2, w, h)
                for c, st in zip(centre, status)]

    def _send_all(self, results) -> None:
        """Every frame's boxes from (centres, status) per object; lost frames are None."""
        for i in range(self.end - self.start + 1):
            found = []
            for (centre, status), (_, _, w, h) in zip(results, self.boxes):
                if status[i] == 0:      # Lost
                    found.append(None)
                else:
                    cx, cy = centre[i]
                    found.append((float(cx) - w / 2, float(cy) - h / 2, w, h))
            self.tracked.emit(self.start + i, found)
