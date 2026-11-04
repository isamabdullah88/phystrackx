"""
Pre-fills real-clip labels (tests/real_labels, see real_clips.py) without a person: a first step
towards labelling experiment footage automatically.

    uv run python -m tests.prelabel_real               # every video in SOURCES (found under PHYSTRACK_REAL_FOOTAGE)
    uv run python -m tests.prelabel_real --jobs 4

For each video:
1. The ball is selected where it rests at the end of the video (END: found by eye once; at rest it
   is easy to place, unlike at the start, where a hand holds it).
2. Two different trackers follow it backward through the last 20 s (the frames reversed): the
   blob tracker on its own, and the offline engine with the background and the physics fit.
3. For each clip in SOURCES (just before the release to some seconds after), every fifth frame
   where both trackers measured the ball within AGREE pixels of each other gets a label, at the
   ball's geometric centre: a circle of its radius fitted to its edge (edge_centre), since both
   trackers' blob centres are pulled toward a shiny ball's highlight. Frames where they disagree,
   or where the edge is not clear, stay unlabelled, for a person to settle in tests/label_real.py.

Labels made this way say "checked": "pre-filled". A file someone has checked (any other value) is
never overwritten. They come from trackers, so they favour the trackers' own mistakes where both
make the same one: check a sample by eye (label_real.py shows them) before trusting them.
"""

import argparse
import json
import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from tests import harness as h
from tests import real_clips as rc

WIDTH = 540            # Frames are scaled to this width (as the app's proxy of a portrait phone video)
RADIUS = 6.0           # The ball's radius at that width
SECONDS = 20.0         # Tracked backward over the last this many seconds
EVERY = 5              # A label on every this many frames
AGREE = 1.5            # ...where the two trackers agree within this (px)
EDGE = 2.5             # ...and the ball's edge is clear (edge_centre's strength), at its geometric centre
SELECT_EDGE = 2.0      # A clip starts at its first frame with the ball this visible (it is selected there)
# The ball's centre on the video's last second (at WIDTH), and the clips to label: (start s, seconds)
SOURCES = {
    "Air Trial 1.mp4": ((234.4, 549.9), [(18.4, 8.0)]),
    "Air Trial 2.mp4": ((251.2, 575.7), [(12.2, 8.0)]),
    "Air Trial 3.mp4": ((254.6, 633.0), [(11.6, 8.0), (25.5, 3.5)]),   # The second: lifted out with a magnet
    "Air Trial 4.mp4": ((232.2, 682.0), [(9.6, 8.0)]),
    "Water 270 Trial 2.mp4": ((240.0, 611.5), [(4.6, 8.0)]),
    "Water 270 Trial 3.mp4": ((232.7, 621.6), [(13.0, 8.0)]),          # A magnet raises it before the release
    "Water 270 Trial 4.mp4": ((232.7, 683.0), [(4.6, 8.0)]),
    "water 270 Trial 1.mp4": ((235.0, 527.5), [(12.3, 8.0)]),
}
TRACKERS = {"blob": ("blob", {}),
            "offline": ("offline", {"background_mix": 1.0, "physics": True})}


