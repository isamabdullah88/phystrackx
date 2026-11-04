"""
Measurements for the Qt spike: tracked positions, turned into physical values with the axes and
the ruler, and the time of each frame. Plain numpy, so it can be tested without a window.

The axes are drawn in the picture (axes_item.py): x runs along the axes' rotated x direction, y
along their rotated direction that points up on screen. Positions are taken in that frame, so the
values match what the user sees, at any rotation. (The Tk app's transform does not do this for
rotated axes; see the README.)
"""

import csv
import math

import numpy as np


def physical(points, origin, rotation_deg: float, scale: float = 1.0) -> np.ndarray:
    """
    Picture pixels (N, 2) to physical (x, y) (N, 2): measured from the origin along the axes,
    with y up, and in real units by `scale` (units per picture pixel).

    Args:
        points: (N, 2) positions in picture pixels.
        origin: The axes' origin, in picture pixels.
        rotation_deg: The x axis' rotation, as AxesItem.rotation() (clockwise on screen).
        scale: Real units per picture pixel (1 before the ruler is calibrated).
    """
    a = math.radians(rotation_deg)
    ux = np.array([math.cos(a), math.sin(a)])
    uy = np.array([math.sin(a), -math.cos(a)])  # Up on screen when the axes are not rotated
    d = np.asarray(points, dtype=float).reshape(-1, 2) - np.asarray(origin, dtype=float)
    return np.column_stack([d @ ux, d @ uy]) * scale


def track_series(boxes: dict, fps: float) -> tuple[np.ndarray, np.ndarray]:
    """
    The frames where an object was tracked (boxes that are not None, in frame order), with the
    centre of each box in picture pixels.

    Returns:
        (frames, centres): frames is an int array, centres is (N, 2).
    """
    frames = sorted(f for f, box in boxes.items() if box is not None)
    centres = np.array([[boxes[f][0] + boxes[f][2] / 2, boxes[f][1] + boxes[f][3] / 2]
                        for f in frames], dtype=float).reshape(-1, 2)
    return np.array(frames, dtype=int), centres


def derivative(values: np.ndarray, t: np.ndarray) -> np.ndarray:
    """d(values)/dt at the sample times (central differences, as np.gradient)."""
    return np.gradient(values, t) if len(t) > 1 else np.zeros(len(values))


def export_csv(path: str, series: list, unit: str) -> None:
    """
    Writes the tracked positions: one row per frame that any object was tracked in, with the
    frame, its time, and x and y for each object.

    Args:
        series: (object number, frames, times, physical xy) per tracked object.
        unit: The unit of x and y (a column heading).
    """
    header = ["frame", "time_s"]
    for number, *_ in series:
        header += [f"x{number} ({unit})", f"y{number} ({unit})"]
    rows: dict[int, list] = {}
    for k, (_, frames, times, xy) in enumerate(series):
        for frame, time, (x, y) in zip(frames, times, xy):
            row = rows.setdefault(int(frame), [int(frame), float(time)] + [""] * (2 * len(series)))
            row[2 + 2 * k] = f"{x:.6g}"
            row[3 + 2 * k] = f"{y:.6g}"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for frame in sorted(rows):
            writer.writerow(rows[frame])
