"""
csvdata.py

Reads a CSV written by the data export back in, so a saved project can be plotted again without
tracking the video.

Author: Isam Balghari
"""

import csv
from dataclasses import dataclass

import numpy as np


@dataclass
class CsvData:
    """The same fields the plots read from the DataManager."""
    timestamps: np.ndarray
    processed_points: list  # One (n, 2) array of x, y per tracked object; NaN where missing


def load_csv(path: str) -> CsvData:
    """
    Reads the time and the x, y columns of an export. Needs the header row, which names the
    columns (T(s), x1, y1, r1, ...).

    Raises:
        ValueError: If the file has no header with a time column and x/y columns.
    """
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"{path} is empty")

    header = [name.strip() for name in rows[0]]
    if "T(s)" not in header:
        raise ValueError(f"{path} has no T(s) column; save with the header option on")
    body = rows[1:]

    def column(name: str) -> np.ndarray:
        idx = header.index(name)
        return np.array([float(r[idx]) if idx < len(r) and r[idx] != "" else np.nan for r in body])

    timestamps = column("T(s)")
    points = []
    i = 1
    while f"x{i}" in header and f"y{i}" in header:
        points.append(np.column_stack([column(f"x{i}"), column(f"y{i}")]))
        i += 1
    if not points:
        raise ValueError(f"{path} has no x/y columns to plot")
    return CsvData(timestamps=timestamps, processed_points=points)
