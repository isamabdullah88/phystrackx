"""
The event history, revert, many windows, and the agent tools through the bridge (as MCP and ptx.py
call them: from another thread, while the app runs), including Space stopping the agent.

    ~/.venvs/phystrackx-qt/bin/python tests/test_agent.py      (PHYSTRACK_QT_SHOW=1 to watch)
"""

import os
import shutil
import threading

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from phystrack_qt import project_file, windows  # noqa: E402
from phystrack_qt.agent import bridge, specs  # noqa: E402
from test_tracking import RADIUS, ball_path, make_clip  # noqa: E402


def call(name: str, args: dict | None = None, timeout: float = 120) -> dict:
    """A tool call from another thread (as the bridge's HTTP threads make them), with the event
    loop running here meanwhile."""
    box = {}
    thread = threading.Thread(target=lambda: box.setdefault("out", bridge.call(name, args or {})))
    thread.start()
    h.pump(lambda: "out" in box, timeout)
    thread.join(1)
    return box.get("out", {"error": "test: no answer"})


def setup_window():
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    return w


def test_history_and_revert() -> None:
    w = setup_window()
    h.check("opening is the first event", [e.op for e in w.history.events] == ["open"])
    w._trim_marks = [5, 80]
    w._apply_trim()
    w.start_axis()
    w._place_axes(QPointF(100, 400))
    w.start_ruler()
    w.ruler.set_length(50, "cm")
    w.apply_ruler()
    h.pump(timeout=0.5)   # Changes are committed after a short pause
    ops = [e.op for e in w.history.events]
    h.check("trim, axes and ruler are events", ops == ["open", "trim", "axes", "ruler"], str(ops))
    h.check("the history panel lists them", w.history_panel.count() == len(ops))
    w.history.flush()
    rows = w.history.since(0)
    h.check("rows are compact [n, who, op, text...]", rows[1][:3] == [2, "u", "trim"], str(rows[1]))

    # Back to the trim: the axes and ruler go, and the revert is an event itself
    h.check("reverting to #2 works", w.revert_to(2))
    h.check("the axes and ruler are gone", w.axes is None and w.ruler is None)
    h.check("the trim stays", w.trim == (5, 80), str(w.trim))
    last = w.history.events[-1]
    h.check("the revert is logged", last.op == "revert" and last.params == {"to": 2})
    h.check("the undone events are marked", [e.undone for e in w.history.events] ==
            [False, False, True, True, False])
    # Forward again by reverting to the ruler event
    h.check("reverting forward works", w.revert_to(4))
    h.check("the axes and ruler are back", w.axes is not None and w.ruler is not None and
            w.ruler.real_length == 50)
    h.check("going forward un-greys what it brings back (only the first revert is undone)",
            [e.undone for e in w.history.events] == [False, False, False, False, True, False],
            str([e.undone for e in w.history.events]))
    # A click on a row reverts too
    item = w.history_panel.item(1)
    w.history_panel.itemClicked.emit(item)
    h.check("a click on an event goes back to it", w.ruler is None and w.history.events[-1].op == "revert")
    # A drag is one event, not one per move
    n = len(w.history.events)
    for x in range(100, 140, 5):
        w._place_axes(QPointF(x, 400))
    h.pump(timeout=0.5)
    h.check("many quick changes make one event", len(w.history.events) == n + 1,
            f"{len(w.history.events) - n} events")
    w._dirty = False
    w.close()


def test_windows() -> None:
    a, b = h.window(), h.window()
    h.check("each window has its own id", a.wid != b.wid and windows.get(a.wid) is a)
    h.check("the id is in the title", f"[{b.wid}]" in b.windowTitle(), b.windowTitle())
    c = windows.new_window(show=False)
    h.check("New Window adds a window", windows.get(c.wid) is c)
    for w in (a, b, c):
        w.close()
    h.check("closed windows are forgotten", all(windows.get(w.wid) is None for w in (a, b, c)))


