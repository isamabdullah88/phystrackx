"""
Frame timing: the container rate (exact for NTSC rates) and the capture rate from a phone's
metadata, read from ffmpeg's report. A slow-motion clip plays at its container rate but was
recorded at its capture rate, so measurements use the capture rate.

    ~/.venvs/phystrackx-qt/bin/python tests/test_timing.py
"""

import os
import subprocess
import threading

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from core import find_ffmpeg  # noqa: E402
from phystrack_qt.timing import Timing, exact_rate, parse_timing, probe_timing  # noqa: E402

# The report `ffmpeg -i` gives for the Pixel slow-motion clip "Air Trial 1.mp4" (trimmed)
SLOW_MOTION = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'Air Trial 1.mp4':
  Metadata:
    com.android.capture.fps: 120.000000
  Duration: 00:00:39.34, start: 0.000000, bitrate: 8354 kb/s
  Stream #0:0[0x1](eng): Video: hevc (Main) (hvc1 / 0x31637668), yuvj420p(pc, bt709), 1920x1080, 8102 kb/s, SAR 1:1 DAR 16:9, 29.97 fps, 29.97 tbr, 90k tbn (default)
  Stream #0:1[0x2](eng): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 191 kb/s (default)
"""

# A clip with no capture tag (Track_Rigid 2.mp4)
PLAIN = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'Track_Rigid 2.mp4':
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 222x428 [SAR 897:896 DAR 99567:191744], 180 kb/s, 29.97 fps, 29.97 tbr, 11988 tbn (default)
"""


def test_slow_motion_report() -> None:
    timing = parse_timing(SLOW_MOTION)
    h.check("container rate is 30000/1001, exact", abs(timing.container_fps - 30000 / 1001) < 1e-9,
            str(timing.container_fps))
    h.check("capture rate is the metadata's 120", timing.capture_fps == 120.0, str(timing.capture_fps))
    h.check("measurements use the capture rate", timing.measure_fps == 120.0)


def test_plain_report() -> None:
    timing = parse_timing(PLAIN)
    h.check("no capture tag: no capture rate", timing.capture_fps is None, str(timing.capture_fps))
    h.check("no capture tag: measurements use the container rate",
            timing.measure_fps == timing.container_fps)
    h.check("the NTSC container rate is exact", abs(timing.container_fps - 30000 / 1001) < 1e-9)


def test_exact_rates() -> None:
    h.check("29.97 is 30000/1001", abs(exact_rate(29.97) - 30000 / 1001) < 1e-9)
    h.check("59.94 is 60000/1001", abs(exact_rate(59.94) - 60000 / 1001) < 1e-9)
    h.check("23.98 is 24000/1001", abs(exact_rate(23.98) - 24000 / 1001) < 1e-9)
    h.check("an integer rate stays as it is", exact_rate(30.0) == 30.0 and exact_rate(120.0) == 120.0)
    h.check("a rate that is no NTSC rate is left alone", exact_rate(25.0) == 25.0)


def test_no_video_no_timing() -> None:
    h.check("a report with no video stream gives no timing",
            parse_timing("Input #0, wav, from 'x.wav':\n  Stream #0:0: Audio: pcm_s16le, 44100 Hz\n") is None)


def test_measure_fps() -> None:
    h.check("the capture rate wins when there is one", Timing(29.97, 120.0).measure_fps == 120.0)
    h.check("the container rate otherwise", Timing(29.97).measure_fps == 29.97)


def test_probe_real_clip() -> None:
    """Makes two clips with ffmpeg: one with the capture tag, one without. Skipped without ffmpeg."""
    try:
        ffmpeg = find_ffmpeg()
    except FileNotFoundError:
        print("  skipped: no ffmpeg")
        return
    tagged, plain = os.path.join(h.WORK, "timing_tagged.mp4"), os.path.join(h.WORK, "timing_plain.mp4")
    base = [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x48:rate=30000/1001",
            "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    # use_metadata_tags writes the dotted key as the QuickTime tag a phone uses; without it ffmpeg drops it
    subprocess.run(base + ["-movflags", "use_metadata_tags", "-metadata", "com.android.capture.fps=120",
                           tagged], check=True)
    subprocess.run(base + [plain], check=True)

    timing = probe_timing(tagged)
    h.check("probe reads the container rate of a made clip",
            timing is not None and abs(timing.container_fps - 30000 / 1001) < 1e-9,
            str(timing))
    h.check("probe reads the capture tag of a made clip",
            timing is not None and timing.capture_fps == 120.0, str(timing))
    timing = probe_timing(plain)
    h.check("probe gives no capture rate without the tag",
            timing is not None and timing.capture_fps is None, str(timing))
    h.check("a file that is not a video gives no timing",
            probe_timing(os.path.join(h.WORK, "missing.mp4")) is None)


def test_the_probe_runs_beside_the_first_frame_read() -> None:
    """Opening a video asks ffmpeg for its timing, a process of about 60 ms. It starts before the source's first frame is
    read, so the two take their time together: a trial's open took the probe's time longer, for each trial of a start."""
    from phystrack_qt import video_source
    from test_tracking import make_clip
    h.app()
    cache, clip = os.path.join(h.WORK, "cache"), make_clip()
    first = video_source.VideoSource(cache)
    first.load(clip)
    h.pump(lambda: first.has_proxy, 60)   # With the proxy made, loading again starts no worker of its own
    os.remove(video_source.info_path(cache, clip))   # (and with the note gone, the load reads the file, as a first one does)

    started = threading.Event()
    seen = {}
    expected = Timing(25.0, 100.0)

    def probe(path: str) -> Timing:
        started.set()
        return expected

    class Reader(video_source.VideoReader):
        def read(self, index=None):
            if "probe_started" not in seen:   # The first read is the source's first frame, for its size
                seen["probe_started"] = started.wait(2.0)
            return super().read(index)

    real = video_source.probe_timing, video_source.VideoReader
    video_source.probe_timing, video_source.VideoReader = probe, Reader
    try:
        source = video_source.VideoSource(cache)
        loaded = source.load(clip)
    finally:
        video_source.probe_timing, video_source.VideoReader = real
    h.check("the clip loads", loaded)
    h.check("the probe has started by the time the first frame is read", seen.get("probe_started") is True,
            str(seen))
    h.check("...and its timing is the one the source takes", source.timing == expected, str(source.timing))

    os.remove(video_source.info_path(cache, clip))   # (the load above noted the fake timing)
    video_source.probe_timing = lambda path: None   # ffmpeg missing or unable: OpenCV's rate stands in
    try:
        other = video_source.VideoSource(cache)
        other.load(clip)
    finally:
        video_source.probe_timing = real[0]
    h.check("without a probe result, the rate is OpenCV's", other.timing is not None
            and abs(other.timing.container_fps - 30.0) < 1e-6 and other.timing.capture_fps is None, str(other.timing))
    h.check("...and that stand-in is not noted: ffmpeg may be there next time", video_source.read_info(cache, clip) is None)


if __name__ == "__main__":
    for test in (test_slow_motion_report, test_plain_report, test_exact_rates, test_no_video_no_timing,
                 test_measure_fps, test_probe_real_clip, test_the_probe_runs_beside_the_first_frame_read):
        print(test.__name__)
        test()
    h.finish()
