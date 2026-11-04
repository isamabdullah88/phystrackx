"""A new project file for each video, named by video, date, and id, never overwriting (no window).

Runs against a temporary folder, so it does not touch the real projects/ folder.
"""

import os
import re
import tempfile

from tests import harness as h
h.setup_env()

from core.project import new_project, read_project  # noqa: E402


def test_new_project_is_created_and_readable():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    video = "/somewhere/Air Trial 1.mp4"
    path = new_project(video, canvas=(640, 900), folder=folder)
    name = os.path.basename(path)
    h.check("project file is in the folder", os.path.dirname(path) == folder, path)
    h.check("name has the video name, date and time, and an id",
            re.fullmatch(r"Air_Trial_1_\d{8}-\d{6}_[0-9a-f]{8}\.phystrack", name) is not None, name)
    state = read_project(path)
    h.check("project names the video", state["video"] == os.path.abspath(video), state["video"])
    h.check("project records the canvas", state["canvas"] == [640, 900], str(state["canvas"]))
    h.check("new project has nothing set up yet",
            state["trim"] is None and state["axes"] is None and state["scale"] is None
            and state["rects"]["track"] == [], str(state))


def test_new_projects_never_overwrite():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    video = "/somewhere/Air Trial 1.mp4"
    paths = {new_project(video, canvas=(640, 900), folder=folder) for _ in range(20)}
    h.check("every launch gets its own file", len(paths) == 20, f"{len(paths)} unique of 20")


def test_default_folder_is_projects_dir():
    import core.project as project
    h.check("tests use a folder inside the work folder, not the repo's projects/",
            project.PROJECTS_DIR.startswith(h.WORK_DIR), project.PROJECTS_DIR)


if __name__ == "__main__":
    h.run_tests([test_new_project_is_created_and_readable, test_new_projects_never_overwrite,
                 test_default_folder_is_projects_dir])
