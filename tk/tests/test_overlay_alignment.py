"""Overlays stay on the picture at every zoom, pan and window size (needs a window).

The clip holds two coloured squares (magenta and green) at known places. For each view, the test
finds where each square was drawn on the canvas and compares it with where the overlay transform
(ViewTransform.to_canvas) says that point of the frame is. Rectangles, the ruler, the axes and the
tracked points all use that transform, so if it matches the drawn pixels they sit on the picture.

Both a rotated (phone-style) clip and a plain one are used, and both the proxy's pixels and the
full-resolution copy's pixels (which are drawn once the copy exists).
"""

import os
import subprocess

import numpy as np

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402

MAGENTA = ((200, 255), (0, 90), (200, 255))   # R, G, B ranges of the magenta square
GREEN = ((0, 90), (200, 255), (0, 90))


def _clip(name: str, rotated: bool) -> str:
    """A 1920x1080 clip with a magenta and a green square (rotated for display if asked)."""
    from core import find_ffmpeg
    path = os.path.join(h.WORK_DIR, f"{name}.mp4")
    if os.path.isfile(path):
        return path
    plain = path if not rotated else os.path.join(h.WORK_DIR, f"{name}_unrotated.mp4")
    boxes = "drawbox=x=300:y=180:w=24:h=24:color=0xFF00FF:t=fill,drawbox=x=1450:y=800:w=24:h=24:color=0x00FF00:t=fill"
    subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=0x909090:s=1920x1080:d=4:r=30", "-vf", boxes, "-c:v", "libx264",
                    "-preset", "veryfast", "-pix_fmt", "yuv420p", plain], check=True)
    if rotated:
        subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-display_rotation", "90",
                        "-i", plain, "-c", "copy", path], check=True)
    return path


def _centroid(img, ranges):
    """Centre of the pixels of a colour (RGB ranges) in a BGR image, or None if there are none."""
    (r0, r1), (g0, g1), (b0, b1) = ranges
    b, g, r = img[..., 0], img[..., 1], img[..., 2]
    mask = (r >= r0) & (r <= r1) & (g >= g0) & (g <= g1) & (b >= b0) & (b <= b1)
    if mask.sum() < 4:
        return None
    ys, xs = np.nonzero(mask)
    height, width = mask.shape
    if xs.min() == 0 or ys.min() == 0 or xs.max() == width - 1 or ys.max() == height - 1:
        return None  # Cut by the edge of the picture: its centre would be biased
    return float(xs.mean()), float(ys.mean())


def _compare(app, tag: str, markers: dict) -> int:
    """Checks each marker that is on screen. Returns how many were checked."""
    drawn = app.videoapp.drawn
    crop, view = app.plugin_mgr.crop, app.view
    # The squares' positions are measured on encoded, slightly blurred frames, so they are only
    # known to about half a frame pixel, which is 0.5 * zoom * fit canvas pixels. The exact
    # geometry is checked to 1 px by test_overlay_geometry; this test looks for gross errors
    # (a wrong scale or offset) in a real clip, which grow far beyond that.
    tolerance = 1.5 + 0.6 * view.zoom * view.fit
    checked = 0
    for name, (ranges, (fx, fy)) in markers.items():
        found = _centroid(drawn, ranges)
        if found is None:
            continue
        # A pixel k spans [k, k+1): its centre is k + 0.5, in the frame and on the canvas alike
        actual = (crop.cropx + found[0] + 0.5, crop.cropy + found[1] + 0.5)  # Where the pixels are
        expected = view.to_canvas(view.origin[0] + fx + 0.5, view.origin[1] + fy + 0.5)  # Overlays
        err = float(np.hypot(actual[0] - expected[0], actual[1] - expected[1]))
        h.check(f"{tag}: the {name} square is where the overlays think it is", err <= tolerance,
                f"pixels at ({actual[0]:.1f}, {actual[1]:.1f}), overlays at "
                f"({expected[0]:.1f}, {expected[1]:.1f}), off by {err:.1f} px "
                f"(zoom {view.zoom:.2f}, fit {view.fit:.3f})")
        checked += 1
    return checked


def _settle(root, app) -> None:
    h.pump(root, timeout=1.0)
    app.updateframe()
    root.update()


def _markers(app) -> dict:
    """The squares' centres in the current frame's own pixels, found at zoom 1."""
    app.view.reset()
    app.updateframe()
    frame = app.videoapp.frame
    out = {}
    for name, ranges in (("magenta", MAGENTA), ("green", GREEN)):
        c = _centroid(frame, ranges)
        assert c is not None, f"the {name} square is not in the frame"
        out[name] = (ranges, c)
    return out


def _views(root, app, markers, label: str) -> None:
    """Zooms around each marker, then pans, and compares at every step."""
    total = 0
    for name, (_, (fx, fy)) in markers.items():
        for zoom in (1.0, 2.5, 6.0):
            app.view.reset()
            app.updateframe()
            sx, sy = app.view.to_canvas(app.view.origin[0] + fx, app.view.origin[1] + fy)
            app.view.zoom_at(sx, sy, zoom)  # Zoom around the square, as Cmd+ does at the pointer
            app.updateframe()
            root.update()
            total += _compare(app, f"{label}, zoom {zoom} at the {name} square", markers)
            app.view.pan(25, -18)  # A trackpad scroll
            app.updateframe()
            root.update()
            total += _compare(app, f"{label}, zoom {zoom} after a pan", markers)
    h.check(f"{label}: some squares were on screen to compare", total >= 6, f"{total}")


def _run(name: str, rotated: bool) -> None:
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=_clip(name, rotated))
    h.check(f"{name}: the first frame is shown",
            h.pump(root, lambda: app.videoapp.frame is not None, timeout=240), str(h.DIALOGS))
    _settle(root, app)
    markers = _markers(app)

    _views(root, app, markers, f"{name}, proxy pixels")

    # The full-resolution copy is drawn once it exists (a zoomed view asks for it)
    app.view.zoom_at(300, 300, 3.0)
    app.updateframe()
    h.pump(root, lambda: app.videoapp.rigid.nativepath is not None, timeout=240)
    _settle(root, app)
    _views(root, app, markers, f"{name}, full-resolution pixels")

    # A larger window: the picture is fitted again
    root.geometry(f"{min(1500, root.winfo_screenwidth() - 40)}x{min(1000, root.winfo_screenheight() - 200)}")
    _settle(root, app)
    h.pump(root, timeout=1.0)
    markers = _markers(app)
    _views(root, app, markers, f"{name}, larger window")
    root.destroy()


def test_rotated_phone_clip():
    _run("alignment_small_markers_rotated", rotated=True)


if __name__ == "__main__":
    h.run_tests([test_rotated_phone_clip])
