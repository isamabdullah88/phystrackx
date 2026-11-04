"""PhysTrackX's Qt app (PySide6). Run it as `phystrackx [video or project.phystrack ...]` (cli.py), or
from a source checkout with `python run.py`. See qt/README.md."""

import os
import sys


def _packages_folder() -> str:
    """The folder holding the repo's core, media, experiments and filters packages: the repo root in a
    source checkout (qt/ is beside them), or site-packages when installed (they are beside this package)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # qt/, or site-packages
    for folder in (os.path.dirname(here), here):
        if os.path.isdir(os.path.join(folder, "core")):
            return folder
    return here


# Put first on the path, so the repo's packages win over any other `core`
PARENT = _packages_folder()
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
