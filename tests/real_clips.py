"""
Real clips with hand-checked ball positions (labels), for tests on real footage.

A label file (tests/real_labels/*.json, made with tests/label_real.py) names a stretch of a real
video and gives the ball's centre on the frames someone checked:

    {"video": "Air Trial 1.mp4",       # found under REAL_FOOTAGE (any depth)
     "start": 12.0, "frames": 300,     # seconds into the video, frame count decoded
     "range": [20, 260],               # optional: the frames used (labels count from its start)
     "width": 540,                     # frames are scaled to this width (as the app's proxy)
     "radius": 5.2,                    # the ball's radius at that width
     "labels": {"0": [236.1, 552.4],   # frame -> centre, or null where the ball cannot be seen
                "5": null, ...},
     "note": "..."}

The video itself is not in the repository (PHYSTRACK_REAL_FOOTAGE names the folder it is in;
clips whose video is missing are skipped). Frames are decoded once into the system temp folder.

    load_frames(spec) -> (n, h, w) grey uint8 frames
    score(spec, centre) -> per-clip scores on the labelled frames
"""

import hashlib
import json
import os
import subprocess
import tempfile

import numpy as np

from tests import harness as h

LABELS = os.path.join(h.REPO, "tests", "real_labels")
REAL_FOOTAGE = os.environ.get("PHYSTRACK_REAL_FOOTAGE", os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Classwork/P440/Specific_heat/Measurements"))
CACHE = os.path.join(tempfile.gettempdir(), "phystrack_real_labelled")


def find_video(name: str) -> str | None:
    """The path of a video called `name` under REAL_FOOTAGE (searched to any depth)."""
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for root, _, files in os.walk(REAL_FOOTAGE):
        if name in files:
            return os.path.join(root, name)
    return None


def footage() -> list[str]:
    """Every experiment video under REAL_FOOTAGE (Air and Water trials)."""
    out = []
    for root, _, files in os.walk(REAL_FOOTAGE):
        for f in files:
            low = f.lower()
            if low.endswith((".mp4", ".mov")) and low.startswith(("air trial", "water")):
                out.append(os.path.join(root, f))
    return sorted(out, key=os.path.basename)


def label_files() -> list[str]:
    if not os.path.isdir(LABELS):
        return []
    return sorted(os.path.join(LABELS, f) for f in os.listdir(LABELS) if f.endswith(".json"))


def load_spec(path: str) -> dict:
    with open(path) as f:
        spec = json.load(f)
    spec["path"] = path
    return spec


def save_spec(spec: dict) -> None:
    path = spec["path"]
    data = {k: v for k, v in spec.items() if k != "path"}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w") as f:
        json.dump(data, f, indent=1)
    os.replace(path + ".part", path)


def decode(video: str, start: float, frames: int, width: int, colour: bool = False) -> np.ndarray:
    """`frames` frames of `video` from `start` seconds, scaled to `width` (rotation applied), as
    grey (n, h, w) or BGR (n, h, w, 3) uint8; cached in the system temp folder."""
    from core import find_ffmpeg
    key = hashlib.sha1(f"{os.path.basename(video)}|{os.path.getsize(video)}|{start}|{frames}|{width}|{colour}".encode()).hexdigest()[:16]
    cache = os.path.join(CACHE, key + ".npy")
    if os.path.exists(cache):
        return np.load(cache, mmap_mode="r")
    out = subprocess.run([find_ffmpeg(), "-v", "error", "-ss", f"{start:.3f}", "-i", video, "-frames:v", str(frames),
                          "-vf", f"scale={width}:-2", "-f", "rawvideo", "-pix_fmt", "bgr24" if colour else "gray", "-"],
                         capture_output=True, check=True).stdout
    probe = subprocess.run([find_ffmpeg(), "-v", "error", "-ss", f"{start:.3f}", "-i", video, "-frames:v", "1",
                            "-vf", f"scale={width}:-2", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                           capture_output=True, check=True).stdout
    height = len(probe) // width
    shape = (-1, height, width, 3) if colour else (-1, height, width)
    data = np.frombuffer(out, np.uint8).reshape(shape)
    os.makedirs(CACHE, exist_ok=True)
    np.save(cache, data)
    return np.load(cache, mmap_mode="r")


def load_frames(spec: dict, colour: bool = False) -> np.ndarray | None:
    """The clip's frames (only its `range`, when it has one), or None when the video is missing."""
    video = find_video(spec["video"])
    if video is None:
        return None
    frames = decode(video, spec["start"], spec["frames"], spec["width"], colour)
    if spec.get("range"):
        a, b = spec["range"]
        frames = frames[a:b]
    return frames


def labelled(spec: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(frame indices, centres, visible) of the labelled frames; centres are NaN where hidden."""
    items = sorted((int(k), v) for k, v in spec.get("labels", {}).items())
    idx = np.array([k for k, _ in items], int)
    pts = np.array([v if v is not None else [np.nan, np.nan] for _, v in items], float).reshape(-1, 2)
    return idx, pts, np.isfinite(pts).all(axis=1)


def score(spec: dict, centre: np.ndarray) -> dict | None:
    """Scores of a track against the labels (frame 0, the selection, is not counted): on-ball
    (within the ball's radius), median and 95th percentile error, over the visible labelled frames.
    None when fewer than 5 frames are labelled."""
    idx, pts, vis = labelled(spec)
    keep = vis & (idx > 0) & (idx < len(centre))
    if keep.sum() < 5:
        return None
    err = np.hypot(*(np.asarray(centre)[idx[keep]] - pts[keep]).T)
    return {"on_ball": float((err <= spec["radius"]).mean()), "median": float(np.median(err)),
            "p95": float(np.percentile(err, 95)), "labelled": int(keep.sum())}
