"""
Copying one trial's setup onto another trial's video: where the ruler, the axes, the ball and the
trim are in the new video. Plain numpy and OpenCV (no Qt), so it is tested on the real trials alone.

QUICK-AND-DIRTY (see docs/AGENT_PLAN.md, "Architecture notes"):
- Each placed thing is found again by template matching a patch of the source frame around it
  (ruler ends, axes origin, the ball) in a wide window of the new frame. The camera moved 50-120 px
  and zoomed about 5% between the Air trials; patches are small enough for that. No reference
  library, no Segment Anything (BATCH_TRIALS_PLAN.md step 3 is the robust version).
- The time offset between the trials is the first motion in the ball's column, under where it was
  marked (the drop), found the same way in both videos; the trim and the ball's frame move by it.
- Every match returns a score; below GOOD it is reported as doubtful, so the caller (a person or
  an agent) knows what to check. Nothing here is trusted blindly.
"""

import math

import cv2
import numpy as np

PATCH = 40         # Half-size of a static thing's patch (ruler end, axes origin), proxy pixels
SEARCH = 220       # How far a static thing may have moved between trials, proxy pixels
GOOD = 0.75        # A match scoring below this is reported as doubtful (the Air trials: right
                   # matches scored 0.78-1.0; a non-ball object that was then lost, 0.56-0.66)
DIFF = 25          # Grey levels: a pixel changed between frames by more than this "moved"
COLUMN = 320       # Length of the column watched under the ball, proxy pixels


