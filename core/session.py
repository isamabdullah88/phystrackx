"""
session.py

Remembers the project the app has open, so that when the session is interrupted (Ctrl-C) the
launcher can say how to pick it up again.

Author: Isam Balghari
"""

import os
import shlex
import sys

_project: str | None = None


def set_project(path: str | None) -> None:
    """Records the project file that is open now (None when no project is open)."""
    global _project
    _project = os.path.abspath(path) if path else None


def current_project() -> str | None:
    return _project


def resume_command(projectpath: str | None, script: str) -> str | None:
    """
    The command that reopens a project: the same Python, the same launcher script, and --project.
    Returns None when there is no project to reopen.
    """
    if not projectpath:
        return None
    return " ".join(shlex.quote(part) for part in
                    (sys.executable, os.path.abspath(script), "--project", projectpath))
