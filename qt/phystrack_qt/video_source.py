"""
Opens a video for the Qt spike.

Frames can be shown at once: the source file is opened straight away (about 75 ms) and read,
scaled to the proxy's size, while the proxy is encoded on a worker thread by the parent repo's
media.proxyvideo (about 11 s for a 39 s 1080p HEVC phone clip; decoding alone is 7 s of that, so
no encoder setting makes the wait go away). When the proxy is ready, reading switches to it:
seeking it is several times faster (about 30 ms vs 200 ms). Frames are in proxy pixels throughout,
so overlays keep their positions across the switch.

Qt signals carry the worker's results back to the UI thread, so the worker never touches a widget.

The first load of a video also notes, beside its proxy, what it found out about the file: its size and its
rates. Later loads of the same file (a restart reopens the last session's videos) read the note instead:
no ffmpeg process (about 60 ms; more on Windows), and the source, a much bigger file than the proxy, is
neither opened nor decoded for its size. A note belongs to the file as it was (place, size, time of change),
as the proxy does; one that is missing, unreadable or out of date is just not used.
"""

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2
from PySide6.QtCore import QObject, Signal

from media import VideoReader, proxyvideo
from media.proxyvideo import _cache_key
from .timing import Timing, probe_timing

PROXY_MAX_SIDE = 1600  # The proxy's long side. The view scales it on the GPU, so this sets detail
# A frame up to this many ahead is reached by reading forward rather than seeking. On the proxy a
# frame read forward (grab, not converted) costs about 0.7 ms and a seek about 40 ms however near,
# so reading forward wins across a whole keyframe interval (the proxy's is 30 frames)
MAX_READ_AHEAD = 30
NOTES_VERSION = "1"    # Changes when what is noted about a video changes (read_info, write_info)


def proxy_size(w: int, h: int) -> tuple[int, tuple[int, int]]:
    """The proxy's width, and its frame size (width, height), for a source of w x h pixels."""
    scale = min(1.0, PROXY_MAX_SIDE / max(w, h))
    width = max(2, round(w * scale / 2) * 2)  # Even, as libx264 needs
    return width, (width, round(h * width / w))


def proxy_file(cache_dir: str, path: str, width: int) -> str:
    """Where the proxy of the video at path is kept. Same cache key as the Tk app, so a changed source or
    encoder setting makes a new proxy."""
    name = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(cache_dir, f"{name}_{_cache_key(path, width, -2)}_proxy.mp4")


def info_path(cache_dir: str, path: str) -> str:
    """The note about the video at path: beside its proxy, and named for the file as it is now (its place, size
    and time of change), so a changed file has no note. Raises OSError if the file is not there."""
    st = os.stat(path)
    raw = f"{NOTES_VERSION}|{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}"
    name = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(cache_dir, f"{name}_{hashlib.sha1(raw.encode()).hexdigest()[:10]}_info.json")


