"""
What each agent tool (specs.SPECS) does. Every tool runs on the Qt thread (the bridge sends it
there) and drives the same MainWindow methods the buttons do, so its changes land in the window's
history like the user's, marked as the agent's.

A tool returns a small JSON-able value, or:
- Wait(until, then): the bridge checks `until()` every 0.1 s (on the Qt thread), then returns
  `then()`. For work the app does by itself: opening (the proxy), tracking, fitting.
- Work(job, then): the bridge runs `job()` on its own thread, then `then(result)` on the Qt
  thread. For slow pure work that must not freeze the window: copy_setup's video scans.
Macros (flag "m": run_recipe) run on the bridge's thread and call other tools through it.

QUICK-AND-DIRTY (see docs/AGENT_PLAN.md, "Architecture notes"): tools reach into MainWindow's
private methods (_apply_trim, _add_ruler, ...) rather than a command layer, and attribution is per
window for the whole call (a user edit in that window during a long agent call counts as the
agent's).
"""

import base64
import math
import os
import re

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF

from core.autoruler import snap_ruler
from core.units import parse_length

from .. import windows
from ..autodetect import find_object, outline_relative
from ..project_file import EXTENSION as PROJECT_TYPE
from ..track_methods import BY_KEY
from ..tracked_object import TrackedObject
from . import relocate
from .specs import KINDS, MODELS, SPECS, check_args

VIDEO_TYPES = (".mp4", ".mov", ".m4v", ".avi", ".mkv")
HISTORY_ROWS = 40          # history() sends at most this many rows (the latest)
CHECK_R2 = 0.9             # run_recipe: a fit below this R² stops it
CHECK_T = 0.25             # run_recipe: a period this far (fraction) from the source's stops it
CHECK_LOST = 0.1           # run_recipe: a track that lost this fraction of its frames stops it


class ToolError(Exception):
    """A tool could not do what was asked; the message says what to do instead."""


class Wait:
    def __init__(self, until, then, timeout: float = 900.0) -> None:
        self.until, self.then, self.timeout = until, then, timeout


class Work:
    def __init__(self, job, then) -> None:
        self.job, self.then = job, then


target: str | None = None    # The agent's current window (open and an explicit w set it)
as_user = False              # Test harnesses (bridge /user): the call is the user's, not the agent's
_motion_cache: dict = {}     # copy_setup: a source video's ball-column motion (the slow scan)
IMPL: dict = {}
MACROS: dict = {}


def _tool(name: str):
    def register(fn):
        (MACROS if "m" in SPECS[name][2] else IMPL)[name] = fn
        return fn
    return register


# --- Running -------------------------------------------------------------------------------------
def checked(name: str, args: dict) -> dict:
    try:
        return check_args(name, args)
    except ValueError as e:
        raise ToolError(str(e)) from None


_touched: list = []   # The windows the call being started marked as the agent's (see run)


def run(name: str, args: dict, touched: list | None = None):
    """Runs tool `name` on the Qt thread: its value, or a Wait or Work for the bridge to finish.
    Each window the call works on is marked as the agent's for the whole call (its changes are
    logged as the agent's) and listed in `touched`, for finish() to unmark: per window, counted,
    so calls that overlap do not unmark each other's."""
    global _touched
    _touched = touched if touched is not None else []
    args = checked(name, args)
    fn = IMPL[name]
    if fn.__code__.co_varnames[:1] == ("win",):
        wid = args.pop("w", None)
        # Reading a window (state w=w1) does not make it the one the agent works in; acting does
        reading = "r" in SPECS[name][2]
        win = window(wid, current=not reading) if not as_user else (windows.get(wid) or window(None))
        if not as_user:
            _mark_agent(win)
        return fn(win, **args)
    args.pop("w", None)
    return fn(**args)


def _mark_agent(win) -> None:
    win.history.flush()   # A change the user just made is still theirs
    win.history.agent_calls += 1
    _touched.append(win)


def finish(touched: list | None = None) -> None:
    """After every call: what the agent changed is committed to the histories, as the agent's,
    and the windows it marked are the user's again (unless another agent call still runs there)."""
    for w in windows.all_windows().values():
        w.history.flush()
    for w in touched or []:
        w.history.agent_calls = max(0, w.history.agent_calls - 1)


CURRENT = ("", "cur", "current", "this", "active", "current window")   # Small models write these for w


def window(wid: str | None = None, current: bool = True):
    """The window `wid`, else the agent's current one, else the user's active one. `current`: a
    window named becomes the agent's current one (not when it is only read)."""
    global target
    if wid is not None and wid.strip().lower() in CURRENT:
        wid = None
    if wid is not None:
        win = windows.get(wid)
        if win is None:
            raise ToolError(f"no window {wid}; open: {', '.join(windows.all_windows()) or 'none'}")
        if current:
            target = wid
        return win
    for candidate in (target, windows.active):
        win = windows.get(candidate) if candidate else None
        if win is not None:
            return win
    raise ToolError("no window open: call open")


def other(wid: str):
    """The window `wid`, named as a source (src): the agent's current window stays as it was."""
    win = windows.get(wid)
    if win is None:
        raise ToolError(f"no window {wid}; open: {', '.join(windows.all_windows()) or 'none'}")
    return win


def _video(win):
    if not win.source.path:
        raise ToolError(f"{win.wid} has no video: call open")
    return win


def _ev(win) -> int:
    win.history.flush()
    return win.history.last()


def _r(value, digits: int = 1):
    """Rounded for the agent: floats in lists and dicts too; NaN becomes None."""
    if isinstance(value, float):
        return None if math.isnan(value) else round(value, digits)
    if isinstance(value, (list, tuple)):
        return [_r(v, digits) for v in value]
    if isinstance(value, dict):
        return {k: _r(v, digits) for k, v in value.items()}
    return value


