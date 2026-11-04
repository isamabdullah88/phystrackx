"""Tracking screen: live frames, refused second run, stop keeps results, manual positions.

The tracker is fast on the test clip, so the frame callback is slowed down. This keeps the run
long enough to press Track again and Stop while it is still going.
"""

import time

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import gui.rigid.rigid_app as ra  # noqa: E402
from core import NormalizedRect  # noqa: E402


def test_tracking_screen():
    h.quiet_dialogs(ra)
    root = ctk.CTk()
    root.geometry("1280x720")
    root.update()
    app = ra.RigidApp(root, videopath=h.make_clip())
    h.pump(root, lambda: app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)
    app.trimvideo(20, 200)
    h.pump(root, lambda: app.trim_range is not None and app.videoapp.fcount > 0)
    h.pump(root, timeout=0.5)
    app.seekbar.mark_trimmed()

    crop = app.plugin_mgr.crop
    app.track_rects.restore([NormalizedRect(0.45, 0.4, 0.1, 0.06)], crop.cropwidth, crop.cropheight,
                            crop.cropx, crop.cropy)

    slow = app._on_tracked_frame

    def slowed(i, frame, boxes):
        time.sleep(0.03)
        slow(i, frame, boxes)
    app._on_tracked_frame = slowed

    # The run is slowed, so these checks happen straight after the call, before any events are processed
    app.strack()
    first_thread = app._track_thread
    h.check("tracking runs in a worker thread", first_thread.is_alive())
    h.check("zoom strip is on the tracking screen", app.viewcontrols.frame.winfo_manager() == "pack")
    h.check("stop button is enabled while tracking", str(app.stopbtn.cget("state")) == "normal")

    app.strack()
    h.check("a second Track press is refused while running", app._track_thread is first_thread)

    h.pump(root, lambda: app._live_frame is not None and app._live_frame[0] > 20, timeout=60)
    h.check("live frames arrive while tracking", app._live_frame is not None and app._live_frame[0] > 20)

    app._request_stop()
    done = h.pump(root, lambda: not app._live_on and not first_thread.is_alive(), timeout=60)
    h.check("stop ends the run", done)
    h.check("stop keeps the results found so far",
            0 < len([p for p in app.videoapp.trackpts[0] if len(p) == 2]) < len(app.videoapp.trackpts[0]))
    h.check("status says it stopped", "Stopped at frame" in app.trackstatus.cget("text"),
            app.trackstatus.cget("text"))
    h.check("manual position is available after stop", str(app.manualbtn.cget("state")) == "normal")

    idx = app.seekbar.idx
    app._set_manual(True)
    ox0, oy0 = app.view.origin
    x, y = app.view.to_canvas(ox0 + 50, oy0 + 60)
    app.videoview.event_generate("<Button-1>", x=int(x), y=int(y))
    root.update()
    pt = app.videoapp.trackpts[0][idx]
    h.check("clicking in manual mode sets the position for the frame shown",
            pt is not None and len(pt) == 2 and abs(pt[0] - 50) < 1 and abs(pt[1] - 60) < 1,
            str(pt))
    app._close_track_view()
    root.update()
    h.check("close hides the tracking strip", not app.trackstrip.winfo_ismapped())

    app.strack()
    h.pump(root, lambda: not app._live_on and not app._track_thread.is_alive(), timeout=120)
    h.check("a full run reports completion", app.trackstatus.cget("text") == "Tracking complete",
            app.trackstatus.cget("text"))
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_tracking_screen])
