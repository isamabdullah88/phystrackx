"""Save a full setup, reopen it in a new process, and compare every part.

The test runs this module twice as subprocesses (phases "save" and "open"), because one
process can only host one app window.
"""

import os
import subprocess
import sys

from tests import harness as h
h.setup_env()

PROJ = os.path.join(h.WORK_DIR, "roundtrip.phystrack")


def phase_save(video: str, proj: str) -> None:
    import time
    import customtkinter as ctk
    import gui.rigid.rigid_app as ra
    from core import PixelRect, NormalizedRect
    from core.project import write_project

    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=video)
    h.pump(root, lambda: app.videoapp.fcount > 0)
    app.trimvideo(20, 200)
    h.pump(root, lambda: app.trim_range is not None and app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)
    app.seekbar.mark_trimmed()
    app.axes.ox, app.axes.oy = 150.0, 120.0
    app.axes.placed = True
    app.axes.theta.set(12.5)
    app.axes.rotate()
    app.scruler.placed = True
    app.scruler.p1, app.scruler.p2 = [200.0, 200.0], [320.0, 200.0]
    app.scruler.real_world_length = 50.0
    app.scruler.draw()
    crop = app.plugin_mgr.crop
    crop.croprect = PixelRect(10, 20, 200, 300)
    crop.set()
    app.updateframe()
    app.track_rects.restore([NormalizedRect(0.2, 0.3, 0.1, 0.15)], crop.cropwidth, crop.cropheight,
                            crop.cropx, crop.cropy)
    write_project(proj, app.project_state())
    root.destroy()
    print("saved", proj)


def phase_open(proj: str) -> None:
    import customtkinter as ctk
    import gui.rigid.rigid_app as ra
    from core.project import read_project

    h.quiet_dialogs(ra)
    saved = read_project(proj)
    saved.pop("version")
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, projectpath=proj)
    h.pump(root, lambda: app.trim_range is not None and app.seekbar.trimmed
           and len(app.track_rects.boxes) == 1 and app.axes.placed and app.scruler.placed)
    h.pump(root, timeout=0.5)
    loaded = app.project_state()

    # The window size stamped on overlays differs between runs (the window is laid out again from
    # its real size); overlays are stored relative to the picture, so the stamp is not compared
    def close(a, b):
        if isinstance(a, dict):
            a = {k: v for k, v in a.items() if k != "canvas"}
            b = {k: v for k, v in b.items() if k != "canvas"}
            return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
        if isinstance(a, list):
            return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) <= 0.6
        return a == b

    for key in saved:
        if key == "canvas":
            continue
        h.check(f"reopened project keeps '{key}'", close(saved[key], loaded[key]),
                f"\n     saved : {saved[key]}\n     loaded: {loaded[key]}")
    root.destroy()


def test_roundtrip():
    video = h.make_clip()
    if os.path.exists(PROJ):
        os.remove(PROJ)
    for args in (["save", video, PROJ], ["open", PROJ]):
        r = subprocess.run([sys.executable, "-m", "tk.tests.test_roundtrip", *args], cwd=h.RUN_CWD,
                           capture_output=True, text=True, env=h.child_env())
        for line in r.stdout.splitlines():
            if line.strip().startswith(("PASS", "FAIL")) or line.startswith("     "):
                print(line)
        h.check(f"phase '{args[0]}' runs without error", r.returncode == 0, r.stderr[-400:])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "save":
        phase_save(sys.argv[2], sys.argv[3])
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "open":
        phase_open(sys.argv[2])
        sys.exit(1 if h._failures else 0)
    h.run_tests([test_roundtrip])
