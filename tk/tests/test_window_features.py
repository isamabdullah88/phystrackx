"""Window features: the File menu and its recent projects, Clear Data, dark text on the cyan strips,
the video area following the window size (overlays stay on the picture), and a project file given
as --video. Needs a window, except the last check.

One app for the module: a second RigidApp in the same process breaks Tk's images.
"""

import os
import sys

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from core import recent  # noqa: E402

_APP: dict = {}


def _app():
    if "app" not in _APP:
        h.quiet_dialogs(ra)
        root = ctk.CTk()
        root.geometry("1280x720")
        root.update()
        app = ra.RigidApp(root, videopath=h.make_clip())
        h.pump(root, lambda: app.videoapp.fcount > 0)
        h.pump(root, timeout=0.5)
        _APP.update(root=root, app=app)
    return _APP["root"], _APP["app"]


def test_file_menu_lists_recent_projects():
    root, app = _app()
    h.check("the window has a menu bar", str(root.cget("menu")) != "")
    h.check("tests keep their projects out of the user's recent list",
            recent.RECENT_FILE.startswith(h.WORK_DIR), recent.RECENT_FILE)
    saved_file = recent.RECENT_FILE
    recent.RECENT_FILE = os.path.join(h.WORK_DIR, "recent_test.json")
    try:
        first = os.path.join(h.WORK_DIR, "first_recent.phystrack")
        second = os.path.join(h.WORK_DIR, "second_recent.phystrack")
        for p in (first, second):
            with open(p, "w", encoding="utf-8") as f:
                f.write("{}")
        recent.forget_all()
        recent.remember(first)
        recent.remember(second)
        recent.remember(first)  # Moves to the top, not listed twice
        h.check("recent projects are newest first, without repeats",
                recent.load() == [os.path.abspath(first), os.path.abspath(second)], str(recent.load()))
        app._fill_recent_menu()
        labels = [app.recentmenu.entrycget(i, "label") for i in range(app.recentmenu.index("end") + 1)
                  if app.recentmenu.type(i) == "command"]
        folder = os.path.basename(h.WORK_DIR)
        h.check("the Open Recent menu lists both projects",
                labels[:2] == [f"first_recent   ({folder})", f"second_recent   ({folder})"], str(labels))
        h.check("the menu ends with Clear Menu", labels[-1] == "Clear Menu", str(labels))
        os.remove(first)
        h.check("a project that no longer exists is left out", recent.load() == [os.path.abspath(second)])
        recent.forget_all()
    finally:
        recent.RECENT_FILE = saved_file


def test_clear_data_discards_the_results():
    root, app = _app()
    app.videoapp.rigid.trackpts.append([[10.0, 20.0], [11.0, 21.0]])
    app.trackstatus.configure(text="Tracking complete")
    h.check("the track strip has a Clear Data button", app.cleardatabtn.cget("text") == "Clear Data")
    app._clear_track_data()
    root.update()
    h.check("Clear Data empties the tracked positions", app.videoapp.trackpts == [])
    h.check("Clear Data says the data is cleared", "cleared" in app.trackstatus.cget("text"),
            app.trackstatus.cget("text"))
    h.check("the manual position button is off after a clear", str(app.manualbtn.cget("state")) == "disabled")


def test_strip_text_is_dark():
    root, app = _app()
    h.check("the crop status text is dark", app.cropstatus.cget("text_color") == "black")
    h.check("the track status text is dark", app.trackstatus.cget("text_color") == "black")


def test_resizing_the_window_keeps_overlays_on_the_picture():
    root, app = _app()
    origin = app.view.origin
    app.scruler.p1 = [origin[0] + 50.0, origin[1] + 40.0]
    app.scruler.p2 = [origin[0] + 50.0, origin[1] + 200.0]
    app.scruler.placed = True
    app.scruler.draw()
    frame_before = (app.scruler.p1[1] - app.view.origin[1], app.scruler.p2[1] - app.view.origin[1])
    fit_before = app.view.fit
    old_w, old_h = app.videoview.winfo_width(), app.videoview.winfo_height()

    new_w = min(1500, root.winfo_screenwidth() - 40)
    new_h = min(1000, root.winfo_screenheight() - 200)
    root.geometry(f"{new_w}x{new_h}")
    h.pump(root, lambda: app.videoview.winfo_height() != old_h, timeout=10)
    h.pump(root, timeout=0.8)  # The layout follows once the resize settles

    grew = app.videoview.winfo_height() > old_h
    h.check("the video area grew with the window", grew, f"{old_h} -> {app.videoview.winfo_height()}")
    if grew:
        h.check("the video area size is the one the layout uses",
                (app.vwidth, app.vheight) == (app.videoview.winfo_width(), app.videoview.winfo_height()),
                f"{app.vwidth}x{app.vheight}")
        h.check("the picture is larger after the resize", app.view.fit > fit_before + 0.02,
                f"{fit_before:.3f} -> {app.view.fit:.3f}")
        frame_after = (app.scruler.p1[1] - app.view.origin[1], app.scruler.p2[1] - app.view.origin[1])
        h.check("the ruler stays on the same part of the picture",
                abs(frame_after[0] - frame_before[0]) < 0.6 and abs(frame_after[1] - frame_before[1]) < 0.6,
                f"{frame_before} -> {frame_after}")
    root.geometry("1280x720")
    h.pump(root, timeout=0.8)


def test_video_argument_takes_a_project_file():
    """--video given a project file opens that project (no window needed)."""
    import phystrackx
    project = os.path.join(h.WORK_DIR, "as_video_arg.phystrack")
    with open(project, "w", encoding="utf-8") as f:
        f.write("{}")
    saved_argv = sys.argv
    sys.argv = ["phystrackx.py", "--video", project]
    try:
        args = phystrackx.parse_args()
    finally:
        sys.argv = saved_argv
    h.check("a .phystrack given as --video is opened as a project",
            args.project == os.path.abspath(project) and args.video is None,
            f"project={args.project} video={args.video}")


if __name__ == "__main__":
    h.run_tests([test_file_menu_lists_recent_projects, test_clear_data_discards_the_results,
                 test_strip_text_is_dark, test_resizing_the_window_keeps_overlays_on_the_picture,
                 test_video_argument_takes_a_project_file])
