"""
Imports a project from the Tk app (format 1: no "format" key, "version": 1) into this app's setup.

The Tk app stored positions in pixels of its canvas, which is the picture as it was on screen, so
they are scaled to the video's frame here and land on the same part of the picture. Newer Tk files
say "anchor": "picture" and store frame pixels already; those are taken as they are. Tracked boxes
are fractions of the picture in the Tk file, so they are multiplied out to frame pixels.

The Tk file keeps no tracks, only the boxes marked before tracking, so each object starts from its
box at the trim's start, to be tracked again. Anything with no counterpart here is dropped, not
kept in a Tk-shaped form: the returned "imported" dict names what was "left_out" (the crop, the
measured data and fits, the OCR boxes) and what to "check". This is one-way: nothing writes the Tk
format, the first save writes this app's format next to the video, and the Tk file is left as it was.
"""

from media import VideoReader   # The app's reader, so the size is the one its frames have


def video_size(path: str) -> tuple[int, int] | None:
    """The frame size (width, height) of a video, or None if it cannot be read."""
    try:
        reader = VideoReader(path)
    except IOError:
        return None
    try:
        return reader.width, reader.height
    finally:
        reader.release()


def from_tk(data: dict, size: tuple[int, int]) -> dict:
    """This app's project state for a Tk project, for a video whose frames are size (width, height).
    Sets "imported" to the notes on what was left out."""
    width, height = size
    left_out = []
    check = []

    trim = data.get("trim")
    crop = trim.get("crop") if isinstance(trim, dict) else data.get("crop")
    if crop:
        left_out.append("the crop (this app trims by frame range only)")
    if data.get("data"):
        left_out.append("the measured data and fits (measure them again)")
    if (data.get("rects") or {}).get("ocr"):
        left_out.append("the OCR boxes")
    if (data.get("rects") or {}).get("track"):
        check.append("each object's box is taken to be on the trim's start frame (the Tk file does "
                     "not record the frame it was marked on)")

    def to_frame(point, anchored, canvas):
        """A Tk point (x, y) in frame pixels, from its canvas-pixel position if not anchored."""
        if anchored:
            return [point[0], point[1]]
        return [point[0] * width / canvas[0], point[1] * height / canvas[1]]

    # Older files have no canvas size in every entry; the canvas then is the frame, unscaled
    axes = data.get("axes")
    axes_state = None
    if axes:
        anchored = axes.get("anchor") == "picture"
        canvas = axes.get("canvas") or (width, height)
        x, y = to_frame((axes["ox"], axes["oy"]), anchored, canvas)
        axes_state = {"x": x, "y": y, "rotation": axes["theta"], "length": 0.3 * min(width, height)}

    scale = data.get("scale")
    ruler_state = None
    if scale:
        anchored = scale.get("anchor") == "picture"
        canvas = scale.get("canvas") or (width, height)
        ruler_state = {"p1": to_frame(scale["p1"], anchored, canvas),
                       "p2": to_frame(scale["p2"], anchored, canvas),
                       "real_length": scale.get("real_world_length"), "unit": scale.get("unit")}

    start = trim["start"] if isinstance(trim, dict) else 0
    rects = data.get("rects") or {}
    shapes = rects.get("track_shapes") or []
    objects = []
    for number, rect in enumerate(rects.get("track", []), 1):
        x, y, w, h = rect
        shape = shapes[number - 1] if number <= len(shapes) else "rectangle"  # As the Tk app drew it
        objects.append({"number": number, "circle": shape == "circle", "outline": None,
                        "marked": [x * width, y * height, w * width, h * height],
                        "marked_frame": start, "changed": True, "tracked_with": None, "boxes": {}})

    return {"video": data["video"],
            "picture": [width, height],
            "frame": start,
            "trim": [trim["start"], trim["end"]] if isinstance(trim, dict) else None,
            "axes": axes_state, "ruler": ruler_state, "objects": objects, "plots": {},
            "imported": {"left_out": left_out, "check": check}}
