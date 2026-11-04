"""
Projects and data files: the recent list, where projects are saved (next to the video, or in
projects/ when that folder is read-only), unique names for new projects, the File menu's Open
Recent, and the plot's saved data and results.

    ~/.venvs/phystrackx-qt/bin/python tests/test_projects.py
"""

import os

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from phystrack_qt import paths, project_file, recent  # noqa: E402
from phystrack_qt.plot_window import DEFAULT_KINDS, write_plot_csv, write_results  # noqa: E402
from test_tracking import make_clip  # noqa: E402


def _file(name: str) -> str:
    path = os.path.join(h.WORK, name)
    open(path, "w").close()
    return path


def test_recent_list() -> None:
    recent.forget_all()
    a, b, c = _file("p_a.phystrack"), _file("p_b.phystrack"), _file("p_c.phystrack")
    for p in (a, b, c, a):  # a is used again: it moves to the top rather than repeating
        recent.remember(p)
    paths = recent.load()
    h.check("the recent list is newest first, with no repeats",
            paths == [os.path.abspath(a), os.path.abspath(c), os.path.abspath(b)],
            str([os.path.basename(p) for p in paths]))
    os.remove(b)
    h.check("a project that was deleted is left out", os.path.abspath(b) not in recent.load())
    recent.forget_all()
    h.check("Clear Recent empties the list", recent.load() == [])
    h.check("the Qt list is its own file (the Tk app's is not touched)",
            os.path.dirname(recent.recent_file()) == os.path.join(h.WORK, "home"))


def test_project_folders() -> None:
    folder = os.path.join(h.WORK, "trial_folder")
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):  # Left over from an earlier run
        os.remove(os.path.join(folder, name))
    video = os.path.join(folder, "clip.mov")
    open(video, "w").close()
    h.check("a writable video folder is where the project goes",
            project_file.default_folder(video) == folder)

    if os.name == "nt":   # chmod does not make a folder read-only on Windows: nothing to test there
        print("  skipped: chmod cannot make a folder read-only on Windows")
    else:
        os.chmod(folder, 0o555)  # Read-only, as a folder on a shared drive can be
        try:
            where = project_file.default_folder(video)
            h.check("a read-only video folder sends the project to the user's projects folder",
                    where == paths.projects_dir(), where)
        finally:
            os.chmod(folder, 0o755)

    h.check("a new project is named after the video",
            os.path.basename(project_file.new_project_path(video)) == "clip" + project_file.EXTENSION,
            os.path.basename(project_file.new_project_path(video)))
    open(os.path.join(folder, "clip" + project_file.EXTENSION), "w").close()
    second = project_file.new_project_path(video)
    h.check("an existing project is not overwritten: the new one gets a number",
            os.path.basename(second) == "clip 2" + project_file.EXTENSION, os.path.basename(second))


def test_open_recent_menu() -> None:
    recent.forget_all()
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    path = os.path.join(h.WORK, "menu_test.phystrack")
    h.check("saving the project works", w.save_project_file(path))
    w._fill_recent_menu()
    texts = [a.text() for a in w.recent_menu.actions()]
    h.check("the File menu's Open Recent lists the saved project",
            any("menu_test.phystrack" in t for t in texts), str(texts))
    w._dirty = False
    w.close()
    recent.forget_all()


def test_plot_files() -> None:
    h.check("the plot opens with the distance plot only", DEFAULT_KINDS == ("r",), str(DEFAULT_KINDS))
    csv_path = os.path.join(h.WORK, "plot_data.csv")
    write_plot_csv(csv_path, ("time_s", "r (cm)"), [0.0, 1 / 30], [10.0, 10.5])
    with open(csv_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    h.check("the plot's data is saved with its column names",
            lines == ["time_s,r (cm)", "0,10", "0.0333333,10.5"], str(lines))
    txt = os.path.join(h.WORK, "plot_results.txt")
    write_results(txt, "[O-1] distance against time", "omega = 9.4 rad/s")
    with open(txt, encoding="utf-8") as f:
        body = f.read()
    h.check("the fit results are saved with the plot's title", body.startswith("[O-1] distance")
            and "omega = 9.4 rad/s" in body)


if __name__ == "__main__":
    h.app()
    for test in (test_recent_list, test_project_folders, test_open_recent_menu, test_plot_files):
        print(test.__name__)
        test()
    h.finish()
