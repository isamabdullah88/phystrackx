"""
How fast the app is on this computer: the start, opening a video or a project, scrubbing, tracking, the plots'
libraries. Prints a table; with --json writes the numbers (for CI, which keeps them per OS and commit), and with
--summary adds the table to a markdown file (GitHub's job summary).

Not a test: it never fails on a number (CI runners are noisy), and a measurement that breaks is reported as an
error beside the others. The tests that count work instead of seconds are in test_performance.py.

    uv run python tests/perf_report.py [--json FILE] [--summary FILE]

Each time is the median of a few runs where a run is cheap. Process-wide costs (the imports, the first window)
are measured in a fresh interpreter, since only the first run in a process pays them.
"""

import argparse
import datetime
import json
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from phystrack_qt import video_source  # noqa: E402
from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402

TESTS = os.path.dirname(os.path.abspath(__file__))

# key, what it measures, unit. The order is the report's.
METRICS = [
    ("import_s", "Import the app (fresh process)", "s"),
    ("window_s", "Make the first window", "s"),
    ("restore_s", "Restore 2 trials, from the first turn of the event loop", "s"),
    ("restore_freeze_ms", "Longest freeze of the window during that restore", "ms"),
    ("first_open_ms", "Open a video never seen, to its first frame", "ms"),
    ("proxy_s", "...and until its proxy is made", "s"),
    ("open_video_ms", "Reopen a video", "ms"),
    ("open_project_ms", "Open a project", "ms"),
    ("scrub_ms", "Show a frame far from the last (scrubbing)", "ms"),
    ("read_fps", "Frames read in a row (playing)", "fps"),
    ("track_fps", "Track an object (NanoTrack)", "fps"),
    ("warm_up_s", "Plots' warm-up: matplotlib, scipy, a first fit and drawing", "s"),
    ("fit_ms", "One curve fit, warm", "ms"),
]

IMPORT = "import time; t = time.perf_counter(); import phystrack_qt.main_window; print('RESULT', time.perf_counter() - t)"

RESTORE = """
import json, sys, time
import harness as h
h.app()
from PySide6.QtCore import QElapsedTimer, QTimer
from phystrack_qt import app, session, windows
from phystrack_qt.agent import bridge
from phystrack_qt.agent.session import AgentSession
bridge.start = lambda: None
AgentSession.warm_up = lambda self: None
AgentSession.shutdown = lambda self: None
began = time.perf_counter()
window = windows.new_window(cache_dir=sys.argv[1])
made = time.perf_counter() - began
gaps, clock = [], QElapsedTimer()
clock.start()
ticker = QTimer()
ticker.timeout.connect(lambda: gaps.append(clock.restart()))
ticker.start(5)
done = []
release = session.release
session.release = lambda: (release(), done.append(time.perf_counter()))
start = time.perf_counter()
app.start_at_launch(h.app(), window, sys.argv[2:])
while not done and time.perf_counter() - start < 120:
    h.app().processEvents()
    time.sleep(0.001)
print("RESULT " + json.dumps({"window_s": made, "restore_s": done[0] - start if done else None, "freeze_ms": max(gaps)}))
"""

WARM_UP = "import time; import harness; from phystrack_qt import plot_warmup; t = time.perf_counter(); " \
          "plot_warmup.warm_now(); print('RESULT', time.perf_counter() - t)"


def run_alone(code: str, *args: str, repeats: int = 1) -> list:
    """Runs `code` in a fresh interpreter `repeats` times; each prints a line 'RESULT <json or number>'."""
    results = []
    for _ in range(repeats):
        done = subprocess.run([sys.executable, "-c", code, *args], cwd=TESTS, capture_output=True, text=True,
                              timeout=600)
        lines = [line for line in done.stdout.splitlines() if line.startswith("RESULT ")]
        if not lines:
            raise RuntimeError(f"no result: {done.stderr[-300:]}")
        results.append(json.loads(lines[-1][len("RESULT "):]))
    return results


def median_ms(samples: list[float]) -> float:
    return statistics.median(samples) * 1000


def measure(name: str, result: dict, errors: dict, function) -> None:
    """Runs function(), which fills `result`; one that breaks is noted in `errors`, not raised."""
    try:
        function()
    except Exception as e:   # A report is no place to stop on: the other numbers still count
        errors[name] = f"{type(e).__name__}: {e}"[:200]


