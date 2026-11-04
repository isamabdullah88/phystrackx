"""
Older projects open here. A Tk-app project is imported: its setup is carried over, scaled from the
canvas to the frame, and what has no counterpart is named. A project whose picture is another size
is scaled to the picture as it is now. A project whose video has moved is found beside the project.
An imported project is never saved over.

    ~/.venvs/phystrackx-qt/bin/python tests/test_migration.py
"""

import json
import os
import shutil

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from phystrack_qt import project_file
from phystrack_qt.tk_import import from_tk, video_size
from test_tracking import make_clip  # noqa: E402

FRAME = (1920, 1080)
CANVAS = (1140, 648)   # The Tk app's canvas for the same video (the sample files' size)


def close(a: float, b: float) -> bool:
    return abs(a - b) < 1e-6


def tk_project(video: str) -> dict:
    """A Tk-app project as the Tk app writes it (older form: canvas positions, no anchor)."""
    return {"version": 1, "video": video, "canvas": list(CANVAS),
            "trim": {"start": 50, "end": 150, "crop": [10, 10, 300, 200]}, "crop": None,
            "axes": {"ox": 570.0, "oy": 324.0, "theta": -3.5, "canvas": list(CANVAS)},
            "scale": {"p1": [100.0, 50.0], "p2": [100.0, 274.0], "real_world_length": 50.0,
                      "unit": "cm", "canvas": list(CANVAS)},
            "data": None,
            "rects": {"track": [[0.25, 0.5, 0.1, 0.2]], "track_shapes": ["circle"], "ocr": []}}


def test_canvas_positions_are_scaled_to_the_frame() -> None:
    state = from_tk(tk_project("clip.mp4"), FRAME)
    kx, ky = FRAME[0] / CANVAS[0], FRAME[1] / CANVAS[1]
    h.check("the axes origin is scaled from the canvas",
            close(state["axes"]["x"], 570 * kx) and close(state["axes"]["y"], 324 * ky), str(state["axes"]))
    h.check("the axes keep their turn", state["axes"]["rotation"] == -3.5)
    p1, p2 = state["ruler"]["p1"], state["ruler"]["p2"]
    h.check("the ruler's ends are scaled from the canvas",
            close(p1[0], 100 * kx) and close(p1[1], 50 * ky) and close(p2[1], 274 * ky), str(state["ruler"]))
    h.check("the ruler keeps its length and unit",
            state["ruler"]["real_length"] == 50.0 and state["ruler"]["unit"] == "cm")
    h.check("the trim is the Tk trim's range", state["trim"] == [50, 150] and state["frame"] == 50)
    h.check("the picture is the frame", state["picture"] == list(FRAME))
    x, y, w, hh = state["objects"][0]["marked"]
    h.check("a tracked box is a fraction of the frame",
            close(x, 0.25 * FRAME[0]) and close(y, 0.5 * FRAME[1]) and close(w, 0.1 * FRAME[0])
            and close(hh, 0.2 * FRAME[1]), str(state["objects"][0]["marked"]))
    h.check("the circle shape carries over", state["objects"][0]["circle"] is True)
    h.check("the object starts at the trim's start, with no track yet",
            state["objects"][0]["marked_frame"] == 50 and state["objects"][0]["boxes"] == {})
    h.check("the crop is named as left out",
            any("crop" in note for note in state["imported"]["left_out"]), str(state["imported"]))
    h.check("the marked frame is named to check",
            any("start frame" in note for note in state["imported"]["check"]), str(state["imported"]))


def test_anchored_positions_are_kept() -> None:
    data = tk_project("clip.mp4")
    data["axes"] = {"ox": 400.0, "oy": 300.0, "theta": 0.0, "anchor": "picture", "canvas": list(CANVAS)}
    data["scale"] = {"p1": [10.0, 20.0], "p2": [30.0, 40.0], "real_world_length": None, "unit": None,
                     "anchor": "picture", "canvas": list(CANVAS)}
    state = from_tk(data, FRAME)
    h.check("an anchored axes origin is already in frame pixels",
            state["axes"]["x"] == 400.0 and state["axes"]["y"] == 300.0, str(state["axes"]))
    h.check("anchored ruler ends are already in frame pixels", state["ruler"]["p2"] == [30.0, 40.0])


