"""
The in-app assistant with the real local model (not in the test suite: it needs the runner and
the model, and takes a minute or two). Sets up a source trial on the synthetic clip, then asks the
model a question, and to repeat the work on a copy of the clip; questions it asks are answered as
the user would. Prints the conversation, the tool calls and the time each request took.

    ollama serve &   (or let the assistant start it)
    ~/.venvs/phystrackx-qt/bin/python tests/live_assistant.py [model]
"""

import os
import shutil
import sys
import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from phystrack_qt.agent import bridge  # noqa: E402
from phystrack_qt.agent.session import AgentSession  # noqa: E402
from test_agent import call, setup_window  # noqa: E402
from test_tracking import RADIUS, ball_path, make_clip  # noqa: E402


def ask(session, text: str, answers: list, timeout: float = 600.0) -> float:
    """Sends `text`, answers the assistant's questions from `answers` in turn; returns seconds."""
    t0 = time.time()
    start = len(session.transcript)
    session.send(text)
    while time.time() - t0 < timeout:
        h.pump(lambda: session.state in ("idle", "waiting", "stopped"), timeout)
        if session.state == "waiting":
            session.send(answers.pop(0) if answers else "Yes, go ahead.")
            continue
        if session.state in ("idle", "stopped"):
            break
    for kind, line in session.transcript[start:]:
        print(f"    {kind:9} {line[:220]}")
    return time.time() - t0


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else None
    bridge.start()
    src = setup_window()
    x0, y0 = ball_path(5)
    pad = RADIUS + 6
    for name, args in (("trim", {"start": 5, "end": 85}),
                       ("ruler", {"p1": [500, 100], "p2": [500, 400], "length": 50, "unit": "cm"}),
                       ("axes", {"x": 60, "y": 460}),
                       ("mark", {"box": [x0 - pad, y0 - pad, 2 * pad, 2 * pad], "frame": 5}),
                       ("track", {}), ("plots", {"kinds": ["x"], "model": "damped_linear"}),
                       ("save_plots", {}), ("export_csv", {})):
        result = call(name, {"w": src.wid, **args}, timeout=180)
        print(f"  setup {name}: {'ok' if 'ok' in result else result}")
    other = os.path.join(h.WORK, "thrown_ball_live.mp4")
    shutil.copy(make_clip(), other)

    session = AgentSession()
    if model:
        session.llm.model = model
    print(f"model {session.llm.model} at {session.llm.url}")
    secs = ask(session, "Which windows are open, and which video is in each?", [])
    print(f"  -> {secs:.1f} s\n")
    secs = ask(session, f"Do the same things I did in {src.wid} on {other}.",
               ["All of them, and save everything as before."])
    print(f"  -> {secs:.1f} s")
    calls = sum(1 for kind, _ in session.transcript if kind == "tool")
    print(f"tool calls {calls}, model turns {sum(1 for m in session.messages if m['role'] == 'assistant')}")


if __name__ == "__main__":
    h.app()
    main()
