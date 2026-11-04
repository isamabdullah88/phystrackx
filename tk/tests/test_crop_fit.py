"""After a crop is applied, the cropped picture is upscaled to fit the view, keeping its ratio
(needs a window).

Overlays and stored positions stay in frame pixels, so only the picture's size on screen changes.
"""

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from core import PixelRect  # noqa: E402


def test_applied_crop_fits_the_view():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=h.make_clip())
    h.pump(root, lambda: app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)

    crop = app.plugin_mgr.crop
    w, hgt = 200, 150  # Landscape crop, so the view's width is the limit
    crop.croprect = PixelRect(40, 60, w, hgt)
    crop.apply()
    root.update()

    fit = min(crop.vwidth / w, crop.vheight / hgt)
    h.check("applied crop gets the fit that fills the view", abs(crop.fit - fit) < 1e-9,
            f"fit {crop.fit:.3f}, expected {fit:.3f}")
    h.check("view uses the same fit", abs(app.view.fit - crop.fit) < 1e-9, str(app.view.fit))

    shown = app.videoapp.tkimg
    h.check("picture is drawn at the fitted size",
            (shown.width(), shown.height()) == (round(w * fit), round(hgt * fit)),
            f"{shown.width()}x{shown.height()}")
    h.check("picture fills the view width", shown.width() == crop.vwidth or
            shown.height() == crop.vheight, f"{shown.width()}x{shown.height()}")
    h.check("picture keeps the crop's ratio",
            abs(shown.width() / shown.height() - w / hgt) < 0.02,
            f"{shown.width() / shown.height():.3f}")

    # A stored frame point is drawn fit-scaled from the picture's corner
    ox, oy = app.view.origin
    cx, cy = app.view.to_canvas(ox + 10, oy + 20)
    h.check("frame point is drawn at fit scale", abs(cx - (ox + 10 * fit)) < 1e-6 and
            abs(cy - (oy + 20 * fit)) < 1e-6, f"{cx:.2f}, {cy:.2f}")
    bx, by = app.view.to_base(cx, cy)
    h.check("screen to base round trip is exact at the fit",
            abs(bx - (ox + 10)) < 1e-6 and abs(by - (oy + 20)) < 1e-6, f"{bx:.3f}, {by:.3f}")

    crop.clear()
    app.updateframe()
    root.update()
    h.check("clearing the crop returns to 1:1", crop.fit == 1.0 and app.view.fit == 1.0)
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_applied_crop_fits_the_view])
