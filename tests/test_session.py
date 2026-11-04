"""The resume command printed on Ctrl-C (no window needed)."""

import os
import sys

from tests import harness as h
h.setup_env()

from core import session  # noqa: E402


def test_no_project_gives_no_command():
    h.check("no project, nothing to resume", session.resume_command(None, "tk/phystrackx.py") is None)


def test_command_reopens_the_project_with_spaces_quoted():
    project = "/Users/me/My Projects/Air Trial 1_20261019.phystrack"
    cmd = session.resume_command(project, "tk/phystrackx.py")
    import shlex
    h.check("command uses this Python", cmd.startswith(shlex.quote(sys.executable)), cmd)
    h.check("command runs the launcher with --project",
            "--project" in cmd and os.path.abspath("tk/phystrackx.py") in cmd, cmd)
    h.check("project path with spaces is quoted", f"'{project}'" in cmd, cmd)


def test_set_project_tracks_the_open_one():
    session.set_project("projects/a.phystrack")
    h.check("open project is remembered", session.current_project() == os.path.abspath("projects/a.phystrack"))
    session.set_project(None)
    h.check("closing forgets it", session.current_project() is None)


if __name__ == "__main__":
    h.run_tests([test_no_project_gives_no_command, test_command_reopens_the_project_with_spaces_quoted,
                 test_set_project_tracks_the_open_one])