def _duration(path: str) -> float:
    from core import find_ffmpeg
    probe = os.path.join(os.path.dirname(find_ffmpeg()), "ffprobe")
    out = subprocess.run([probe if os.path.exists(probe) else "ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout)


def backtrack(name: str):
    """Both trackers' tracks of the ball over the video's last SECONDS, tracked backward from END."""
    h.setup_env()
    import cv2
    cv2.setNumThreads(1)
    from experiments.rigid.cliptrack import track_frames
    from experiments.rigid.physics import quality
    path = rc.find_video(name)
    if path is None:
        return None
    (x, y), _ = SOURCES[name]
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    duration = _duration(path)
    start = max(0.0, duration - 1.0 - SECONDS)
    frames = int((duration - 1.0 - start) * fps)
    grey = np.asarray(rc.decode(path, start, frames + 1, WIDTH))
    angle = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    outline = np.column_stack([x + RADIUS * np.cos(angle), y + RADIUS * np.sin(angle)])
    tracks = {}
    for label, (engine, values) in TRACKERS.items():
        out = track_frames(grey[::-1], None, engine, values, outline=outline)
        centre, status = out.centre[::-1], out.status[::-1]
        tracks[label] = {"centre": centre, "status": status, "quality": quality(centre, status, RADIUS).to_dict()}
    track = {"video": name, "start": start, "frames": len(grey), "fps": fps, "tracks": tracks}
    return track, label_clips(track, grey)


def edge_centre(gray, p, r: float, reach: float = 4.0, step: float = 0.25):
    """The ball's geometric centre near p: where a circle of radius r lies along the strongest edges
    (gradient magnitude summed over the circle, searched within `reach` px in `step` px steps).
    Independent of the trackers' blob centres, which a shiny ball's highlight pulls aside.
    Returns (centre, strength): strength is the mean edge along the best circle over the mean edge
    of the window (about 1 for no circle; a clear ball gives 2 or more)."""
    import cv2
    pad = int(r + reach + 3)
    x0, y0 = int(round(p[0])) - pad, int(round(p[1])) - pad
    if x0 < 0 or y0 < 0 or x0 + 2 * pad + 1 > gray.shape[1] or y0 + 2 * pad + 1 > gray.shape[0]:
        return np.asarray(p, float), 0.0
    win = cv2.GaussianBlur(np.asarray(gray[y0:y0 + 2 * pad + 1, x0:x0 + 2 * pad + 1], np.float32), (0, 0), 0.8)
    edge = cv2.magnitude(cv2.Sobel(win, cv2.CV_32F, 1, 0), cv2.Sobel(win, cv2.CV_32F, 0, 1))
    angle = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    ring = np.column_stack([r * np.cos(angle), r * np.sin(angle)])
    best, where = -1.0, np.asarray(p, float)
    offsets = np.arange(-reach, reach + 1e-9, step)
    for dy in offsets:
        for dx in offsets:
            c = np.array([p[0] - x0 + dx, p[1] - y0 + dy])
            pts = (ring + c).astype(np.float32)
            v = cv2.remap(edge, pts[:, 0].reshape(1, -1), pts[:, 1].reshape(1, -1), cv2.INTER_LINEAR)
            score = float(v.mean())
            if score > best:
                best, where = score, np.array([p[0] + dx, p[1] + dy])
    return where, best / max(float(edge.mean()), 1e-6)


def label_clips(track: dict, grey) -> list[str]:
    """Writes the label files of one video's clips; returns their paths. A label is where the two
    trackers agree, moved to the ball's geometric centre (edge_centre) when its edge is clear."""
    from experiments.rigid.cliptrack import MEASURED
    a, b = track["tracks"]["offline"], track["tracks"]["blob"]
    written = []
    for s0, seconds in SOURCES[track["video"]][1]:
        k0 = max(0, int(round((s0 - track["start"]) * track["fps"])))
        k1 = min(track["frames"], k0 + int(round(seconds * track["fps"])))
        # The clip starts where the ball can be seen (it is selected there): not inside the hand
        for k in range(k0, min(k1, k0 + int(2 * track["fps"]))):
            if edge_centre(grey[k], a["centre"][k], RADIUS)[1] >= SELECT_EDGE:
                k0 = k
                break
        labels, edges = {}, []
        for k in list(range(k0, k1, EVERY)):
            agree = a["status"][k] == MEASURED and np.hypot(*(a["centre"][k] - b["centre"][k])) <= AGREE
            if not agree and k != k0:
                continue
            centre, strength = edge_centre(grey[k], a["centre"][k], RADIUS)
            if strength < EDGE and k != k0:
                continue        # No clear edge (blurred, partly covered): left for a person
            edges.append(strength)
            labels[str(k - k0)] = [round(float(v), 2) for v in (centre if strength >= EDGE else a["centre"][k])]
        stem = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(track["video"])[0].lower()).strip("_")
        path = os.path.join(rc.LABELS, f"{stem}_{s0:.1f}.json")
        if os.path.exists(path) and rc.load_spec(path).get("checked") != "pre-filled":
            written.append(f"{os.path.basename(path)}: checked by hand, kept")
            continue
        rc.save_spec({"path": path, "video": track["video"], "start": track["start"],
                      "frames": track["frames"], "range": [k0, k1], "fps": track["fps"], "width": WIDTH,
                      "radius": RADIUS, "labels": labels, "checked": "pre-filled",
                      "note": (f"Pre-filled by tests/prelabel_real.py: frames where two trackers ({', '.join(TRACKERS)}) "
                               f"agree within {AGREE} px, tracking backward from the ball at rest at the end, each "
                               "moved to the ball's geometric centre by a circle fit to its edge. Not yet checked "
                               "by hand. Frame numbers count from range[0] of the decoded stretch.")})
        written.append(f"{os.path.basename(path)}: frames {k0}-{k1}, {len(labels)} of {len(range(k0, k1, EVERY))} "
                       f"labelled, edge strength {np.median(edges):.1f}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    h.setup_env()
    names = [n for n in SOURCES if rc.find_video(n)]
    missing = sorted(set(SOURCES) - set(names))
    if missing:
        print(f"not found under {rc.REAL_FOOTAGE}: {', '.join(missing)}")
    with ProcessPoolExecutor(args.jobs) as pool:
        for done in pool.map(backtrack, names):
            if done is None:
                continue
            track, written = done
            q = {k: v["quality"] for k, v in track["tracks"].items()}
            print(f"{track['video']}: " + "; ".join(
                f"{k} measured {v['measured']:.0%}, jitter {v['jitter']:.2f} px" for k, v in q.items())
                + "".join(f"\n  {line}" for line in written), flush=True)


if __name__ == "__main__":
    main()
