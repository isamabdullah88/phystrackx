"""Trim with a crop, and the zoom strip for axes and scale (needs a window)."""

import types

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from core import PixelRect  # noqa: E402


def test_trim_with_crop_and_zoom_strip():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=h.make_clip())
    h.pump(root, lambda: app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)

    app.loadseek()
    root.update()
    h.check("trim step shows the crop strip", app.cropstrip.winfo_ismapped())

    crop = app.plugin_mgr.crop
    crop.croprect = PixelRect(40, 60, 200, 300)
    crop.set()
    app._update_crop_status()
    h.check("crop status shows the chosen size", "200 x 300" in app.cropstatus.cget("text"),
            app.cropstatus.cget("text"))

    app.trimvideo(20, 200)
    h.pump(root, lambda: app.trim_range is not None and app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)
    h.check("trim records the crop", app.trim_range["crop"] == [40, 60, 200, 300],
            str(app.trim_range))
    h.check("trimmed clip has the cropped size", (app.videoapp.fwidth, app.videoapp.fheight) == (200, 300),
            f"{app.videoapp.fwidth}x{app.videoapp.fheight}")
    h.check("crop is consumed by the trim (no second crop)", crop.croprect is None)
    h.check("crop strip hides after the trim", not app.cropstrip.winfo_ismapped())
    app.seekbar.mark_trimmed()

    app.markaxes()
    root.update()
    h.check("axes show the zoom strip", app.viewcontrols.frame.winfo_ismapped())
    h.check("axes hide the shape switch", not app.viewcontrols.shape_switch.winfo_ismapped())
    app.viewcontrols.zoomvar.set(2.0)
    app.viewcontrols._on_zoom()
    root.update()
    c = app.videoview
    app.axes.onclick(types.SimpleNamespace(x=c.winfo_width() // 2, y=c.winfo_height() // 2))
    app.axes.onapply()
    root.update()
    h.check("axes apply hides the strip", not app.viewcontrols.frame.winfo_ismapped())
    h.check("axes apply keeps the zoom", app.view.zoom == 2.0, str(app.view.zoom))
    h.check("axes stay placed after apply", app.axes.placed)

    app.scale()
    root.update()
    h.check("scale shows the zoom strip", app.viewcontrols.frame.winfo_ismapped())
    app.scruler.onapply()
    root.update()
    h.check("scale apply hides the strip", not app.viewcontrols.frame.winfo_ismapped())
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_trim_with_crop_and_zoom_strip])
