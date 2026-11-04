"""
Imports modules from the repo's packages (core, media, experiments) without running their package __init__ files.

The parent's experiments/__init__.py imports Rigid, which imports customtkinter, the Tk-bound GUI
plugins (Crop, Filters) and OCR. The tracker itself (experiments/rigid/mltracker.py) needs only
OpenCV. Until the migration makes those package imports lazy (a one-line change per __init__,
left alone for now because tracker work is going on in the parent), the packages are registered
here as empty shells so their submodules can be imported on their own.
"""

import importlib
import os
import sys
import types

from phystrack_qt import PARENT   # The folder holding those packages (the repo root, or site-packages)


def import_light(module: str):
    """Imports e.g. "experiments.rigid.mltracker" without running experiments/__init__.py or
    experiments/rigid/__init__.py. Packages that are already imported are left as they are."""
    parts = module.split(".")
    if parts[0] == "core":   # core's __init__ is light (no GUI imports): a normal import, so `from core import ...` works
        return importlib.import_module(module)
    for i in range(1, len(parts)):
        package = ".".join(parts[:i])
        if package not in sys.modules:
            shell = types.ModuleType(package)
            shell.__path__ = [os.path.join(PARENT, *parts[:i])]
            sys.modules[package] = shell
    return importlib.import_module(module)
