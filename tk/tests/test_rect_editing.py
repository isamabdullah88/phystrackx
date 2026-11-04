"""Rectangle and circle drawing, moving, and resizing on a bare canvas (needs a window)."""

from math import hypot

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
from gui.components.rects.rect import Rect  # noqa: E402
from gui.components.view import ViewTransform  # noqa: E402


_WINDOW = {}


def _root():
    """One window for the module: the app caches button images per process, so a second
    window in the same process fails."""
    if "root" not in _WINDOW:
        root = ctk.CTk()
        root.geometry("700x600")
        root.update()
        _WINDOW["root"] = root
    return _WINDOW["root"]


def _coords(canvas, item):
    return [round(v) for v in canvas.tk.call(canvas._w, "coords", item)]


def test_drawing_is_the_same_at_any_zoom():
    root = _root()
    canvas = ctk.CTkCanvas(root, width=600, height=500)
    canvas.pack()
    h.pump(root, timeout=0.3)
    btn = ctk.CTkButton(root, text="d")
    view = ViewTransform()

    def draw(zoom, start, end, shape="rect"):
        view.reset()
        view.configure((20, 10), (400, 480))
        view.set_zoom(zoom)
        r = Rect(canvas, 600, 500, {"rectangle": btn}, btn, view=view)
        r.shape = shape
        r.drawrect(400, 480, 20, 10)
        s, e = view.to_canvas(*start), view.to_canvas(*end)
        for event, pt in (("<Button-1>", s), ("<B1-Motion>", e), ("<ButtonRelease-1>", e)):
            canvas.event_generate(event, x=int(pt[0]), y=int(pt[1]))
            root.update()
        return r

    r1 = draw(1, (60, 60), (120, 110))
    r4 = draw(4, (60, 60), (120, 110))
    h.check("a box drawn at zoom 4 stores the same position as at zoom 1",
            len(r1.boxes) == 1 and len(r4.boxes) == 1 and
            all(abs(a - b) < 1e-9 for a, b in zip(r1.rects[0].totuple(), r4.rects[0].totuple())))

    r4.refresh()
    expected = [round(v) for v in view.to_canvas(60, 60) + view.to_canvas(120, 110)]
    h.check("refresh puts the box back on the picture at zoom 4",
            _coords(canvas, r4.boxes[0].tkrect) == expected,
            f"{_coords(canvas, r4.boxes[0].tkrect)} vs {expected}")

    rc = draw(1, (300, 200), (330, 200), shape="circle")
    b = rc.boxes[0]
    h.check("circle is stored as a square of its diameter",
            b.shape == "circle" and round(b.pixelrect.width) == 60 and round(b.pixelrect.height) == 60)
    h.check("circle is drawn as an oval", canvas.type(b.tkrect) == "oval")

    tiny = draw(1, (50, 50), (52, 51))
    h.check("a click without a drag stores nothing", len(tiny.boxes) == 0)
    canvas.destroy()


def test_move_and_resize_handle():
    root = _root()
    canvas = ctk.CTkCanvas(root, width=600, height=500)
    canvas.pack()
    h.pump(root, timeout=0.3)
    btn = ctk.CTkButton(root, text="d")
    view = ViewTransform()
    view.configure((20, 10), (400, 480))
    r = Rect(canvas, 600, 500, {"rectangle": btn}, btn, view=view)
    r.drawrect(400, 480, 20, 10)

    def gesture(pts):
        for event, pt in zip(("<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"), pts):
            canvas.event_generate(event, x=int(pt[0]), y=int(pt[1]))
            root.update()

    s, e = view.to_canvas(120, 100), view.to_canvas(200, 180)
    gesture([s, e, e])
    box = r.boxes[0]
    before = (box.pixelrect.xmin, box.pixelrect.ymin)

    c = view.to_canvas(160, 140)  # press inside the box, drag by (+30, +20)
    gesture([c, view.to_canvas(190, 160), view.to_canvas(190, 160)])
    moved = (round(box.pixelrect.xmin - before[0]), round(box.pixelrect.ymin - before[1]))
    h.check("dragging inside a box moves it by the drag distance", moved == (30, 20), str(moved))

    hx, hy = r._handle_point(box)
    gesture([view.to_canvas(hx, hy), view.to_canvas(hx + 40, hy + 30), view.to_canvas(hx + 40, hy + 30)])
    # The box starts 80 px wide, moves right by 30, then the handle adds 40: 120 px. Height 80 + 30.
    h.check("dragging the handle resizes the box",
            round(box.pixelrect.width) == 120 and round(box.pixelrect.height) == 110,
            f"{box.pixelrect.width}x{box.pixelrect.height}")
    canvas.destroy()


if __name__ == "__main__":
    h.run_tests([test_drawing_is_the_same_at_any_zoom, test_move_and_resize_handle])
