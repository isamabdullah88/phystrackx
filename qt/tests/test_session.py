"""
A bare start reopens the session: the trial windows open when the app was last closed, each with its
project if it has one. Quitting with several windows open keeps them all; a window closed during use
drops out at once. A start with files given opens those, not the session.

    uv run python tests/test_session.py
"""

import json
import os
import shutil

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from phystrack_qt import app, recent, session
from test_tracking import make_clip  # noqa: E402


def reset() -> None:
    """A clean record, and no record file: the tests share one home folder."""
    session._entries.clear()
    if os.path.exists(session.session_file()):
        os.remove(session.session_file())


def record() -> list[dict]:
    with open(session.session_file(), encoding="utf-8") as f:
        return json.load(f)["windows"]


def test_window_is_recorded_by_video_then_project() -> None:
    reset()
    clip = make_clip()
    w = h.window()
    w.load_video(clip)
    h.check("a video is recorded", record() == [{"project": None, "video": os.path.abspath(clip)}], str(record()))
    project = os.path.join(h.WORK, "session_case.phystrack")
    w.save_project_file(project)
    h.check("a saved project is recorded by its project file, with its video",
            record() == [{"project": project, "video": os.path.abspath(clip)}], str(record()))
    h.check("a bare start restores the project", session.restorable() == [project])
    w._dirty = False
    w.close()
    h.pump(lambda: False, 0.1)


def test_an_empty_window_is_not_recorded() -> None:
    reset()
    w = h.window()
    h.check("a window with no video leaves no record", not os.path.exists(session.session_file()))
    w.close()
    h.pump(lambda: False, 0.1)


def test_quitting_with_two_windows_keeps_both() -> None:
    """Quitting closes the windows in one pass, before the event loop runs again: both stay recorded."""
    reset()
    first, second = h.window(), h.window()
    first.load_video(make_clip())
    second.load_video(make_clip())
    first.close()
    second.close()   # The quit: both closed back to back
    recorded = record()   # Read before the event loop runs again, as at a quit
    h.check("quitting with two windows open keeps both in the session", len(recorded) == 2, str(recorded))
    h.check("...in the order they were opened", recorded[0]["video"] == os.path.abspath(first.source.path))


def test_a_window_closed_during_use_drops_out() -> None:
    reset()
    kept, closed = h.window(), h.window()
    kept.load_video(make_clip())
    closed.load_video(make_clip())
    closed.close()
    h.pump(lambda: len(record()) == 1, 5)
    h.check("a window closed during use is dropped from the session", len(record()) == 1, str(record()))
    kept._dirty = False
    kept.close()
    h.pump(lambda: False, 0.1)


def test_a_hold_keeps_the_record_until_released() -> None:
    """The start reopens the last session's trials one by one (app.open_trials). Until the last is open the
    record on disk stays the whole session, so a quit part-way does not shrink it."""
    reset()
    first = h.window()
    first.load_video(make_clip())
    whole = record()
    session.hold()
    second = h.window()
    second.load_video(make_clip())
    h.check("while held, opening a trial does not rewrite the record", record() == whole, str(record()))
    session.release()
    h.check("released, the record holds every trial", len(record()) == 2, str(record()))
    first._dirty = second._dirty = False
    first.close()
    second.close()
    h.pump(lambda: False, 0.1)


def test_a_hold_with_nothing_to_write_writes_nothing() -> None:
    reset()
    session.hold()
    session.release()
    h.check("a hold and release with no change leave no record", not os.path.exists(session.session_file()))


def test_missing_files_are_skipped() -> None:
    reset()
    os.makedirs(os.path.dirname(session.session_file()), exist_ok=True)
    with open(session.session_file(), "w", encoding="utf-8") as f:
        json.dump({"windows": [{"project": "/no/such/project.phystrack", "video": "/no/such/video.mp4"},
                               {"project": None, "video": make_clip()}]}, f)
    targets = session.restorable()
    h.check("a window whose files are gone is left out, the others are kept",
            targets is not None and len(targets) == 1 and targets[0].endswith(".mp4"), str(targets))


def test_startup_choices() -> None:
    reset()
    h.check("a bare start with no record opens the most recent project",
            app.startup_files([]) == recent.load()[:1])
    clip = make_clip()
    os.makedirs(os.path.dirname(session.session_file()), exist_ok=True)
    with open(session.session_file(), "w", encoding="utf-8") as f:
        json.dump({"windows": [{"project": None, "video": clip}]}, f)
    h.check("a bare start opens the session's windows", app.startup_files([]) == [clip], str(app.startup_files([])))
    h.check("a start with files given opens those, not the session",
            app.startup_files(["/x/a.mp4"]) == ["/x/a.mp4"])


if __name__ == "__main__":
    h.app()
    for test in (test_window_is_recorded_by_video_then_project, test_an_empty_window_is_not_recorded,
                 test_quitting_with_two_windows_keeps_both, test_a_window_closed_during_use_drops_out,
                 test_a_hold_keeps_the_record_until_released, test_a_hold_with_nothing_to_write_writes_nothing,
                 test_missing_files_are_skipped, test_startup_choices):
        print(test.__name__)
        test()
    h.finish()
