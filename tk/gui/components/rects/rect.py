from typing import Optional
from dataclasses import dataclass
from math import hypot

import customtkinter as ctk
import tkinter as tk
from core import PixelRect, NormalizedRect
from ..view import ViewTransform
from .label import Labels
from ..buttons import SubmitButton, BinButton


@dataclass
class BoundingBox:
    """Encapsulates canvas graphical ID and spatial coordinates in one place."""
    tkrect: int
    pixelrect: PixelRect
    normrect: NormalizedRect
    shape: str = "rect"  # "rect" or "circle" (a circle's box is its bounding square)


class Rect:
    """Manages interactive bounding-box and circle drawing, selection, moving, and resizing."""
    OUTLINE_DRAWING = "red"
    OUTLINE_PENDING = "magenta"
    OUTLINE_APPLIED = "#2ecc71"
    LINE_WIDTH = 2
    MIN_BOX_PX = 4  # Smaller drags are treated as clicks and not stored
    HANDLE_TOL_PX = 10  # Screen distance that counts as hitting the resize handle
    HANDLE_SIZE_PX = 5
    BIN_BUTTON_SIZE = 30
    APPLY_BUTTON_SIZE = 50

    def __init__(self, canvas, vwidth, vheight, button_list, active_button,
                 view: Optional[ViewTransform] = None):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.view = view or ViewTransform()

        self.shape = "rect"  # Shape used for the next box drawn
        self.on_apply = None  # Optional callback after Apply (used to leave marking mode)

        self._session = False  # True from Mark until Apply
        self._mode = None      # "draw", "move", "resize", or None
        self._rcoords = None
        self._ctkbox = 0
        self._drawshape = "rect"
        self._drag_start = None
        self._drag_geom = None
        self._handle_id = None

        self.selected: Optional[BoundingBox] = None
        self.boxes: list[BoundingBox] = []

        self.labels = Labels(self.canvas)

        self.bin_button = BinButton(self.canvas, command=self.clearrect, size=self.BIN_BUTTON_SIZE,
                                tooltip="Delete Last Rect")

        self.apply_button = SubmitButton(self.canvas, command=self.onapply, size=self.APPLY_BUTTON_SIZE,
                                     tooltip="Apply Rects")

        self.button_list = button_list
        self.active_button = active_button

    # ---------------------------------------------------------------------------------------------
    # Drawing helpers
    def _outline(self) -> str:
        return self.OUTLINE_PENDING if self._session else self.OUTLINE_APPLIED

    def _canvas_bbox(self, prect: PixelRect) -> tuple[float, float, float, float]:
        """On-screen bounding box of a stored (unzoomed, crop-relative) pixel rectangle."""
        ox0, oy0 = self.view.origin
        x1, y1 = ox0 + prect.xmin, oy0 + prect.ymin
        x2, y2 = x1 + prect.width, y1 + prect.height
        cx1, cy1 = self.view.to_canvas(x1, y1)
        cx2, cy2 = self.view.to_canvas(x2, y2)
        return min(cx1, cx2), min(cy1, cy2), max(cx1, cx2), max(cy1, cy2)

    def _create_item(self, shape: str, bbox, outline: str) -> int:
        create = self.canvas.create_oval if shape == "circle" else self.canvas.create_rectangle
        return create(*bbox, outline=outline, width=self.LINE_WIDTH)

    def refresh(self) -> None:
        """Redraws every box and the handle at the current zoom and pan."""
        for box in self.boxes:
            self.canvas.delete(box.tkrect)
            box.tkrect = self._create_item(box.shape, self._canvas_bbox(box.pixelrect), self._outline())
        self._draw_handle()

    # ---------------------------------------------------------------------------------------------
    # Geometry, in unzoomed base coordinates (absolute canvas positions at zoom 1)
    def _geom(self, box: BoundingBox) -> tuple:
        """(x1, y1, x2, y2) for a rectangle, or (cx, cy, r) for a circle."""
        ox0, oy0 = self.view.origin
        p = box.pixelrect
        x1, y1 = ox0 + p.xmin, oy0 + p.ymin
        if box.shape == "circle":
            r = p.width / 2
            return x1 + r, y1 + r, r
        return x1, y1, x1 + p.width, y1 + p.height

    def _set_geom(self, box: BoundingBox, geom: tuple) -> None:
        """Stores new base geometry and redraws the box."""
        ox0, oy0 = self.view.origin
        if box.shape == "circle":
            cx, cy, r = geom
            prect = PixelRect(cx - r - ox0, cy - r - oy0, 2 * r, 2 * r)
        else:
            x1, y1, x2, y2 = geom
            prect = PixelRect(min(x1, x2) - ox0, min(y1, y2) - oy0,
                              abs(x2 - x1), abs(y2 - y1))
        box.pixelrect = prect
        box.normrect = prect.pix2norm(*self.view.size)
        self.canvas.coords(box.tkrect, *self._canvas_bbox(prect))

    def _handle_point(self, box: BoundingBox) -> tuple[float, float]:
        g = self._geom(box)
        if box.shape == "circle":
            return g[0] + g[2], g[1]
        return g[2], g[3]

    def _box_at(self, bx: float, by: float) -> Optional[BoundingBox]:
        """Topmost box under a base-coordinate point."""
        for box in reversed(self.boxes):
            g = self._geom(box)
            if box.shape == "circle":
                if hypot(bx - g[0], by - g[1]) <= g[2]:
                    return box
            elif g[0] <= bx <= g[2] and g[1] <= by <= g[3]:
                return box
        return None

    def _tolerance(self) -> float:
        return self.HANDLE_TOL_PX / self.view.zoom

    # ---------------------------------------------------------------------------------------------
    # Selection
    def _select(self, box: Optional[BoundingBox]) -> None:
        self.selected = box
        self._draw_handle()

    def _draw_handle(self) -> None:
        if self._handle_id is not None:
            self.canvas.delete(self._handle_id)
            self._handle_id = None
        if self.selected is None:
            return
        hx, hy = self.view.to_canvas(*self._handle_point(self.selected))
        s = self.HANDLE_SIZE_PX
        self._handle_id = self.canvas.create_rectangle(hx - s, hy - s, hx + s, hy + s,
                                                       fill="white", outline="black")

    def clearrect(self):
        """Deletes the last drawn rectangle"""
        if self.boxes:
            box = self.boxes.pop()
            self.canvas.delete(box.tkrect)
            if self.selected is box:
                self._select(None)
            if self.boxes:
                self.bin_button.pack(anchor=tk.N, pady=50)
            else:
                self.bin_button.pack_forget()

    def cleartkrects(self):
        """Deletes all drawn rectangles"""
        for box in self.boxes:
            self.canvas.delete(box.tkrect)
        self._select(None)


    def clear(self):
        self.labels.clear()
        self.labels.pack_forget()

        self.cleartkrects()
        self.boxes.clear()

    # ---------------------------------------------------------------------------------------------
    # Marking session: draw new boxes, select, drag to move, and resize with the handle
    def drawrect(self, fwidth, fheight, fx, fy):
        """Starts a marking session: draw boxes (or circles), then select, move, and resize them."""
        # Disable other buttons
        for k,btn in self.button_list.items():
            if btn != self.active_button:
                btn.configure(state="disabled")

        if fwidth is None:
            fwidth = self.vwidth
        if fheight is None:
            fheight = self.vheight
        self.view.configure((fx, fy), (fwidth, fheight))

        self._session = True
        self.refresh()
        self.apply_button.pack(side=tk.BOTTOM, anchor=tk.E, padx=10, pady=10)
        if self.boxes:
            self.bin_button.pack(anchor=tk.N, pady=10)

        self.canvas.bind("<Button-1>", self._onpress)
        self.canvas.bind("<B1-Motion>", self._ondrag)
        self.canvas.bind("<ButtonRelease-1>", self._onrelease)

    def _onpress(self, event):
        bx, by = self.view.to_base(event.x, event.y)
        self._mode = None

        # Resize: pressing the handle of the selected box
        if self.selected is not None:
            hx, hy = self._handle_point(self.selected)
            if hypot(bx - hx, by - hy) <= self._tolerance():
                self._mode = "resize"
                self._drag_start = (bx, by)
                self._drag_geom = self._geom(self.selected)
                return

        # Move: pressing inside a box selects it and drags it
        hit = self._box_at(bx, by)
        if hit is not None:
            self._select(hit)
            self._mode = "move"
            self._drag_start = (bx, by)
            self._drag_geom = self._geom(hit)
            return

        # Otherwise start a new box
        self._select(None)
        self._mode = "draw"
        self._drawshape = self.shape
        self._rcoords = (event.x, event.y)
        self._ctkbox = self._create_item(self._drawshape, (event.x, event.y, event.x, event.y),
                                         self.OUTLINE_DRAWING)

    def _ondrag(self, event):
        if self._mode == "draw":
            sx, sy = self._rcoords
            ex, ey = (event.x, event.y)
            if self._drawshape == "circle":
                r = hypot(ex - sx, ey - sy)
                self.canvas.coords(self._ctkbox, sx - r, sy - r, sx + r, sy + r)
            else:
                self.canvas.coords(self._ctkbox, sx, sy, ex, ey)
            return

        if self._mode not in ("move", "resize") or self.selected is None:
            return
        bx, by = self.view.to_base(event.x, event.y)
        box = self.selected
        g = self._drag_geom
        if self._mode == "move":
            dx, dy = bx - self._drag_start[0], by - self._drag_start[1]
            if box.shape == "circle":
                geom = (g[0] + dx, g[1] + dy, g[2])
            else:
                geom = (g[0] + dx, g[1] + dy, g[2] + dx, g[3] + dy)
        elif box.shape == "circle":
            r = max(hypot(bx - g[0], by - g[1]), self.MIN_BOX_PX / 2)
            geom = (g[0], g[1], r)
        else:
            geom = (g[0], g[1], max(bx, g[0] + self.MIN_BOX_PX), max(by, g[1] + self.MIN_BOX_PX))
        self._set_geom(box, geom)
        self._draw_handle()

    def _onrelease(self, event):
        mode, self._mode = self._mode, None
        if mode != "draw":
            return

        # A click without a drag makes an empty box, which cannot be tracked. Discard it
        # and keep drawing enabled.
        sx, sy = self._rcoords
        ex, ey = (event.x, event.y)
        shape = self._drawshape
        too_small = (hypot(ex - sx, ey - sy) < self.MIN_BOX_PX if shape == "circle"
                     else abs(ex - sx) < self.MIN_BOX_PX or abs(ey - sy) < self.MIN_BOX_PX)
        if too_small:
            self.canvas.delete(self._ctkbox)
            return

        bx0, by0 = self.view.to_base(sx, sy)
        bx1, by1 = self.view.to_base(ex, ey)
        ox0, oy0 = self.view.origin
        if shape == "circle":
            r = hypot(bx1 - bx0, by1 - by0)
            prect = PixelRect(bx0 - r - ox0, by0 - r - oy0, 2 * r, 2 * r)
        else:
            prect = PixelRect(min(bx0, bx1) - ox0, min(by0, by1) - oy0,
                              abs(bx1 - bx0), abs(by1 - by0))
        nrect = prect.pix2norm(*self.view.size)

        box = BoundingBox(self._ctkbox, prect, nrect, shape)
        self.boxes.append(box)
        self.canvas.itemconfig(box.tkrect, outline=self._outline())
        self.bin_button.pack(anchor=tk.N, pady=10)
        self._select(box)

    def cancel(self):
        """Another tool was started: this marking session ends. The boxes drawn so far are kept,
        as if Apply had been pressed."""
        if self._session:
            self.onapply()

    def onapply(self):
        """Finalize rects and colors on apply, and end the marking session"""
        self._session = False
        self._select(None)
        for box in self.boxes:
            self.canvas.itemconfig(box.tkrect, outline=self.OUTLINE_APPLIED, width=self.LINE_WIDTH)

        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

        self.bin_button.pack_forget()
        self.apply_button.pack_forget()

        self.labels.pack(side=tk.TOP, anchor=tk.NW, padx=10, pady=60)
        self.labels.add_labels([box.pixelrect for box in self.boxes], color=self.OUTLINE_APPLIED)

        # Activate all buttons
        for k,btn in self.button_list.items():
            btn.configure(state="normal")

        if self.on_apply:
            self.on_apply()

    def restore(self, normrects: list[NormalizedRect], fwidth: int, fheight: int,
                fx: int, fy: int, shapes: Optional[list[str]] = None) -> None:
        """Recreates applied boxes from saved normalized rectangles (see drawrect for the frame)."""
        self.view.configure((fx, fy), (fwidth, fheight))
        self._session = False
        shapes = shapes or ["rect"] * len(normrects)
        for nrect, shape in zip(normrects, shapes):
            prect = nrect.norm2pix(fwidth, fheight)
            tkrect = self._create_item(shape, self._canvas_bbox(prect), self.OUTLINE_APPLIED)
            self.boxes.append(BoundingBox(tkrect, prect, nrect, shape))

        if self.boxes:
            self.labels.pack(side=tk.TOP, anchor=tk.NW, padx=10, pady=60)
            self.labels.add_labels([box.pixelrect for box in self.boxes], color=self.OUTLINE_APPLIED)

    @property
    def rects(self) -> list[NormalizedRect]:
        """Returns a list of normalized rectangles."""
        return [box.normrect for box in self.boxes]

    @property
    def shapes(self) -> list[str]:
        """Shape of each box, in the same order as `rects`."""
        return [box.shape for box in self.boxes]



