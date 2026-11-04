"""Zoomed views show full-resolution pixels, scaled without smoothing (needs a window).

Enlarged pictures must keep the source's colours (nearest neighbour), not blend them, and a zoomed
view reads its visible part from the full-resolution copy once that copy exists.
"""

import numpy as np

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from gui.rigid.video_app import Video  # noqa: E402


def test_enlarging_keeps_source_colours():
    """A 2x2 checker enlarged: nearest neighbour adds no new colours; smoothing would."""
    src = np.zeros((2, 2, 3), np.uint8)
    src[0, 0] = src[1, 1] = (255, 255, 255)
    big = Video._scale(src, (40, 40))
    colours = {tuple(c) for c in big.reshape(-1, 3)}
    h.check("enlarged picture has only the source colours", colours <= {(0, 0, 0), (255, 255, 255)},
            str(colours))


def test_zoomed_view_reads_the_full_resolution_copy():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=h.make_clip())
    h.pump(root, lambda: app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)

    app.view.set_zoom(4.0)
    app.view.set_fraction(0.5, 0.5)
    app.updateframe()
    h.pump(root, lambda: app.videoapp.rigid.nativepath is not None, timeout=180)
    app.updateframe()
    root.update()

    part = app.videoapp._native_picture(app.view)
    h.check("zoomed view takes its pixels from the full-resolution copy", part is not None)
    if part is not None:
        proxy_w = app.videoapp.rigid.proxysize[0]
        native_w = app.videoapp.rigid._nativereader.width
        x, y, w, h_ = app.view.window()
        # The part is the window widened to whole frame pixels (the view can be placed at a
        # fraction of a pixel), so it is the window's width plus up to two frame pixels
        ratio = native_w / proxy_w
        h.check("the native part covers the same picture area",
                (w - 1) * ratio - 2 <= part.shape[1] <= (w + 2) * ratio + 2,
                f"{part.shape} for window {w}x{h_}")
    # A trimmed clip (cut from the proxy) zooms from the full-resolution copy too
    app.view.reset()
    app.trimvideo(20, 200, crop=(40, 60, 200, 300))
    h.pump(root, lambda: app.trim_range is not None and app.videoapp.fcount > 0, timeout=120)
    h.pump(root, timeout=0.5)
    app.seekbar.mark_trimmed()
    app.view.set_zoom(4.0)
    app.view.set_fraction(0.5, 0.5)
    app.updateframe()
    root.update()
    trimmed = app.videoapp._native_picture(app.view)
    h.check("zoomed trimmed clip also reads the full-resolution copy", trimmed is not None)
    if trimmed is not None:
        x, y, w, h_ = app.view.window()
        native_w = app.videoapp.rigid._nativereader.width
        proxy_w = app.videoapp.rigid.proxysize[0]
        ratio = native_w / proxy_w
        h.check("the trimmed part's size matches the native pixels",
                (w - 1) * ratio - 2 <= trimmed.shape[1] <= (w + 2) * ratio + 2, f"{trimmed.shape}")
    root.destroy()


def test_rotated_source_is_not_read_directly():
    """A phone video stores its rotation as metadata: it needs the rotated copy, not the file."""
    import os
    import subprocess
    from core import find_ffmpeg
    from media.proxyvideo import source_is_plain
    clip = h.make_clip()
    rotated = os.path.join(h.WORK_DIR, "rotated_clip.mp4")
    subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-display_rotation", "90", "-i", clip,
                    "-c", "copy", rotated], check=True)
    h.check("an unrotated clip with even size is read directly", source_is_plain(clip))
    h.check("a rotated clip is not read directly", not source_is_plain(rotated))


if __name__ == "__main__":
    h.run_tests([test_rotated_source_is_not_read_directly, test_enlarging_keeps_source_colours, test_zoomed_view_reads_the_full_resolution_copy])
