"""
Frame timing of a video, from its container and its metadata.

Two rates matter. The container rate is the rate the file plays at, and playback follows it. A
phone's slow-motion clip is recorded at a higher rate and stored at the container rate, so it plays
slowed down. Its metadata then records the capture rate (com.android.capture.fps), which is the
real time between frames, so measurements use that.

Read with ffmpeg's report (`ffmpeg -i`, which prints to stderr), so it needs no ffprobe.
"""

import re
import subprocess
from dataclasses import dataclass

from core import find_ffmpeg

RATE = re.compile(r",\s*([0-9.]+)\s*(?:fps|tbr)\b")  # The video stream's rate, as ffmpeg prints it
CAPTURE = re.compile(r"com\.android\.capture\.fps\s*:\s*([0-9.]+)")
NTSC_TOLERANCE = 0.01  # ffmpeg prints 29.97 for 30000/1001: within half a hundredth of the printed value


@dataclass(frozen=True)
class Timing:
    container_fps: float               # The rate the file plays at: sets the playback speed
    capture_fps: float | None = None   # The rate it was recorded at, when the metadata says so

    @property
    def measure_fps(self) -> float:
        """Frames per second of real time: frame / measure_fps is the time of a frame, in seconds."""
        return self.capture_fps or self.container_fps


def exact_rate(fps: float) -> float:
    """ffmpeg prints NTSC rates rounded (29.97 for 30000/1001). Returns the exact rate for those."""
    if abs(fps - round(fps)) <= NTSC_TOLERANCE:
        return fps  # An integer rate, such as 30 or 120
    for n in (24, 30, 60, 120, 240):
        if abs(fps - n * 1000 / 1001) <= NTSC_TOLERANCE:
            return n * 1000 / 1001
    return fps


def parse_timing(report: str) -> Timing | None:
    """The timing in ffmpeg's report for a file. None if the report has no video stream rate."""
    video = next((line for line in report.splitlines() if "Video:" in line), None)
    rate = RATE.search(video) if video else None
    if rate is None:
        return None
    capture = CAPTURE.search(report)
    capture_fps = float(capture.group(1)) if capture and float(capture.group(1)) > 0 else None
    return Timing(exact_rate(float(rate.group(1))), capture_fps)


def probe_timing(path: str) -> Timing | None:
    """The timing of the video at path. None if ffmpeg is missing or cannot read the file."""
    try:
        ffmpeg = find_ffmpeg()
        done = subprocess.run([ffmpeg, "-hide_banner", "-i", path], capture_output=True,
                              encoding="utf-8", errors="replace", timeout=30)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    return parse_timing(done.stderr)
