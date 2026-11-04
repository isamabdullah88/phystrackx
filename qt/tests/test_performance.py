"""
Speed of the start, as counts of work rather than seconds, so the tests do not depend on the machine: a trial
that draws its frame four times does four times the work on any computer. (tests/perf_report.py measures the
seconds, on each OS, in CI.)

- A video is drawn once when it opens, a project twice (its first frame, which sizes the picture that its saved
  boxes are fitted to, then its saved frame). Opening one decoded and uploaded up to four times, about 25 ms
  each in a real window: also the proxy becoming ready, and the saved frame again after the seek bar's signal.
- Reopening a video reads what the app noted about it (its size and rate, beside its proxy), not the file: no
  ffmpeg process, and the full-size source is not opened and decoded just to learn its size. About 80 ms each.
- The plots' warm-up thread (matplotlib, scipy) never holds the window up for long: the event loop turns
  all through it.

    uv run python tests/test_performance.py
"""

import collections
import contextlib
import json
import os
import shutil
import subprocess
import sys

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from phystrack_qt import video_source  # noqa: E402
from phystrack_qt.main_window import MainWindow  # noqa: E402
from phystrack_qt.video_source import VideoSource  # noqa: E402
from phystrack_qt.video_view import VideoView  # noqa: E402
from test_tracking import make_clip  # noqa: E402


@contextlib.contextmanager
def counting(*targets):
    """Counts the calls of (class, method name) pairs while the block runs, by 'Class.name'. `counts.args` has, for
    each, the whole-number argument of every call (for _show and frame: which frame)."""
    counts = collections.Counter()
    counts.args = collections.defaultdict(list)
    saved = []

    def wrap(cls, name):
        real = getattr(cls, name)
        key = f"{cls.__name__}.{name}"

        def counted(*args, **kwargs):
            counts[key] += 1
            counts.args[key].append(next((a for a in args[1:] if isinstance(a, int)), None))
            return real(*args, **kwargs)

        saved.append((cls, name, real))
        setattr(cls, name, counted)

    for cls, name in targets:
        wrap(cls, name)
    try:
        yield counts
    finally:
        for cls, name, real in saved:
            setattr(cls, name, real)


def close(window) -> None:
    window._dirty = False
    window.close()


def test_a_trial_is_not_drawn_more_than_it_needs() -> None:
    clip = make_clip()
    first = h.window()
    first.load_video(clip)
    h.check("the proxy is made (a restart finds it there)", h.pump(lambda: first.source.has_proxy, 60))
    first.seek.setValue(30)
    project = os.path.join(h.WORK, "perf_frame30.phystrack")
    h.check("a project at frame 30 is saved", first.save_project_file(project))
    close(first)

    draws = ((MainWindow, "_show"), (VideoSource, "frame"), (VideoView, "show_frame"))
    shown = "MainWindow._show"
    video = h.window()
    with counting(*draws) as n:
        video.load_video(clip)
        h.pump(timeout=0.2)   # A draw asked for by a signal comes on the turns after
    h.check("a video is drawn once: one decode, one upload, of the first frame",
            n["MainWindow._show"] == 1 and n["VideoSource.frame"] == 1 and n["VideoView.show_frame"] == 1
            and n.args["MainWindow._show"] == [0], f"{dict(n)} {dict(n.args)}")
    close(video)

    opened = h.window()
    with counting(*draws) as n:
        h.check("the project opens", opened.open_project_file(project))
        h.pump(timeout=0.2)
    h.check("a project is drawn twice: its first frame, then its saved frame (and not again on the next turns)",
            n[shown] == 2 and n["VideoSource.frame"] == 2 and n["VideoView.show_frame"] == 2
            and n.args[shown] == [0, 30], f"{dict(n)} {dict(n.args)}")
    h.check("...and that frame is the one shown", opened.seek.value() == 30 and "frame 30" in opened.frame_label.text(),
            f"{opened.seek.value()} {opened.frame_label.text()!r}")
    close(opened)

    # A video with no proxy yet: drawn from the source at once, and again when its proxy is made (the redraw stays)
    fresh = os.path.join(h.WORK, "perf_fresh.mp4")
    shutil.copy(clip, fresh)
    later = h.window()
    with counting(*draws) as n:
        later.load_video(fresh)
        h.check("a video with no proxy yet is drawn at once, from the source", n["MainWindow._show"] == 1,
                str(dict(n)))
        h.check("...and again when its proxy is ready", h.pump(lambda: later.source.has_proxy, 60)
                and h.pump(lambda: n["MainWindow._show"] == 2, 5), str(dict(n)))
    close(later)