def _name(path: str | None) -> str | None:
    return os.path.basename(path) if path else None


# --- Reading -------------------------------------------------------------------------------------
@_tool("windows")
def tool_windows():
    return [{"w": wid, "video": _name(w.source.path), "ev": w.history.last(),
             **({"project": _name(w.project_path)} if w.project_path else {}),
             **({"cur": True} if wid == (target or windows.active) else {})}
            for wid, w in windows.all_windows().items()]


@_tool("state")
def tool_state(win):
    s = {"w": win.wid, "video": _name(win.source.path)}
    if not win.source.path:
        return s
    s.update(frames=win.source.fcount, fps=round(win.source.measure_fps, 3), frame=win.seek.value(),
             trim=list(win.trim) if win.trim else None)
    if win.job is not None:
        s["tracking"] = True
    if win.ruler is not None:
        r = win.ruler
        s["ruler"] = _r({"p1": [r.p1.x(), r.p1.y()], "p2": [r.p2.x(), r.p2.y()], "px": r.px_length(),
                         "len": r.real_length, "unit": r.unit or None})
    if win.axes is not None:
        p = win.axes.pos()
        s["axes"] = _r({"x": p.x(), "y": p.y(), "rot": win.axes.rotation()}, 2)
    objects = []
    for o in win.objects:
        tracked = sorted(f for f, b in o.boxes.items() if b is not None)
        entry = {"n": o.number, "box": _r(list(o.marked)), "frame": o.marked_frame}
        if o.circle:
            entry["circle"] = True
        if tracked:
            entry["tracked"] = [tracked[0], tracked[-1]]
            entry["lost"] = sum(1 for b in o.boxes.values() if b is None)
            if o.tracked_with:
                entry["by"] = o.tracked_with[0]
        objects.append(entry)
    s["objects"] = objects
    if win.plots.get("kinds"):
        s["plots"] = list(win.plots["kinds"])
    # The fits: of the open plots, else the settings the next plots will use (without the
    # internal anchor of a copied range)
    fits = _fit_summaries(win) or _r({kind: {k: v for k, v in fit.items() if k not in ("from_low", "from_high")}
                                      for kind, fit in (win.plots.get("fits") or {}).items()}, 3)
    if fits:
        s["fits"] = fits
    s["ev"] = win.history.last()
    s["project_saved"] = not win._dirty
    return s


@_tool("history")
def tool_history(win, since: int = 0):
    rows = win.history.since(max(0, since))
    if len(rows) > HISTORY_ROWS:
        return [["...", f"{len(rows) - HISTORY_ROWS} older rows: ask with a higher since"]] + rows[-HISTORY_ROWS:]
    return rows


def _folders() -> list:
    """Folders of the open videos, the agent's current window's first."""
    order = [target, windows.active] + list(windows.all_windows())
    seen = []
    for wid in order:
        w = windows.get(wid) if wid else None
        if w is not None and w.source.path:
            folder = os.path.dirname(os.path.abspath(w.source.path))
            if folder not in seen:
                seen.append(folder)
    return seen


@_tool("videos")
def tool_videos():
    folders = _folders()
    if not folders:
        raise ToolError("no video open yet: open one by its path")
    folder = folders[0]
    open_in = {os.path.abspath(w.source.path): wid for wid, w in windows.all_windows().items()
               if w.source.path}
    out = []
    for name in sorted(os.listdir(folder), key=str.lower):
        if name.lower().endswith(VIDEO_TYPES) and not name.startswith("."):
            wid = open_in.get(os.path.join(folder, name))
            out.append(f"{name} ({wid})" if wid else name)
        elif name.lower().endswith(PROJECT_TYPE) and not name.startswith("."):   # A trial's setup and saves
            out.append(f"{name} (project)")
    return {"folder": os.path.basename(folder), "videos": out}


@_tool("recipe")
def tool_recipe(src: str):
    return recipe(other(src))


def recipe(S) -> dict:
    """The cookbook of window S: tool calls that redo its work on another trial, in the order it
    was done, and what its results were (for run_recipe's checks)."""
    _video(S)
    steps = [["copy_setup", {"src": S.wid}]]
    tracked = [o for o in S.objects if o.boxes]
    if tracked:
        method = tracked[0].tracked_with[0] if tracked[0].tracked_with else S.track_method_used
        steps.append(["track", {"method": method}])
    if S.plots.get("kinds"):
        step = {"kinds": list(S.plots["kinds"])}
        models = {f.get("model") for k, f in (S.plots.get("fits") or {}).items()
                  if k in step["kinds"] and f.get("model")}
        if len(models) == 1:   # Said in the step (copy_setup also brings it, with the fit range)
            step["model"] = models.pop()
        steps.append(["plots", step])
    # The source's fits, per object and plot ("2r" = object 2's r plot). Trials of one experiment
    # should come out alike, so run_recipe checks the new fits against these
    source_fits = {}
    for op, params in S.history.cookbook:   # The saves and exports, in the order they were first done
        if [op, {}] not in steps:
            steps.append([op, {}])
        if op == "save_plots" and "T" in params:
            source_fits[f"{params['n']}{params['kind']}"] = {"T": params["T"], "r2": params.get("r2")}
    for f in _fit_summaries(S):   # Plots open now say it best
        if "T" in f:
            source_fits[f"{f['n']}{f['kind']}"] = {"T": f["T"], "r2": f.get("r2")}
    # No questions here: the steps are the source's work as it was done (a source with no plots or
    # saves has none to repeat), so the agent asks only about a choice the request leaves open
    return {"src": S.wid, "video": _name(S.source.path), "steps": steps,
            **({"source_fits": source_fits} if source_fits else {})}


