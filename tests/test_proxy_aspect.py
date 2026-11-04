"""A phone-style clip (stored landscape, shown upright) keeps its shown shape in the proxy.

The proxy is scaled from the video as it is shown. If its size were worked out from the stored
frame, the upright picture would be squeezed into a landscape grid and drawn stretched.
"""

import os
import subprocess

from tests import harness as h
h.setup_env()

from core import find_ffmpeg  # noqa: E402
from experiments.rigid.rigid import Rigid  # noqa: E402


def _rotated_clip() -> str:
    """A 1920x1080 clip shown upright (1080x1920), made once in the work folder."""
    path = os.path.join(h.WORK_DIR, "aspect_rotated_1920x1080.mp4")
    if not os.path.isfile(path):
        plain = os.path.join(h.WORK_DIR, "aspect_plain_1920x1080.mp4")
        subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "testsrc2=duration=2:size=1920x1080:rate=30", "-c:v", "libx264",
                        "-preset", "veryfast", "-pix_fmt", "yuv420p", plain], check=True)
        subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-display_rotation", "90",
                        "-i", plain, "-c", "copy", path], check=True)
    return path


def test_rotated_proxy_keeps_the_shown_shape():
    rig = Rigid(trimpath=os.path.join(h.WORK_DIR, "aspect_trim.mp4"), vwidth=600, vheight=598)
    rig.addvideo(_rotated_clip())
    w, hgt = rig.proxysize
    h.check("proxy is portrait, as the video is shown (1080x1920)",
            abs(w / hgt - 1080 / 1920) < 0.005, f"proxy {w}x{hgt}")


if __name__ == "__main__":
    h.run_tests([test_rotated_proxy_keeps_the_shown_shape])