def test_tk_project_opens_through_the_loader() -> None:
    clip = make_clip()
    folder = os.path.join(h.WORK, "tk_import")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "clip tk.phystrack")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tk_project(clip), f)
    state = project_file.load(path)
    h.check("a Tk project loads as an imported project", "imported" in state)
    h.check("the frame size is the video's", state["picture"] == list(video_size(clip)), str(state["picture"]))


def test_moved_video_is_found_beside_the_project() -> None:
    clip = make_clip()
    folder = os.path.join(h.WORK, "moved")
    os.makedirs(folder, exist_ok=True)
    shutil.copy(clip, os.path.join(folder, os.path.basename(clip)))
    path = os.path.join(folder, "moved.phystrack")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"format": project_file.FORMAT, "version": project_file.VERSION,
                   "video": "/no/such/folder/" + os.path.basename(clip), "trim": None}, f)
    state = project_file.load(path)
    h.check("a project whose video moved finds it beside the project",
            os.path.samefile(state["video"], os.path.join(folder, os.path.basename(clip))), state["video"])


def test_unreadable_tk_video_is_refused_with_a_message() -> None:
    path = os.path.join(h.WORK, "tk_missing.phystrack")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tk_project("/no/such/video.mp4"), f)
    try:
        project_file.load(path)
        h.check("a Tk project whose video is missing is refused", False)
    except ValueError as e:
        h.check("a Tk project whose video is missing is refused with a message",
                "cannot be read" in str(e), str(e))


def test_window_scales_a_project_to_its_picture() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    now = w.view.picture.pixmap().size()
    state = {"picture": [now.width() / 2, now.height() / 2], "frame": 0, "trim": None,
             "axes": {"x": 10.0, "y": 20.0, "rotation": 0.0, "length": 50.0},
             "ruler": {"p1": [5.0, 5.0], "p2": [10.0, 10.0], "real_length": None, "unit": None},
             "objects": [{"number": 1, "circle": False, "outline": None, "marked": [4.0, 6.0, 8.0, 10.0],
                          "marked_frame": 0, "changed": True, "tracked_with": None,
                          "boxes": {"3": [1.0, 2.0, 3.0, 4.0]}}],
             "plots": {}}
    fitted = w._fit_state(state)
    h.check("a project at half the picture's size is doubled to it",
            close(fitted["axes"]["x"], 20.0) and close(fitted["axes"]["y"], 40.0)
            and fitted["ruler"]["p2"] == [20.0, 20.0], str(fitted["axes"]))
    h.check("object boxes are doubled too",
            fitted["objects"][0]["marked"] == [8.0, 12.0, 16.0, 20.0]
            and fitted["objects"][0]["boxes"]["3"] == [2.0, 4.0, 6.0, 8.0])
    h.check("the state's picture is now the picture's size", fitted["picture"] == [now.width(), now.height()])
    h.check("a project at the picture's size is used as it is",
            w._fit_state({**state, "picture": [now.width(), now.height()]})["axes"]["x"] == 10.0)
    w.close()


def test_imported_project_is_not_saved_over() -> None:
    clip = make_clip()
    folder = os.path.join(h.WORK, "tk_open")
    os.makedirs(folder, exist_ok=True)
    shutil.copy(clip, os.path.join(folder, "clip.mp4"))
    path = os.path.join(folder, "clip.phystrack")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tk_project(os.path.join(folder, "clip.mp4")), f)
    before = open(path, encoding="utf-8").read()
    w = h.window()
    h.check("opening a Tk project succeeds", w.open_project_file(path))
    h.check("an imported project has no project file yet (Save makes a new one)", w.project_path is None)
    h.check("an imported project counts as unsaved", w._dirty)
    w.save_project()
    h.check("saving writes a new project, not the Tk file",
            w.project_path is not None and w.project_path != path and open(path, encoding="utf-8").read() == before,
            str(w.project_path))
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    for test in (test_canvas_positions_are_scaled_to_the_frame, test_anchored_positions_are_kept,
                 test_tk_project_opens_through_the_loader, test_moved_video_is_found_beside_the_project,
                 test_unreadable_tk_video_is_refused_with_a_message, test_window_scales_a_project_to_its_picture,
                 test_imported_project_is_not_saved_over):
        print(test.__name__)
        test()
    h.finish()
