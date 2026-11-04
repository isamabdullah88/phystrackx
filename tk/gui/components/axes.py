"""
axes.py

Defines the Axes class that manages coordinate transformations and GUI-based axis selection.

Author: Isam Balghari
"""

import tkinter as tk

import numpy as np
import customtkinter as ctk
from .anglecontrol import AngleControl
from .buttons import SubmitButton

class Axes:
    DRAG_TOLERANCE = 10  # Screen pixels from the origin or an axis line that start a drag

    def __init__(self, root, canvas, vwidth: int, vheight: int, btnlist: dict,
                 activebtn: ctk.CTkButton):
        self.root = root
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.theta = ctk.DoubleVar(value=0)
        self.angle = None
        self.placed = False  # True once the user has set an origin
        self.view = None  # ViewTransform, set by the app so axes follow zoom and pan
        self.on_apply = None  # Optional callback after Apply (used to leave marking mode)

        self.ox = 0.0
        self.oy = float(self.vheight)

        self.btnlist = btnlist
        self.activebtn = activebtn
        self.applybtn = SubmitButton(self.canvas, command=self.onapply, size=50,
                                     tooltip="Apply Axes")
        self.on_cancel = None  # Optional callback when selection is aborted (used to leave marking)
        self._selecting = False  # True while the axis tool is open (placing or editing)
        self._before = (self.ox, self.oy, 0.0, False)  # Axes when the tool opened, for cancel
        self._dragging = None  # (dx, dy) from the pointer to the origin while dragging
        self._items = None  # Canvas ids of the two lines and two labels, reused while moving

    def _picture_origin(self) -> tuple[float, float]:
        """Canvas position of the picture's top-left corner (the frame's pixel (0, 0))."""
        return self.view.origin if self.view is not None else (0, 0)

    def get_state(self) -> dict:
        """Axes origin relative to the picture's top-left corner (in frame pixels), so the axes stay
        on the same part of the picture whatever the window size."""
        ox, oy = self._picture_origin()
        return {"ox": self.ox - ox, "oy": self.oy - oy, "theta": self.theta.get(),
                "anchor": "picture", "canvas": [self.vwidth, self.vheight]}

    def restore_state(self, state: dict) -> None:
        """Re-places the axes. Older projects stored canvas positions, which are scaled if the
        window size has changed."""
        if state.get("anchor") == "picture":
            ox, oy = self._picture_origin()
            self.ox = state["ox"] + ox
            self.oy = state["oy"] + oy
        else:
            sx = self.vwidth / state["canvas"][0]
            sy = self.vheight / state["canvas"][1]
            self.ox = state["ox"] * sx
            self.oy = state["oy"] * sy
        self.theta.set(state["theta"])
        self.placed = True
        self.rotate()

    def shift(self, dx: float, dy: float) -> None:
        """Moves the axes with the picture, when the picture is placed again after a resize."""
        if not self.placed:
            return
        self.ox += dx
        self.oy += dy
        self.rotate()

    def clear(self):
        """Clear all canvas drawings related to sliders and axes."""
        self.placed = False
        self.theta.set(0)
        self.canvas.delete("axes")
        self._items = None

        if self.angle is not None:
            self.angle.hide()

    def markaxes(self):
        """
        Opens the axis tool. Without axes yet, they follow the pointer until a click places the
        origin. With axes already placed, they can be dragged straight away. Either way they can
        then be dragged by the origin or by either axis, the rotation bar turns them, and Apply
        ends the tool.
        """
        self._before = (self.ox, self.oy, self.theta.get(), self.placed)
        self._selecting = True
        self._toplevel().bind("<Escape>", self.cancelaxes)
        for btn in self.btnlist.values():
            if btn != self.activebtn:
                btn.configure(state="disabled")

        if self.placed:
            self._start_editing()
        else:
            self.canvas.delete("oval")
            self.canvas.delete("axes")
            self.canvas.bind("<Motion>", self.onmove)
            self.canvas.bind("<Button-1>", self.onclick)

    def _toplevel(self):
        """The window that receives key presses (the frame holding the canvas does not)."""
        return self.canvas.winfo_toplevel()

    def _start_editing(self) -> None:
        """Placed axes: drag them to move, turn them with the bar, then Apply."""
        self.canvas.unbind("<Motion>")
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.applybtn.pack(side="right", padx=10, pady=10, anchor="se")
        # Strip below the video (not over it), so the picture stays visible. The narrow bar gives
        # fine control; the text box covers larger angles. Made once and reused.
        if self.angle is None:
            self.angle = AngleControl(self.root, self.theta, self.rotate)
        self.angle.show(before=self.canvas)
        self.rotate()

    def _unbind(self) -> None:
        for sequence in ("<Motion>", "<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"):
            self.canvas.unbind(sequence)
        self._toplevel().unbind("<Escape>")

    def _end_tool(self) -> None:
        self._selecting = False
        self._dragging = None
        self._unbind()
        self.applybtn.pack_forget()
        if self.angle is not None:
            self.angle.hide()
        for btn in self.btnlist.values():
            btn.configure(state="normal")

    def cancelaxes(self, event=None):
        """Escape, or another tool started: the axes go back to how they were when the tool
        opened (none, if there were none)."""
        if not self._selecting:
            return
        self._end_tool()
        ox, oy, theta, placed = self._before
        self.ox, self.oy, self.placed = ox, oy, placed
        self.theta.set(theta)
        if self.placed:
            self.rotate()
        else:
            self.canvas.delete("axes")
        if self.on_cancel:
            self.on_cancel()

    # ---------------------------------------------------------------------------------------------
    # Dragging
    def _base(self, x: float, y: float) -> tuple[float, float]:
        return self.view.to_base(x, y) if self.view is not None else (x, y)

    def _screen_origin(self) -> tuple[float, float]:
        if self.view is not None:
            return self.view.to_canvas(self.ox, self.oy)
        return self.ox, self.oy

    def _directions(self):
        """Unit canvas directions of the x and y axes at the current angle."""
        theta_rad = -np.deg2rad(self.theta.get())
        dirs = []
        for vec in ((1.0, 0.0), (0.0, 1.0)):
            dx, dy = self._canvas_dir(*self.rotatez(*vec, theta_rad))
            norm = np.hypot(dx, dy) or 1.0
            dirs.append((dx / norm, dy / norm))
        return dirs

    def _hits_axes(self, x: float, y: float) -> bool:
        """True when the screen point is on the origin or on either axis (within a few pixels)."""
        sx, sy = self._screen_origin()
        vx, vy = x - sx, y - sy
        tol = self.DRAG_TOLERANCE
        if np.hypot(vx, vy) <= 1.5 * tol:
            return True
        for dx, dy in self._directions():
            along = vx * dx + vy * dy
            if along >= -tol and abs(vx * dy - vy * dx) <= tol:
                return True
        return False

    def _on_press(self, event) -> None:
        if not self._hits_axes(event.x, event.y):
            self._dragging = None
            return
        bx, by = self._base(event.x, event.y)
        self._dragging = (self.ox - bx, self.oy - by)

    def _on_drag(self, event) -> None:
        if self._dragging is None:
            return
        bx, by = self._base(event.x, event.y)
        self.ox, self.oy = bx + self._dragging[0], by + self._dragging[1]
        self.rotate()

    def _on_release(self, event) -> None:
        self._dragging = None

    def drawaxes(self, startx, starty, xp, yp):
        """Draw x and y axes lines with arrow heads and labels.

        The endpoints must already be on screen (see ray_to_edge). They are not clamped here:
        clamping each coordinate separately bends the line, so the angle changes with zoom.
        """
        sx0, sy0 = startx
        sx1, sy1 = starty
        x0, y0 = xp
        x1, y1 = yp

        # The items are made once and then moved: deleting and recreating them on every pointer
        # move made dragging and the preview lag
        items = self._items
        if items is None or not self.canvas.type(items[0]):
            self._items = (
                self.canvas.create_line(sx0, sy0, x0, y0, fill="red", arrow=ctk.LAST,
                                        width=2, tags="axes"),
                self.canvas.create_line(sx1, sy1, x1, y1, fill="blue", arrow=ctk.LAST,
                                        width=2, tags="axes"),
                self.canvas.create_text(x0 - 15, y0 - 15, text="x", fill="red",
                                        font=("Arial", 15, "bold"), tags="axes"),
                self.canvas.create_text(x1 + 15, y1 - 15, text="y", fill="blue",
                                        font=("Arial", 15, "bold"), tags="axes"),
            )
            return
        xline, yline, xtext, ytext = items
        tk.Canvas.coords(self.canvas, xline, sx0, sy0, x0, y0)
        tk.Canvas.coords(self.canvas, yline, sx1, sy1, x1, y1)
        tk.Canvas.coords(self.canvas, xtext, x0 - 15, y0 - 15)
        tk.Canvas.coords(self.canvas, ytext, x1 + 15, y1 - 15)

    def canvas2reg(self, xc, yc, tx, ty):
        """Convert canvas coordinates to regular (math) frame."""
        return xc - tx, -yc + ty

    def reg2canvas(self, xr, yr, tx, ty):
        """Convert regular (math) coordinates to canvas frame."""
        return xr + tx, -yr + ty

    def rotatez(self, x, y, theta):
        """Rotate a point (x, y) by angle `theta` (radians) around the origin."""
        c, s = np.cos(theta).item(), np.sin(theta).item()
        return x * c - y * s, x * s + y * c

    def rotate(self, event=None):
        """Redraw axes based on the current rotation angle."""

        theta_rad = -np.deg2rad(self.theta.get())
        # Canvas direction of each axis (y points down on screen, so the regular y flips)
        xdx, xdy = self._canvas_dir(*self.rotatez(self.vwidth, 0, theta_rad))
        ydx, ydy = self._canvas_dir(*self.rotatez(0, self.vheight, theta_rad))

        # Stored positions are unzoomed; map the origin to the screen. Zoom scales both axes
        # equally, so the directions above hold on screen too.
        sx, sy = self.ox, self.oy
        if self.view is not None:
            sx, sy = self.view.to_canvas(sx, sy)

        self._draw_from(sx, sy, (xdx, xdy), (ydx, ydy))

    @staticmethod
    def _canvas_dir(xr: float, yr: float) -> tuple[float, float]:
        """Regular (math) vector -> canvas vector."""
        return xr, -yr

    def _draw_from(self, sx: float, sy: float, xdir, ydir) -> None:
        """Draws both axes through the screen point (sx, sy) along their directions."""
        segs = []
        for direction in (xdir, ydir):
            seg = self.visible_segment(sx, sy, *direction, self.vwidth, self.vheight)
            # An axis that misses the visible canvas is drawn as a point (nothing visible)
            segs.append(seg if seg is not None else ((sx, sy), (sx, sy)))
        (xlo, xhi), (ylo, yhi) = segs
        self.drawaxes(xlo, ylo, xhi, yhi)

    @staticmethod
    def visible_segment(sx: float, sy: float, dx: float, dy: float, w: float, h: float):
        """
        The part of the axis line through (sx, sy) along (dx, dy) that is inside the canvas
        [0, w] x [0, h]. Its far end is the arrow tip, in the +direction.

        If the origin is on the canvas, the axis starts there and runs forward, as before. If the
        origin is off the canvas (for example when zoomed to another part of the video), the
        whole visible stretch of the line is returned, so the axis stays visible.

        Returns:
            ((x, y) near end, (x, y) far end), or None if the line misses the canvas.
        """
        lo, hi = -float("inf"), float("inf")
        for s, d, bound in ((sx, dx, w), (sy, dy, h)):
            if abs(d) < 1e-12:
                if s < 0 or s > bound:
                    return None
                continue
            t1, t2 = (0.0 - s) / d, (bound - s) / d
            lo, hi = max(lo, min(t1, t2)), min(hi, max(t1, t2))
        if lo > hi:
            return None

        if 0.0 <= sx <= w and 0.0 <= sy <= h:
            lo = 0.0  # Origin on the canvas: start there, as the axis always has
        return (sx + lo * dx, sy + lo * dy), (sx + hi * dx, sy + hi * dy)

    def onmove(self, event):
        """Update axes preview to follow mouse position."""

        # Unrotated preview: x along +x, y along -y (up the screen)
        self._draw_from(event.x, event.y, (1.0, 0.0), (0.0, -1.0))

    def onclick(self, event):
        """Places the origin where the user clicked. The axes can then be dragged and turned."""
        self.ox, self.oy = self._base(event.x, event.y)
        self.placed = True
        if not self._selecting:  # Placed directly (not from the tool): still allow editing
            self._before = (self.ox, self.oy, self.theta.get(), False)
            self._selecting = True
        self._start_editing()

    def onapply(self):
        """Finalize axis placement and restore other UI buttons."""
        self._end_tool()
        if self.on_apply:
            self.on_apply()
