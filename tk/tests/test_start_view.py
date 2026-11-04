"""On start, a rotated phone-style clip is shown whole, fitted to the video area (needs a window).

The clip is landscape with a 90-degree display rotation, like the phone videos that open too large.
The test waits for the first frame, then checks the picture that was drawn: it must lie inside the
video area and fill one of its sides. No tolerance: the picture size is an exact function of the
frame size, the view fit and the area.
"""

import os
import shutil
import subprocess

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402


def _rotated_clip() -> str:
    """A 1920x1080 clip shown as portrait (display rotation), made once in the work folder."""
    from core import find_ffmpeg
    path = os.path.join(h.WORK_DIR, "start_rotated_1920x1080.mp4")
    if not os.path.isfile(path):
        plain = os.path.join(h.WORK_DIR, "start_plain_1920x1080.mp4")
        subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "testsrc2=duration=4:size=1920x1080:rate=30", "-c:v", "libx264",
                        "-preset", "veryfast", "-pix_fmt", "yuv420p", plain], check=True)
        subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-display_rotation", "90",
                        "-i", plain, "-c", "copy", path], check=True)
    return path


def test_picture_fits_the_video_area_on_start():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=_rotated_clip())
    loaded = h.pump(root, lambda: app.videoapp.frame is not None, timeout=240)
    h.check("the first frame is shown", loaded, f"dialogs: {h.DIALOGS}")
    if not loaded:
        root.destroy()
        return
    h.pump(root, timeout=1.0)  # Let the layout settle (a resize is laid out after a short delay)

    frame_h, frame_w = app.videoapp.frame.shape[:2]
    area_w, area_h = app.videoview.winfo_width(), app.videoview.winfo_height()
    drawn_w, drawn_h = app.videoapp.tkimg.width(), app.videoapp.tkimg.height()
    detail = (f"frame {frame_w}x{frame_h}, area {area_w}x{area_h}, drawn {drawn_w}x{drawn_h}, "
              f"fit {app.view.fit:.3f}, zoom {app.view.zoom}, proxy {app.videoapp.rigid.proxysize}, "
              f"reader {app.videoapp.rigid._vidreader.width}x{app.videoapp.rigid._vidreader.height}, "
              f"crop {app.plugin_mgr.crop.cropwidth}x{app.plugin_mgr.crop.cropheight}, "
              f"native {app.videoapp.rigid.nativepath is not None}")
    h.check("the drawn picture is inside the video area",
            drawn_w <= area_w and drawn_h <= area_h, detail)
    h.check("the drawn picture fills one side of the video area",
            max(drawn_w / area_w, drawn_h / area_h) > 0.95, detail)
    h.check("the drawn picture is the frame scaled by the view fit",
            abs(drawn_w - frame_w * app.view.fit) <= 1 and abs(drawn_h - frame_h * app.view.fit) <= 1,
            detail)
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_picture_fits_the_video_area_on_start])