# =====================================================================
# Main Testing Function
# =====================================================================

def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Testing Interactive Rect Selection")
    root.geometry("850x600")

    # 1. Top Control Toolbar
    toolbar = ctk.CTkFrame(root, height=50)
    toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))

    btn_dict = {}

    btn_draw = ctk.CTkButton(toolbar, text="Draw Rectangle", width=130)
    btn_draw.pack(side=tk.LEFT, padx=5, pady=5)
    btn_dict["draw"] = btn_draw

    btn_other = ctk.CTkButton(toolbar, text="Other Action (Test Lock)", width=160)
    btn_other.pack(side=tk.LEFT, padx=5, pady=5)
    btn_dict["other"] = btn_other

    btn_clear_all = ctk.CTkButton(
        toolbar,
        text="Clear All",
        fg_color="#e03131",
        hover_color="#c92a2a",
        width=100
    )
    btn_clear_all.pack(side=tk.RIGHT, padx=5, pady=5)

    # 2. Canvas Area
    canvas_width, canvas_height = 800, 500
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="#1e1e1e", highlightthickness=0)
    canvas.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 3. Instantiate Rect Tool
    rect_tool = Rect(
        canvas=canvas,
        vwidth=canvas_width,
        vheight=canvas_height,
        button_list=btn_dict,
        active_button=btn_draw
    )

    # 4. Attach Callbacks
    btn_draw.configure(command=lambda: rect_tool.drawrect(canvas_width, canvas_height, 0, 0))
    btn_clear_all.configure(command=rect_tool.clear)

    root.mainloop()


if __name__ == "__main__":
    main()
