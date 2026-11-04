"""
crash.py

Reports every failure, including ones that end the process:

- Python exceptions on the main thread, on worker threads (tracking, loading), and inside Tk
  callbacks are logged with their full traceback, to the console and the session log, and also
  appended to logs/crash.log.
- A crash inside C code (OpenCV, Tk, torch: a segmentation fault or an abort) cannot be caught,
  but faulthandler still prints the Python stack of every thread at the moment of the crash, to
  the terminal (or to logs/crash.log when there is no terminal).

Each report starts with the Python and library versions and the open project, which is what is
usually needed to reproduce it.

Author: Isam Balghari
"""

import faulthandler
import gc
import logging
import os
import platform
import sys
import threading
import traceback
from datetime import datetime

CRASH_LOG = os.path.join("logs", "crash.log")

_fault_file = None  # Kept open for the whole session: faulthandler writes to it at crash time


def environment() -> str:
    """One line with the versions and the open project, for the top of a report."""
    parts = [f"Python {sys.version.split()[0]}", platform.platform()]
    for name in ("numpy", "cv2", "torch", "customtkinter"):
        module = sys.modules.get(name)
        if module is not None:
            parts.append(f"{name} {getattr(module, '__version__', '?')}")
    try:
        from core import session
        project = session.current_project()
        if project:
            parts.append(f"project {project}")
    except Exception:  # The report must not fail because of the report
        pass
    return " | ".join(parts)


def report(exc_type, exc, tb, where: str) -> str:
    """Logs an exception with its traceback and returns the text that was written."""
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    message = (f"Unhandled error in {where} (thread {threading.current_thread().name})\n"
               f"{environment()}\n{text}")
    logging.getLogger("crash").error(message)
    try:
        os.makedirs(os.path.dirname(CRASH_LOG), exist_ok=True)
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n{message}\n")
    except OSError:
        pass
    return message


def install() -> None:
    """Installs the handlers for Python exceptions and C-level crashes. Call once, early."""
    global _fault_file

    def on_main(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        report(exc_type, exc, tb, "the main program")

    def on_thread(args):
        if args.exc_type is SystemExit:
            return
        report(args.exc_type, args.exc_value, args.exc_traceback,
               f"thread {args.thread.name if args.thread else '?'}")

    sys.excepthook = on_main
    threading.excepthook = on_thread

    # C-level crashes: the terminal shows the stacks when there is one; otherwise the crash log
    stream = sys.__stderr__
    if stream is None or not stream.isatty():
        os.makedirs(os.path.dirname(CRASH_LOG), exist_ok=True)
        _fault_file = open(CRASH_LOG, "a", encoding="utf-8")
        _fault_file.write(f"\n=== Session {datetime.now():%Y-%m-%d %H:%M:%S} | {environment()} ===\n")
        _fault_file.flush()
        stream = _fault_file
    faulthandler.enable(file=stream, all_threads=True)


def collect_on_ui_thread(root, every_ms: int = 250, full_every: int = 20) -> None:
    """
    Runs Python's garbage collector on the UI thread only.

    Tk objects (fonts, images, variables) delete themselves with a Tk call when they are collected.
    The cycle collector normally runs in whichever thread happens to be allocating, which during
    tracking is the worker thread, and a Tk call from there crashes Tk (a segmentation fault or bus
    error in Font.__del__, seen while tracking). So automatic collection is turned off and done
    here instead: the young objects every `every_ms`, everything every `full_every` ticks.
    """
    if getattr(root, "_gc_on_ui_thread", False):
        return  # Already running for this window
    root._gc_on_ui_thread = True
    gc.disable()
    ticks = {"n": 0}

    def tick():
        ticks["n"] += 1
        gc.collect() if ticks["n"] % full_every == 0 else gc.collect(0)
        root.after(every_ms, tick)

    root.after(every_ms, tick)


def install_tk(root) -> None:
    """Tk catches exceptions raised in its callbacks and prints them where they are easily lost.
    Route them through the same report, and tell the user something went wrong. Also keeps
    garbage collection (and so the deletion of Tk objects) on the UI thread."""
    collect_on_ui_thread(root)

    def on_callback(exc_type, exc, tb):
        report(exc_type, exc, tb, "a window callback")
        try:
            from tkinter import messagebox
            messagebox.showerror("Error", f"{exc_type.__name__}: {exc}\n\n"
                                          f"The details are in the terminal and in {CRASH_LOG}.")
        except Exception:
            pass

    root.report_callback_exception = on_callback