def read_info(cache_dir: str, path: str) -> tuple[int, int, Timing] | None:
    """(width, height, timing) noted for the video at path (upright, in source pixels), or None: no note, the
    file changed since, or the note cannot be read."""
    try:
        with open(info_path(cache_dir, path), encoding="utf-8") as f:
            note = json.load(f)
        width, height, container = int(note["width"]), int(note["height"]), float(note["container_fps"])
        capture = None if note.get("capture_fps") is None else float(note["capture_fps"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    if width < 2 or height < 2 or not container > 0:
        return None
    return width, height, Timing(container, capture)


def write_info(cache_dir: str, path: str, width: int, height: int, timing: Timing) -> None:
    """Notes the video's size and rates (atomically). Failing costs only the time the note would have saved."""
    try:
        target = info_path(cache_dir, path)
        os.makedirs(cache_dir, exist_ok=True)
        part = f"{target}.{os.getpid()}.part"
        with open(part, "w", encoding="utf-8") as f:
            json.dump({"width": width, "height": height, "container_fps": timing.container_fps,
                       "capture_fps": timing.capture_fps}, f)
        os.replace(part, target)
    except OSError:
        pass


class VideoSource(QObject):
    progress = Signal(float)   # Proxy encoding, 0.0 to 1.0
    proxy_ready = Signal()     # Reading has switched to the proxy
    failed = Signal(str)       # A message for the user
    _proxy_made = Signal(str, int)  # Worker to UI thread: the proxy's path and its load's number

    def __init__(self, cache_dir: str) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.reader: VideoReader | None = None
        self.path: str | None = None
        self.proxy_path: str | None = None
        self.size = (0, 0)          # Frame size in proxy pixels (width, height)
        self.timing: Timing | None = None  # Read from the source file, so the proxy cannot change it
        self._from_source = False   # Frames come from the source (scaled) until the proxy exists
        self._job = 0               # Which load a finishing worker belongs to
        self._proxy_made.connect(self._use_proxy)  # Queued: runs on the UI thread

    @property
    def fcount(self) -> int:
        return self.reader.fcount if self.reader else 0

    @property
    def fps(self) -> float:
        """The container rate, exact (playback follows it)."""
        return self.timing.container_fps if self.timing else 0

    @property
    def measure_fps(self) -> float:
        """The rate that turns a frame into real time: the capture rate when the file has one."""
        return self.timing.measure_fps if self.timing else 0

    @property
    def fps_text(self) -> str:
        if self.timing and self.timing.capture_fps:
            return f"{self.fps:.2f} fps, recorded at {self.timing.capture_fps:g} fps"
        return f"{self.fps:.2f} fps"

    @property
    def has_proxy(self) -> bool:
        return self.reader is not None and not self._from_source

    def load(self, path: str) -> bool:
        """
        Opens path for reading at once (False, after emitting failed, if it cannot be read). The
        proxy follows: proxy_ready is emitted when frames come from it. A video loaded before, whose
        proxy is still there, is opened on its proxy alone (see the note on the module).
        """
        noted = read_info(self.cache_dir, path)
        if noted is not None and self._load_noted(path, *noted):
            return True
        try:
            reader = VideoReader(path)
        except IOError as e:
            self.failed.emit(str(e))
            return False
        # The container rate from the file's own report (exact, not rounded down as VideoReader.fps
        # is); OpenCV's unrounded value if ffmpeg cannot be run. Asking ffmpeg is a process of about
        # 60 ms, so it starts first and runs while the first frame is read
        with ThreadPoolExecutor(max_workers=1) as pool:
            probing = pool.submit(probe_timing, path)
            # Phone videos are stored sideways with a rotation flag; the proxy is upright, so the
            # source must be too. (media.VideoReader does not ask for this; set on its capture here.)
            reader._reader.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
            h, w = reader.read(0).shape[:2]
            width, self.size = proxy_size(w, h)
        probed = probing.result()
        self.timing = probed or Timing(float(reader._reader.get(cv2.CAP_PROP_FPS)))
        if probed is not None:   # (OpenCV's rate, a stand-in, is not noted: ffmpeg may be there next time)
            write_info(self.cache_dir, path, w, h, probed)
        if self.reader is not None:
            self.reader.release()
        self.path, self.reader, self._from_source = path, reader, True
        self._job += 1

        os.makedirs(self.cache_dir, exist_ok=True)
        out = proxy_file(self.cache_dir, path, width)
        if os.path.isfile(out):
            self._use_proxy(out, self._job)
        else:
            threading.Thread(target=self._make_proxy, args=(path, out, width, self.fcount,
                                                            self._job), daemon=True).start()
        return True

    def _load_noted(self, path: str, w: int, h: int, timing: Timing) -> bool:
        """Opens the video's proxy at once, with the size and rates from its note: the source is not opened. False,
        with nothing changed, when there is no proxy to open (it was deleted, or is unreadable): the load then
        goes on as the first time did."""
        try:
            width, size = proxy_size(w, h)
            out = proxy_file(self.cache_dir, path, width)
            if not os.path.isfile(out):
                return False
            reader = VideoReader(out)
        except OSError:
            return False
        if self.reader is not None:
            self.reader.release()
        self.size, self.timing = size, timing
        self.path, self.reader, self.proxy_path, self._from_source = path, reader, out, False
        self._job += 1
        self.proxy_ready.emit()
        return True

    def _make_proxy(self, path: str, out: str, width: int, total: int, job: int) -> None:
        # Made under a name of its own, then moved into place: two tabs opening the same video at once each make
        # one, and with one name (and one temporary file) the second's rename failed
        # If the other finished first, its proxy is used and this one deleted: the same video and settings make
        # the same proxy, and on Windows a file that is open (the other tab reads it) cannot be replaced
        own = f"{os.path.splitext(out)[0]}.{os.getpid()}-{id(self)}-{job}.mp4"
        try:
            made = proxyvideo(path, width=width, writepath=own, on_progress=self.progress.emit,
                              total_frames=total)
            if made is not None:
                if not os.path.isfile(out):
                    try:
                        os.replace(made, out)
                    except PermissionError:   # Windows: the other's proxy was put in place, and opened, just now
                        if not os.path.isfile(out):
                            raise
                if os.path.isfile(made):   # Not moved: the other's is in place
                    try:
                        os.remove(made)
                    except OSError:
                        pass   # A stray file in the cache costs only space
                made = out
        except Exception as e:  # Reported to the user rather than lost on the worker thread
            made = None
            self.failed.emit(f"Making the proxy failed: {e}")
        if made is not None:
            # Back on the UI thread through a queued signal; a newer load makes this one stale
            self._proxy_made.emit(made, job)

    def _use_proxy(self, out: str, job: int) -> None:
        if job != self._job:
            return
        self.reader.release()
        self.reader = VideoReader(out)
        self.proxy_path, self._from_source = out, False
        self.proxy_ready.emit()

    def frame(self, index: int):
        """The frame at index (BGR), in proxy pixels."""
        self._read_forward_to(index)
        frame = self.reader.read(index)
        if self._from_source:
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        return frame

    def _read_forward_to(self, index: int) -> None:
        """Skips the frames before index by reading them, when index is a little ahead of the next
        frame, so that reading index needs no seek. Playback skips frames whenever one is slow to
        draw; seeking for each skip made the next frame slower still, and playback fell to about a
        third of its speed. (media.VideoReader, shared with the Tk app, seeks for any skip.)"""
        reader = self.reader
        if reader._next is None or not 0 < index - reader._next <= MAX_READ_AHEAD:
            return
        while reader._next < index and reader._reader.grab():
            reader._next += 1