def report() -> dict:
    result: dict = {}
    errors: dict = {}
    clip = make_clip()
    cache = os.path.join(h.WORK, "perf-cache")
    shutil.rmtree(cache, ignore_errors=True)
    h.app()

    def process() -> None:
        result["import_s"] = statistics.median(run_alone(IMPORT, repeats=3))
        result["warm_up_s"] = statistics.median(run_alone(WARM_UP, repeats=2))

    def first_open() -> None:
        opens, proxies = [], []
        for n in range(2):   # Each a copy, so that the file is new to the cache
            copy = os.path.join(h.WORK, f"perf_first_{n}.mp4")
            shutil.copy(clip, copy)
            source = video_source.VideoSource(cache)
            began = time.perf_counter()
            source.load(copy)
            opens.append(time.perf_counter() - began)
            h.pump(lambda: source.has_proxy, 300)
            proxies.append(time.perf_counter() - began)
        result["first_open_ms"], result["proxy_s"] = median_ms(opens), statistics.median(proxies)

    state: dict = {}   # What one step leaves for the next: the window with the video, the saved projects

    def reopen() -> None:
        w = state["window"] = h.window()
        w.load_video(clip)
        h.pump(lambda: w.source.has_proxy, 300)
        times = []
        for _ in range(7):
            began = time.perf_counter()
            w.load_video(clip)
            times.append(time.perf_counter() - began)
        result["open_video_ms"] = median_ms(times)

    def scrubbing() -> None:
        source = state["window"].source
        rng = random.Random(1)
        frames = source.fcount
        times, last = [], 0
        for _ in range(30):
            index = (last + rng.randrange(frames // 3, frames * 2 // 3)) % frames   # Far from the last
            began = time.perf_counter()
            source.frame(index)
            times.append(time.perf_counter() - began)
            last = index
        result["scrub_ms"] = median_ms(times)
        began = time.perf_counter()
        for index in range(frames):
            source.frame(index)
        result["read_fps"] = frames / (time.perf_counter() - began)

    def tracking() -> None:
        w = state["window"]
        w.seek.setValue(0)
        x0, y0 = ball_path(0)
        pad = RADIUS + 6
        w.start_mark()
        drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
        QTest.keyClick(w, Qt.Key.Key_Escape)
        began = time.perf_counter()
        w.toggle_track()
        h.pump(lambda: w.job is None, 300)
        seconds = time.perf_counter() - began
        tracked = len(w.objects[0].boxes) if w.objects else 0
        if not tracked:
            raise RuntimeError("nothing was tracked")
        result["track_fps"] = tracked / seconds

    def saving() -> None:
        w = state["window"]
        state["paths"] = [os.path.join(h.WORK, name) for name in ("perf_a.phystrack", "perf_b.phystrack")]
        for path in state["paths"]:
            if not w.save_project_file(path):
                raise RuntimeError(f"could not save {path}")
        w._dirty = False
        w.close()

    def opening_project() -> None:
        w = h.window()
        times = []
        for _ in range(7):
            began = time.perf_counter()
            w.open_project_file(state["paths"][0])
            times.append(time.perf_counter() - began)
        result["open_project_ms"] = median_ms(times)
        w._dirty = False
        w.close()

    def restoring() -> None:
        once = run_alone(RESTORE, cache, *state["paths"])[0]
        result["window_s"] = once["window_s"]
        result["restore_s"] = once["restore_s"]
        result["restore_freeze_ms"] = once["freeze_ms"]

    def fit() -> None:
        import numpy as np
        from phystrack_qt.analysis import fitting
        t = np.arange(300) / 30
        y = np.cos(3 * t) * np.exp(-0.2 * t)
        fitting.fit_model(t, y, fitting.DEFAULT_MODEL)   # Warm
        times = []
        for _ in range(3):
            began = time.perf_counter()
            fitting.fit_model(t, y, fitting.DEFAULT_MODEL)
            times.append(time.perf_counter() - began)
        result["fit_ms"] = median_ms(times)

    for name, step in (("import_s", process), ("first_open_ms", first_open), ("open_video_ms", reopen),
                       ("scrub_ms", scrubbing), ("track_fps", tracking), ("saving", saving),
                       ("open_project_ms", opening_project), ("restore_s", restoring), ("fit_ms", fit)):
        measure(name, result, errors, step)
    return {"schema": 1, "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commit": os.environ.get("GITHUB_SHA") or git_head(), "run": os.environ.get("GITHUB_RUN_ID"),
            "os": {"Darwin": "macOS"}.get(platform.system(), platform.system()), "machine": platform.machine(),
            "python": platform.python_version(), "cpus": os.cpu_count(),
            "metrics": {key: result.get(key) for key, _, _ in METRICS}, "errors": errors}


def git_head() -> str | None:
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=TESTS, capture_output=True, text=True, timeout=20)
        return done.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def number(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "s":
        return f"{value:.2f} s"
    if unit == "fps":
        return f"{value:.0f} /s"
    return f"{value:.0f} ms"


def table(data: dict) -> str:
    """The report as markdown: a heading with what it ran on, then one row per measurement."""
    head = (f"{data['os']} {data['machine']}, Python {data['python']}, {data['cpus']} CPUs"
            + (f", commit {data['commit'][:7]}" if data.get("commit") else ""))
    lines = [f"## Speed: {head}", "", "| | |", "|---|---:|"]
    for key, label, unit in METRICS:
        lines.append(f"| {label} | {number(data['metrics'].get(key), unit)} |")
    for key, message in data["errors"].items():
        lines.append(f"| ⚠ {key} failed | {message} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", help="write the numbers to this file")
    parser.add_argument("--summary", help="add the table to this markdown file")
    args = parser.parse_args()
    data = report()
    text = table(data)
    print(text)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
