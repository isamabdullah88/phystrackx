"""
The agent tools: names, one-line descriptions and parameters. Pure data (no Qt), shared by the app
(tools.py does what they say), the MCP shim (mcp_server.py) and the command line (ptx.py).

Made for small, cheap models (docs/AGENT_PLAN.md, "Tool design"):
- Few tools, one obvious way to do each thing; the usual job ("do for trial Y what I did for
  trial X") is two calls: open, then run_recipe.
- `w` (a window id such as "w2") is optional everywhere: tools act on the agent's current window,
  which `open` sets. Videos are named by file name, never by long paths.
- Results are compact JSON (rounded numbers, no prose); errors say what to do instead.
- Long work (open, copy_setup, track, plots) blocks until it is done: there is no polling to get
  wrong.
- A result that changed something has "ev", the history event it made, for `revert`.
"""

# Parameter types: int, num, str, bool, pt ([x, y] picture pixels, or [t0, t1] seconds),
# box ([x, y, w, h] picture pixels), strs (list of strings). A trailing "?" = optional.
# Flags: "r" = reads only (allowed while the user has stopped the agent), "m" = runs other tools.
KINDS = ["x", "y", "r", "xy", "dx", "dy", "d2x", "d2y"]
MODELS = ["damped", "damped_linear", "damped_exp", "drag", "drag_linear", "both_exp", "gas", "friction"]
METHODS = ["offline", "blob_background", "blob", "nanotrack"]

SPECS = {
    "windows": ("Open windows: id, video, last event; cur = yours.", {}, "r"),
    "videos": ("Videos in the current video's folder, and which window has each open. A trial's project "
               "file (.phystrack, marked project) holds its setup, plots and saves: open it to use that "
               "trial's work as a source.", {}, "r"),
    "state": ("A window's setup: trim, ruler, axes, objects, plots and fits.", {}, "r"),
    "history": ("A window's events after #since: [n, u|a (user|agent), op, text, params].",
                {"since": "int?"}, "r"),
    "recipe": ("Steps that redo window src's work on another trial: [[tool, args], ...].",
               {"src": "str"}, "r"),
    "data": ("An object's measured curve, thinned to about `points` points: [[t s, value], ...] "
             "(kind: x y r; default r and the first object). To see where a drop or a disturbance is.",
             {"n": "int?", "kind": "str?", "points": "int?"}, "r"),
    "get_video_frame": ("See a video frame as an image. Omit frame for the frame currently shown; "
                        "otherwise frame is a zero-based frame index (nearest integer; out-of-range "
                        "values clamp to the nearest available frame). Omit region for the whole frame, "
                        "or give [x, y, width, height] in frame pixels for a crop; partial crops are clipped.",
                        {"frame": "num?", "region": "box?"}, "r"),
    "quick_look": ("Return an unmarked small image crop around object n on frame (default: shown). "
                   "Set selection=true to also return its selection geometry as a separate transparent "
                   "PNG mask; this is the selection shape, not an image segmentation of the object.",
                   {"n": "int", "frame": "int?", "selection": "bool?"}, "r"),
    "resume": ("After the user stopped you (Space): lets you go on. Returns what they changed.", {}, "r"),
    "open": ("Open a video (name from videos, or a path) in a new window, shown to the user; it "
             "becomes your current window. A project file opens that trial's setup and saves, to use "
             "as a source.", {"video": "str"}, ""),
    "run_recipe": ("Do recipe(src) on the current window, step by step, checking each; returns each "
                   "step's result. only: the object numbers to copy (default all). start: the step "
                   "to begin at (0 = first). Stops at a failed check: fix it or ask the user, then "
                   "call again with start=next.", {"src": "str", "only": "ints?", "start": "int?"}, "m"),
    "copy_setup": ("Copy trim, ruler, axes, the objects (only: their numbers; default all) and the "
                   "plot settings from window src, each found again in this video. Returns match "
                   "scores (0-1) and warnings for doubtful ones.", {"src": "str", "only": "ints?"}, ""),
    "revert": ("Go back to event n (logged too; revert to a later n to undo it).", {"n": "int"}, ""),
    "trim": ("Trim to frames start..end.", {"start": "int", "end": "int"}, ""),
    "ruler": ("Place or change the ruler: ends p1, p2; real length and unit (50, cm); auto snaps "
              "the ends to the ruler's ends.",
              {"p1": "pt?", "p2": "pt?", "length": "num?", "unit": "str?", "auto": "bool?"}, ""),
    "axes": ("Place or change the axes: origin x, y; rot in degrees (clockwise). auto turns them "
             "(up to 10 deg) to line up with the nearest straight line (a tube, a track), sliding "
             "the origin onto it; axis: x or y to line up (default: whichever lies along a line).",
             {"x": "num?", "y": "num?", "rot": "num?", "auto": "bool?", "axis": "str?"}, ""),
    "mark": ("Mark an object to track: box on frame (default: the frame shown); auto fits its outline.",
             {"box": "box", "frame": "int?", "circle": "bool?", "auto": "bool?"}, ""),
    "set_object_selection": ("Select object n in the Objects list. Optionally set its selection box "
                              "[x, y, width, height] in frame pixels on frame (default: the frame shown); "
                              "then call track to track again from the corrected selection.",
                              {"n": "int", "box": "box?", "frame": "int?"}, ""),
    "remove": ("Remove object n.", {"n": "int"}, ""),
    "delete_points": ("Drop object n's points on frames start..end (e.g. ball hidden); fits skip them.", {"n": "int", "start": "int", "end": "int?"}, ""),
    "seek": ("Show frame n.", {"n": "int"}, ""),
    "track": ("Track every object from its marked frame to the trim's end; waits. method: "
              + ", ".join(METHODS) + " (default: the one the objects were tracked with, else offline).",
              {"method": "str?"}, ""),
    "plots": ("Open or update plots and their fits; waits for the fits. kinds: " + " ".join(KINDS)
              + "; model: " + ", ".join(MODELS) + "; range: fit range [t0, t1] s.",
              {"kinds": "strs?", "model": "str?", "range": "pt?"}, ""),
    "save_plots": ("Save the open plots (PNG, CSV, fit) next to the video.", {}, ""),
    "export_csv": ("Export the tracked positions (CSV) next to the video.", {}, ""),
    "save_project": ("Save the project next to the video.", {}, ""),
}

