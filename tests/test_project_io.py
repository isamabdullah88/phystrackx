"""Project file writing and reading (no window needed)."""

import json
import os

from tests import harness as h
h.setup_env()

from core.project import PROJECT_VERSION, read_project, write_project  # noqa: E402


def _path(name):
    return os.path.join(h.WORK_DIR, name)


def test_write_then_read_keeps_state():
    p = _path("io_roundtrip.phystrack")
    state = {"video": "/x/y.mp4", "canvas": [1, 2], "trim": None, "crop": None,
             "axes": None, "scale": None, "rects": {"track": [], "ocr": []}}
    write_project(p, state)
    data = read_project(p)
    h.check("file keeps version", data["version"] == PROJECT_VERSION)
    h.check("file keeps the state", all(data[k] == v for k, v in state.items()))


def test_wrong_version_is_rejected():
    p = _path("io_badversion.phystrack")
    with open(p, "w") as f:
        json.dump({"version": 999, "video": "x"}, f)
    try:
        read_project(p)
        h.check("version 999 is rejected", False)
    except ValueError as e:
        h.check("version 999 is rejected with a message", "Unsupported project version" in str(e))


def test_missing_video_is_rejected():
    p = _path("io_novideo.phystrack")
    with open(p, "w") as f:
        json.dump({"version": PROJECT_VERSION}, f)
    try:
        read_project(p)
        h.check("project without a video is rejected", False)
    except ValueError:
        h.check("project without a video is rejected", True)


def test_save_is_atomic_on_failure():
    # A failing write must not leave a half-written file behind, nor remove the old one
    p = _path("io_atomic.phystrack")
    write_project(p, {"video": "old.mp4"})
    try:
        write_project(p, {"video": object()})  # not JSON serialisable
    except TypeError:
        pass
    h.check("old project survives a failed save", read_project(p)["video"] == "old.mp4")
    h.check("no temp files are left behind",
            not [f for f in os.listdir(h.WORK_DIR) if f.endswith(".part")])


if __name__ == "__main__":
    h.run_tests([test_write_then_read_keeps_state, test_wrong_version_is_rejected,
                 test_missing_video_is_rejected, test_save_is_atomic_on_failure])
