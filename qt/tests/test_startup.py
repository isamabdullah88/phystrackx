"""
The start: the event loop turns before the trials open, and between them. Opening a trial decodes video on the
Qt thread (seconds), and while that runs the loop does not turn: the window cannot paint, and macOS cannot
finish bringing the app forward, so its menu bar stays the previous app's until the opening is over. So the
first turn only brings the window forward; the trials open after a short pause, one per turn, and the agent
tools and the assistant start after the last one. The session record is held meanwhile (a quit part-way must
not shrink it), and a trial that fails to open does not stop the rest. And opening a trial does not load the
libraries the plots need (matplotlib and scipy, about 2.5 s): the warm-up thread loads them, and it starts
only after the last trial is open (it would take the interpreter's lock from the trials).

    uv run python tests/test_startup.py
"""

import contextlib
import json
import os
import subprocess
import sys
import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QTimer  # noqa: E402

from phystrack_qt import app, plot_warmup, session, windows  # noqa: E402
from phystrack_qt.agent import bridge  # noqa: E402
from phystrack_qt.agent.session import AgentSession  # noqa: E402
from phystrack_qt.main_window import MainWindow  # noqa: E402


def close_all() -> None:
    """Every window closed, so each test starts alone."""
    for w in list(windows.all_windows().values()):
        w._dirty = False
        w.close()
    for host in windows.hosts():
        host.close()
    h.pump(timeout=0.1)
    windows.closed.clear()


class Turns:
    """Counts the event loop's turns: a zero-interval timer fires once per pass of the loop, and not at all
    while something holds the loop up."""

    def __init__(self) -> None:
        self.count = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(0)

    def _tick(self) -> None:
        self.count += 1

    def stop(self) -> None:
        self.timer.stop()


@contextlib.contextmanager
def recorded(events: list, turns: Turns, bad: tuple = ()):
    """The start's slow and outside parts replaced by recorders, each noting (what, path, window, turns so far)
    in `events`: opening a trial (slow, and failing for the paths in `bad`), the session record's hold and
    release, the agent tools, the assistant."""

    def trial(kind: str):
        def open_it(self, path, *args, **kwargs):
            events.append((kind, path, self, turns.count))
            time.sleep(0.02)   # A slow open: the loop cannot turn meanwhile
            if path in bad:
                raise ValueError(f"cannot open {path}")
        return open_it

    saved = (MainWindow.load_video, MainWindow.open_project_file, bridge.start, AgentSession.warm_up,
             AgentSession.shutdown, session.hold, session.release, os.environ.get("PHYSTRACK_BRIDGE"))
    MainWindow.load_video, MainWindow.open_project_file = trial("video"), trial("project")
    bridge.start = lambda: events.append(("bridge", None, None, turns.count))
    AgentSession.warm_up = lambda self: events.append(("assistant", None, None, turns.count))
    AgentSession.shutdown = lambda self: None
    session.hold = lambda: events.append(("hold", None, None, turns.count))
    session.release = lambda: events.append(("release", None, None, turns.count))
    os.environ.pop("PHYSTRACK_BRIDGE", None)
    try:
        yield
    finally:
        (MainWindow.load_video, MainWindow.open_project_file, bridge.start, AgentSession.warm_up,
         AgentSession.shutdown, session.hold, session.release) = saved[:7]
        if saved[7] is not None:
            os.environ["PHYSTRACK_BRIDGE"] = saved[7]


