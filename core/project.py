"""
project.py

Reads and writes PhysTrackX project files. A project stores the video path, trim range,
crop, axes, scale ruler, and tracked rectangles, so the setup can be reopened later with
`tk/phystrackx.py --project <file>`.

Author: Isam Balghari
"""

import json
import os
import re
import tempfile
import uuid
from datetime import datetime

PROJECT_VERSION = 1
PROJECT_EXTENSION = ".phystrack"

# Where new projects go, next to the app (not the working directory)
PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")


def write_project(path: str, state: dict) -> None:
    """Writes the project atomically, so a failed save never leaves a half-written file."""
    data = {"version": PROJECT_VERSION, **state}
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def new_project(videopath: str, canvas: tuple[int, int], folder: str | None = None) -> str:
    """
    Creates a new project file for a video, with nothing set up yet, and returns its path.

    The name is the video's name, the date and time, and a random id, so two projects never
    share a file and an existing project is never overwritten.

    Args:
        videopath: The video the project is for.
        canvas: The (width, height) of the video view the project is made in.
        folder: Where to create it. Defaults to PROJECTS_DIR, read at call time.

    Returns:
        str: Path to the new project file.
    """
    folder = folder or PROJECTS_DIR
    os.makedirs(folder, exist_ok=True)

    base = os.path.splitext(os.path.basename(videopath))[0]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_") or "video"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    while True:
        path = os.path.join(folder, f"{safe}_{stamp}_{uuid.uuid4().hex[:8]}{PROJECT_EXTENSION}")
        try:
            # Reserve the name exclusively, so a concurrent launch cannot take it too
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        break

    write_project(path, {
        "video": os.path.abspath(videopath),
        "canvas": list(canvas),
        "trim": None,
        "crop": None,
        "axes": None,
        "scale": None,
        "rects": {"track": [], "track_shapes": [], "ocr": []},
        "data": None,
    })
    return path


def read_project(path: str) -> dict:
    """Reads a project file and checks its version.

    Raises:
        ValueError: If the file is not a PhysTrackX project or uses a newer format.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    version = data.get("version")
    if version != PROJECT_VERSION:
        raise ValueError(f"Unsupported project version {version!r} in {path}; "
                         f"this build reads version {PROJECT_VERSION}.")
    if "video" not in data:
        raise ValueError(f"{path} does not name a video.")
    return data
