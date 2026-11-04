"""
Main window of the Qt spike: a left sidebar of tool buttons, the video view, and a seek bar with
trim controls under it. Experimental; the real app is the Tk one in the parent folder.

Tracking: Mark Rectangle (drag a box, as many as wanted), then Track runs from the current frame to
the end of the trim (or of the video). The view follows the tracker live; scrubbing stays free.
Measuring: Place Ruler (its real length and unit give the scale) and Place Axis (the origin and
direction) turn the tracked positions into physical values; Plots shows them, and Export Data
writes them to CSV. Projects save the whole setup next to the video (see project_file.py).

History and agents (docs/AGENT_PLAN.md): every change is an event in the History dock (click one
to go back to it); there can be any number of trials, each a tab (windows.py, tab_window.py); the agent tools
(agent/tools.py) drive these same methods, and Space stops an agent that is working.
"""

import copy
import math
import os
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence, QPen, QShortcut
from PySide6.QtWidgets import (QDialog, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QProgressBar, QPushButton, QSlider, QVBoxLayout,
                               QWidget)

from core.autoaxis import snap_axis
from core.autoruler import snap_ruler
from core.units import parse_length

from . import plot_warmup, project_file, recent, session, windows
from .axes_item import AxesItem
from .history import History, HistoryPanel
from .measure import export_csv, physical, track_series
from .ruler_item import RulerItem
from .tracked_object import OutlineItem, TrackedObject
from .track_methods import BY_KEY, DEFAULT as DEFAULT_METHOD, TrackDialog, engine_settings
from .tracking import TrackJob
from .video_source import VideoSource
from .autodetect import DEFAULT_TOLERANCE, find_object, outline_relative
from .key_button import KeyButton
from .video_view import TOOL_AUTO, TOOL_BOX, TOOL_CIRCLE, TOOL_CLICK, TOOL_MOVE, TOOL_NONE, VideoView

SIDEBAR_WIDTH = 170
FLASH_STYLE = "QPushButton { border: 3px solid #ff2020; }"  # The red outline shown when a button is pressed
FLASH_MS = 400
SPEEDS = [0.25, 0.5, 1.0, 1.5]  # Playback speeds, in the order the Speed button steps through them


RULER_HALF_WIDTH = 15  # Auto Ruler: half the bar's width, in picture pixels (the object lies within it)



def _run_key(method: str, settings: dict, start: int, end: int) -> tuple:
    """What a track was made with (an object's tracked_with): equal keys give the same track."""
    return (method, tuple(sorted(settings.items())), start, end)


def _run_to_json(run):
    return None if run is None else {"method": run[0], "settings": dict(run[1]), "start": run[2], "end": run[3]}


def _run_from_json(data):
    return None if not data else _run_key(data["method"], data["settings"], data["start"], data["end"])