def test_tools() -> None:
    port = bridge.start()
    h.check("the bridge starts", port is not None)
    src = setup_window()
    # Trial X, by the tools: trim, ruler, axes, ball, track, plots, save
    x0, y0 = ball_path(5)
    r = call("trim", {"w": src.wid, "start": 5, "end": 85})
    h.check("trim", r.get("ok", {}).get("trim") == [5, 85], str(r))
    r = call("ruler", {"p1": [500, 100], "p2": [500, 400], "length": 50, "unit": "cm"})
    h.check("ruler", r.get("ok", {}).get("len") == 50 and r["ok"]["px"] == 300.0, str(r))
    r = call("axes", {"x": 60, "y": 460})
    h.check("axes", "ev" in r.get("ok", {}), str(r))
    pad = RADIUS + 6
    r = call("mark", {"box": [x0 - pad, y0 - pad, 2 * pad, 2 * pad], "frame": 5})
    h.check("mark", r.get("ok", {}).get("n") == 1 and r["ok"]["frame"] == 5, str(r))
    corrected_box = [x0 - pad + 1, y0 - pad + 1, 2 * pad, 2 * pad]
    r = call("set_object_selection", {"n": 1, "box": corrected_box, "frame": 5})
    h.check("the agent can select and correct an object's tracking box",
            r.get("ok", {}).get("selected") == 1 and r["ok"].get("marked_frame") == 5 and
            all(abs(a - b) <= 0.05 + 1e-9 for a, b in zip(r["ok"].get("box", []), corrected_box)), str(r))   # Boxes come back rounded to 0.1 px
    h.check("corrected selection is marked for retracking",
            src.objects[0].changed and src._selected_object() is src.objects[0], str(r))
    r = call("quick_look", {"n": 1, "frame": 5})
    quick = r.get("ok", {})
    h.check("quick_look returns an image crop and selection metadata",
            quick.get("selection_source") == "marked at frame 5" and
            quick.get("image", "").startswith("data:image/jpeg;base64,") and
            "selection_image" not in quick and quick.get("width", 0) < src.source.size[0], str(r)[:300])
    r = call("quick_look", {"n": 1, "frame": 5, "selection": True})
    quick_pair = r.get("ok", {})
    h.check("quick_look selection comparison has a separate transparent PNG mask",
            quick_pair.get("image", "").startswith("data:image/jpeg;base64,") and
            quick_pair.get("selection_image", "").startswith("data:image/png;base64,"), str(r)[:300])
    r = call("mark", {"box": [1, 2, 3]})
    h.check("a bad argument says what is expected", "box must be box [x, y, w, h]" in r.get("error", ""),
            str(r))
    r = call("track", {"method": "offline"}, timeout=180)
    h.check("track waits and reports each object", r.get("ok", {}).get("objects", [{}])[0].get("found", 0) > 50,
            str(r))
    r = call("plots", {"kinds": ["y"], "model": "drag"}, timeout=120)
    fits = r.get("ok", {}).get("fits", [])
    h.check("plots wait for the fit (done, or failed with a reason)", fits and fits[0]["model"] == "drag"
            and ("r2" in fits[0] or "error" in fits[0]) and "fitting" not in fits[0], str(r))
    r = call("save_plots")
    h.check("save_plots names its files", any(f.endswith(".png") for f in r.get("ok", {}).get("files", [])),
            str(r))
    r = call("export_csv")
    h.check("export_csv", r.get("ok", {}).get("file", "").endswith(".csv"), str(r))
    r = call("state")
    s = r.get("ok", {})
    h.check("state is compact", s.get("trim") == [5, 85] and s["objects"][0]["tracked"][0] == 5 and
            len(str(s)) < 800, f"{len(str(s))} chars")
    r = call("history", {"since": 0})
    who = {row[1] for row in r.get("ok", [])[1:]}
    h.check("the agent's events are marked as its own", who == {"a"}, str(r.get("ok"))[:300])
    rec = call("recipe", {"src": src.wid}).get("ok", {})
    names = [s[0] for s in rec.get("steps", [])]
    h.check("the recipe is the work, in order", names == ["copy_setup", "track", "plots", "save_plots",
                                                          "export_csv"], str(rec))

    # Tracking again: nothing to do when nothing changed; a correction is tracked from, keeping
    # the track before it, and then left alone; the plots of the old track are not reported
    r = call("track")
    h.check("track with nothing changed does nothing", "nothing to track" in r.get("ok", {}).get("note", ""),
            str(r))
    obj = src.objects[0]
    before = {f: b for f, b in obj.boxes.items() if f < 40}
    src.seek.setValue(40)
    h.pump(timeout=0.1)
    src._show(40)
    bx, by = ball_path(40)
    from PySide6.QtCore import QRectF
    src._object_dragged(obj, QRectF(bx - pad, by - pad, 2 * pad, 2 * pad))
    r = call("track", timeout=180)
    h.check("a correction is tracked from where it was made",
            all(obj.boxes.get(f) == b for f, b in before.items()) and max(obj.boxes) >= 80, str(r))
    fits = call("state").get("ok", {}).get("fits")
    h.check("the plots of the old track are closed, and not reported",
            not src.plot_windows() and not isinstance(fits, list), f"open {len(src.plot_windows())}, fits {fits}")
    r = call("track")
    h.check("the corrected track is then left alone", "nothing to track" in r.get("ok", {}).get("note", ""),
            str(r))

    # Trial Y: another video, the recipe run on it
    other = os.path.join(h.WORK, "thrown_ball_trial2.mp4")
    shutil.copy(make_clip(), other)
    r = call("open", {"video": other})
    h.check("open makes a new window and waits for it", r.get("ok", {}).get("w") not in (None, src.wid), str(r))
    dst = windows.get(r.get("ok", {}).get("w"))
    r = call("run_recipe", {"src": src.wid}, timeout=300)
    out = r.get("ok", {})
    first = (out.get("done") or [out.get("check")])[0] or [None, None, None]
    h.check("run_recipe runs steps and returns their results", first[1] == "copy_setup" and
            "ruler" in (first[2] if len(first) > 2 and isinstance(first[2], dict) else out.get("result", {})),
            str(r))
    h.check("the setup is copied", dst.ruler is not None and dst.ruler.real_length == 50 and
            dst.axes is not None and len(dst.objects) == 1, str(r))
    if "check" in out:   # A check stopped it: go on from where it says, as an agent would
        r = call("run_recipe", {"src": src.wid, "start": out["next"]}, timeout=300)
        out = r.get("ok", {})
    h.check("the recipe finishes", out.get("ok") is True or "check" in out, str(r))
    h.check("the new trial is tracked", any(o.boxes for o in dst.objects))
    h.check("copy_setup is one agent event", [e.op for e in dst.history.events].count("copy_setup") >= 1 and
            all(e.who == "agent" for e in dst.history.events if e.op == "copy_setup"))

    # Space stops the agent; its calls are refused until it resumes, which says what the user did
    windows.AGENT.last = __import__("time").time()   # The agent counts as working just now
    dst.activateWindow()   # Space is a window shortcut: the window the user is in
    h.pump(lambda: dst.isActiveWindow(), 2)
    QTest.keyClick(dst, Qt.Key.Key_Space)
    h.check("Space stops a working agent", windows.AGENT.stopped)
    r = call("trim", {"start": 1, "end": 50})
    h.check("calls are refused while stopped", "stopped" in r, str(r))
    h.check("reading is still allowed", "ok" in call("state"))
    dst._trim_marks = [2, 70]
    dst._apply_trim()
    h.pump(timeout=0.5)
    r = call("resume")
    changes = r.get("ok", {}).get("user_changes", {})
    h.check("resume lists the user's changes", dst.wid in changes and changes[dst.wid][0][2] == "trim",
            str(r))
    h.check("calls work again after resume", "ok" in call("seek", {"n": 10}))

    # Space while a track runs: the call reports the stop (not a track that merely ended early),
    # however fast the track winds down
    box = {}
    thread = threading.Thread(target=lambda: box.setdefault("out", bridge.call("track", {"method": "blob"})))
    thread.start()
    h.pump(lambda: dst.job is not None or "out" in box, 60)
    if dst.job is not None:
        dst._space()
        h.pump(lambda: "out" in box, 60)
        h.check("Space during a track is reported as stopped", "stopped" in box.get("out", {}), str(box))
    else:
        print("  (the track ended before Space could be pressed: stop race not exercised)")
    thread.join(5)
    call("resume")

    # Space between an agent's calls (it is thinking, or done): it stops the agent, and still plays
    h.pump(lambda: dst.job is None, 30)   # The stopped track winds down first (no play while tracking)
    dst._pause()
    windows.AGENT.last = __import__("time").time()
    dst._space()
    h.check("Space between agent calls stops the agent and still plays", windows.AGENT.stopped and dst._playing,
            f"stopped {windows.AGENT.stopped}, playing {dst._playing}, job {dst.job}, proxy "
            f"{dst.source.has_proxy}, seek {dst.seek.isEnabled()}, busy {windows.AGENT.busy()}")
    dst._pause()
    call("resume")

    # The Plots button (and P) as the user presses it: clicked passes a bool, which is not kinds
    import phystrack_qt.plot_window as plot_window
    real_choose = plot_window.choose_plots
    plot_window.choose_plots = lambda parent, default=None: ["x"]
    try:
        src.plots_btn.click()
        h.check("the Plots button still opens the chosen plots",
                any(w.kind == "x" for w in src.plot_windows()))
    finally:
        plot_window.choose_plots = real_choose
    for w in (src, dst):
        w._dirty = False
        w.close()


