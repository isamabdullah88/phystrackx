"""Command-line options of tk/phystrackx.py (runs the entry point in a subprocess)."""

import os
import subprocess
import sys

from tests import harness as h
h.setup_env()


def _run(*args):
    return subprocess.run([sys.executable, "tk/phystrackx.py", *args], cwd=h.REPO,
                          capture_output=True, text=True, env=os.environ)


def test_help_lists_options():
    r = _run("--help")
    for opt in ("--skip-intro", "--video", "--project", "--download-models"):
        h.check(f"--help lists {opt}", opt in r.stdout, r.stderr[-200:])


def test_missing_video_is_an_error():
    r = _run("--video", "/nonexistent/clip.mp4")
    h.check("missing --video file exits with code 2", r.returncode == 2)
    h.check("missing --video file says so", "video file not found" in r.stderr)


def test_missing_project_is_an_error():
    r = _run("--project", "/nonexistent/p.phystrack")
    h.check("missing --project file exits with code 2", r.returncode == 2)


def test_video_and_project_conflict():
    clip = h.make_clip()
    r = _run("--video", clip, "--project", "/nonexistent/p.phystrack")
    h.check("--video with --project is refused", r.returncode == 2 and "cannot be used together" in r.stderr)


if __name__ == "__main__":
    h.run_tests([test_help_lists_options, test_missing_video_is_an_error,
                 test_missing_project_is_an_error, test_video_and_project_conflict])
