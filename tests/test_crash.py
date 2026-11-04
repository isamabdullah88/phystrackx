"""Crash reporting: exceptions on worker threads are logged with their traceback, and a crash in
C code still prints the Python stack (no window needed, except the garbage-collection check)."""

import os
import subprocess
import sys
import threading

from tests import harness as h
h.setup_env()

from core import crash  # noqa: E402


def test_thread_exception_is_reported():
    crash.install()
    before = os.path.getsize(crash.CRASH_LOG) if os.path.exists(crash.CRASH_LOG) else 0

    def boom():
        raise ValueError("worker failed on purpose")

    t = threading.Thread(target=boom, name="test-worker")
    t.start()
    t.join()
    with open(crash.CRASH_LOG, encoding="utf-8") as f:
        f.seek(before)
        added = f.read()
    h.check("the thread's exception is written to the crash log", "worker failed on purpose" in added,
            added[-200:])
    h.check("the report names the thread", "test-worker" in added)
    h.check("the report has the traceback", "Traceback" in added)
    h.check("the report has the versions", "Python " in added)


def test_native_crash_prints_the_python_stack():
    """A segmentation fault in C code: faulthandler still prints where Python was."""
    code = ("import sys; sys.path.insert(0, '.')\n"
            "from core import crash; crash.install()\n"
            "import ctypes\n"
            "def inside_tracking():\n"
            "    ctypes.string_at(0)\n"
            "inside_tracking()\n")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            cwd=h.RUN_CWD, env=h.child_env(), timeout=60)
    out = result.stderr
    if "Fatal Python error" not in out and os.path.exists(crash.CRASH_LOG):
        with open(crash.CRASH_LOG, encoding="utf-8") as f:
            out = f.read()[-3000:]  # No terminal in the test: the stack goes to the crash log
    h.check("the process ends with a crash", result.returncode != 0, str(result.returncode))
    h.check("the crash prints a fatal error", "Fatal Python error" in out, out[-300:])
    h.check("the crash shows the Python function it was in", "inside_tracking" in out)


def test_garbage_collection_runs_on_the_ui_thread():
    import gc
    import customtkinter as ctk
    root = ctk.CTk()
    crash.collect_on_ui_thread(root)
    crash.collect_on_ui_thread(root)  # A second call must not start a second timer
    h.check("automatic collection is off", not gc.isenabled())
    collected = []
    gc.callbacks.append(lambda phase, info: collected.append(threading.current_thread().name)
                        if phase == "start" else None)
    h.pump(root, timeout=0.8)
    gc.callbacks.clear()
    h.check("collection runs on a timer", len(collected) >= 2, str(len(collected)))
    h.check("every collection runs on the UI thread",
            all(name == threading.main_thread().name for name in collected), str(set(collected)))
    root.destroy()
    gc.enable()


if __name__ == "__main__":
    h.run_tests([test_thread_exception_is_reported, test_native_crash_prints_the_python_stack,
                 test_garbage_collection_runs_on_the_ui_thread])
