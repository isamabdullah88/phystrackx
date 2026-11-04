"""
Starts the app from a source checkout, without installing it:

    ~/.venvs/phystrackx-qt/bin/python run.py [video or project.phystrack ...]

The installed command is `phystrackx` (see README.md); both run the same program (cli.py).
"""

from phystrack_qt import cli

if __name__ == "__main__":
    cli.main()