def test_the_loop_turns_before_and_between_the_trials() -> None:
    close_all()
    turns = Turns()
    events: list[tuple] = []
    try:
        with recorded(events, turns):
            window = windows.new_window()
            files = ["/x/a.mp4", "/x/b.phystrack", "/x/c.mp4"]
            h.pump(timeout=0.1)
            turns_at_start = turns.count
            app.start_at_launch(h.app(), window, files)
            h.check("the first turn opens no trial, and holds the session record",
                    [e[0] for e in events] == ["hold"], str([e[:2] for e in events]))
            done = h.pump(lambda: len(events) == len(files) + 4, 5.0)
            kinds = [e[:2] for e in events]
            h.check("the trials open in order, a project as a project; then the record is released, and the "
                    "tools and the assistant start",
                    done and kinds == [("hold", None), ("video", "/x/a.mp4"), ("project", "/x/b.phystrack"),
                                       ("video", "/x/c.mp4"), ("release", None), ("bridge", None),
                                       ("assistant", None)], str(kinds))
            opened = [e for e in events if e[0] in ("video", "project")]
            h.check("the first trial opens in the first window, each further one in a tab of its own",
                    len(opened) == 3 and opened[0][2] is window and opened[1][2] is not window
                    and opened[2][2] is not opened[1][2] and opened[1][2].host is window.host,
                    str([e[2] for e in opened]))
            h.check("the loop turned before the first trial opened",
                    len(opened) == 3 and opened[0][3] > turns_at_start,
                    f"turns at start {turns_at_start}, at the first trial {opened[0][3] if opened else None}")
            h.check("...and between the trials",
                    len(opened) == 3 and opened[1][3] > opened[0][3] and opened[2][3] > opened[1][3],
                    str([e[3] for e in opened]))
            h.check("...and before the tools and the assistant start",
                    len(events) >= 2 and len(opened) == 3 and events[-2][3] > opened[2][3],
                    str([e[3] for e in events]))
    finally:
        turns.stop()
        close_all()


def test_a_failing_trial_does_not_stop_the_rest() -> None:
    """The failure is reported (Qt prints it), and the later trials, the release and the tools still follow."""
    close_all()
    turns = Turns()
    events: list[tuple] = []
    errors: list[BaseException] = []
    hook = sys.excepthook
    sys.excepthook = lambda kind, value, tb: errors.append(value)
    try:
        with recorded(events, turns, bad=("/x/bad.mp4",)):
            window = windows.new_window()
            app.start_at_launch(h.app(), window, ["/x/a.mp4", "/x/bad.mp4", "/x/c.mp4"])
            done = h.pump(lambda: [e[0] for e in events][-1:] == ["assistant"], 5.0)
            kinds = [e[:2] for e in events]
            h.check("the trial after the failing one still opens, then the release and the assistant",
                    done and kinds == [("hold", None), ("video", "/x/a.mp4"), ("video", "/x/bad.mp4"),
                                       ("video", "/x/c.mp4"), ("release", None), ("bridge", None),
                                       ("assistant", None)], str(kinds))
            h.check("the failure is reported, not hidden", len(errors) == 1 and "bad.mp4" in str(errors[0]),
                    str(errors))
    finally:
        sys.excepthook = hook
        turns.stop()
        close_all()


# Run in a fresh interpreter: the windows of the tests before leave timers that start the warm-up thread, which loads the
# plot libraries in the background, so this process could not tell what the opening itself loaded
OPEN_ALONE = """
import json, sys
import harness as h
h.app()
from phystrack_qt import plot_warmup
plot_warmup._warm = lambda: None   # The warm-up thread would load the libraries a moment after a window is made
loaded = lambda: sorted(name for name in ("matplotlib", "scipy") if name in sys.modules)
window = h.window()
made = loaded()
opened = window.open_project_file(sys.argv[1])
print("RESULT " + json.dumps([opened, window.plots.get("fits", {}).get("r", {}).get("model"), made, loaded()]))
"""


def test_opening_a_project_loads_no_plot_libraries() -> None:
    """A project keeps its plots' settings (a model and a range per kind), but its plots are not opened with it. So
    opening it needs neither matplotlib nor scipy, and the first trial of a start no longer waits for them: on the
    Intel MacBook Pro that was 2.4 s of the 3.5 s the window stood frozen."""
    from test_tracking import make_clip
    close_all()
    first = h.window()
    first.load_video(make_clip())
    h.pump(lambda: first.source.has_proxy, 60)
    first.plots = {"kinds": ["r"], "fits": {"r": {"model": "both_exp", "range": [0.5, 1.5]}}}   # As the projects of a lab session have
    path = os.path.join(h.WORK, "plot_settings.phystrack")
    h.check("a project with plot settings is saved", first.save_project_file(path))
    first._dirty = False
    first.close()
    done = subprocess.run([sys.executable, "-c", OPEN_ALONE, path], cwd=os.path.dirname(os.path.abspath(__file__)),
                          capture_output=True, text=True, timeout=180)
    lines = [line for line in done.stdout.splitlines() if line.startswith("RESULT ")]
    opened, model, made, loaded = json.loads(lines[-1][len("RESULT "):]) if lines else (False, None, None, None)
    h.check("the project opens, its plot settings with it", opened and model == "both_exp",
            f"opened {opened}, model {model} {done.stderr[-300:]}")
    h.check("making the window loads neither matplotlib nor scipy", made == [], str(made))
    h.check("...and neither does opening the project", loaded == [], str(loaded))
    close_all()