class MainWindow(QMainWindow):
    host = None   # The TabWindow this trial is a tab of (None: a window of its own)

    def __init__(self, cache_dir: str) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.wid = windows.add(self)          # "w1", "w2"...: how agents and the user name this window
        self.plots: dict = {}                 # Plot settings: {"kinds": [...], "fits": {kind: {"model", "range"}}}
        self.history = History(self._snapshot, lambda: self.statusBar().currentMessage())
        self.source = VideoSource(cache_dir)
        self.source.progress.connect(self._on_progress)
        self.source.proxy_ready.connect(self._on_proxy_ready)
        self.source.failed.connect(self._on_failed)
        self.axes: AxesItem | None = None
        self.ruler: RulerItem | None = None
        self.trim = None            # (start, end) frames once a trim is applied
        self._pending_frame = None  # Latest frame asked for by the seek bar, drawn once per batch
        self._loading = False       # A video is being opened (load_video): its proxy may be ready at once
        self.objects: list[TrackedObject] = []
        self.job: TrackJob | None = None
        self.track_method = DEFAULT_METHOD     # The method Track last ran with (offered first next time)
        self.track_options: dict = {}          # Method -> its options as last chosen
        self.track_method_used = DEFAULT_METHOD  # The method of the run under way (or the last one)
        self.last_track: dict | None = None    # How the last run went (for the agent tools)
        self.agent_track = False               # The run under way was started by an agent (Space stops it)
        self._move_from = None                  # The selected box when a Move drag began
        self._job_objects: list = []           # The objects the running job tracks (in its order)
        self.ask_track_method = True           # Track first asks for the method (tests turn it off)
        self._live_frame = None     # Latest frame the tracker finished, shown at most 30 times a s
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(33)
        self._live_timer.timeout.connect(self._follow_tracker)
        self._play_timer = QTimer(self)       # Playback: moves the seek bar on by the time passed
        self._play_timer.setInterval(16)
        self._play_timer.timeout.connect(self._play_tick)
        self._playing = False
        self._play_from = (0, 0.0)            # (frame, time) the playback started from
        self._speed = SPEEDS.index(1.0)
        self.project_path: str | None = None  # Where the project is saved, once it has been
        self._dirty = False                   # Changed since it was last saved or opened
        self._plot_windows: list = []         # Kept referenced, so the plot windows stay open
        QTimer.singleShot(1500, plot_warmup.start)   # Plots open fast: matplotlib and scipy load early
        self.candidate: OutlineItem | None = None  # An automatically found object, awaiting confirmation
        self._found: dict | None = None            # Its outline and box
        self._last_box = None                      # The box it was found in, found again when tuned

        # Menu: grouped as a browser's File menu is (new and open; close and save; export)
        file_menu = self.menuBar().addMenu("File")
        self._action(file_menu, "New Tab", lambda: windows.new_window(host=self.host), "Ctrl+T")
        self._action(file_menu, "New Window", lambda: windows.new_window(separate=True), "Ctrl+N")
        self._action(file_menu, "Reopen Closed Tab", lambda: windows.reopen_closed(), "Ctrl+Shift+T")
        self._action(file_menu, "Open Video…", self.choose_video, "Ctrl+Shift+O")
        self._action(file_menu, "Open Project…", self.open_project, "Ctrl+O")
        self.recent_menu = file_menu.addMenu("Open Recent")
        self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        file_menu.addSeparator()
        self._action(file_menu, "Close Window", lambda: self.window().close(), "Ctrl+Shift+W")   # Every tab in it
        self._action(file_menu, "Close Tab", self.close_tab, "Ctrl+W")
        self._action(file_menu, "Save Project", self.save_project, "Ctrl+S")
        self._action(file_menu, "Save Project As…", self.save_project_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        self._action(file_menu, "Export Data (CSV)…", self.export_data)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        side = QVBoxLayout(sidebar)
        self.import_btn = KeyButton("Import Video", "i")
        self.trim_btn = KeyButton("Trim", "y")
        self.ruler_btn = KeyButton("Place Ruler", "f")
        self.axis_btn = KeyButton("Place Axis", "g")
        self.mark_btn = KeyButton("Mark Rectangle", "r")
        self.circle_btn = KeyButton("Mark Circle", "c")
        self.find_btn = KeyButton("Auto Object", "z")
        self.track_btn = KeyButton("Track", "t")
        self.plots_btn = KeyButton("Plots", "p")
        self.export_btn = QPushButton("Export Data")
        self.start_btn = KeyButton("Video Start", "s")  # Bottom of the sidebar: jump to the trim
        self.end_btn = KeyButton("Video End", "e")
        self.speed_btn = KeyButton("", "1-4")
        for button, action in ((self.import_btn, self.choose_video),
                               (self.trim_btn, self.toggle_trim),
                               (self.ruler_btn, self.start_ruler),
                               (self.axis_btn, self.start_axis),
                               (self.mark_btn, self.start_mark),
                               (self.circle_btn, self.start_circle),
                               (self.find_btn, self.start_auto),
                               (self.track_btn, self.toggle_track),
                               (self.plots_btn, lambda: self.show_plots()),   # Not clicked's bool as kinds
                               (self.export_btn, self.export_data),
                               (self.start_btn, self.go_start),
                               (self.end_btn, self.go_end),
                               (self.speed_btn, self.cycle_speed)):
            button.setMinimumHeight(40)
            button.clicked.connect(action)
        side.addWidget(self.import_btn)
        side.addWidget(self.trim_btn)
        side.addWidget(self.ruler_btn)
        # The ruler's own buttons, shown while it is being placed
        self.ruler_panel = QFrame()
        panel = QVBoxLayout(self.ruler_panel)
        panel.setContentsMargins(0, 0, 0, 0)
        self.set_length_btn = QPushButton("Set Length…")
        self.auto_btn = QPushButton("Auto Ruler")
        self.undo_btn = QPushButton("Undo Auto Ruler")
        self.apply_btn = QPushButton("Apply Ruler")
        self.remove_btn = QPushButton("Remove Ruler")
        for button, action in ((self.set_length_btn, self.set_ruler_length),
                               (self.auto_btn, self.auto_ruler),
                               (self.undo_btn, self.undo_auto_ruler),
                               (self.apply_btn, self.apply_ruler),
                               (self.remove_btn, self.remove_ruler)):
            button.setMinimumHeight(32)
            button.clicked.connect(action)
            panel.addWidget(button)
        self.undo_btn.setEnabled(False)
        self.ruler_panel.hide()
        side.addWidget(self.ruler_panel)
        side.addWidget(self.axis_btn)
        # The axes' own buttons, shown once they are placed
        self.axes_panel = QFrame()
        panel = QVBoxLayout(self.axes_panel)
        panel.setContentsMargins(0, 0, 0, 0)
        self.auto_axis_btn = QPushButton("Auto Axis")
        self.auto_axis_btn.setToolTip("Turn the axes to line up with the straight line nearest one "
                                      "of them (a tube, a track), sliding the origin onto it")
        self.undo_axis_btn = QPushButton("Undo Auto Axis")
        for button, action in ((self.auto_axis_btn, lambda: self.auto_axis()),  # Not clicked's bool
                               (self.undo_axis_btn, self.undo_auto_axis)):
            button.setMinimumHeight(32)
            button.clicked.connect(action)
            panel.addWidget(button)
        self.undo_axis_btn.setEnabled(False)
        self.axes_panel.hide()
        side.addWidget(self.axes_panel)
        side.addWidget(self.mark_btn)
        side.addWidget(self.circle_btn)
        side.addWidget(self.find_btn)
        # Confirm an automatically found object before it is tracked
        self.candidate_panel = QFrame()
        confirm = QVBoxLayout(self.candidate_panel)
        confirm.setContentsMargins(0, 0, 0, 0)
        # Higher selects more; the outline is found again as it moves (higher = more of the picture)
        self.tolerance_label = QLabel()
        self.tolerance = QSlider(Qt.Orientation.Horizontal)
        self.tolerance.setRange(0, 100)
        self.tolerance.setValue(int(DEFAULT_TOLERANCE))
        self.tolerance.valueChanged.connect(self._tolerance_changed)
        self._tune_timer = QTimer(self)  # Finds again once the slider has settled
        self._tune_timer.setSingleShot(True)
        self._tune_timer.setInterval(200)
        self._tune_timer.timeout.connect(self._retune)
        confirm.addWidget(self.tolerance_label)
        confirm.addWidget(self.tolerance)
        self._show_tolerance()
        for text, action in (("Accept Object", self.accept_candidate),
                             ("Try Again", self.start_auto),
                             ("Cancel", self.cancel_candidate)):
            button = QPushButton(text)
            button.setMinimumHeight(32)
            button.clicked.connect(action)
            confirm.addWidget(button)
        self.candidate_panel.hide()
        side.addWidget(self.candidate_panel)
        side.addWidget(self.track_btn)
        side.addWidget(self.plots_btn)
        side.addWidget(self.export_btn)
        side.addStretch()
        side.addWidget(self.start_btn)
        side.addWidget(self.end_btn)
        side.addWidget(self.speed_btn)
        self._show_speed()
        self.video_buttons = (self.trim_btn, self.ruler_btn, self.axis_btn, self.mark_btn,
                              self.circle_btn, self.find_btn, self.track_btn, self.plots_btn,
                              self.export_btn, self.start_btn, self.end_btn, self.speed_btn)
        for button in self.video_buttons:
            button.setEnabled(False)

        # Video view
        self.view = VideoView()
        self.view.clicked.connect(self._place_axes)
        self.view.box_drawn.connect(self._add_object)
        self.view.dragged.connect(self._move_drag)
        self.view.zoom_changed.connect(lambda z: self.zoom_label.setText(f"zoom {z:.2f}x"))

        # Seek bar, frame number, and the trim row (shown while trimming)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setEnabled(False)
        self.seek.valueChanged.connect(self._seek_to)
        self.frame_label = QLabel("no video")
        self.frame_label.setMinimumWidth(130)
        seek_row = QHBoxLayout()
        seek_row.addWidget(self.seek, 1)
        seek_row.addWidget(self.frame_label)

        self.trim_row = QWidget()
        trim = QHBoxLayout(self.trim_row)
        trim.setContentsMargins(0, 0, 0, 0)
        self.trim_start_btn = QPushButton("Start here")
        self.trim_end_btn = QPushButton("End here")
        self.trim_label = QLabel()
        self.trim_label.setMinimumWidth(320)  # Room for the range and the warning
        apply_btn = QPushButton("Apply Trim")
        clear_btn = QPushButton("Whole Video")
        self.trim_start_btn.clicked.connect(lambda: self._mark_trim(0))
        self.trim_end_btn.clicked.connect(lambda: self._mark_trim(1))
        apply_btn.clicked.connect(self._apply_trim)
        clear_btn.clicked.connect(self._clear_trim)
        for w in (self.trim_start_btn, self.trim_end_btn, self.trim_label):
            trim.addWidget(w)
        trim.addStretch()
        trim.addWidget(clear_btn)
        trim.addWidget(apply_btn)
        self.trim_row.hide()
        self._trim_marks = [0, 0]

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 8, 8)
        right.addWidget(self.view, 1)
        right.addLayout(seek_row)
        right.addWidget(self.trim_row)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(sidebar)
        body.addLayout(right, 1)
        central = QWidget()
        central.setLayout(body)
        self.setCentralWidget(central)

        # Status bar: messages on the left; load progress, zoom and draw time on the right
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.hide()
        self.zoom_label = QLabel()
        self.draw_label = QLabel()
        self.agent_label = QLabel()   # Shown while an agent works: Space stops it
        self.agent_label.setStyleSheet("QLabel { color: white; background: #3a7bd5; padding: 1px 6px; }")
        self.agent_label.hide()
        for w in (self.agent_label, self.progress, self.zoom_label, self.draw_label):
            self.statusBar().addPermanentWidget(w)
        self.statusBar().showMessage("Import a video to start")
        self._build_object_dock()
        self._build_history_dock()
        self._build_assistant_dock()
        windows.AGENT.changed.connect(self._show_agent)

        # One frame at a time with the arrows; Escape ends a tool; zoom from the keyboard
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self._step(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self._step(1))
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self._cancel_tool)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._space)   # Plays, or stops a working agent
        # Letters act as pressing the button labelled with them (a disabled button does nothing)
        for key, button in ((Qt.Key.Key_I, self.import_btn), (Qt.Key.Key_Y, self.trim_btn),
                            (Qt.Key.Key_F, self.ruler_btn), (Qt.Key.Key_G, self.axis_btn),
                            (Qt.Key.Key_S, self.start_btn), (Qt.Key.Key_E, self.end_btn),
                            (Qt.Key.Key_Z, self.find_btn), (Qt.Key.Key_R, self.mark_btn),
                            (Qt.Key.Key_C, self.circle_btn), (Qt.Key.Key_T, self.track_btn),
                            (Qt.Key.Key_P, self.plots_btn), (Qt.Key.Key_V, self.clear_obj_btn),
                            (Qt.Key.Key_D, self.remove_obj_btn), (Qt.Key.Key_M, self.move_obj_btn)):
            QShortcut(QKeySequence(key), self, button.click)
        # [ and ] shrink and grow the selected object by a pixel (its size line does it by dragging)
        QShortcut(QKeySequence(Qt.Key.Key_BracketLeft), self, lambda: self.resize_selected(-1))
        QShortcut(QKeySequence(Qt.Key.Key_BracketRight), self, lambda: self.resize_selected(1))
        for index, key in enumerate((Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4)):
            QShortcut(QKeySequence(key), self, lambda i=index: self.set_speed(i))
        self.seek.sliderPressed.connect(self._pause)  # Scrubbing stops playback
        QShortcut(QKeySequence("Ctrl+0"), self, self.view.fit)  # Cmd 0 on macOS, as in the Tk app
        QShortcut(QKeySequence("Ctrl+="), self, lambda: self.view.zoom_by(1.25))
        QShortcut(QKeySequence("Ctrl+-"), self, lambda: self.view.zoom_by(1 / 1.25))
        # Every button flashes a red outline when pressed, by mouse or by its key, so the press is seen
        self._flash_timers: dict[QPushButton, QTimer] = {}
        for button in self.findChildren(QPushButton):
            button.clicked.connect(lambda _=False, b=button: self._flash(b))
        self._title()

    @staticmethod
    def _action(menu, text: str, slot, shortcut: str | None = None) -> QAction:
        action = QAction(text, menu)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action

    # --- Import ----------------------------------------------------------------------------------
    def choose_video(self) -> None:
        """Import Video: picks a video, or a project (which opens its video and setup)."""
        if not self._confirm_discard():
            return
        videos = "*.mp4 *.mov *.m4v *.avi *.mkv"
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Video or Project", self._browse_folder(),
            f"Videos and projects ({videos} *{project_file.EXTENSION});;"
            f"Videos ({videos});;Projects (*{project_file.EXTENSION});;All (*)")
        if not path:
            return
        if path.lower().endswith(project_file.EXTENSION):
            self.open_project_file(path)
        else:
            self.load_video(path)

    def _browse_folder(self) -> str:
        """Where a file dialog starts: the folder of the open video, else home."""
        if self.source.path:
            return os.path.dirname(os.path.abspath(self.source.path))
        return os.path.expanduser("~")

    def load_video(self, path: str) -> bool:
        """Shows the video at once; scrubbing gets faster when the proxy is ready. A new video
        starts a new, unsaved project."""
        t0 = time.perf_counter()
        self._loading = True   # A proxy that is there already is ready at once, inside load: nothing to redraw yet
        try:
            loaded = self.source.load(path)
        finally:
            self._loading = False
        if not loaded:
            return False
        self.project_path = None
        self._on_opened()
        self._dirty = False
        self._title()
        session.update(self)
        name = os.path.basename(path)
        self.history.reset()   # A new video is a new history, starting from it
        self.history.log("open", f"Opened {name}", {"video": name})
        took = (time.perf_counter() - t0) * 1000
        if self.source.has_proxy:
            self.statusBar().showMessage(f"{name}: {self.source.fcount} frames, "
                                         f"{self.source.fps_text} (opened in {took:.0f} ms)")
        else:
            self._proxy_since = time.perf_counter()
            self.progress.setRange(0, 100)
            self.progress.setFormat("%p%")
            self.progress.setValue(0)
            self.progress.show()
            self.statusBar().showMessage(f"{name} opened in {took:.0f} ms. Making a copy for fast "
                                         "scrubbing; you can look around meanwhile")
        return True

    def _on_progress(self, fraction: float) -> None:
        self.progress.setValue(round(fraction * 100))

    def _on_proxy_ready(self) -> None:
        self.progress.hide()
        if hasattr(self, "_proxy_since"):
            took = time.perf_counter() - self._proxy_since
            self.statusBar().showMessage(f"Fast scrubbing ready ({took:.1f} s)")
        if not self._loading:
            self._show(self.seek.value())  # Same frame, now from the proxy

    def _on_opened(self) -> None:
        self._pause()
        if self.job is not None:
            self.job.stop()
        self._clear_setup()       # The setup belongs to the old video
        self.plots = {}
        for window in self.plot_windows():   # And so do its plots
            window.close()
        self.seek.blockSignals(True)
        self.seek.setRange(0, max(0, self.source.fcount - 1))
        self.seek.setValue(0)
        self.seek.blockSignals(False)
        self.seek.setEnabled(True)
        for button in self.video_buttons:
            button.setEnabled(True)
        self._show(0)   # (Also what a project's boxes are fitted to: the size of the picture, see _fit_state)

    def _clear_setup(self) -> None:
        """Removes the objects, axes, ruler and trim (a new video, or a revert that puts others back)."""
        self._end_tools()
        self._drop_candidate()
        for obj in self.objects:
            obj.remove()
        self.objects.clear()
        self._refresh_objects()
        self.trim = None
        self.trim_row.hide()
        if self.axes is not None:
            self.view.scene().removeItem(self.axes)
            self.axes = None
        self.axes_panel.hide()
        self.undo_axis_btn.setEnabled(False)
        if self.ruler is not None:
            self.view.scene().removeItem(self.ruler)
            self.ruler = None
        self.ruler_panel.hide()
        self.undo_btn.setEnabled(False)

    def _on_failed(self, message: str) -> None:
        self.progress.hide()
        self.statusBar().clearMessage()
        QMessageBox.warning(self, "Import Video", message)

    # --- Projects --------------------------------------------------------------------------------
    def _touch(self, op: str = "edit", params: dict | None = None) -> None:
        """Something changed: the project now needs saving, and the history gets an event `op`
        (committed after a short pause, so a drag is one event)."""
        if not self._dirty:
            self._dirty = True
            self._title()
        self.history.note(op, params)

    def _file_name(self) -> str | None:
        """The project's file name, else the video's, else None."""
        if self.project_path:
            return os.path.basename(self.project_path)
        if self.source.path:
            return os.path.basename(self.source.path)
        return None

    def tab_name(self) -> str:
        """The tab's text: the project or video, starred if it has unsaved changes."""
        name = self._file_name()
        return f"{name}{' *' if self._dirty else ''}" if name else "New Tab"

    def _title(self) -> None:
        name = self._file_name()
        star = " *" if self._dirty else ""
        self.setWindowTitle(f"PhysTrackX (Qt spike) [{self.wid}]" + (f" – {name}{star}" if name else ""))

    def _confirm_discard(self) -> bool:
        """True if the current project may be replaced or closed: unchanged, or the user chose to
        discard it, or chose to save and the save worked."""
        if not self._dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved Changes")
        box.setText("Save the changes to this project?")
        save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == save:
            return self.save_project()
        return clicked == discard

    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", os.path.expanduser("~"),
                                              f"Projects (*{project_file.EXTENSION});;All (*)")
        if path:
            self.open_project_file(path)

    def open_project_file(self, path: str) -> bool:
        try:
            state = project_file.load(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Open Project", str(e))
            return False
        if not os.path.isfile(state["video"]):
            QMessageBox.warning(self, "Open Project",
                                f"The video for this project is missing:\n{state['video']}")
            return False
        if not self.load_video(state["video"]):
            return False
        self.history.paused = True   # Opening is one event, not one per thing put back
        try:
            self._apply_state(state)
        finally:
            self.history.paused = False
        imported = state.get("imported")
        # An imported file is never saved over: Save writes a new project next to the video
        self.project_path = None if imported is not None else path
        self._dirty = imported is not None
        recent.remember(path)
        self._title()
        if imported is not None:
            parts = [f"Imported the Tk project {os.path.basename(path)}: the objects start at their "
                     "marked boxes, to track again."]
            if imported["left_out"]:
                parts.append(f"Not carried over: {'; '.join(imported['left_out'])}.")
            parts += [f"Check: {note}." for note in imported["check"]]
            self.statusBar().showMessage(" ".join(parts), 20000)
        else:
            self.statusBar().showMessage(f"Opened {os.path.basename(path)}")
        self.history.reset()
        self.history.cookbook = list(state.get("cookbook", []))   # The saves and exports of the trial that made it
        self.history.log("open", f"Opened project {os.path.basename(path)}",
                         {"project": os.path.basename(path)})
        session.update(self)
        return True

    def _fill_recent_menu(self) -> None:
        self.recent_menu.clear()
        paths = recent.load()
        if not paths:
            self.recent_menu.addAction("No recent projects").setEnabled(False)
            return
        for path in paths:
            action = self.recent_menu.addAction(f"{os.path.basename(path)}   ({os.path.dirname(path)})")
            action.triggered.connect(lambda _=False, p=path: self._open_recent(p))
        self.recent_menu.addSeparator()
        self.recent_menu.addAction("Clear Recent").triggered.connect(recent.forget_all)

    def _open_recent(self, path: str) -> None:
        if self._confirm_discard():
            self.open_project_file(path)

    def save_project(self) -> bool:
        """Saves without asking: to the project's file, or a new one next to the video, named after it."""
        if self.project_path is None:
            if not self.source.path:
                return False
            return self.save_project_file(project_file.new_project_path(self.source.path))
        return self.save_project_file(self.project_path)

    def save_project_as(self) -> bool:
        if not self.source.path:
            return False
        default = project_file.new_project_path(self.source.path)
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", default,
                                              f"Projects (*{project_file.EXTENSION})")
        if not path:
            return False
        if not path.endswith(project_file.EXTENSION):
            path += project_file.EXTENSION
        return self.save_project_file(path)

    def save_project_file(self, path: str) -> bool:
        try:
            project_file.save(path, {**self._project_state(), "cookbook": self.history.cookbook})
        except OSError as e:
            QMessageBox.warning(self, "Save Project", f"The project could not be saved:\n{e}")
            return False
        self.project_path = path
        self._dirty = False
        recent.remember(path)
        self._title()
        self.statusBar().showMessage(f"Saved the project to {os.path.abspath(path)}")
        self.history.log("save_project", f"Saved {os.path.basename(path)}", {"file": os.path.basename(path)})
        session.update(self)
        return True

    def _project_state(self, boxes: bool = True) -> dict:
        """Everything the project keeps: all in picture pixels, so it reopens at any window size.
        `boxes`: with each object's track (as JSON wants it: frame numbers as text)."""
        axes = None
        if self.axes is not None:
            p = self.axes.pos()
            axes = {"x": p.x(), "y": p.y(), "rotation": self.axes.rotation(),
                    "length": self.axes.length}
        ruler = None
        if self.ruler is not None:
            r = self.ruler
            ruler = {"p1": [r.p1.x(), r.p1.y()], "p2": [r.p2.x(), r.p2.y()],
                     "real_length": r.real_length, "unit": r.unit}
        objects = [{"number": o.number, "circle": o.circle, "outline": o.outline, "marked": list(o.marked),
                    "marked_frame": o.marked_frame, "changed": o.changed,
                    "tracked_with": _run_to_json(o.tracked_with),
                    "boxes": {str(f): (list(b) if b is not None else None)
                              for f, b in o.boxes.items()} if boxes else None}
                   for o in self.objects]
        return {"video": os.path.abspath(self.source.path),
                "picture": list(self.view.picture.pixmap().size().toTuple()),
                "frame": self.seek.value(),
                "trim": list(self.trim) if self.trim else None,
                "axes": axes, "ruler": ruler, "objects": objects,
                "plots": copy.deepcopy(self.plots)}

    def _snapshot(self) -> dict | None:
        """The history's snapshot, once a video is open: the project state, but cheap, as it is
        taken on every change (each move of a drag). Tracks are shallow copies (frame -> box
        tuple); _apply_state reads these as it reads a project file's."""
        if not self.source.path:
            return None
        state = self._project_state(boxes=False)
        for entry, obj in zip(state["objects"], self.objects):
            entry["boxes"] = dict(obj.boxes)
        return state

    def revert_to(self, n: int) -> bool:
        """Goes back to the history's event n (logged as an event, so it can be undone too)."""
        if self.job is not None:
            self.statusBar().showMessage("Stop tracking before going back in the history")
            return False
        snap = self.history.revert_target(n)
        if snap is None:
            return False
        self.history.paused = True   # Putting the snapshot back is the revert event, not more events
        try:
            self._pause()
            self._clear_setup()
            self.seek.setRange(0, max(0, self.source.fcount - 1))
            self._apply_state(snap)
        finally:
            self.history.paused = False
        self._dirty = True
        self._title()
        closed = " Plots whose data changed were closed (Plots opens them again)." \
            if self._close_stale_plots() else ""
        self.statusBar().showMessage(f"Back to #{n}. Click a later event to go forward again.{closed}")
        return True

    def _data_keys(self) -> dict:
        """Each object's measured track as a key (object number -> key): a plot drawn from other
        data (an older track, other axes or scale) is stale."""
        return {number: (len(t), round(float(xy.sum()), 6)) for number, _, t, xy in self._measured()}

    def _close_stale_plots(self) -> int:
        """Closes the plots that no longer show their object's data. Returns how many."""
        keys = self._data_keys()
        stale = [w for w in self.plot_windows() if keys.get(w.number) != getattr(w, "data_key", None)]
        for window in stale:
            window.close()
        return len(stale)

    def _fit_state(self, state: dict) -> dict:
        """The state with its positions scaled to the picture as it is now. The picture is the proxy
        once that is ready, so its size can differ from the one the project was saved at (or from a
        video imported from the Tk app, which is at the frame's size). Returns state itself if equal."""
        saved = state.get("picture")
        now = self.view.picture.pixmap().size()
        if not saved or not saved[0] or not saved[1] or list(saved) == [now.width(), now.height()]:
            return state
        kx, ky = now.width() / saved[0], now.height() / saved[1]
        state = copy.deepcopy(state)
        if state.get("axes"):
            state["axes"]["x"] *= kx
            state["axes"]["y"] *= ky
            state["axes"]["length"] *= (kx + ky) / 2
        if state.get("ruler"):
            state["ruler"]["p1"] = [state["ruler"]["p1"][0] * kx, state["ruler"]["p1"][1] * ky]
            state["ruler"]["p2"] = [state["ruler"]["p2"][0] * kx, state["ruler"]["p2"][1] * ky]
        for entry in state.get("objects", []):
            x, y, w, h = entry["marked"]
            entry["marked"] = [x * kx, y * ky, w * kx, h * ky]
            entry["boxes"] = {f: (None if b is None else [b[0] * kx, b[1] * ky, b[2] * kx, b[3] * ky])
                              for f, b in (entry.get("boxes") or {}).items()}
        state["picture"] = [now.width(), now.height()]
        return state

    def _apply_state(self, state: dict) -> None:
        """Puts a project's setup back on the video that was just loaded (or, for a revert, on the
        video cleared of its setup)."""
        state = self._fit_state(state)
        self.plots = copy.deepcopy(state.get("plots") or {})
        self._apply_plot_settings()
        trim = state.get("trim")
        # The frame is drawn once, at the end: not again, on the next turn, for the seek bar's signal (each
        # draw is a decode and an upload, about 25 ms)
        self.seek.blockSignals(True)
        try:
            if trim:
                self.trim = (int(trim[0]), int(trim[1]))
                self.seek.setRange(*self.trim)
            self.seek.setValue(min(max(int(state.get("frame", 0)), self.seek.minimum()),
                                   self.seek.maximum()))
        finally:
            self.seek.blockSignals(False)
        self._pending_frame = None   # A draw already asked for (a drag just before) would show an older frame
        ax = state.get("axes")
        if ax:
            self.axes = self._make_axes(ax["length"])
            self.axes.setPos(QPointF(ax["x"], ax["y"]))
            self.axes.setRotation(ax["rotation"])
        rl = state.get("ruler")
        if rl:
            self._add_ruler(QPointF(*rl["p1"]), QPointF(*rl["p2"]))
            if rl["real_length"] is not None:
                self.ruler.set_length(rl["real_length"], rl["unit"])
        for o in state.get("objects", []):
            obj = TrackedObject(o["number"], QRectF(*o["marked"]), o["marked_frame"],
                                self.view.picture, bool(o.get("circle", False)),
                                o.get("outline"))
            obj.on_move = self._object_dragged
            obj.boxes = {int(f): (tuple(b) if b is not None else None)
                         for f, b in o["boxes"].items()}
            obj.changed = bool(o.get("changed", True))
            obj.tracked_with = _run_from_json(o.get("tracked_with"))
            obj.draw_trail()
            self.objects.append(obj)
        self._refresh_objects()
        self._show(self.seek.value())

    # --- Seeking ---------------------------------------------------------------------------------
    def _seek_to(self, index: int) -> None:
        """Seek bar moved. A drag sends many moves; only the latest is drawn, once they are handled."""
        first = self._pending_frame is None
        self._pending_frame = index
        if first:
            QTimer.singleShot(0, self._draw_pending)

    def _draw_pending(self) -> None:
        index, self._pending_frame = self._pending_frame, None
        if index is not None:
            self._show(index)

    def _show(self, index: int) -> None:
        t0 = time.perf_counter()
        frame = self.source.frame(index)
        t1 = time.perf_counter()
        self.view.show_frame(frame, index)
        t2 = time.perf_counter()
        for obj in self.objects:
            obj.show_frame(index)
        self.frame_label.setText(self.frame_text(index))
        self.draw_label.setText(f"decode {(t1 - t0) * 1000:.0f} ms, upload {(t2 - t1) * 1000:.0f} ms")

    def _step(self, delta: int) -> None:
        self._pause()  # Stepping by hand stops playback
        if self.seek.isEnabled():
            self.seek.setValue(self.seek.value() + delta)  # Clamped to the (trimmed) range

    # --- Playback --------------------------------------------------------------------------------
    # Space plays and pauses. Playback moves by the time passed, so it keeps its speed when frames
    # are slow to draw (frames are skipped rather than played late). It stops at the trim's end.
    def _show_speed(self) -> None:
        self.speed_btn.setText(f"Speed: {SPEEDS[self._speed] * 100:.0f}%")

    def cycle_speed(self) -> None:
        self.set_speed((self._speed + 1) % len(SPEEDS))

    def set_speed(self, index: int) -> None:
        """Sets the speed to SPEEDS[index]; keys 1 to 4 choose 25, 50, 100 and 150 percent."""
        if not self.speed_btn.isEnabled():
            return
        self._flash(self.speed_btn)
        self._speed = index
        self._show_speed()
        if self._playing:  # Carry on from the frame shown, at the new speed
            self._play_from = (self.seek.value(), time.perf_counter())

    def toggle_play(self) -> None:
        if self._playing:
            self._pause()
        else:
            self._play()

    def _play(self) -> None:
        if not self.seek.isEnabled() or self.job is not None or not self.source.has_proxy:
            return
        if self.seek.value() >= self.seek.maximum():  # At the end: play again from the start
            self.seek.setValue(self.seek.minimum())
        self._play_from = (self.seek.value(), time.perf_counter())
        self._playing = True
        self._play_timer.start()
        self.statusBar().showMessage(f"Playing at {SPEEDS[self._speed] * 100:.0f}%. Space pauses")

    def _flash(self, button: QPushButton) -> None:
        """A thick red outline on the button for a moment. A press that comes again restarts it."""
        if button not in self._flash_timers:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda b=button: b.setStyleSheet(""))
            self._flash_timers[button] = timer
        button.setStyleSheet(FLASH_STYLE)
        self._flash_timers[button].start(FLASH_MS)

    def _pause(self) -> None:
        if self._playing:
            self._playing = False
            self._play_timer.stop()
            self.statusBar().showMessage("Paused. Space plays")

    def _play_tick(self) -> None:
        frame, t0 = self._play_from
        fps = self.source.fps or 30.0
        target = frame + (time.perf_counter() - t0) * fps * SPEEDS[self._speed]
        if target >= self.seek.maximum():
            self.seek.setValue(self.seek.maximum())
            self._pause()
            return
        self.seek.setValue(int(target))

    # --- Trim ------------------------------------------------------------------------------------
    # The spike only limits the seek bar to a range. The Tk app also writes a trimmed (and cropped)
    # clip with media.trimvideo; that comes later.
    def toggle_trim(self) -> None:
        if self.trim_row.isVisible():
            self.trim_row.hide()
            return
        self._end_tools()
        self._trim_marks = list(self.trim) if self.trim else [0, self.source.fcount - 1]
        self.seek.setRange(0, self.source.fcount - 1)  # The whole video while choosing
        self._show_trim_marks()
        self.trim_row.show()
        self.statusBar().showMessage("Move to the first frame and press Start here, then the last "
                                     "and press End here")

    def go_start(self) -> None:
        """The first frame of the trimmed video (the first frame, if there is no trim)."""
        self.seek.setValue(self.trim[0] if self.trim else 0)

    def go_end(self) -> None:
        """The last frame of the trimmed video (the last frame, if there is no trim)."""
        self.seek.setValue(self.trim[1] if self.trim else self.source.fcount - 1)

    def _mark_trim(self, which: int) -> None:
        self._trim_marks[which] = self.seek.value()
        self._show_trim_marks()

    def _show_trim_marks(self) -> None:
        start, end = self._trim_marks
        bad = start >= end
        self.trim_label.setText(f"frames {start} to {end}" + ("  (start must be before end)"
                                                               if bad else ""))

    def _apply_trim(self) -> None:
        start, end = self._trim_marks
        if start >= end:
            return
        self.trim = (start, end)
        self.seek.setRange(start, end)
        self.trim_row.hide()
        self._touch("trim", {"start": start, "end": end})
        self.statusBar().showMessage(f"Trimmed to frames {start} to {end} ({end - start + 1} frames)")

    def _clear_trim(self) -> None:
        self.trim = None
        self.seek.setRange(0, self.source.fcount - 1)
        self.trim_row.hide()
        self._touch("trim")
        self.statusBar().showMessage("Whole video")

    # --- Ruler -----------------------------------------------------------------------------------
    def start_ruler(self) -> None:
        self._end_tools()
        self.trim_row.hide()
        if self.ruler is None:
            size = self.view.picture.boundingRect()
            centre = size.center()
            half = 0.15 * size.width()
            self._add_ruler(QPointF(centre.x() - half, centre.y()),
                            QPointF(centre.x() + half, centre.y()))
        self.ruler.set_editable(True)
        self.ruler_panel.show()
        self.statusBar().showMessage("Drag the ends or the bar. Double-click the ruler, or Set "
                                     "Length, to give its real length. Apply Ruler when done")

    def _add_ruler(self, p1: QPointF, p2: QPointF) -> None:
        self.ruler = RulerItem(p1, p2, self.view.picture)
        self.ruler.changed.connect(self._on_ruler_changed)
        self.ruler.length_requested.connect(self.set_ruler_length)

    def _on_ruler_changed(self) -> None:
        self._touch("ruler")
        self.undo_btn.setEnabled(self.ruler.can_undo())
        self._report_ruler()

    def _report_ruler(self) -> None:
        r = self.ruler
        if r.real_length is None:
            text = (f"Ruler: {r.px_length():.0f} picture pixels. Double-click it, or Set Length, "
                    "to give its real length")
        else:
            text = f"Ruler: {r.label_text()}. One picture pixel is {r.scale():.4g} {r.unit_label()}"
        self.statusBar().showMessage(text)

    def set_ruler_length(self) -> None:
        if self.ruler is None:
            return
        r = self.ruler
        current = f"{r.real_length:g} {r.unit}".strip() if r.real_length is not None else ""
        text, ok = QInputDialog.getText(
            self, "Scale Calibration",
            "Enter the real-world length this ruler represents, with its unit (e.g. 50 cm):",
            QLineEdit.EchoMode.Normal, current)
        if not ok:
            return
        try:
            value, unit = parse_length(text)
        except ValueError as e:
            QMessageBox.warning(self, "Scale Calibration",
                                f"{e}.\nEnter a length such as 50 or 50 cm.")
            return
        r.set_length(value, unit)

    def auto_ruler(self) -> None:
        """Moves the ends onto the edges of the object the ruler lies along (core.autoruler)."""
        if self.ruler is None:
            return
        frame = self.source.frame(self.seek.value())
        p1, p2 = self.ruler.p1, self.ruler.p2
        try:
            q1, q2 = snap_ruler(frame, (p1.x(), p1.y()), (p2.x(), p2.y()), side="left",
                                half_width=RULER_HALF_WIDTH)
        except ValueError as e:
            QMessageBox.warning(self, "Auto Ruler", str(e))
            return
        self.ruler.snap_to(q1, q2)
        self.statusBar().showMessage("Auto Ruler moved the ends onto the object's ends. Undo Auto "
                                     "Ruler puts them back")

    def undo_auto_ruler(self) -> None:
        if self.ruler is not None:
            self.ruler.undo_snap()

    def apply_ruler(self) -> None:
        if self.ruler is None:
            return
        self.ruler.set_editable(False)
        self.ruler_panel.hide()
        self._report_ruler()

    def remove_ruler(self) -> None:
        if self.ruler is None:
            return
        self.view.scene().removeItem(self.ruler)
        self.ruler = None
        self.ruler_panel.hide()
        self.undo_btn.setEnabled(False)
        self._touch("ruler")
        self.statusBar().showMessage("Ruler removed")

    # --- Axes ------------------------------------------------------------------------------------
    def _make_axes(self, length: float) -> AxesItem:
        axes = AxesItem(length, self.view.picture)
        axes.changed.connect(self._report_axes)
        axes.changed.connect(lambda: self._touch("axes"))
        axes.changed.connect(lambda: self.undo_axis_btn.setEnabled(axes.can_undo()))
        self.axes_panel.show()
        self.undo_axis_btn.setEnabled(False)
        return axes

    def start_axis(self) -> None:
        self._end_tools()
        self.trim_row.hide()
        self.view.set_tool(TOOL_CLICK)
        self.statusBar().showMessage("Click on the picture to place the origin (Escape to cancel)")

    def _place_axes(self, point) -> None:
        self.view.set_tool(TOOL_NONE)
        if self.axes is None:
            size = self.view.picture.boundingRect()
            self.axes = self._make_axes(0.3 * min(size.width(), size.height()))
        self.axes.setPos(point)
        self._touch("axes")
        self._report_axes()

    def _report_axes(self) -> None:
        p = self.axes.pos()
        self.statusBar().showMessage(f"Axes: origin ({p.x():.1f}, {p.y():.1f}) px, "
                                     f"angle {self.axes.angle():.1f}°. Drag a line to move, the "
                                     "handle to rotate")

    def auto_axis(self, axis: str | None = None) -> str | None:
        """Lines the axes up with the straight line nearest them (core.autoaxis): mostly a turn,
        with the origin slid a little onto the line. `axis` is "x" or "y"; by default both are
        tried, and the one along the stronger line is used. Returns the axis lined up, or None
        (with a message) when neither lies along a line."""
        if self.axes is None:
            return None
        try:
            found = self._find_axis_line(axis)
        except ValueError as e:
            QMessageBox.warning(self, "Auto Axis", str(e))
            return None
        which, origin, rotation = found
        old_pos, old_rot = self.axes.pos(), self.axes.rotation()
        self.axes.snap_to(origin, rotation)
        slide = math.hypot(origin[0] - old_pos.x(), origin[1] - old_pos.y())
        self.statusBar().showMessage(
            f"Auto Axis lined the {which} axis up with the line beside it: turned "
            f"{rotation - old_rot:+.2f}°, origin moved {slide:.1f} px. Undo Auto Axis puts it back")
        return which

    def _find_axis_line(self, axis: str | None = None) -> tuple[str, tuple[float, float], float]:
        """(axis, origin, rotation) of the snapped axes; ValueError when no line is found."""
        frame = self.source.frame(self.seek.value())
        p = self.axes.pos()
        found, errors = [], []
        for which in ((axis,) if axis else ("x", "y")):
            try:
                origin, rotation, strength = snap_axis(frame, (p.x(), p.y()), self.axes.rotation(),
                                                       which)
                found.append((strength, which, origin, rotation))
            except ValueError as e:
                errors.append(str(e))
        if not found:
            raise ValueError(errors[0] + " Put an axis roughly along the line first (within 10°).")
        _, which, origin, rotation = max(found)
        return which, origin, rotation

    def undo_auto_axis(self) -> None:
        if self.axes is not None:
            self.axes.undo_snap()

    # --- Tools -----------------------------------------------------------------------------------
    def _end_tools(self) -> None:
        """Ends whichever tool is waiting for the mouse. A ruler being placed is applied."""
        self.view.set_tool(TOOL_NONE)
        self.move_obj_btn.setChecked(False)
        if self.ruler is not None and self.ruler.editable:
            self.apply_ruler()

    def _cancel_tool(self) -> None:
        if self.candidate is not None:
            self.cancel_candidate()
        if self.view.tool != TOOL_NONE or (self.ruler is not None and self.ruler.editable):
            self._end_tools()
            self.statusBar().clearMessage()

    # --- Mark and track --------------------------------------------------------------------------
    def start_mark(self) -> None:
        self._start_marking(TOOL_BOX, "Drag a box around the object (Escape when done)")

    def start_circle(self) -> None:
        self._start_marking(TOOL_CIRCLE, "Drag from the centre of the object out to its edge "
                                         "(Escape when done)")

    def _start_marking(self, tool: str, message: str) -> None:
        self._end_tools()
        self.trim_row.hide()
        self.view.set_tool(tool)
        self.statusBar().showMessage(message)

    def start_auto(self) -> None:
        self._start_marking(TOOL_AUTO, "Drag a loose box around the object, or click on it. Its "
                                       "outline is shown for you to check")

    def _add_object(self, box, kind: str = "box") -> None:
        """A box, a circle's square, or an auto box was dragged out. The tool stays on, so several
        objects can be marked in a row."""
        if kind == "auto":
            self._find_object(box)
            return
        frame = self.seek.value()
        circle = kind == "circle"
        obj = TrackedObject(self._next_number(), box, frame, self.view.picture, circle)
        obj.on_move = self._object_dragged
        self.objects.append(obj)
        self._refresh_objects(select=obj)   # So D removes it at once, and it can be moved or sized
        self._touch("mark", {"n": obj.number})
        shape = "circle" if circle else "object"
        self.statusBar().showMessage(f"{shape.capitalize()} {obj.number} marked on frame {frame}. "
                                     "Mark another, or Escape when done, then Track (D removes it)")

    def toggle_track(self) -> None:
        if self.job is not None:
            self._stop_track()
            return
        self._end_tools()
        self._pause()
        if not self.objects:
            QMessageBox.information(self, "Track", "Mark an object first.")
            return
        if not self.source.has_proxy:
            QMessageBox.information(self, "Track", "The fast copy of the video is still being made; "
                                    "Track can start once it is ready.")
            return
        start = self.seek.value()
        end = self.trim[1] if self.trim else self.source.fcount - 1
        if start >= end:
            QMessageBox.information(self, "Track", "Move to a frame before the end first.")
            return
        if not self.ask_track_method:
            self.start_track(self.track_method, self.track_options.get(self.track_method))
            return
        # Pick the method before running (Enter takes the last one used)
        dialog = TrackDialog(self, self.track_method, self.track_options, len(self.objects), end - start + 1)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        method, options = dialog.chosen()
        self.track_method = method
        self.track_options = dict(dialog.options, **{method: options})
        self.start_track(method, options)

    def start_track(self, method: str = DEFAULT_METHOD, options: dict | None = None) -> None:
        """Tracks every object from the current frame to the end (of the trim) with `method`
        (track_methods.METHODS) and its options (each method's defaults where not given)."""
        start = self.seek.value()
        end = self.trim[1] if self.trim else self.source.fcount - 1
        if start >= end or not self.objects or not self.source.has_proxy:
            return
        # Only objects that are new, were moved or resized, or were tracked another way or over
        # another range are tracked; the others keep their tracks
        run = _run_key(method, engine_settings(BY_KEY[method], options or {}), start, end)
        todo = [o for o in self.objects if o.changed or not o.boxes or o.tracked_with != run]
        if not todo:
            self.statusBar().showMessage(
                f"Nothing to track: every object is already tracked from {self.frame_text(start)} with "
                f"{BY_KEY[method].title}. Move or resize an object, or pick another method, to track again")
            return
        # Each object starts from its box as shown on this frame (the marked box, or where the last
        # run had it here, or where the user moved it), so tracking can be restarted from any
        # frame. Its track before this frame is kept: only the part from here on is tracked again
        boxes, outlines = [], []
        for obj in todo:
            r = obj.rect.rect()
            boxes.append((r.x(), r.y(), r.width(), r.height()))
            outlines.append(obj.outline)
            obj.keep_before(start, first=self.trim[0] if self.trim else 0)
            obj.restart_frame = None
            obj.tracked_with = run
        self._job_objects = todo
        self.job = TrackJob(self.source.proxy_path, boxes, start, end, method, options, outlines)
        self.job.tracked.connect(self._on_tracked)
        self.job.shown.connect(self._on_shown)
        self.job.progress.connect(self._on_track_progress)
        self.job.path.connect(self._on_path)
        self.job.finished.connect(self._on_track_done)
        self.job.failed.connect(self._on_track_failed)
        self._track_method_title = BY_KEY[method].title
        self.track_method_used = method
        self._track_t0, self._track_range = time.perf_counter(), (start, end)
        self.progress.setRange(0, 1000)   # The whole run: every object and pass, once
        self.progress.setFormat(self.frame_text(start))
        self.progress.setValue(0)
        self.progress.show()
        self.track_btn.setText("Stop")
        self.mark_btn.setEnabled(False)
        self.circle_btn.setEnabled(False)
        self.find_btn.setEnabled(False)
        self._update_object_buttons()
        self._live_timer.start()
        self.job.run()

    # --- Auto Object -----------------------------------------------------------------------------
    def _show_tolerance(self) -> None:
        self.tolerance_label.setText(f"Tolerance: {self.tolerance.value()}")

    def _tolerance_changed(self, _value: int) -> None:
        self._show_tolerance()
        if self._last_box is not None:
            self._tune_timer.start()  # Found again once the slider stops moving

    def _retune(self) -> None:
        if self._last_box is not None:
            self._find_object(self._last_box, retuning=True)

    def _find_object(self, box, retuning: bool = False) -> None:
        """Finds the object in the box, and shows its outline for the user to accept or redo. A new box
        starts again; a retune keeps the box and the panel."""
        self._last_box = box
        self._drop_candidate(hide_panel=not retuning)
        frame = self.source.frame(self.seek.value())
        try:
            found = find_object(frame, (box.x(), box.y(), box.width(), box.height()),
                                self.tolerance.value())
        except ValueError as e:
            self.statusBar().showMessage(str(e))
            if not retuning:
                QMessageBox.information(self, "Auto Object", str(e))
            return
        bx, by, bw, bh = found["bbox"]
        self._found = {"box": (bx, by, bw, bh), "outline": outline_relative(found["points"], found["bbox"])}
        self.candidate = OutlineItem(QRectF(bx, by, bw, bh), self.view.picture, False,
                                     self._found["outline"])
        pen = QPen(QColor("#ffffff"), 2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self.candidate.setPen(pen)
        self.candidate.setZValue(4)
        self.candidate_panel.show()
        self.statusBar().showMessage(f"Found an object of about {found['area']:.0f} pixels. Accept it "
                                     "to track it, or Try Again with a tighter box")

    def accept_candidate(self) -> None:
        if self._found is None:
            return
        bx, by, bw, bh = self._found["box"]
        frame = self.seek.value()
        obj = TrackedObject(self._next_number(), QRectF(bx, by, bw, bh), frame, self.view.picture,
                            False, self._found["outline"])
        obj.on_move = self._object_dragged
        self._last_box = None
        self._drop_candidate()
        self.objects.append(obj)
        self._refresh_objects(select=obj)
        self._touch("mark", {"n": obj.number, "auto": True})
        self._show(frame)
        self.statusBar().showMessage(f"Object {obj.number} accepted on frame {frame}. Mark another, "
                                     "or Escape when done, then Track")

    def cancel_candidate(self) -> None:
        self._last_box = None
        self._drop_candidate()
        self.statusBar().showMessage("Cancelled")

    def _drop_candidate(self, hide_panel: bool = True) -> None:
        if self.candidate is not None:
            self.view.scene().removeItem(self.candidate)
        self.candidate = None
        self._found = None
        if hide_panel:
            self.candidate_panel.hide()

    def _on_tracked(self, index: int, boxes: list) -> None:
        for obj, box in zip(self._job_objects, boxes):
            obj.add(index, box)
        self._live_frame = index

    def _follow_tracker(self) -> None:
        """Draws the trails and the status, at most 30 times a second (the picture is _on_shown)."""
        if self._live_frame is None:
            return
        self._live_frame = None
        for obj in self._job_objects:
            obj.draw_trail()

    def frame_text(self, index: int) -> str:
        """A frame as the app names it everywhere: "frame 123 / 1178" (of the whole video)."""
        return f"frame {index} / {self.source.fcount - 1}"

    def _on_track_progress(self, stage: str, index: int, fraction: float) -> None:
        """The run's progress: the bar fills once over all objects and passes, and says the frame
        it is on, as beside the seek bar."""
        self.progress.setValue(round(1000 * min(max(fraction, 0.0), 1.0)))
        self.progress.setFormat(self.frame_text(index))
        self.statusBar().showMessage(f"{stage}: {self.frame_text(index)}")

    def _on_path(self, k: int, boxes: list) -> None:
        """An object's best path so far (whole clip), from the run's first frame on."""
        if k >= len(self._job_objects):
            return
        obj = self._job_objects[k]
        start = self._track_range[0]
        # The path replaces the track from the run's start on; the frames before it are kept
        kept = {f: b for f, b in obj.boxes.items() if f < start}
        obj.boxes = {**kept, **{start + i: box for i, box in enumerate(boxes)}}
        obj.draw_trail()
        obj.show_frame(self.seek.value())

    def _on_shown(self, index: int, frame) -> None:
        """A frame from the tracker's own reader, drawn as it is: no decoding on this thread."""
        self.view.show_frame(frame, index)
        for obj in self.objects:
            obj.show_frame(index)
        self.seek.blockSignals(True)  # Moves the bar without seeking again
        self.seek.setValue(index)
        self.seek.blockSignals(False)
        self.frame_label.setText(self.frame_text(index))

    def _on_track_done(self, completed: bool) -> None:
        self._end_track()
        start, end = self._track_range
        ran = self._job_objects
        done = max((max(o.boxes) for o in ran if o.boxes), default=start) - start
        took = time.perf_counter() - self._track_t0
        lost = sum(1 for o in ran for f, b in o.boxes.items() if f >= start and b is None)   # This run's
        for obj in ran:
            obj.changed = not completed   # A stopped run's objects are tracked again next time
        kept = len(self.objects) - len(ran)
        self.last_track = {"frames": done, "lost": lost, "s": round(took, 1), "completed": completed}
        self._touch("track", {"method": self.track_method_used, "completed": completed})
        closed = self._close_stale_plots()   # Plots of the old track
        self.statusBar().showMessage(
            f"{'Tracked' if completed else 'Stopped after'} {done} frames in {took:.1f} s "
            f"({done / max(took, 1e-6):.0f} frames/s) with {self._track_method_title}, "
            f"{len(ran)} object(s), {lost} lost frame(s)"
            + (f"; {kept} unchanged object(s) kept their tracks" if kept else "")
            + ("; plots of the old track were closed (Plots opens them again)" if closed else ""))

    def _on_track_failed(self, message: str) -> None:
        for obj in self._job_objects:
            obj.changed = True
        self._end_track()
        QMessageBox.warning(self, "Track", message)

    def _stop_track(self) -> None:
        """Stops at once: the button says so straight away, and results still queued from the
        tracker are dropped. The tracker finishes the frame it is on (a few milliseconds)."""
        self.job.stop()
        self.job.tracked.disconnect(self._on_tracked)
        self.job.shown.disconnect(self._on_shown)
        self.job.progress.disconnect(self._on_track_progress)
        self.track_btn.setText("Stopping…")
        self.track_btn.setEnabled(False)

    def _end_track(self) -> None:
        self._live_timer.stop()
        self.progress.hide()
        self._follow_tracker()  # The whole trail
        self.job = None
        self.agent_track = False
        self.track_btn.setText("Track")
        self.track_btn.setEnabled(True)
        self.mark_btn.setEnabled(True)
        self.circle_btn.setEnabled(True)
        self.find_btn.setEnabled(True)
        last = max((max(o.boxes) for o in self._job_objects if o.boxes), default=None)
        if last is not None:  # The picture is the last frame tracked (a stopped run may not have shown it)
            self._show(last)
        self._refresh_objects()

    # --- Measurements, plots and export ----------------------------------------------------------
    def _unit(self) -> str:
        return self.ruler.unit_label() if self.ruler is not None else "px"

    def _measured(self) -> list:
        """(object number, frames, times in s, physical (x, y)) for each object with tracked
        frames. Empty until the axes are placed."""
        if self.axes is None or self.source.measure_fps <= 0:
            return []
        origin = self.axes.pos()
        rotation = self.axes.rotation()
        scale = self.ruler.scale() if self.ruler is not None else 1.0
        rows = []
        for obj in self.objects:
            frames, centres = track_series(obj.boxes, self.source.measure_fps)
            if len(frames) < 2:
                continue
            xy = physical(centres, (origin.x(), origin.y()), rotation, scale)
            rows.append((obj.number, frames, frames / self.source.measure_fps, xy))
        return rows

    def show_plots(self, kinds: list | None = None) -> list:
        """Opens the plots `kinds` for every tracked object (asks which when not given). A plot that
        is open already is kept (and brought up), not opened twice. Returns the plot windows."""
        from .plot_window import DEFAULT_KINDS, choose_plots, open_plots  # matplotlib and scipy: loaded on first use (startup)
        self._end_tools()
        if not isinstance(kinds, (list, tuple)):   # A signal's argument (clicked passes a bool): ask
            kinds = None
        asked = kinds is None
        if self.axes is None:
            if asked:
                QMessageBox.information(self, "Plots", "Place the axes first: the plots are measured "
                                        "from their origin.")
            return []
        series = self._measured()
        if not series:
            if asked:
                QMessageBox.information(self, "Plots", "Track an object first.")
            return []
        if asked:
            kinds = choose_plots(self, self.plots.get("kinds") or DEFAULT_KINDS)
            if not kinds:
                return []
        self._close_stale_plots()   # An open plot of older data is replaced, not brought up
        open_now = {(w.number, w.kind): w for w in self.plot_windows()}
        shown = []
        for number, _, t, xy in series:
            todo = [k for k in kinds if (number, k) not in open_now]
            for window in open_plots(number, t, xy, self._unit(), todo, self.source.path):
                window.data_key = (len(t), round(float(xy.sum()), 6))   # As _data_keys
                self._plot_windows.append(window)
                window.on_saved = lambda message, w=window: self._plot_saved(w, message)
                if window.fit_panel is not None:
                    window.fit_panel.on_change = lambda w=window: self._fit_changed(w)
                shown.append(window)
            for k in kinds:
                if (number, k) in open_now:
                    open_now[(number, k)].raise_()
                    shown.append(open_now[(number, k)])
        self.plots["kinds"] = list(dict.fromkeys(list(self.plots.get("kinds", [])) + list(kinds)))
        self._apply_plot_settings()
        fits = self.plots.setdefault("fits", {})
        for window in shown:   # A kind's first plot: its default model and range are the settings
            if window.fit_panel is not None:
                fit = fits.setdefault(window.kind, {})
                fit.setdefault("model", window.fit_panel.model)
                fit.setdefault("range", [float(v) for v in window.fit_panel.range])
        params = {"kinds": list(kinds)}
        first = next((fits[k] for k in kinds if k in fits), None)
        if first:   # The fit is in the event, so the agent (and the user) can tell refits apart
            params["model"] = first.get("model")
            if first.get("range"):
                params["range"] = [round(v, 3) for v in first["range"]]
        self.history.log("plots", f"Plots {', '.join(kinds)}", params)
        return shown

    def plot_windows(self) -> list:
        """The open plot windows of this window's video."""
        self._plot_windows = [w for w in self._plot_windows if w.isVisible()]   # Closed ones go
        return list(self._plot_windows)

    def _apply_plot_settings(self) -> None:
        """The fit model and range of each kind, as the settings say, on the open plots.
        QUICK-AND-DIRTY: settings are per kind (every object's r plot shares one), and a revert
        sets the model and range of open plots but does not redraw their data."""
        self._applying_plots = True
        try:
            fits = self.plots.get("fits") or {}
            # A fit range copied from another trial counts from the end of the initial drop: put
            # it on this trial's drop, found on the object of that kind that drops most. With no plot
            # open it waits for one; and nothing is imported before then: the plots' libraries
            # (matplotlib, scipy) took 2.4 s of every start, with the window frozen
            for kind, fit in fits.items():
                if fit.get("from_low") and self.plot_windows():
                    from .analysis import drop_low
                    lows = [drop_low(w.fit_panel.t, w.fit_panel.y) for w in self.plot_windows()
                            if w.kind == kind and w.fit_panel is not None]
                    lows = [low for low in lows if low is not None]
                    if lows:
                        _, t_low, t_high = max(lows)
                        rel = fit.pop("from_low")
                        # A range that started at the source's release starts at this one's
                        start = t_high if fit.pop("from_high", False) else t_low + rel[0]
                        fit["range"] = [start, t_low + rel[1]]
            for window in self.plot_windows():
                fit = fits.get(window.kind)
                panel = window.fit_panel
                if fit is None or panel is None:
                    continue
                if fit["model"] != panel.model and fit["model"] in panel.keys:
                    if window.model_table is not None:
                        window.model_table.select(fit["model"])   # Its row; that chooses the model
                    panel.choose(fit["model"])
                if fit.get("range"):
                    lo, hi = fit["range"]
                    if abs(lo - panel.range[0]) > 1e-6 or abs(hi - panel.range[1]) > 1e-6:
                        panel.set_range(lo, hi)
        finally:
            self._applying_plots = False

    def _fit_changed(self, window) -> None:
        """A plot's model or range changed: kept in the settings (and so in the history)."""
        if getattr(self, "_applying_plots", False):
            return
        panel = window.fit_panel
        fits = self.plots.setdefault("fits", {})
        fit = {"model": panel.model, "range": [float(panel.range[0]), float(panel.range[1])]}
        if fits.get(window.kind) != fit:
            fits[window.kind] = fit
            self._touch("fit", {"kind": window.kind, "model": panel.model,
                                "range": [round(v, 3) for v in fit["range"]]})

    def _plot_saved(self, window, message: str) -> None:
        self.statusBar().showMessage(message)
        params = {"kind": window.kind, "n": window.number}
        if window.fit_panel is not None:
            params.update(window.fit_panel.summary())
        self.history.log("save_plots", f"Saved plot {window.kind} of object {window.number}", params)

    def export_data(self) -> str | None:
        """Writes every object's positions to CSV next to the video. Returns the path."""
        series = self._measured()
        if not series:
            QMessageBox.information(self, "Export Data", "Place the axes and track an object first.")
            return None
        # No questions: every object, next to the video, named after it
        path = project_file.output_path(self.source.path, "_data", ".csv")
        try:
            export_csv(path, series, self._unit())
        except OSError as e:
            QMessageBox.warning(self, "Export Data", f"The data could not be saved:\n{e}")
            return None
        self.statusBar().showMessage(f"Exported {len(series)} object(s) to {path}")
        self.history.log("export_csv", f"Exported {os.path.basename(path)}", {"file": os.path.basename(path)})
        return path

    # --- Objects ---------------------------------------------------------------------------------
    def _build_object_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.object_list = QListWidget()
        self.object_list.itemSelectionChanged.connect(self._update_object_buttons)
        layout.addWidget(self.object_list, 1)
        self.move_obj_btn = KeyButton("Move", "m")
        self.move_obj_btn.setCheckable(True)
        self.move_obj_btn.setToolTip("Drag anywhere on the picture to move the selected object; "
                                     "drag the knob on its line, or press [ and ], to resize it")
        self.move_obj_btn.toggled.connect(self._move_mode)
        self.clear_obj_btn = KeyButton("Clear Track", "v")
        self.remove_obj_btn = KeyButton("Remove", "d")
        self.remove_all_btn = QPushButton("Remove All")
        self.clear_obj_btn.clicked.connect(self.clear_object_track)
        self.remove_obj_btn.clicked.connect(self.remove_object)
        self.remove_all_btn.clicked.connect(self.remove_all_objects)
        for button in (self.move_obj_btn, self.clear_obj_btn, self.remove_obj_btn, self.remove_all_btn):
            layout.addWidget(button)
        for key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):  # Backspace is Delete on a Mac
            shortcut = QShortcut(QKeySequence(key), self.object_list)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.remove_object)
        dock = QDockWidget("Objects", self)
        dock.setWidget(panel)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.object_dock = dock
        self._update_object_buttons()

    def _build_assistant_dock(self) -> None:
        """The assistant, under the history: the app's one conversation with the local model
        (agent/session.py); every window shows it."""
        from .agent.chat_panel import ChatPanel
        from .agent.session import shared
        self.assistant_panel = ChatPanel(shared(), focus_after_send=self.view)
        dock = QDockWidget("Assistant", self)
        dock.setWidget(self.assistant_panel)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.splitDockWidget(self.history_dock, dock, Qt.Orientation.Vertical)
        self.resizeDocks([self.object_dock, self.history_dock, dock], [2, 3, 4], Qt.Orientation.Vertical)
        self.assistant_dock = dock

    def _build_history_dock(self) -> None:
        """The history, under the objects: every change, newest last; a click goes back to one.
        The assistant's dock goes under it (_build_assistant_dock)."""
        self.history_panel = HistoryPanel(self.history, self.revert_to)
        dock = QDockWidget("History", self)
        dock.setWidget(self.history_panel)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.splitDockWidget(self.object_dock, dock, Qt.Orientation.Vertical)
        self.resizeDocks([self.object_dock, dock], [1, 1], Qt.Orientation.Vertical)
        self.history_dock = dock

    # --- Agent -----------------------------------------------------------------------------------
    def _space(self) -> None:
        """Space stops an agent that is working: while one of its calls runs, that is all it does.
        Between its calls (an agent thinking, or done) it stops the agent and still plays and
        pauses, so Space never stops playing the video for an agent that has finished."""
        gate = windows.AGENT
        if gate.busy():
            gate.stop()
            self.statusBar().showMessage("Agent stopped. Correct what you need (the history shows "
                                         "it), then tell the agent to resume")
            return
        if gate.running():
            gate.stop()
        self.toggle_play()

    def _show_agent(self) -> None:
        gate = windows.AGENT
        if gate.stopped:
            self.agent_label.setText("🤖 Agent stopped: tell it to resume")
            self.agent_label.show()
        elif gate.running():
            self.agent_label.setText("Agent running, 'space' to stop")
            self.agent_label.show()
            if gate.calls == 0:   # Idle: the label goes once it counts as not working any more
                QTimer.singleShot(int(gate.ACTIVE_S * 1000) + 200, self._show_agent)
        else:
            self.agent_label.hide()

    def changeEvent(self, event) -> None:
        # A tab's window (its TabWindow) says which tab is active; every tab gets that window's activation
        if event.type() == event.Type.ActivationChange and self.isWindow() and self.isActiveWindow():
            windows.activated(self.wid)
        super().changeEvent(event)

    def _next_number(self) -> int:
        return max((o.number for o in self.objects), default=0) + 1

    def _selected_object(self) -> TrackedObject | None:
        items = self.object_list.selectedItems()
        if not items:
            return None
        number = items[0].data(Qt.ItemDataRole.UserRole)
        return next((o for o in self.objects if o.number == number), None)

    def _refresh_objects(self, select: TrackedObject | None = None) -> None:
        """The list shows every object: its frames tracked, or the frame it was marked on. The
        selection is kept, or moves to `select`."""
        selected = select or self._selected_object()
        selected_number = selected.number if selected else None
        self.object_list.blockSignals(True)
        self.object_list.clear()
        for obj in self.objects:
            tracked = sorted(f for f, b in obj.boxes.items() if b is not None)
            lost = sum(1 for b in obj.boxes.values() if b is None)
            name = "Circle" if obj.circle else "Object"
            if tracked:
                text = f"{name} {obj.number}: frames {tracked[0]} to {tracked[-1]}"
                text += f", {lost} lost" if lost else ""
            else:
                text = f"{name} {obj.number}: marked on frame {obj.marked_frame}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, obj.number)
            self.object_list.addItem(item)
            if obj.number == selected_number:
                self.object_list.setCurrentItem(item)
        self.object_list.blockSignals(False)
        self._update_object_buttons()

    def _update_object_buttons(self) -> None:
        """Object actions are off while a run is tracking, and need a selected object. The selected
        object is drawn thicker on the picture, and is the one that can be dragged there."""
        busy = self.job is not None
        selected = self._selected_object()
        for obj in self.objects:
            obj.set_selected(obj is selected, movable=obj is selected and not busy)
        has_selection = selected is not None
        self.move_obj_btn.setEnabled(has_selection and not busy)
        if self.move_obj_btn.isChecked() and (not has_selection or busy):
            self.move_obj_btn.setChecked(False)
        self.clear_obj_btn.setEnabled(has_selection and not busy)
        self.remove_obj_btn.setEnabled(has_selection and not busy)
        self.remove_all_btn.setEnabled(bool(self.objects) and not busy)

    def _object_dragged(self, obj: TrackedObject, box) -> None:
        """The user dragged a selected object's box on the picture. Before tracking, that moves where
        tracking starts; after it, it moves the box on the frame shown (where the object is tracked)."""
        rect = (box.x(), box.y(), box.width(), box.height())
        frame = self.seek.value()
        obj.changed = True   # Tracked again on the next run
        if obj.boxes:
            obj.boxes[frame] = rect
            obj.restart_frame = frame   # A correction part-way: tracking goes on from here
            obj.draw_trail()
        else:
            obj.marked = rect
        obj.show_frame(frame)
        self._touch("move", {"n": obj.number})
        self.statusBar().showMessage(f"Moved or resized object {obj.number} on frame {frame}; Track will "
                                     "track it again", 5000)

    def _move_mode(self, on: bool) -> None:
        """Move (M): a drag anywhere on the picture moves the selected object (no need to hit a small
        ball's box). Escape, another tool or Move again ends it."""
        if on:
            if self._selected_object() is None or self.job is not None:
                self.move_obj_btn.setChecked(False)
                return
            if self.view.tool not in (TOOL_NONE, TOOL_MOVE):
                self.view.set_tool(TOOL_NONE)
            self.trim_row.hide()
            self.view.set_tool(TOOL_MOVE)
            self.statusBar().showMessage(f"Move: drag anywhere on the picture to move object "
                                         f"{self._selected_object().number}; drag the knob on its line, "
                                         "or press [ and ], to resize it. Escape or M when done")
        elif self.view.tool == TOOL_MOVE:
            self.view.set_tool(TOOL_NONE)

    def _move_drag(self, start: QPointF, now: QPointF, done: bool) -> None:
        """A Move drag: the selected object's box follows it, and is the object's when it ends."""
        obj = self._selected_object()
        if obj is None:
            return
        if self._move_from is None:
            self._move_from = obj.rect.rect()
        box = self._move_from.translated(now - start)
        obj.rect.setRect(box)
        obj.show_handle(True)
        obj._place_label()
        if done:
            self._move_from = None
            if box != obj.rect.rect() or now != start:
                self._object_dragged(obj, box)

    def resize_selected(self, pixels: float) -> None:
        """[ and ]: the selected object a pixel smaller or bigger (in radius), about its centre."""
        obj = self._selected_object()
        if obj is None or self.job is not None or not obj.rect.isVisible():
            return
        obj.resize_by(pixels)

    def remove_object(self) -> None:
        obj = self._selected_object()
        if obj is None or self.job is not None:
            return
        obj.remove()
        self.objects.remove(obj)
        self._after_objects_change(f"Removed object {obj.number}")

    def clear_object_track(self) -> None:
        obj = self._selected_object()
        if obj is None or self.job is not None:
            return
        obj.clear_track()
        self._after_objects_change(f"Cleared the track of object {obj.number}")

    def remove_all_objects(self) -> None:
        if self.job is not None or not self.objects:
            return
        answer = QMessageBox.question(self, "Remove All",
                                      f"Remove all {len(self.objects)} objects and their tracks?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        for obj in self.objects:
            obj.remove()
        self.objects.clear()
        self._after_objects_change("All objects removed")

    def _after_objects_change(self, message: str) -> None:
        self._refresh_objects()
        self._show(self.seek.value())
        self._touch("objects")
        self._close_stale_plots()   # A removed object's plots, or a cleared track's
        self.statusBar().showMessage(message)

    # --- Window ----------------------------------------------------------------------------------
    _confirmed_close = False   # Set by close_tab, after its unsaved-changes check: the close does not ask again

    def closeEvent(self, event) -> None:
        if self._confirmed_close or self._confirm_discard():
            event.accept()
            if self.job is not None:
                self.job.stop()
            if self.source.path:
                windows.remember_closed(self._closed_entry())
            windows.remove(self.wid)
            session.forget(self.wid)
            if self.host is not None:
                self.host.remove(self)
        else:
            event.ignore()

    def close_tab(self) -> None:
        """Cmd+W (Ctrl+W), or the tab's close button: closes this trial after the unsaved-changes check (on its
        tab, shown first). The tab to its right is shown next, else the one to its left. The last tab of the
        last window is not closed: a blank tab takes its place, so the app stays open. The last tab of
        another window closes that window."""
        if self.host is not None:
            if self._dirty:
                windows.focus(self)
            if not self._confirm_discard():
                return
            self._confirmed_close = True
            host = self.host
            if len(host.trials()) == 1 and windows.hosts() == [host]:
                windows.new_window(host=host)
            self.close()
            return
        # A window of its own (no tab bar): the window opened after it comes to the front
        if not self._confirm_discard():
            return
        self._confirmed_close = True
        following = windows.neighbour(self.wid)
        if following is None:
            blank = windows.new_window()
            self.close()
            windows.focus(blank)
            return
        windows.focus(windows.get(following))
        self.close()

    def _closed_entry(self) -> dict:
        """What reopening a closed trial needs: its video, its project file if it has one, its setup as it was
        (saved or not), and whether it had changes."""
        return {"video": os.path.abspath(self.source.path), "project": self.project_path,
                "state": self._project_state(), "dirty": self._dirty, "cookbook": list(self.history.cookbook)}

    def restore_closed(self, entry: dict) -> bool:
        """Puts a closed trial back on this window (see _closed_entry). False if its video cannot be opened."""
        if not self.load_video(entry["video"]):
            return False
        self.history.cookbook = list(entry.get("cookbook", []))
        self.history.paused = True   # Putting the setup back is one event, as opening a project is
        try:
            self._apply_state(entry["state"])
        finally:
            self.history.paused = False
        self.project_path = entry["project"]
        self._dirty = entry["dirty"]
        self._title()
        session.update(self)
        return True