@_tool("data")
def tool_data(win, n=None, kind="r", points=40):
    series = win._measured()
    if not series:
        raise ToolError("no measured track: it needs the axes and a tracked object")
    numbers = [s[0] for s in series]
    entry = next((s for s in series if n is None or s[0] == n), None)
    if entry is None:
        raise ToolError(f"object {n} has no measured track; tracked: {numbers}")
    if kind not in ("x", "y", "r"):
        raise ToolError("kind must be x, y or r")
    number, _, t, xy = entry
    values = {"x": xy[:, 0], "y": xy[:, 1], "r": np.hypot(xy[:, 0], xy[:, 1])}[kind]
    step = max(1, len(t) // max(2, min(int(points), 400)))
    picked = list(range(0, len(t), step))
    if picked[-1] != len(t) - 1:
        picked.append(len(t) - 1)
    return {"n": number, "kind": kind, "unit": win._unit(),
            "points": [[round(float(t[i]), 3), round(float(values[i]), 2)] for i in picked]}


@_tool("get_video_frame")
def tool_get_video_frame(win, frame=None, region=None):
    _video(win)
    if win.source.reader is None:
        raise ToolError("the video is still loading")
    corrections = []
    index = (win.view.current_frame_index if win.view.current_frame_index is not None else win.seek.value()) \
        if frame is None else int(round(frame))
    if frame is not None and frame != index:
        corrections.append(f"rounded frame {frame} to {index}")
    if index < 0 and index >= -win.source.fcount:
        index += win.source.fcount
        corrections.append(f"interpreted negative frame as {index} from the end")
    bounded_index = min(max(index, 0), win.source.fcount - 1)
    if bounded_index != index:
        corrections.append(f"clamped frame {index} to {bounded_index}")
    index = bounded_index
    image = win.view.current_frame if frame is None else None
    if image is None:
        image = win.source.frame(index)
    height, width = image.shape[:2]
    crop = None
    if region is not None:
        if any(abs(value - round(value)) > 1e-6 for value in region):
            corrections.append("rounded crop coordinates and dimensions to whole pixels")
        x, y, crop_width, crop_height = (int(round(value)) for value in region)
        if crop_width < 0:
            x, crop_width = x + crop_width, -crop_width
            corrections.append("normalized negative crop width")
        if crop_height < 0:
            y, crop_height = y + crop_height, -crop_height
            corrections.append("normalized negative crop height")
        if crop_width == 0 or crop_height == 0:
            raise ToolError("crop width and height must be nonzero; use region=[x, y, width, height]")
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(width, x + crop_width), min(height, y + crop_height)
        if x0 >= x1 or y0 >= y1:
            raise ToolError(f"crop {region} does not overlap the {width} x {height} frame; "
                            "use region=[x, y, width, height] in frame pixels")
        if (x0, y0, x1, y1) != (x, y, x + crop_width, y + crop_height):
            corrections.append(f"clipped crop to frame bounds: {[x0, y0, x1 - x0, y1 - y0]}")
        image = image[y0:y1, x0:x1]
        crop = [x0, y0, x1 - x0, y1 - y0]
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ToolError("could not encode the frame as JPEG")
    data_url = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")
    return {"frame": index, "width": image.shape[1], "height": image.shape[0],
            "frame_width": width, "frame_height": height,
            "region": crop, "mime_type": "image/jpeg", "image": data_url,
            **({"corrected": corrections} if corrections else {})}


@_tool("quick_look")
def tool_quick_look(win, n: int, frame=None, selection=False):
    _video(win)
    obj = next((candidate for candidate in win.objects if candidate.number == n), None)
    if obj is None:
        raise ToolError(f"no object {n}; objects: {[candidate.number for candidate in win.objects] or 'none'}; "
                        "call state for object numbers")
    if win.source.reader is None:
        raise ToolError("the video is still loading")
    index = (win.view.current_frame_index if win.view.current_frame_index is not None else win.seek.value()) \
        if frame is None else frame
    if not 0 <= index < win.source.fcount:
        raise ToolError(f"frame must be 0..{win.source.fcount - 1}")
    selection_source = "tracked"
    if obj.boxes:
        if index not in obj.boxes:
            if index != obj.marked_frame:
                raise ToolError(f"object {n} has no tracked selection at frame {index}; tracked frames are "
                                f"{min(obj.boxes)}..{max(obj.boxes)}. Use a tracked frame or its marked frame "
                                "and set_object_selection")
            box = obj.marked
            selection_source = f"marked at frame {obj.marked_frame}"
        else:
            box = obj.boxes[index]
            if box is None:
                raise ToolError(f"object {n} was lost at frame {index}; try a nearby tracked frame, then "
                                "correct the selection with set_object_selection")
    else:
        box = obj.marked
        selection_source = f"marked at frame {obj.marked_frame}"

    image = win.source.frame(index)
    frame_height, frame_width = image.shape[:2]
    x, y, width, height = box
    padding = max(20, int(round(max(width, height) * 0.75)), (96 - int(max(width, height))) // 2)
    x0 = max(0, int(math.floor(x - padding)))
    y0 = max(0, int(math.floor(y - padding)))
    x1 = min(frame_width, int(math.ceil(x + width + padding)))
    y1 = min(frame_height, int(math.ceil(y + height + padding)))
    if x0 >= x1 or y0 >= y1:
        raise ToolError(f"object {n}'s selection {list(box)} is outside the {frame_width} x {frame_height} frame")
    crop = image[y0:y1, x0:x1].copy()
    left, top = max(0, int(round(x - x0))), max(0, int(round(y - y0)))
    right, bottom = min(crop.shape[1] - 1, int(round(x + width - x0))), \
        min(crop.shape[0] - 1, int(round(y + height - y0)))
    ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ToolError("could not encode Quick Look as JPEG")
    data_url = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")
    result = {"object": n, "frame": index, "selection_box": _r(list(box)),
              "selection_source": selection_source, "region": [x0, y0, x1 - x0, y1 - y0],
              "width": crop.shape[1], "height": crop.shape[0],
              "mime_type": "image/jpeg", "image": data_url}
    if selection:
        mask = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
        if obj.outline:
            points = np.array([[round(x + u * width - x0), round(y + v * height - y0)]
                               for u, v in obj.outline], dtype=np.int32)
            cv2.fillPoly(mask, [points], (255, 255, 255, 255), cv2.LINE_AA)
        elif obj.circle:
            cv2.ellipse(mask, ((left + right) // 2, (top + bottom) // 2),
                        (max(1, (right - left) // 2), max(1, (bottom - top) // 2)), 0, 0, 360,
                        (255, 255, 255, 255), -1, cv2.LINE_AA)
        else:
            cv2.rectangle(mask, (left, top), (right, bottom), (255, 255, 255, 255), -1, cv2.LINE_AA)
        ok, mask_encoded = cv2.imencode(".png", mask)
        if not ok:
            raise ToolError("could not encode selection-only Quick Look as PNG")
        result["selection_image"] = "data:image/png;base64," + base64.b64encode(mask_encoded).decode("ascii")
    return result


@_tool("resume")
def tool_resume():
    changes = windows.AGENT.resume()
    return {"user_changes": changes} if changes else {"user_changes": "none"}


# --- Windows ---------------------------------------------------------------------------------------
def _find_video(video: str) -> str:
    if os.path.isabs(os.path.expanduser(video)):
        path = os.path.expanduser(video)
        if os.path.isfile(path):
            return path
        raise ToolError(f"no file {video}")
    # The name as videos lists it: "trial.phystrack (project)", "trial.mp4 (w2)"
    video = re.sub(r"\s+\((project|w\d+)\)\s*$", "", video.strip())
    for folder in _folders():
        exact = os.path.join(folder, video)
        if os.path.isfile(exact):
            return exact
        # Case forgiven: "air trial 2". Without an extension a video is preferred to its project
        stem, ext = os.path.splitext(video)
        for name in sorted(os.listdir(folder), key=lambda n: n.lower().endswith(PROJECT_TYPE)):
            base, kind = os.path.splitext(name)
            if base.lower() == stem.lower() and name.lower().endswith(VIDEO_TYPES + (PROJECT_TYPE,)) \
                    and (not ext or kind.lower() == ext.lower()):
                return os.path.join(folder, name)
    raise ToolError(f"no video {video!r}: call videos for the names")


@_tool("open")
def tool_open(video: str):
    global target
    path = _find_video(video)
    project = path.endswith(PROJECT_TYPE)
    for wid, w in windows.all_windows().items():   # Open already: that window (a project: its own project)
        shown = w.project_path if project else w.source.path
        if shown and os.path.abspath(shown) == os.path.abspath(path):
            target = wid
            windows.focus(w)
            return {"w": wid, "frames": w.source.fcount, "note": "already open"}
    win = windows.new_window()
    _mark_agent(win)
    ok = win.open_project_file(path) if path.endswith(".phystrack") else win.load_video(path)
    if not ok:
        win.close()
        raise ToolError(f"could not open {video}")
    target = win.wid
    windows.focus(win)
    # A video opens as a new, empty project. Its trial's saved work is in its project files: say
    # so, or a model takes this window as the source and finds no setup to copy
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    projects = [] if project else sorted(
        n for n in os.listdir(os.path.dirname(path))
        if n.lower().endswith(PROJECT_TYPE) and n.lower().startswith(stem) and not n.startswith("."))

    def done():
        out = {"w": win.wid, "frames": win.source.fcount,
               "fps": round(win.source.measure_fps, 3), "ev": _ev(win)}
        if projects:
            out["note"] = f"new empty project; this trial's saved work is in {projects}: open that as a source"
        return out
    return Wait(lambda: win.source.has_proxy, done, timeout=600)


@_tool("revert")
def tool_revert(win, n: int):
    if not win.revert_to(n):
        raise ToolError(f"cannot go back to {n}: events are 1..{win.history.last() - 1}, and not "
                        "while tracking")
    target_event = win.history.events[n - 1]
    return {"to": n, "now": f"{target_event.op}: {target_event.text[:80]}", "ev": _ev(win)}


# --- Setup ---------------------------------------------------------------------------------------
@_tool("copy_setup")
def tool_copy_setup(win, src: str, only=None):
    D = _video(win)
    S = _video(other(src))
    if S is D:
        raise ToolError("src is this window: open the other trial first")
    if D.job is not None:
        raise ToolError("this window is tracking: wait, or stop it")
    numbers = [o.number for o in S.objects]
    if only is not None and not set(only) <= set(numbers):
        raise ToolError(f"{S.wid} has objects {numbers}, not {sorted(set(only) - set(numbers))}")

    def start():
        state = S._project_state()
        if only is not None:   # Only the objects asked for (e.g. the ball, not a marker)
            state["objects"] = [o for o in state["objects"] if o["number"] in only]
        if not state.get("objects") and not state.get("ruler") and not state.get("axes"):
            raise ToolError(f"{S.wid} has no setup to copy")
        args = (state, S.source.proxy_path, S.source.fcount, D.source.proxy_path, D.source.fcount,
                S.source.measure_fps or 30.0, D.source.measure_fps or 30.0, _motion_cache)
        return Work(lambda: relocate.plan_copy(*args), lambda plan: _apply_plan(S, D, plan))

    if S.source.has_proxy and D.source.has_proxy:
        return start()
    return Wait(lambda: S.source.has_proxy and D.source.has_proxy, start, timeout=600)


def _fit_anchors(S, release_frame) -> dict:
    """Each fitted kind's range in S, counted from the end of the initial drop (its low), on the
    object that drops most: {kind: [from, to] s}. Drops last differently from trial to trial (the
    Air trials: 0.5-0.6 s), so a range kept from the trim start fits part of the fall in some.
    When S's track starts after its drop (the video shows the release earlier: `release_frame`),
    its first "drop" is a later swing; the copy then starts at the new trial's own drop low, which
    fits well on every Air trial (R2 0.997 or more), for as long as S's range lasted."""
    from ..analysis import drop_low
    out = {}
    series = S._measured()
    fps = S.source.measure_fps or 30.0
    for kind, fit in (S.plots.get("fits") or {}).items():
        if kind not in ("x", "y", "r") or not fit.get("range"):
            continue
        lows = []
        for _, _, t, xy in series:
            values = {"x": xy[:, 0], "y": xy[:, 1], "r": np.hypot(xy[:, 0], xy[:, 1])}[kind]
            low = drop_low(t, values)
            if low is not None:
                lows.append((low[0], low[1], low[2], float(t[0])))
        if not lows:
            continue
        _, t_low, t_high, t_first = max(lows)
        lo, hi = fit["range"]
        if release_frame is not None and t_first > release_frame / fps + 0.1:
            out[kind] = {"from_low": [0.0, hi - lo]}
        else:
            out[kind] = {"from_low": [lo - t_low, hi - t_low]}
            if abs(lo - t_high) < 0.05:   # It starts at the release (a model of the whole motion, as gas)
                out[kind]["from_high"] = True
    return out


def _apply_plan(S, D, plan: dict) -> dict:
    if D.job is not None:
        raise ToolError("this window started tracking meanwhile")
    release = (plan["scores"].get("drop_frames") or [None])[0]
    for kind, anchor in _fit_anchors(S, release).items():   # Fit ranges, from the drop
        if kind in (plan["plots"].get("fits") or {}):
            plan["plots"]["fits"][kind].update(anchor)
    state = {"trim": plan["trim"], "frame": plan["frame"], "axes": plan["axes"],
             "ruler": plan["ruler"], "objects": plan["objects"], "plots": plan["plots"],
             "picture": list(D.view.picture.pixmap().size().toTuple())}
    D.history.paused = True   # One event for the whole copy
    try:
        D._pause()
        D._clear_setup()
        D.seek.setRange(0, max(0, D.source.fcount - 1))
        D._apply_state(state)
    finally:
        D.history.paused = False
    D._close_stale_plots()   # Plots of the setup that was replaced
    D._dirty = True
    D._title()
    windows.focus(D)
    D.statusBar().showMessage(f"Setup copied from {S.wid}: check the ruler, axes and ball"
                              + (f" ({'; '.join(plan['warn'])})" if plan["warn"] else ""))
    D.history.log("copy_setup", f"Copied the setup of {S.wid} ({_name(S.source.path)})",
                  {"src": S.wid, "offset": plan["offset"], "scores": plan["scores"]})
    sc = plan["scores"]
    out = {"trim": plan["trim"], "frame": plan["frame"], "offset": plan["offset"]}
    if plan.get("trim_to_end"):   # Said, so the end that moved to this video's end is no surprise
        out["trim_to_end"] = True
    if plan["ruler"]:   # Its length in pixels here and in the source: a zoom shows as a difference
        out["ruler"] = {"px": round(D.ruler.px_length(), 1), "src_px": round(S.ruler.px_length(), 1),
                        "match": sc.get("ruler")}
    if plan["axes"]:
        out["axes"] = {"match": sc.get("axes")}
    out["objects"] = [{"n": o["number"], "frame": o["marked_frame"], "match": sc.get(f"object{o['number']}")}
                      for o in plan["objects"]]
    if plan["warn"]:
        out["warn"] = plan["warn"]
    out["ev"] = _ev(D)
    return out


@_tool("trim")
def tool_trim(win, start: int, end: int):
    _video(win)
    last = win.source.fcount - 1
    if not 0 <= start < end <= last:
        raise ToolError(f"need 0 <= start < end <= {last}")
    win._trim_marks = [start, end]
    win._apply_trim()
    return {"trim": [start, end], "ev": _ev(win)}


@_tool("ruler")
def tool_ruler(win, p1=None, p2=None, length=None, unit=None, auto=False):
    _video(win)
    if win.ruler is None:
        if p1 is None or p2 is None:
            raise ToolError("no ruler yet: give p1 and p2 (its ends)")
        win._add_ruler(QPointF(*p1), QPointF(*p2))
        win._touch("ruler")
    elif p1 is not None or p2 is not None:
        r = win.ruler
        win.ruler.set_ends(QPointF(*p1) if p1 else QPointF(r.p1), QPointF(*p2) if p2 else QPointF(r.p2))
    if auto:
        frame = win.source.frame(win.seek.value())
        r = win.ruler
        try:
            q1, q2 = snap_ruler(frame, (r.p1.x(), r.p1.y()), (r.p2.x(), r.p2.y()), side="left",
                                half_width=15)
        except ValueError as e:
            raise ToolError(f"auto: {e}") from None
        r.snap_to(q1, q2)
    if length is not None:
        if unit is None and win.ruler.unit is None:
            raise ToolError("give the unit too (e.g. cm)")
        try:
            parse_length(f"{length} {unit or win.ruler.unit}")
        except ValueError as e:
            raise ToolError(str(e)) from None
        win.ruler.set_length(float(length), unit or win.ruler.unit)
    r = win.ruler
    return _r({"p1": [r.p1.x(), r.p1.y()], "p2": [r.p2.x(), r.p2.y()], "px": r.px_length(),
               "len": r.real_length, "unit": r.unit or None}) | {"ev": _ev(win)}


@_tool("axes")
def tool_axes(win, x: float | None = None, y: float | None = None, rot: float | None = None,
              auto: bool = False, axis: str | None = None):
    _video(win)
    if axis not in (None, "x", "y"):
        raise ToolError("axis must be x or y")
    if win.axes is None:
        if x is None or y is None:
            raise ToolError("no axes yet: give the origin x, y")
        size = win.view.picture.boundingRect()
        win.axes = win._make_axes(0.3 * min(size.width(), size.height()))
    if x is not None or y is not None:
        p = win.axes.pos()
        win.axes.setPos(QPointF(p.x() if x is None else x, p.y() if y is None else y))
    if rot is not None:
        win.axes.setRotation(rot)
    win._touch("axes")
    out = {}
    if auto:
        try:
            which, origin, rotation = win._find_axis_line(axis)
        except ValueError as e:
            raise ToolError(f"auto: {e}") from None
        win.axes.snap_to(origin, rotation)
        out["snapped"] = which
    p = win.axes.pos()
    return {"x": round(p.x(), 1), "y": round(p.y(), 1), "rot": round(win.axes.rotation(), 2)} \
        | out | {"ev": _ev(win)}


@_tool("mark")
def tool_mark(win, box, frame=None, circle=False, auto=False):
    _video(win)
    if win.job is not None:
        raise ToolError("tracking: wait for it to end")
    if frame is not None:
        _seek(win, frame)
    f = win.seek.value()
    x, y, w, h = box
    pw, ph = win.view.picture.pixmap().size().toTuple()
    if w < 3 or h < 3 or x < 0 or y < 0 or x + w > pw or y + h > ph:
        raise ToolError(f"box must be inside the picture ({pw} x {ph}) and at least 3 px wide")
    outline = None
    if auto:
        try:
            found = find_object(win.source.frame(f), (x, y, w, h), win.tolerance.value())
        except ValueError as e:
            raise ToolError(f"auto: {e}") from None
        x, y, w, h = found["bbox"]
        outline = outline_relative(found["points"], found["bbox"])
    obj = TrackedObject(win._next_number(), QRectF(x, y, w, h), f, win.view.picture, bool(circle), outline)
    obj.on_move = win._object_dragged
    win.objects.append(obj)
    win._refresh_objects(select=obj)
    win.statusBar().showMessage(f"Object {obj.number} marked on frame {f}")
    win._touch("mark", {"n": obj.number})
    win._show(f)
    return {"n": obj.number, "box": _r([x, y, w, h]), "frame": f, "ev": _ev(win)}


@_tool("set_object_selection")
def tool_set_object_selection(win, n: int, box=None, frame=None):
    _video(win)
    if win.job is not None:
        raise ToolError("tracking is in progress; wait for it to end before changing a selection")
    obj = next((candidate for candidate in win.objects if candidate.number == n), None)
    if obj is None:
        raise ToolError(f"no object {n}; objects: {[candidate.number for candidate in win.objects] or 'none'}; "
                        "call state to see object numbers")
    if box is not None:
        x, y, width, height = box
        frame_width, frame_height = win.view.picture.pixmap().size().toTuple()
        if width < 3 or height < 3 or x < 0 or y < 0 or x + width > frame_width or y + height > frame_height:
            raise ToolError(f"box must be inside the picture ({frame_width} x {frame_height}) and at least "
                            "3 px wide and high; use [x, y, width, height]")
    frame_index = frame
    if box is not None or frame is not None:
        if frame_index is None:
            frame_index = win.view.current_frame_index
        if frame_index is None:
            frame_index = win.seek.value()
        if not 0 <= frame_index < win.source.fcount:
            raise ToolError(f"frame must be 0..{win.source.fcount - 1}")
        _seek(win, frame_index)
    win.object_list.setCurrentRow(win.objects.index(obj))
    if box is not None:
        rect = QRectF(x, y, width, height)
        obj.rect.setRect(rect)
        if not obj.boxes:
            obj.marked_frame = frame_index
        win._object_dragged(obj, rect)
        win._refresh_objects(select=obj)
    rect = obj.rect.rect()
    out = {"selected": n, "frame": frame_index if frame_index is not None else win.seek.value(),
           "box": _r([rect.x(), rect.y(), rect.width(), rect.height()]),
           "marked_frame": obj.marked_frame, "restart_frame": obj.restart_frame,
           "changed": obj.changed}
    if box is not None:
        out["ev"] = _ev(win)
    return out


@_tool("delete_points")
def tool_delete_points(win, n: int, start: int, end: int | None = None):
    """Drops object n's tracked points on frames start..end (inclusive; end defaults to start),
    e.g. where the ball is hidden behind the stopper. They become gaps (as if lost), so plots, fits
    and exports leave them out; revert undoes it."""
    obj = next((o for o in win.objects if o.number == n), None)
    if obj is None:
        raise ToolError(f"no object {n}; objects: {[o.number for o in win.objects]}")
    if win.job is not None:
        raise ToolError("tracking: wait for it to end")
    end = start if end is None else end
    frames = [f for f in obj.boxes if start <= f <= end and obj.boxes[f] is not None]
    for f in frames:
        obj.boxes[f] = None
    obj.draw_trail()
    win._after_objects_change(f"Deleted {len(frames)} points of object {n} ({start}..{end})")
    return {"deleted": len(frames), "frames": [start, end], "ev": _ev(win)}


@_tool("remove")
def tool_remove(win, n: int):
    obj = next((o for o in win.objects if o.number == n), None)
    if obj is None:
        raise ToolError(f"no object {n}; objects: {[o.number for o in win.objects]}")
    if win.job is not None:
        raise ToolError("tracking: wait for it to end")
    obj.remove()
    win.objects.remove(obj)
    win._after_objects_change(f"Removed object {n}")
    return {"removed": n, "objects": [o.number for o in win.objects], "ev": _ev(win)}


def _seek(win, n: int) -> int:
    win._pause()   # Playback would move on from here (and fight a track), as the buttons pause it
    n = min(max(int(n), win.seek.minimum()), win.seek.maximum())
    win.seek.setValue(n)
    win._show(n)   # At once, not when the seek bar's draw comes round
    return n


@_tool("seek")
def tool_seek(win, n: int):
    _video(win)
    return {"frame": _seek(win, n)}


# --- Tracking, plots, files ----------------------------------------------------------------------
@_tool("track")
def tool_track(win, method=None):
    _video(win)
    if not win.objects:
        raise ToolError("no objects: call mark or copy_setup")
    if win.job is not None:
        raise ToolError("already tracking")
    method_asked = method is not None
    if method is None:
        runs = [o.tracked_with[0] for o in win.objects if o.tracked_with]
        method = runs[0] if runs else win.track_method
    if method not in BY_KEY:
        raise ToolError(f"method must be one of {', '.join(BY_KEY)}")

    # Only what needs it is tracked: an object that is new, was moved or resized, or was stopped
    # part-way, or every object when another method is asked for. One that is tracked and
    # unchanged keeps its track (a correction the user tracked from is not undone).
    # Each object is tracked from the frame it was marked on: one run per start frame (an
    # object marked mid-fall must not start from where the ball was before the drop), and one
    # the user corrected part-way (moved its tracked box) goes on from that frame.
    # QUICK-AND-DIRTY: MainWindow.start_track runs every object on one start frame, so each run
    # briefly gives it only that frame's objects.
    groups: dict = {}
    for o in win.objects:
        redo = method_asked and o.tracked_with and o.tracked_with[0] != method
        if not (o.changed or not o.boxes or redo):
            continue
        frame = o.restart_frame if o.restart_frame is not None and o.boxes and not redo else o.marked_frame
        groups.setdefault(frame, []).append(o)
    order = sorted(groups)
    ran, secs, ended = [], [], []

    def report():
        per = []
        for o in ran:   # Each object run: how much of it was found
            found = sum(1 for b in o.boxes.values() if b is not None)
            entry = {"n": o.number, "found": found, "lost": len(o.boxes) - found}
            if not o.boxes:
                entry["not_run"] = True   # The run ended before it came to this object
            per.append(entry)
        if not per:
            return {"note": "nothing to track: every object is tracked so already", "ev": _ev(win)}
        return {"secs": round(sum(secs), 1), "completed": all(ended), "objects": per, "ev": _ev(win)}

    def run(i: int):
        if i >= len(order):
            return report()
        frame = order[i]
        _seek(win, frame)
        everyone = win.objects
        win.objects = groups[frame]
        try:
            win.start_track(method, win.track_options.get(method))
        finally:
            win.objects = everyone
        if win.job is None:   # Nothing to do for these (tracked so already), or no room
            return run(i + 1)
        win.agent_track = True   # Space stops it
        ran.extend(win._job_objects)

        def after():
            secs.append((win.last_track or {}).get("s") or 0.0)
            ended.append(bool((win.last_track or {}).get("completed")))
            return run(i + 1)
        return Wait(lambda: win.job is None, after)

    if win.source.has_proxy:
        return run(0)
    return Wait(lambda: win.source.has_proxy, lambda: run(0), timeout=600)


def _fit_summaries(win) -> list:
    """The fits of the open plots that show their object's data now (a stale one is left out)."""
    keys = win._data_keys()
    out = []
    for w in win.plot_windows():
        if w.fit_panel is not None and keys.get(w.number) == getattr(w, "data_key", None):
            out.append({"n": w.number, "kind": w.kind, **_r(w.fit_panel.summary(), 4)})
    return out


def _fits_done(win) -> bool:
    return all(not w.fit_panel.fitting() for w in win.plot_windows() if w.fit_panel is not None)


@_tool("plots")
def tool_plots(win, kinds=None, model=None, range=None):
    _video(win)
    kinds = kinds or win.plots.get("kinds") or ["r"]
    bad = [k for k in kinds if k not in KINDS]
    if bad:
        raise ToolError(f"unknown kinds {bad}; kinds: {' '.join(KINDS)}")
    if model is not None and model not in MODELS:
        raise ToolError(f"unknown model; models: {', '.join(MODELS)}")
    if range is not None and not range[0] < range[1]:
        raise ToolError("range must be [t0, t1] with t0 < t1 (seconds)")
    if win.axes is None or not win._measured():
        raise ToolError("plots need the axes and a tracked object: call axes / track first")
    fits = win.plots.setdefault("fits", {})
    for kind in kinds:
        if kind in ("x", "y", "r") and (model or range):   # The kinds with a fit panel
            fit = fits.setdefault(kind, {"model": model or "damped_linear", "range": None})
            if model:
                fit["model"] = model
            if range:
                fit["range"] = [float(range[0]), float(range[1])]
                fit.pop("from_low", None)   # A range given wins over one copied from a trial
                fit.pop("from_high", None)
    for kind in list(fits):    # A model given without a range keeps the plot's own range
        if fits[kind].get("range") is None:
            fits[kind].pop("range", None)
    win._close_stale_plots()   # A plot of data tracked again is redrawn, not reused
    win.show_plots(kinds)      # Applies the settings, and logs the event

    def report():
        out = {"fits": _fit_summaries(win)}
        warn = []
        for w in win.plot_windows():   # Ranges cut to the data, said rather than done silently
            fit = fits.get(w.kind) or {}
            if w.fit_panel is not None and fit.get("range"):
                (lo, hi), (plo, phi) = fit["range"], w.fit_panel.range
                moved_lo, moved_hi = abs(lo - plo) > 1e-3, abs(hi - phi) > 1e-3
                if moved_lo or moved_hi:
                    which = "end cut to where the data ends" if not moved_lo else \
                        "start moved to where the data starts" if not moved_hi else "range cut to the data"
                    warn.append(f"object {w.number} {w.kind}: fit {which}: [{plo:.3g}, {phi:.3g}] s")
                    fit["range"] = [float(plo), float(phi)]   # The settings say what is shown
        for f in out["fits"]:          # A period with an error larger than itself is no period
            if f.get("T") and f.get("dT") and f["dT"] > 0.5 * abs(f["T"]):
                warn.append(f"object {f['n']} {f['kind']}: no clear period (T {f['T']} ± {f['dT']} s): "
                            "check the fit range (after the drop?) or the model")
        if warn:
            out["warn"] = warn
        out["ev"] = _ev(win)
        return out
    return Wait(lambda: _fits_done(win), report, timeout=120)


@_tool("save_plots")
def tool_save_plots(win):
    _video(win)
    had = bool(win.plot_windows())
    win._close_stale_plots()   # Never saves a plot of data that has changed since
    if not win.plot_windows():
        raise ToolError("the plots were out of date (their data changed): call plots, then save_plots"
                        if had else "no plots open: call plots")

    def save():
        files = []
        for w in win.plot_windows():
            files += [_name(p) for p in w.save_all()]
        return {"files": files, "ev": _ev(win)}
    return Wait(lambda: _fits_done(win), save, timeout=120)


@_tool("export_csv")
def tool_export_csv(win):
    _video(win)
    if win.axes is None or not win._measured():
        raise ToolError("export needs the axes and a tracked object")
    path = win.export_data()
    if path is None:
        raise ToolError("the CSV could not be written")
    return {"file": _name(path), "ev": _ev(win)}


@_tool("save_project")
def tool_save_project(win):
    _video(win)
    if not win.save_project():
        raise ToolError("the project could not be saved")
    return {"file": _name(win.project_path), "ev": _ev(win)}


# --- The recipe, run step by step (on the bridge's thread) --------------------------------------
def _problem(name: str, result: dict, expect: dict) -> str | None:
    """Why a step's result needs a person's look, or None."""
    if not isinstance(result, dict):
        return None
    if name == "copy_setup" and result.get("warn"):
        return "; ".join(result["warn"])
    if name == "track" and "objects" in result:
        if result.get("completed") is False:
            return "tracking ended before the trim's end"
        bad = [f"object {o['n']} " + ("was not tracked" if o.get("not_run") else
                                      f"lost on {o['lost']} of {o['found'] + o['lost']} frames")
               for o in result["objects"] if o["found"] < 10 or o["lost"] > CHECK_LOST * (o["found"] + o["lost"])]
        if bad:
            return "; ".join(bad) + ": check it (move its box, or remove it if not needed)"
    if name == "plots":
        bad = []
        for f in result.get("fits", []):
            e = expect.get(f"{f['n']}{f['kind']}")
            which = f"object {f['n']} {f['kind']}"
            if f.get("error"):
                bad.append(f"{which}: fit failed ({f['error']})")
                continue
            floor = CHECK_R2 if e is None or e.get("r2") is None else min(CHECK_R2, e["r2"] - 0.05)
            if f.get("r2") is not None and f["r2"] < floor:
                bad.append(f"{which}: R2 {f['r2']}, the source's was {e['r2'] if e else '?'}")
            elif e and e.get("T") and (e.get("r2") or 0) >= CHECK_R2 and f.get("T") \
                    and abs(f["T"] - e["T"]) > CHECK_T * e["T"]:
                bad.append(f"{which}: period {f['T']} s, the source's was {e['T']} s")
        bad += [w for w in result.get("warn", []) if "no clear period" in w and w not in bad]
        if bad:
            return "; ".join(bad) + (": check the fit range with plots range=[t0, t1]: start at the "
                                     "drop's low, and end before the motion is disturbed (try ending "
                                     "earlier); or try another model")
    return None


@_tool("run_recipe")
def tool_run_recipe(invoke, src: str, only=None, start: int = 0, w: str | None = None):
    from .bridge import Stopped   # The bridge runs macros; a stop from Space ends this one too
    w = w or target or windows.active   # Every step goes to the window the recipe started on
    if w == src:
        raise ToolError("the current window is src: open the other trial (or give w)")
    rec = invoke("recipe", {"src": src})
    steps, expect = rec["steps"], rec.get("source_fits", {})
    done = []   # [k, tool, its result]: the steps that ran and passed their check
    for k, (name, args) in enumerate(steps):
        if k < start:
            continue
        if w:
            args = {**args, "w": w}
        if only is not None and name == "copy_setup":
            args = {**args, "only": only}
        try:
            result = invoke(name, args)
        except Stopped:   # Space: this step is done again when the agent goes on
            return {"stopped": "the user pressed Space", "done": done, "next": k}
        except ToolError as e:
            return {"done": done, "failed": [k, name, str(e)], "next": k}
        if windows.AGENT.stopped:
            return {"stopped": "the user pressed Space", "done": done, "next": k}
        brief = {key: v for key, v in result.items() if key != "ev"} if isinstance(result, dict) else result
        problem = _problem(name, result, expect)
        if problem:
            # A track must be run again once its problem is fixed; the other steps' results stand
            # (the user or the agent fixes them by hand), so the recipe goes on after them
            return {"done": done, "check": [k, name, problem], "result": brief,
                    "next": k if name == "track" else k + 1}
        done.append([k, name, brief])
    return {"done": done, "ok": True, "steps": len(steps)}