ALLOWED_WHEN_STOPPED = {name for name, (_, _, flags) in SPECS.items() if "r" in flags}

INSTRUCTIONS = (
    "PhysTrackX: a video-tracking app, one trial video per window (w1, w2...). Every change is in a "
    "window's history. To repeat the work of trial X on trial Y: open X's project file if it is not "
    "open (a name from videos, marked project), so it is window wX; open(Y), then "
    "run_recipe(src=wX); if it stops at a check, ask the user or fix it, then run_recipe again with "
    "start=next. A result with a \"stopped\" key means the user pressed Space: make no more calls "
    "until they say to go on, then call resume first. Every tool also takes w (a window id; default "
    "your current window). Times are in seconds; T is a period, dT its error. \"warn\" is for "
    "information; act on it only when run_recipe stops.")

_TYPES = {
    "int": {"type": "integer"},
    "num": {"type": "number"},
    "str": {"type": "string"},
    "bool": {"type": "boolean"},
    "pt": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
    "box": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
    "strs": {"type": "array", "items": {"type": "string"}},
    "ints": {"type": "array", "items": {"type": "integer"}},
}


def json_schema(params: dict) -> dict:
    """The JSON schema of a tool's parameters (MCP inputSchema), with the optional window `w`."""
    props = {name: dict(_TYPES[t.rstrip("?")]) for name, t in params.items()}
    props["w"] = {"type": "string", "description": "window id (default: current)"}
    required = [name for name, t in params.items() if not t.endswith("?")]
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def check_args(name: str, args: dict) -> dict:
    """The arguments, checked against the tool's parameters: an unknown or missing one, or one
    of the wrong type, raises ValueError with a message that says what is expected."""
    if name not in SPECS:
        raise ValueError(f"no tool {name!r}; tools: {', '.join(SPECS)}")
    args = dict(args or {})
    if name == "get_video_frame":
        for alias in ("frame_index", "frame_number", "index"):
            if alias in args and "frame" not in args:
                args["frame"] = args.pop(alias)
        for alias in ("crop", "box", "rect"):
            if alias in args and "region" not in args:
                args["region"] = args.pop(alias)
        if "region" not in args and all(key in args for key in ("x", "y", "width", "height")):
            args["region"] = [args.pop("x"), args.pop("y"), args.pop("width"), args.pop("height")]
    params = SPECS[name][1]
    out = {}
    for key, value in (args or {}).items():
        if key == "w":
            if value is not None:
                out["w"] = str(value)
            continue
        if key not in params:
            raise ValueError(f"{name} takes {', '.join(params) or 'nothing'} (and w), not {key!r}")
        if value is None:
            continue
        out[key] = _convert(name, key, params[key].rstrip("?"), value)
    missing = [k for k, t in params.items() if not t.endswith("?") and k not in out]
    if missing:
        raise ValueError(f"{name} needs {', '.join(f'{k} ({params[k]})' for k in missing)}")
    return out


def _convert(tool: str, key: str, kind: str, value):
    bad = ValueError(f"{tool}: {key} must be {kind}" + {"pt": " [a, b]", "box": " [x, y, w, h]",
                                                        "strs": " [\"...\"]", "ints": " [1, 2]"}.get(kind, ""))
    try:
        if kind == "int":
            if isinstance(value, bool) or float(value) != int(float(value)):
                raise bad
            return int(float(value))
        if kind == "num":
            if isinstance(value, bool):
                raise bad
            return float(value)
        if kind == "str":
            return str(value)
        if kind == "bool":
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "y")
            return bool(value)
        if kind in ("pt", "box"):
            n = 2 if kind == "pt" else 4
            if kind == "box" and isinstance(value, dict):
                value = [value.get(k) for k in ("x", "y", "width", "height")]
            if isinstance(value, str):
                value = [v for v in value.replace("[", " ").replace("]", " ").replace(",", " ").split()]
            if len(value) != n:
                raise bad
            return [float(v) for v in value]
        if kind == "strs":
            if isinstance(value, str):
                value = value.replace("[", " ").replace("]", " ").replace(",", " ").replace('"', " ").split()
            return [str(v) for v in value]
        if kind == "ints":
            if isinstance(value, (int, float, str)) and not isinstance(value, bool):
                value = str(value).replace("[", " ").replace("]", " ").replace(",", " ").split()
            out = [int(float(v)) for v in value]
            if not out:
                raise bad
            return out
    except (TypeError, ValueError):
        raise bad from None
    raise bad