def test_reopening_a_video_reads_the_notes_not_the_file() -> None:
    clip = os.path.join(h.WORK, "perf_notes.mp4")
    shutil.copy(make_clip(), clip)   # Its own copy: the test changes its modification time
    cache = os.path.join(h.WORK, "cache")
    first = VideoSource(cache)
    h.check("the first load opens the clip", first.load(clip))
    h.check("...and makes its proxy", h.pump(lambda: first.has_proxy, 60))
    notes = video_source.info_path(cache, clip)
    h.check("...and notes its size and rate beside the proxy", os.path.isfile(notes), notes)

    probes, readers = [], []
    real_probe, real_reader = video_source.probe_timing, video_source.VideoReader

    class Counting(real_reader):
        def __init__(self, path: str) -> None:
            readers.append(path)
            super().__init__(path)

    def counting_probe(path: str):
        probes.append(path)
        return real_probe(path)

    def load_again():
        probes.clear()
        readers.clear()
        video_source.probe_timing, video_source.VideoReader = counting_probe, Counting
        try:
            source = VideoSource(cache)
            return source, source.load(clip)
        finally:
            video_source.probe_timing, video_source.VideoReader = real_probe, real_reader

    second, loaded = load_again()
    h.check("the second load works, on the proxy", loaded and second.has_proxy, str(second.proxy_path))
    h.check("...with no ffmpeg process", probes == [], str(probes))
    h.check("...and the full-size source not opened: only the proxy is",
            readers == [second.proxy_path], str(readers))
    h.check("...and it knows what the first load did: size, rate, frames",
            second.size == first.size and second.timing == first.timing and second.fcount == first.fcount,
            f"{second.size} {second.timing} {second.fcount} / {first.size} {first.timing} {first.fcount}")

    with open(notes, "w", encoding="utf-8") as f:
        f.write("{ not json")
    third, loaded = load_again()
    h.check("notes that cannot be read are ignored: the file is read, as the first time",
            loaded and probes == [clip] and clip in readers and third.size == first.size, f"{probes} {readers}")
    h.check("...and noted again", video_source.read_info(cache, clip) is not None)

    stat = os.stat(clip)
    os.utime(clip, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))   # The file changed
    fourth, loaded = load_again()
    h.check("a changed file is read again, not taken from the notes", loaded and probes == [clip], f"{probes}")
    h.pump(lambda: fourth.has_proxy, 60)   # (its proxy is made again: the key follows the file)
    os.remove(clip)
    fifth, loaded = load_again()
    h.check("a file that is gone fails as it did: notes do not hide it", not loaded)


WARM_UP_GAPS = """
import json, threading, time
import harness as h
h.app()
from PySide6.QtCore import QElapsedTimer, QTimer
from phystrack_qt import plot_warmup
gaps, clock = [], QElapsedTimer()
clock.start()
ticker = QTimer()
ticker.timeout.connect(lambda: gaps.append(clock.restart()))
ticker.start(5)
plot_warmup.start()
thread = next(t for t in threading.enumerate() if t.name == "plot warm-up")
began = time.time()
while thread.is_alive() and time.time() - began < 120:
    h.app().processEvents()
    time.sleep(0.001)
print("RESULT " + json.dumps([max(gaps), len(gaps), round(time.time() - began, 2), thread.is_alive()]))
"""

WARM_UP_GAP_LIMIT_MS = 1000   # About 50 ms here; a stall of the old kind (10 s) or a lock held across an import is far over


def test_the_warm_up_does_not_hold_the_window_up() -> None:
    """The warm-up thread imports matplotlib and scipy and draws a figure: seconds of Python beside the window. The event
    loop must keep turning through it (a 5 ms ticker counts the turns), in a fresh interpreter so that every import
    is really made."""
    done = subprocess.run([sys.executable, "-c", WARM_UP_GAPS], cwd=os.path.dirname(os.path.abspath(__file__)),
                          capture_output=True, text=True, timeout=300)
    lines = [line for line in done.stdout.splitlines() if line.startswith("RESULT ")]
    longest, ticks, seconds, alive = json.loads(lines[-1][len("RESULT "):]) if lines else (None, 0, 0, True)
    h.check("the warm-up finishes", lines and not alive, f"{seconds} s {done.stderr[-300:]}")
    h.check(f"the longest gap between the event loop's turns is under {WARM_UP_GAP_LIMIT_MS} ms",
            longest is not None and longest < WARM_UP_GAP_LIMIT_MS, f"{longest} ms over {seconds} s, {ticks} ticks")


if __name__ == "__main__":
    h.app()
    for test in (test_a_trial_is_not_drawn_more_than_it_needs, test_reopening_a_video_reads_the_notes_not_the_file,
                 test_the_warm_up_does_not_hold_the_window_up):
        print(test.__name__)
        test()
    h.finish()
