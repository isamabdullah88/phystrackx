"""
Project files for the Qt app: the setup for one video (trim, axes, ruler, tracked boxes), as
JSON with a .phystrack extension, written next to the video.

Format 2 is this app's own. The Tk app's files are format 1 (no "format" key); load() imports them
(tk_import.py) and never writes them, so saving an imported project writes a new file of this format
next to the video. A file of another format, or a newer version of this one, is refused.

To change this format: bump VERSION, and in load() convert each older version to the next one.
"""

import json
import os
import tempfile

from phystrack_qt import paths, tk_import

FORMAT = "phystrackx-qt"
VERSION = 2
TK_VERSION = 1   # The Tk app's format: no "format" key
EXTENSION = ".phystrack"


def default_folder(video_path: str) -> str:
    """Next to the video, so a trial's files stay together; the user's data folder if that is read-only."""
    folder = os.path.dirname(os.path.abspath(video_path))
    if os.access(folder, os.W_OK):
        return folder
    projects = paths.projects_dir()
    os.makedirs(projects, exist_ok=True)
    return projects


def new_project_path(video_path: str) -> str:
    """A path for a new project for this video, next to it, that does not overwrite a file."""
    return output_path(video_path, "", EXTENSION)


def output_path(video_path: str, suffix: str, extension: str) -> str:
    """A path next to the video for something saved from it, named after it ("Air Trial 1" +
    suffix + extension), that does not overwrite a file: " 2", " 3"... are added when needed."""
    folder = default_folder(video_path)
    stem = os.path.splitext(os.path.basename(video_path))[0] + suffix
    path = os.path.join(folder, stem + extension)
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{stem} {n}{extension}")
        n += 1
    return path


def save(path: str, state: dict) -> None:
    """Writes the project atomically, so a failed save never leaves a half-written file."""
    data = {"format": FORMAT, "version": VERSION, **state}
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load(path: str) -> dict:
    """
    Reads a project file and checks it.

    Raises:
        ValueError: If the file is not a project this app can read, or names no video, or its video
            cannot be read (a Tk project's frame size is needed to import it).
        OSError: If it cannot be read.
    """
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{name} is not a project file ({e}).") from e
    if "video" not in data:
        raise ValueError(f"{name} does not name a video.")
    if not os.path.isfile(data["video"]):
        # The project's folder was moved (or the file saved on another computer): the video is
        # often still beside the project, with the same name
        beside = os.path.join(os.path.dirname(os.path.abspath(path)), os.path.basename(data["video"]))
        if os.path.isfile(beside):
            data = {**data, "video": beside}
    if "format" not in data and data.get("version") == TK_VERSION:
        size = tk_import.video_size(data["video"])
        if size is None:
            raise ValueError(f"{name} is a Tk project, and its video cannot be read to import it: "
                             f"{data['video']}")
        return tk_import.from_tk(data, size)
    if data.get("format") != FORMAT:
        raise ValueError(f"{name} is not a project this app can read.")
    if data.get("version") != VERSION:
        raise ValueError(f"{name} is project version {data.get('version')!r}; "
                         f"this app reads version {VERSION}.")
    return data
