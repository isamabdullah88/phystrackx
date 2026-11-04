"""
The `phystrackx` command: opens PhysTrackX on videos and projects.

    phystrackx [--version] [video.mp4 | project.phystrack ...]

Arguments are checked here, before Qt is imported, so --help, --version and a missing file answer at
once. The first file opens in the main window; each further one in a window of its own.
"""

import argparse
import os
import sys

from phystrack_qt.version import __version__


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="phystrackx", description="Measure motion in a video.")
    parser.add_argument("--version", action="version", version=f"phystrackx {__version__}")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="a video to open, or a .phystrack project")
    # The install's hidden launch (build.py warm_launch): load everything, show nothing, quit
    parser.add_argument("--warm-launch", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    for path in args.files:
        if not os.path.isfile(path):
            parser.error(f"no such file: {path}")
    args.files = [os.path.abspath(path) for path in args.files]
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse(sys.argv[1:] if argv is None else argv)
    from phystrack_qt import app   # Qt is loaded only now
    if args.warm_launch:
        app.warm_launch()
    else:
        app.run(args.files)