def _gray(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame


def read_frames(path: str, indices) -> dict:
    """Grey frames at `indices` (those that exist)."""
    cap = cv2.VideoCapture(path)
    out = {}
    try:
        for i in sorted(set(int(i) for i in indices if i >= 0)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if ok:
                out[i] = _gray(frame)
    finally:
        cap.release()
    return out


def relocate(src: np.ndarray, point, dst_frames, half: int = PATCH, search: int = SEARCH,
             around=None) -> tuple:
    """Where the patch of `src` around `point` is in the best of `dst_frames`, searched within
    `search` px of `around` (default: the same place). Returns ((x, y), score in [-1, 1])."""
    x, y = int(round(point[0])), int(round(point[1]))
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x - half), max(0, y - half), min(w, x + half), min(h, y + half)
    template = src[y0:y1, x0:x1]
    cx, cy = (x, y) if around is None else (int(round(around[0])), int(round(around[1])))
    best = ((float(point[0]), float(point[1])), -1.0)
    if template.size == 0 or template.std() < 1:
        return best   # Nothing to match (off the picture, or flat)
    for img in dst_frames:
        H, W = img.shape[:2]
        sx0, sy0 = max(0, cx - (x - x0) - search), max(0, cy - (y - y0) - search)
        sx1, sy1 = min(W, cx + (x1 - x) + search), min(H, cy + (y1 - y) + search)
        region = img[sy0:sy1, sx0:sx1]
        if region.shape[0] < template.shape[0] or region.shape[1] < template.shape[1]:
            continue
        result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(result)
        if score > best[1]:
            best = ((float(sx0 + loc[0] + (point[0] - x0)), float(sy0 + loc[1] + (point[1] - y0))),
                    float(score))
    return best


def column_motion(path: str, box) -> np.ndarray:
    """Per frame, in the column under `box` (x, y, w, h), where the ball falls when it is let go:
    [pixels changed since the previous frame, their mean row]. One pass over the video (2-3 s)."""
    x, y, w, h = box
    cap = cv2.VideoCapture(path)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    x0, x1 = int(max(0, x)), int(min(W, x + w))
    y0 = int(min(H - 2, y + 2 * h))     # Below the hand (and the cloth) that holds the ball
    y1 = int(min(H, y0 + COLUMN))
    out, prev = [], None
    try:
        while cap.grab():
            ok, frame = cap.retrieve()
            if not ok:
                break
            g = cv2.GaussianBlur(_gray(frame[y0:y1, x0:x1]), (3, 3), 0)
            if prev is None:
                out.append((0, -1.0))
            else:
                rows = np.nonzero(cv2.absdiff(g, prev) > DIFF)[0]
                out.append((len(rows), float(rows.mean()) if len(rows) else -1.0))
            prev = g
    finally:
        cap.release()
    return np.array(out, dtype=float).reshape(-1, 2)


def first_motion(motion: np.ndarray, area: float) -> int | None:
    """The drop: the first frame where something about the ball's size starts moving down the
    column and keeps going for three frames (a person or the hand moving about does not). None if
    it never happens."""
    counts, rows = motion[:, 0], motion[:, 1]
    blob = (counts >= 0.3 * area) & (counts <= 8 * area)
    for i in range(len(counts) - 3):
        if blob[i] and blob[i + 1] and blob[i + 2] and rows[i] < rows[i + 1] < rows[i + 2]:
            return i
    return None


def _angle(p1, p2) -> float:
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def plan_copy(src: dict, src_video: str, src_frames: int, dst_video: str, dst_frames: int,
              src_fps: float, dst_fps: float, motion_cache: dict | None = None) -> dict:
    """
    The source setup `src` (a window's _project_state(), with "plots") moved onto the new video.

    Returns {"trim", "ruler", "axes", "objects", "plots", "scores", "warn", "offset"}: the same
    shapes as the state (so the window applies it as a state), plus how good each match was.
    `motion_cache` keeps the source's column motion between calls (it is the slow part).
    """
    warn: list[str] = []
    scores: dict = {}
    objects = src.get("objects") or []
    s_trim = src.get("trim") or [0, src_frames - 1]
    key_frame = int(objects[0]["marked_frame"]) if objects else int(s_trim[0])
    s_img = read_frames(src_video, [key_frame]).get(key_frame)
    if s_img is None:
        raise ValueError(f"cannot read frame {key_frame} of the source video")
    probe = [min(key_frame, dst_frames - 1), dst_frames // 2, dst_frames // 4]
    d_imgs = list(read_frames(dst_video, probe).values())
    shifts = []

    # The ruler: each end found again (so a small zoom is followed too)
    ruler = None
    if src.get("ruler"):
        r = dict(src["ruler"])
        (q1, s1), (q2, s2) = (relocate(s_img, r["p1"], d_imgs), relocate(s_img, r["p2"], d_imgs))
        scores["ruler"] = round(min(s1, s2), 2)
        if min(s1, s2) < GOOD:
            warn.append(f"ruler match {min(s1, s2):.2f}: check its ends")
        shifts += [(q1[0] - r["p1"][0], q1[1] - r["p1"][1]), (q2[0] - r["p2"][0], q2[1] - r["p2"][1])]
        ruler = {**r, "p1": list(q1), "p2": list(q2)}

    # The axes: the origin found again; turned as much as the ruler turned
    axes = None
    if src.get("axes"):
        a = dict(src["axes"])
        q, s = relocate(s_img, (a["x"], a["y"]), d_imgs, half=int(PATCH * 1.5))
        scores["axes"] = round(s, 2)
        if s < GOOD:
            warn.append(f"axes origin match {s:.2f}: check the origin")
        turn = 0.0
        if ruler is not None:
            turn = _angle(ruler["p1"], ruler["p2"]) - _angle(src["ruler"]["p1"], src["ruler"]["p2"])
        axes = {**a, "x": q[0], "y": q[1], "rotation": a["rotation"] + turn}
        shifts.append((q[0] - a["x"], q[1] - a["y"]))
    shift = tuple(np.median(np.array(shifts), axis=0)) if shifts else (0.0, 0.0)

    # When: the drop, in the ball's column, in both videos
    offset, r_src = 0, None
    if objects:
        bx, by, bw, bh = objects[0]["marked"]
        area = bw * bh
        cache = motion_cache if motion_cache is not None else {}
        cache_key = (src_video, tuple(round(v) for v in objects[0]["marked"]))
        if cache_key not in cache:
            cache[cache_key] = column_motion(src_video, (bx, by, bw, bh))
        r_src = first_motion(cache[cache_key], area)
        r_dst = first_motion(column_motion(dst_video, (bx + shift[0], by + shift[1], bw, bh)), area)
        scores["drop_frames"] = [r_src, r_dst]
        if r_src is None or r_dst is None:
            warn.append("no drop found in the ball's column: trim copied as it was, check it")
        else:
            offset = r_dst - r_src
    a0, a1 = int(s_trim[0]) + offset, int(s_trim[1]) + offset
    to_end = int(s_trim[1]) >= src_frames - 1
    if to_end:
        a1 = dst_frames - 1     # The source ran to its end: so does this one
    trim = [max(0, min(a0, dst_frames - 2)), max(1, min(a1, dst_frames - 1))]

    # The objects: each found again on its frame, moved by the offset. The ball is taken just
    # before the drop when the source tracked it there (it is then at the release point; earlier
    # the hand may still be moving it about), else where it was marked
    new_objects = []
    for o in objects:
        f_src, box = int(o["marked_frame"]), o["marked"]
        before = r_src - 2 if r_src is not None else None
        if before is not None and (o.get("boxes") or {}).get(str(before)):
            f_src, box = before, o["boxes"][str(before)]
        bx, by, bw, bh = box
        s_ball = s_img if f_src == key_frame else read_frames(src_video, [f_src]).get(f_src)
        size = max(bw, bh)
        centre = (bx + bw / 2, by + bh / 2)
        best = ((centre[0] + shift[0], centre[1] + shift[1]), -1.0, f_src + offset)
        for f, img in read_frames(dst_video, range(f_src + offset - 2, f_src + offset + 3)).items():
            q, s = relocate(s_ball, centre, [img], half=int(size), search=int(3 * size),
                            around=(centre[0] + shift[0], centre[1] + shift[1]))
            if s > best[1]:
                best = (q, s, f)
        q, s, f_dst = best
        f_dst = max(0, min(int(f_dst), dst_frames - 1))
        scores[f"object{o['number']}"] = round(s, 2)
        if s < GOOD:
            warn.append(f"object {o['number']} match {s:.2f}: check it on frame {f_dst}")
        new_objects.append({"number": o["number"], "circle": o.get("circle", False),
                            "outline": o.get("outline"), "marked_frame": f_dst,
                            "marked": [q[0] - bw / 2, q[1] - bh / 2, bw, bh], "changed": True,
                            "tracked_with": None, "boxes": {}})
    if new_objects:   # Tracking starts at the first object's frame: the trim must include it
        trim[0] = min(trim[0], min(o["marked_frame"] for o in new_objects))

    # The plots: the same kinds and models. The fit range is kept from the end of the initial drop
    # ("from_low", resolved on the new data when its plots open: drops last differently in each
    # trial); until then, at the same time after the trim start, within the video
    plots = {}
    if src.get("plots"):
        plots = {"kinds": list(src["plots"].get("kinds", []))}
        fits = {}
        end = (dst_frames - 1) / dst_fps
        for kind, f in (src["plots"].get("fits") or {}).items():
            if not f.get("range"):
                fits[kind] = {"model": f["model"]}
                continue
            lo, hi = f["range"]
            t0s, t0d = s_trim[0] / src_fps, trim[0] / dst_fps
            fits[kind] = {"model": f["model"], "range": [min(lo - t0s + t0d, end), min(hi - t0s + t0d, end)]}
            if f.get("from_low"):
                fits[kind]["from_low"] = list(f["from_low"])
        plots["fits"] = fits
    return {"trim": trim, "ruler": ruler, "axes": axes, "objects": new_objects, "plots": plots,
            "frame": new_objects[0]["marked_frame"] if new_objects else trim[0],
            "offset": offset, "trim_to_end": to_end, "shift": [round(shift[0], 1), round(shift[1], 1)],
            "scores": scores, "warn": warn}
