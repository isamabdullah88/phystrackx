"""The picture and the overlays use the same geometry, at every zoom, pan and fit (needs a window).

No video: a synthetic frame with two squares at exact places is drawn by Video.show_array, and the
centre of each drawn square is compared with where the overlay transform (ViewTransform.to_canvas)
puts that point of the frame. Rectangles, the ruler, the axes and tracked points all use that
transform, so if it lands on the drawn pixels, they sit on the picture. The errors left are the
rounding of the squares' edges to whole canvas pixels (at most half a pixel).

Both ways of drawing are checked: the proxy's pixels, and a piece of the full-resolution copy
(made here by enlarging the frame three times, with a frame offset as a trim or crop would give).
"""

import cv2
import numpy as np

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from gui.rigid.video_app import NativePart  # noqa: E402

FW, FH = 336, 598
# Two squares, each (x, y, size) in frame pixels: pixel k spans [k, k+1), so the centre is x + size/2
SQUARES = {"magenta": (100, 200, 6, (255, 0, 255)), "green": (250, 80, 6, (0, 255, 0))}


def _frame() -> np.ndarray:
    img = np.full((FH, FW, 3), 144, np.uint8)
    for x, y, s, (b, g, r) in SQUARES.values():
        img[y:y + s, x:x + s] = (b, g, r)
    return img


def _centre(drawn, colour):
    b, g, r = colour
    mask = (drawn[..., 0] == b) & (drawn[..., 1] == g) & (drawn[..., 2] == r)
    if mask.sum() < 4:
        return None
    ys, xs = np.nonzero(mask)
    height, width = mask.shape
    if xs.min() == 0 or ys.min() == 0 or xs.max() == width - 1 or ys.max() == height - 1:
        return None  # Cut by the edge of the picture
    return float(xs.mean()) + 0.5, float(ys.mean()) + 0.5  # Centre of the pixels' cells


def _native_part(frame, view, off_x, off_y, scale=3):
    """The part of a 3x enlarged copy that the view needs, as Video._native_view would cut it."""
    big = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    x0, y0 = max(0, int(np.floor(view.ox))), max(0, int(np.floor(view.oy)))
    x1 = min(FW, int(np.ceil(view.ox + FW / view.zoom)))
    y1 = min(FH, int(np.ceil(view.oy + FH / view.zoom)))
    # The frame is the proxy shifted by (off_x, off_y); the copy holds the proxy at 3x
    nx0, ny0 = round((off_x + x0) * scale), round((off_y + y0) * scale)
    nx1, ny1 = round((off_x + x1) * scale), round((off_y + y1) * scale)
    canvas = np.full((int((FH + off_y + 40) * scale), int((FW + off_x + 40) * scale), 3), 77, np.uint8)
    canvas[int(off_y * scale):int(off_y * scale) + big.shape[0],
           int(off_x * scale):int(off_x * scale) + big.shape[1]] = big
    return NativePart(canvas[ny0:ny1, nx0:nx1], nx0, ny0, float(scale), float(scale), off_x, off_y)


def _check(app, tag, results, native=None) -> None:
    """Draws the frame and adds (error, description) to results for each square that is visible."""
    crop, view = app.plugin_mgr.crop, app.view
    app.videoapp.show_array(_frame(), view, native=native)
    drawn = app.videoapp.drawn
    for name, (x, y, s, colour) in SQUARES.items():
        found = _centre(drawn, colour)
        if found is None:
            continue
        actual = (crop.cropx + found[0], crop.cropy + found[1])
        expected = view.to_canvas(view.origin[0] + x + s / 2, view.origin[1] + y + s / 2)
        err = float(np.hypot(actual[0] - expected[0], actual[1] - expected[1]))
        results.append((err, f"{tag}, {name} square: pixels at ({actual[0]:.2f}, {actual[1]:.2f}), "
                             f"overlays at ({expected[0]:.2f}, {expected[1]:.2f}), "
                             f"zoom {view.zoom:.2f}, fit {view.fit:.3f}, "
                             f"window origin {view.ox:.2f}, {view.oy:.2f}"))


def _report(label, results) -> int:
    """One check for a group: the worst error among its views must be within half a pixel of
    rounding at each edge (1 px)."""
    if not results:
        h.check(f"{label}: some squares were on screen to compare", False)
        return 0
    worst = max(results)
    h.check(f"{label}: the picture and the overlays agree (worst {worst[0]:.2f} px of "
            f"{len(results)} comparisons)", worst[0] <= 1.0, worst[1])
    return len(results)


def test_picture_and_overlays_agree():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root)  # No video: the frame is drawn directly
    root.update()
    crop, view = app.plugin_mgr.crop, app.view
    rng = np.random.default_rng(3)

    def place(window):
        crop.set(FW, FH)
        crop.relayout(*window)
        view.origin, view.fit = (crop.cropx, crop.cropy), crop.fit
        view.configure(view.origin, (FW, FH))
        view.reset()

    total = 0
    for window in ((1130, 654), (1130, 767), (1500, 900), (700, 500)):  # Fits above and below 1
        place(window)
        for zoom in (1.0, 1.7, 2.5, 4.0, 6.0, 8.0):
            proxy, native = [], {(0, 0): [], (17, 23): []}
            for name, (x, y, s, _) in SQUARES.items():
                for step in range(4):
                    view.reset()
                    sx, sy = view.to_canvas(view.origin[0] + x + s / 2, view.origin[1] + y + s / 2)
                    view.zoom_at(sx, sy, zoom)  # Zoom around the square, as Cmd+ does at the pointer
                    if step:
                        view.pan(float(rng.uniform(-30, 30)), float(rng.uniform(-30, 30)))
                    _check(app, "proxy", proxy)
                    if view.zoom * view.fit > 1:
                        for off, bucket in native.items():  # A trimmed or cropped clip is offset
                            _check(app, f"full resolution {off}", bucket,
                                   native=_native_part(_frame(), view, *off))
            label = f"window {window[0]}x{window[1]}, zoom {zoom}"
            total += _report(f"{label}, proxy pixels", proxy)
            for off, bucket in native.items():
                if bucket or zoom * view.fit > 1:
                    total += _report(f"{label}, full-resolution pixels, frame offset {off}", bucket)
    h.check("many views were compared", total > 300, str(total))
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_picture_and_overlays_agree])
