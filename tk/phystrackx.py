"""
phystrackx.py

Entry point for launching the PhysTrackX GUI application.

Author: Isam Balghari
"""

import argparse
import os
import signal
import sys

# core and media are shared with the Qt app, so they live at the repo root, beside this folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from gui.menu import MenuScreen
from core import crash, session, setup_logging
from core.project import PROJECT_EXTENSION


class GUI:
    """Main GUI launcher for PhysTrackX."""

    def __init__(self, skip_intro: bool = False, video_path: str | None = None,
                 project_path: str | None = None) -> None:
        self.skip_intro = skip_intro
        self.video_path = video_path
        self.project_path = project_path
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

    def start(self) -> None:
        """Initializes and starts the main GUI loop. Ctrl-C ends it and says how to resume."""
        self.menu = MenuScreen(skip_intro=self.skip_intro, video_path=self.video_path,
                               project_path=self.project_path)
        root = self.menu.root
        crash.install_tk(root)

        # Tk swallows KeyboardInterrupt raised inside its callbacks, so Ctrl-C asks the loop to
        # stop instead. The short timer keeps Python running often enough to see the signal.
        def on_interrupt(signum, frame):
            root.quit()

        signal.signal(signal.SIGINT, on_interrupt)

        def tick():
            root.after(200, tick)
        tick()

        try:
            root.mainloop()
        finally:
            self.report_resume()

    def report_resume(self) -> None:
        """Prints the open project and the command that reopens it, if a project is open."""
        project = session.current_project()
        command = session.resume_command(project, __file__)
        if command is None:
            return
        print(f"\nSession ended. Project: {os.path.basename(project)}", flush=True)
        print(f"Resume with:\n  {command}", flush=True)


def parse_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="Launch the PhysTrackX GUI.")
    parser.add_argument("--skip-intro", action="store_true",
                        help="Skip the startup animation and music.")
    parser.add_argument("--video", metavar="PATH",
                        help="Load this video on startup and skip the start button.")
    parser.add_argument("--project", metavar="PATH",
                        help="Open a saved project (video, trim, axes, scale, and rectangles).")
    parser.add_argument("--download-models", action="store_true",
                        help="Download the tracking models if missing, then exit.")
    args = parser.parse_args()

    # A project file given as --video opens that project (its video is named inside it)
    if args.video and args.video.lower().endswith(PROJECT_EXTENSION):
        args.project, args.video = args.video, None

    if args.video and args.project:
        parser.error("--video and --project cannot be used together; the project names its video")
    if args.video:
        args.video = os.path.abspath(args.video)
        if not os.path.isfile(args.video):
            parser.error(f"video file not found: {args.video}")
    if args.project:
        args.project = os.path.abspath(args.project)
        if not os.path.isfile(args.project):
            parser.error(f"project file not found: {args.project}")
    return args


def main() -> None:
    """Runs the PhysTrackX GUI application."""
    args = parse_args()
    setup_logging()
    crash.install()  # Tracebacks for every failure, including crashes inside C code

    if args.download_models:
        from experiments.rigid.modelfiles import download_all
        download_all()
        print("Tracking models are present.")
        return

    program = GUI(skip_intro=args.skip_intro, video_path=args.video, project_path=args.project)
    program.start()


if __name__ == "__main__":
    main()
