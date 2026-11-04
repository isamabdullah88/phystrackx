"""
The packaged program keeps matplotlib's font cache between starts. PyInstaller's runtime hook points matplotlib at
a new, empty folder at every start and deletes it at exit, so the font cache (about 10 s to build) was rebuilt
each time. It builds while matplotlib is imported, and the main thread, importing matplotlib too, waited for it:
the window was frozen, and macOS could not take the menu bar over. packaging/entry.py (what the packaged
program runs) sets the folder again, after the hook and before matplotlib is imported.

    uv run python tests/test_entry.py
"""

import os
import subprocess
import sys
import tempfile

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from platformdirs import user_cache_dir  # noqa: E402

from phystrack_qt import paths  # noqa: E402

ENTRY = os.path.join(h.QT, "packaging", "entry.py")


def test_the_entry_keeps_matplotlibs_folder() -> None:
    hook_folder = tempfile.mkdtemp(prefix="mpl-hook-")   # What PyInstaller's runtime hook sets, before the entry runs
    code = ("import os, runpy, sys\n"
            "sys.argv = ['phystrackx', '--version']\n"
            "try:\n"
            f"    runpy.run_path({ENTRY!r}, run_name='__main__')\n"
            "except SystemExit:\n"
            "    pass\n"
            "print('MPLCONFIGDIR=' + os.environ.get('MPLCONFIGDIR', ''))\n")
    env = dict(os.environ, MPLCONFIGDIR=hook_folder, PYTHONPATH=os.pathsep.join([h.QT, os.path.dirname(h.QT)]))
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    lines = [line for line in done.stdout.splitlines() if line.startswith("MPLCONFIGDIR=")]
    folder = lines[-1].split("=", 1)[1] if lines else ""
    h.check("the entry points matplotlib at a folder that lasts, not the hook's",
            folder != "" and folder != hook_folder and folder == paths.matplotlib_dir(),
            f"{folder!r} (hook: {hook_folder!r}) {done.stderr[-300:]}")
    cache = user_cache_dir(paths.APP_NAME, appauthor=False)
    h.check("...in the user's cache folder, whatever the data home (the install's hidden launch fills it)",
            folder.startswith(cache) and not folder.startswith(os.environ["PHYSTRACK_QT_HOME"]), folder)


if __name__ == "__main__":
    h.app()
    for test in (test_the_entry_keeps_matplotlibs_folder,):
        print(test.__name__)
        test()
    h.finish()
