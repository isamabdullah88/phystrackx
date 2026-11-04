"""Trimming a trimmed clip again (with a crop), and a trim that FFmpeg rejects (needs a window).

A second trim is recorded in full-video terms, so the trim is the same whether it was made in
one step or two. A failed trim must leave the clip that is on screen untouched.
"""

import os

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from core import PixelRect  # noqa: E402


def test_trim_again_and_failed_trim():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=h.make_clip())
    h.pump(root, lambda: app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)

    app.trimvideo(20, 200, crop=(40, 60, 200, 300))
    h.pump(root, lambda: app.trim_range is not None and app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)
    app.seekbar.mark_trimmed()

    # Second trim, with a crop given in the first clip's pixels
    app.plugin_mgr.crop.croprect = PixelRect(20, 30, 100, 150)
    app.trimvideo(10, 100, crop=(20, 30, 100, 150))
    h.pump(root, lambda: app.trim_range["start"] == 30 and app.videoapp.fwidth == 100)
    h.pump(root, timeout=0.5)
    h.check("second trim is recorded in full-video frames", app.trim_range["start"] == 30
            and app.trim_range["end"] == 120, str(app.trim_range))
    h.check("second trim's crop is the full-video crop", app.trim_range["crop"] == [60, 90, 100, 150],
            str(app.trim_range))
    h.check("full-resolution map follows the second trim",
            (app.videoapp.trimstart, app.videoapp.trimorigin) == (30, (60, 90)),
            f"{app.videoapp.trimstart} {app.videoapp.trimorigin}")
    h.check("second trim's clip has the new size", (app.videoapp.fwidth, app.videoapp.fheight) == (100, 150),
            f"{app.videoapp.fwidth}x{app.videoapp.fheight}")

    # A crop of zero size makes FFmpeg fail. The clip on screen must stay as it was.
    before = dict(app.trim_range)
    size_before = (app.videoapp.fwidth, app.videoapp.fheight)
    frames_before = app.videoapp.fcount
    dialogs_before = len(h.DIALOGS)
    app.trimvideo(10, 50, crop=(0, 0, 0, 0))
    h.pump(root, lambda: len(h.DIALOGS) > dialogs_before, timeout=60)
    h.pump(root, timeout=0.5)
    h.check("failed trim tells the user", len(h.DIALOGS) > dialogs_before and
            h.DIALOGS[-1][1] == "Trim", str(h.DIALOGS[-1:]))
    h.check("failed trim keeps the trim record", app.trim_range == before, str(app.trim_range))
    h.check("failed trim keeps the clip size",
            (app.videoapp.fwidth, app.videoapp.fheight) == size_before)
    h.check("failed trim keeps the frame count", app.videoapp.fcount == frames_before)
    h.check("the clip file is still there", os.path.isfile(app.videoapp.trimpath))
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_trim_again_and_failed_trim])