def test_the_plot_warm_up_waits_for_the_trials() -> None:
    """The warm-up thread (matplotlib and scipy: seconds of Python) shares the interpreter's one lock with the thread
    that opens the trials. Started by the window's timer in the middle of the opening, it made two trials take 0.85 s
    instead of 0.5 s. It starts after the last trial is open (and still starts)."""
    close_all()
    turns = Turns()
    events: list[tuple] = []
    saved = plot_warmup._warm, plot_warmup._started
    plot_warmup._warm = lambda: events.append(("warm-up", None, None, turns.count))
    try:
        with recorded(events, turns):
            opened = MainWindow.load_video

            def open_with_the_timer_firing(self, path, *args, **kwargs):
                opened(self, path, *args, **kwargs)
                plot_warmup.start()   # What the window's 1.5 s timer does, in the middle of the opening

            MainWindow.load_video = open_with_the_timer_firing
            window = windows.new_window()
            plot_warmup._started = False   # (the timers of earlier tests' windows may have started it)
            app.start_at_launch(h.app(), window, ["/x/a.mp4", "/x/b.mp4"])
            h.pump(lambda: "assistant" in [e[0] for e in events], 5.0)   # The opening is over
            h.pump(lambda: "warm-up" in [e[0] for e in events], 1.0)
            kinds = [e[0] for e in events]
            h.check("the warm-up starts, after the last trial is open and the record released",
                    "warm-up" in kinds and "release" in kinds and kinds.index("warm-up") > kinds.index("release")
                    and kinds.index("release") > max(i for i, k in enumerate(kinds) if k == "video"), str(kinds))
            h.check("...and only once", kinds.count("warm-up") == 1, str(kinds))
    finally:
        plot_warmup._warm, plot_warmup._started = saved
        plot_warmup._held = plot_warmup._wanted = False
        turns.stop()
        close_all()


def test_a_hold_only_delays_the_warm_up() -> None:
    """Releasing a hold that nothing asked the warm-up to start under starts nothing; a start after the release (the window's
    timer, if it fires later) starts it, once."""
    def wait(cond, timeout: float) -> bool:
        """Waits without running the event loop: the timers of the windows made by the tests before call start() too."""
        end = time.time() + timeout
        while not cond() and time.time() < end:
            time.sleep(0.005)
        return cond()

    ran: list[int] = []
    saved = plot_warmup._warm, plot_warmup._started
    plot_warmup._warm = lambda: ran.append(1)
    plot_warmup._started = False
    try:
        plot_warmup.hold()
        plot_warmup.release()
        wait(lambda: False, 0.2)
        h.check("a release with no start asked for starts nothing", ran == [], str(ran))
        plot_warmup.start()
        h.check("a start after the release starts the warm-up", wait(lambda: ran == [1], 2.0), str(ran))
        plot_warmup.start()
        wait(lambda: False, 0.2)
        h.check("...once", ran == [1], str(ran))
    finally:
        plot_warmup._warm, plot_warmup._started = saved
        plot_warmup._held = plot_warmup._wanted = False


if __name__ == "__main__":
    h.app()
    for test in (test_the_loop_turns_before_and_between_the_trials, test_a_failing_trial_does_not_stop_the_rest,
                 test_opening_a_project_loads_no_plot_libraries, test_the_plot_warm_up_waits_for_the_trials,
                 test_a_hold_only_delays_the_warm_up):
        print(test.__name__)
        test()
    h.finish()
