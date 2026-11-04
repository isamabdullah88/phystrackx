"""
Keyboard shortcuts: each button's label shows its key, and the key acts as pressing the button. Keys
1 to 4 set the playback speed.

    ~/.venvs/phystrackx-qt/bin/python tests/test_keys.py
"""

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from phystrack_qt.video_view import TOOL_AUTO, TOOL_BOX, TOOL_CIRCLE, TOOL_CLICK, TOOL_NONE  # noqa: E402
from test_tracking import ball_path, make_clip  # noqa: E402

LABELS = {"import_btn": ("Import Video", "i"), "trim_btn": ("Trim", "y"),
          "ruler_btn": ("Place Ruler", "f"), "axis_btn": ("Place Axis", "g"),
          "start_btn": ("Video Start", "s"), "end_btn": ("Video End", "e"), "find_btn": ("Auto Object", "z"),
          "mark_btn": ("Mark Rectangle", "r"), "circle_btn": ("Mark Circle", "c"), "track_btn": ("Track", "t"),
          "plots_btn": ("Plots", "p"), "clear_obj_btn": ("Clear Track", "v"), "remove_obj_btn": ("Remove", "d"),
          "move_obj_btn": ("Move", "m")}


def test_keys() -> None:
    w = h.window()
    for name, (text, key) in LABELS.items():
        button = getattr(w, name)
        h.check(f"the label is '{text}', with the key '{key}' beside it", button.text() == text
                and button.key == key, f"{button.text()!r} key {button.key!r}")
    h.check("the speed button shows its key range", w.speed_btn.text() == "Speed: 100%"
            and w.speed_btn.key == "1-4", w.speed_btn.text())

    QTest.keyClick(w, Qt.Key.Key_R)
    h.check("with no video, a key does nothing (r does not start Mark Rectangle)",
            w.view.tool == TOOL_NONE)

    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    last = w.source.fcount - 1
    QTest.keyClick(w, Qt.Key.Key_E)
    h.check("e goes to the video end", w.seek.value() == last, str(w.seek.value()))
    QTest.keyClick(w, Qt.Key.Key_S)
    h.check("s goes to the video start", w.seek.value() == 0, str(w.seek.value()))

    QTest.keyClick(w, Qt.Key.Key_E)
    h.check("a key press flashes the button's red outline", "ff2020" in w.end_btn.styleSheet(),
            w.end_btn.styleSheet())
    h.pump(lambda: False, 0.6)
    h.check("the outline goes again after a moment", w.end_btn.styleSheet() == "")
    QTest.mouseClick(w.speed_btn, Qt.MouseButton.LeftButton)
    h.check("a mouse click flashes it too", "ff2020" in w.speed_btn.styleSheet())
    h.pump(lambda: False, 0.6)
    h.check("and it goes again", w.speed_btn.styleSheet() == "")

    QTest.keyClick(w, Qt.Key.Key_R)
    h.check("r starts Mark Rectangle", w.view.tool == TOOL_BOX)
    QTest.keyClick(w, Qt.Key.Key_Escape)
    QTest.keyClick(w, Qt.Key.Key_C)
    h.check("c starts Mark Circle", w.view.tool == TOOL_CIRCLE)
    QTest.keyClick(w, Qt.Key.Key_Escape)
    QTest.keyClick(w, Qt.Key.Key_Z)
    h.check("z starts Auto Object", w.view.tool == TOOL_AUTO)
    QTest.keyClick(w, Qt.Key.Key_Escape)
    QTest.keyClick(w, Qt.Key.Key_G)
    h.check("g starts Place Axis", w.view.tool == TOOL_CLICK)
    QTest.keyClick(w, Qt.Key.Key_Escape)
    QTest.keyClick(w, Qt.Key.Key_F)
    h.check("f starts Place Ruler", w.ruler is not None and w.ruler.editable)
    w.apply_ruler()
    QTest.keyClick(w, Qt.Key.Key_Y)
    h.check("y opens Trim", w.trim_row.isVisible())
    QTest.keyClick(w, Qt.Key.Key_Y)
    QTest.keyClick(w, Qt.Key.Key_Escape)

    for key, speed in ((Qt.Key.Key_1, "25"), (Qt.Key.Key_2, "50"), (Qt.Key.Key_3, "100"),
                       (Qt.Key.Key_4, "150")):
        QTest.keyClick(w, key)
        h.check(f"the number key sets the speed to {speed}%",
                w.speed_btn.text() == f"Speed: {speed}%", w.speed_btn.text())

    # Plots would open a dialog: the key is checked by seeing that it presses the button
    w.plots_btn.clicked.disconnect()
    presses = []
    w.plots_btn.clicked.connect(lambda: presses.append(1))
    QTest.keyClick(w, Qt.Key.Key_P)
    h.check("p presses Plots", presses == [1], str(presses))

    QTest.keyClick(w, Qt.Key.Key_S)  # The flash check moved to the end: track from the start
    w._add_object(QRectF(*(ball_path(0)[0] - 20, ball_path(0)[1] - 20, 40, 40)))
    w.object_list.setCurrentRow(0)
    QTest.keyClick(w, Qt.Key.Key_T)
    h.check("t starts tracking, and the button now says Stop",
            w.job is not None and w.track_btn.text() == "Stop", w.track_btn.text())
    h.pump(lambda: w.job is None, 60)
    h.check("tracking finishes, and the object is tracked", w.objects[0].boxes and
            w.track_btn.text() == "Track")
    QTest.keyClick(w, Qt.Key.Key_V)
    h.check("v clears the selected object's track", w.objects[0].boxes == {})
    QTest.keyClick(w, Qt.Key.Key_D)
    h.check("d removes the selected object", w.objects == [])
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    print("test_keys")
    test_keys()
    h.finish()
