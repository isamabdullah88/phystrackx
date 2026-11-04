"""
Playback: Space plays and pauses, the Speed button steps through 25, 50, 100 and 150 percent, playing
stops at the trim's end, and the arrows and scrubbing stop it.

    ~/.venvs/phystrackx-qt/bin/python tests/test_playback.py
"""

import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from test_tracking import make_clip  # noqa: E402


def test_playback() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    h.check("the speed button starts at 100%", w.speed_btn.text() == "Speed: 100%", w.speed_btn.text())
    texts = []
    for _ in range(4):
        w.speed_btn.click()
        texts.append(w.speed_btn.text())
    h.check("the speed button steps 150, 25, 50, 100 percent",
            texts == ["Speed: 150%", "Speed: 25%", "Speed: 50%", "Speed: 100%"],
            str(texts))

    w.seek.setValue(0)
    h.pump(lambda: w.frame_label.text().startswith("frame 0 "), 5)
    QTest.keyClick(w, Qt.Key.Key_Space)
    h.check("Space starts playback", w._playing)
    t0 = time.time()
    h.pump(lambda: False, 0.5)
    moved = w.seek.value()
    h.check("playing at 100% moves on by about the frame rate (about 15 frames in half a second)",
            8 <= moved <= 25, f"frame {moved} after {time.time() - t0:.2f} s")
    QTest.keyClick(w, Qt.Key.Key_Space)
    h.check("Space pauses", not w._playing)
    paused_at = w.seek.value()
    h.pump(lambda: False, 0.3)
    h.check("paused: the frame does not move", w.seek.value() == paused_at == moved,
            f"{paused_at} then {w.seek.value()}")

    w.speed_btn.click()  # 150%, from the 100% it was at
    w.seek.setValue(w.seek.maximum() - 3)
    h.pump(lambda: w.frame_label.text().startswith(f"frame {w.seek.maximum()-3} "), 5)
    QTest.keyClick(w, Qt.Key.Key_Space)
    h.check("playing stops at the last frame", h.pump(lambda: not w._playing, 10))
    h.check("and is on that frame", w.seek.value() == w.seek.maximum(), str(w.seek.value()))
    QTest.keyClick(w, Qt.Key.Key_Space)
    h.check("Space at the end plays again from the start", w.seek.value() == w.seek.minimum() and w._playing)
    QTest.keyClick(w, Qt.Key.Key_Space)

    w.speed_btn.setFocus()  # Focus on a button: Space still plays, rather than pressing the button
    QTest.keyClick(w, Qt.Key.Key_Space)
    h.check("with the Speed button focused, Space still plays", w._playing)
    w._pause()
    w.seek.setValue(10)
    QTest.keyClick(w, Qt.Key.Key_Space)
    QTest.keyClick(w, Qt.Key.Key_Right)
    h.check("the Right arrow stops playback, as stepping by hand does", not w._playing)
    w._pause()

    # A frame a little ahead (playback skipping a frame) is read forward, not seeked: seeking for each
    # skip made playback fall far behind. It must be the same frame a seek gives.
    reader = w.source.reader
    seeks = []
    seek = reader.seek
    reader.seek = lambda index: (seeks.append(index), seek(index))
    w.source.frame(20)
    seeks.clear()
    ahead = w.source.frame(25)
    h.check("a frame 5 ahead is read forward, without a seek", seeks == [], str(seeks))
    w.source.frame(60)  # Far ahead: seeks
    h.check("a frame far ahead seeks", seeks == [60], str(seeks))
    h.check("the frame read forward is the frame a seek gives",
            np.array_equal(ahead, w.source.frame(25)) and seeks[-1] == 25, str(seeks))
    reader.seek = seek
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    print("test_playback")
    test_playback()
    h.finish()