def test_cookbook_in_project() -> None:
    # A trial's saves are kept in its project file: opened later, the project is a source for recipe
    bridge.start()
    w = setup_window()
    w.history.log("save_plots", "Saved plot y of object 1", {"kind": "y", "n": 1, "T": 1.25, "r2": 0.98})
    path = os.path.join(h.WORK, "cookbook trial.phystrack")
    h.check("the project saves", w.save_project_file(path))
    h.check("the saves are in the file", project_file.load(path).get("cookbook") ==
            [["save_plots", {"kind": "y", "n": 1, "T": 1.25, "r2": 0.98}]], str(project_file.load(path).get("cookbook")))
    w._dirty = False
    w.close()   # Its folder has no open window now: the project is opened by its path
    r = call("open", {"video": path})
    wid = r.get("ok", {}).get("w")
    h.check("the project opens in a window", wid is not None, str(r))
    rec = call("recipe", {"src": wid}).get("ok", {})
    h.check("the recipe of a project has its saves", ["save_plots", {}] in rec.get("steps", []) and
            rec.get("source_fits") == {"1y": {"T": 1.25, "r2": 0.98}}, str(rec))
    listing = call("videos").get("ok", {}).get("videos", [])
    h.check("videos lists the project as one", "cookbook trial.phystrack (project)" in listing, str(listing))
    again = call("open", {"video": "cookbook trial.phystrack (project)"})   # The name as listed
    h.check("open takes a project's name as videos lists it", again.get("ok", {}).get("w") == wid, str(again))
    shown = [row for row in call("windows").get("ok", []) if row["w"] == wid]
    h.check("windows says which project a window is", shown and shown[0].get("project") == "cookbook trial.phystrack",
            str(shown))
    windows.get(wid).close()


def test_specs() -> None:
    schema = specs.json_schema(specs.SPECS["mark"][1])
    h.check("schemas mark required parameters", schema["required"] == ["box"])
    h.check("every tool has an implementation", set(specs.SPECS) ==
            set(__import__("phystrack_qt.agent.tools", fromlist=["IMPL"]).IMPL) |
            set(__import__("phystrack_qt.agent.tools", fromlist=["MACROS"]).MACROS))
    size = sum(len(d) + len(str(p)) for d, p, _ in specs.SPECS.values())
    h.check("the tool list stays small", size < 4000, f"{size} chars")


if __name__ == "__main__":
    h.app()
    for test in (test_specs, test_history_and_revert, test_windows, test_tools, test_cookbook_in_project):
        print(test.__name__)
        test()
    h.finish()
