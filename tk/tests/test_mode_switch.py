"""Starting a second selection (axes or ruler) cancels an unfinished first one (needs a window).

One app for the module: a second RigidApp in the same process breaks Tk's images.
"""

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402


def test_axis_then_ruler_then_axis():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=h.make_clip())
    h.pump(root, lambda: app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)

    app.markaxes()
    root.update()
    h.check("axis selection starts", app.axes._selecting)

    app.scale()  # Axis not set: the ruler starts, and the axis selection is cancelled
    root.update()
    h.check("ruler starts while axis is unfinished", app.scruler.applybtn is not None)
    h.check("the unfinished axis selection is cancelled", not app.axes._selecting)
    h.check("cancelled axis leaves no axes placed", not app.axes.placed)

    app.markaxes()  # Ruler not applied: the ruler is removed, and axis selection starts
    root.update()
    h.check("axis starts while ruler is unfinished", app.axes._selecting)
    h.check("the unfinished ruler is cancelled", app.scruler.applybtn is None)
    h.check("a never-calibrated ruler is not kept", not app.scruler.placed)

    app.seekbar.mark_trimmed()  # Box mode needs a trimmed clip
    app.drawrect()  # Box mode: then the tracker starts, and box mode must end
    root.update()
    h.check("box mode starts", app.track_rects._session)
    app.strack()
    root.update()
    h.check("starting the tracker ends box mode", not app.track_rects._session)

    app.drawrect()
    root.update()
    app.scale()  # Box mode ends when the ruler starts
    root.update()
    h.check("starting the ruler ends box mode", not app.track_rects._session)
    h.check("the ruler is placing", app.scruler.applybtn is not None)
    app.markaxes()
    root.update()

    app.drawcrop()  # Crop mode: then the axes start, and the crop must be dropped
    root.update()
    h.check("crop mode starts", app.plugin_mgr.crop._drawing)
    app.markaxes()
    root.update()
    h.check("starting the axes ends crop mode", not app.plugin_mgr.crop._drawing)
    app.axes.cancelaxes()
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_axis_then_ruler_then_axis])
