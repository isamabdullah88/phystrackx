"""The program a packaged app starts: the same command-line entry as `phystrackx` (phystrack_qt/cli.py)."""

import os
import sys

from phystrack_qt import paths

# PyInstaller's runtime hook has just pointed matplotlib at a new, empty folder, and deletes it at exit, so
# matplotlib's font cache was rebuilt at every start: about 10 s, during which the main thread, importing
# matplotlib too, waited for it, the window was frozen, and macOS could not take the menu bar over. (The hook
# is for a one-file build, which unpacks to a new folder at each start and would leave a kept cache pointing
# at fonts that are gone. This build is one folder: its fonts stay where they are, and matplotlib rebuilds the
# cache by itself if they ever move.) So: a folder that lasts, set before matplotlib is imported.
os.environ["MPLCONFIGDIR"] = paths.matplotlib_dir()

if sys.stdout is None or sys.stderr is None:
    # The Windows build has no console (phystrackx.spec), so Python has no output streams. Send them to a log
    # file: otherwise a crash would leave no trace. The logging setup in core/logging.py must see these
    # streams, so this runs before the import below.
    from platformdirs import user_log_dir
    log_dir = user_log_dir("PhysTrackX", appauthor=False)
    try:
        os.makedirs(log_dir, exist_ok=True)
        log = open(os.path.join(log_dir, "phystrackx.log"), "a", encoding="utf-8", buffering=1)
    except OSError:
        log = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stderr = log

from phystrack_qt.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
