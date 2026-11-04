"""
rigidapp.py

Main orchestrator interface for video-based tracking and visual instrumentation dashboards.
Includes hierarchical parent-handler session logging profiles.

Author: Isam Balghari
"""

import logging
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import BooleanVar, filedialog, messagebox

import cv2
import customtkinter as ctk
from PIL import Image, ImageTk

from core import PixelRect, NormalizedRect
from core import crash, recent, session
from gui.components.plot.csvdata import load_csv
from core.project import PROJECT_EXTENSION, new_project, read_project, write_project
from gui.app import App
from gui.components.view import ViewTransform
from gui.components.viewcontrols import ViewControls

# Component imports
from gui.components.spinner import Spinner
from gui.components.progressbar import ProgressBar
from gui.components.rects.rect import Rect
from gui.components.tpoints import TPoints
from gui.components.ruler import ScaleRuler
from gui.components.titlebar import TitleBar
from .video_app import Video

# Sub-module managers
from gui.components.seekbar import SeekBar, SeekMode
from gui.components.buttons import PluginsButton
from .plugins_manager import PluginManager
from .data_pipeline import DataPipelineManager


class _LoadProgress:
    """Load progress (0 to 100) set from the loader thread and read by ProgressBar.update.
    Keeps Tk variables off the worker thread."""

    def __init__(self) -> None:
        self._value = 0

    def set(self, value: int) -> None:
        self._value = value

    def get(self) -> int:
        return self._value


class RigidApp(App):
    """Main GUI application class for the PhysTrack Rigid tool."""
    
    def __init__(self, root, videopath: str | None = None, projectpath: str | None = None) -> None:
        super().__init__(root)
        # Worker threads (loading, trimming, tracking) must never run Tk code, and garbage
        # collection deletes Tk objects: keep it on this (the UI) thread
        crash.collect_on_ui_thread(root)
        self.projectpath: str | None = None
        self.trim_range: dict | None = None
        
        # Initialize component-specific logging namespace
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing high-level RigidApp workspace modules.")

        # 1. Instantiate Structural Sub-Managers
        self.plugin_mgr = PluginManager(self)
        self.pipeline_mgr = DataPipelineManager(self.videoview)
        self.saved_data: dict | None = None  # {"dir": folder, "files": [CSV paths]} once saved
        self.loaded_data = None  # CsvData read from the project's last saved CSV
        self.pipeline_mgr.saver.on_saved = self._on_data_saved
        self.seekbar = SeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self._scrub_soon)
        self.seekbar.set_trim_callback(self.trimvideo)

        # 2. Local Overlay Views
        self.track_rects = Rect(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.btnlist,
                                self.plugin_mgr.btnlist.get('rectangle'))

        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.btnlist,
                             self.plugin_mgr.btnlist.get('rectangle'))
        
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)

        # self.processanim = ProcessAnimation(self.videoview, self.plugin_mgr.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth,
                                       vheight=self.vheight)
        
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight,
                                  self.plugin_mgr.btnlist, self.plugin_mgr.btnlist.get("ruler"))

        # Video Backend Thread Attachment
        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.crop,
                              self.plugin_mgr.filters)

        # Zoom and pan: every overlay shares one view, so they all follow the picture
        self.view = ViewTransform()
        self.track_rects.view = self.view
        self.ocrrects.view = self.view
        self.tpoints.view = self.view
        self.axes.view = self.view
        self.scruler.view = self.view
        self.scruler.frame_source = lambda: self.videoapp.frame  # For Auto Ruler
        # The full-resolution copy for zoomed views arrives on a worker thread: redraw on the UI thread
        self.videoapp.on_native_ready = lambda: self._post_to_ui(self.updateframe)
        self.track_rects.on_apply = self._leave_marking
        self.ocrrects.on_apply = self._leave_marking
        self.axes.on_apply = self._leave_marking
        self.axes.on_cancel = self._leave_marking
        self.scruler.on_apply = self._leave_marking
        self.scruler.on_cancel = self._leave_marking
        self.viewcontrols = ViewControls(self.vidframe, self.view, on_change=self._on_view_change,
                                         on_shape=self._on_shape)
        self._bind_view_gestures()
        self._relayout_job = None
        self._loading = False  # True from loadvideo until the video is ready to be drawn
        self.videoview.bind("<Configure>", self._on_video_area_resized)

        # Crop step of the trim tool: crops the trimmed clip, not just the display
        self.cropstrip = ctk.CTkFrame(self.vidframe, fg_color="transparent")
        # Dark text on the cyan strips below the video (the default white is hard to read there)
        self.cropstatus = ctk.CTkLabel(self.cropstrip, text="", font=("Arial", 14, "bold"),
                                       text_color="black")
        self.cropstatus.pack(side="left", padx=10)
        ctk.CTkButton(self.cropstrip, text="Crop Region", width=110,
                      command=self._start_trim_crop).pack(side="left", padx=5)
        ctk.CTkButton(self.cropstrip, text="Clear Crop", width=100,
                      command=self._clear_trim_crop).pack(side="left", padx=5)
        # Tracking reads the full-size source, so measurements are not limited by the window's size
        self.fullres_var = BooleanVar(value=True)
        ctk.CTkCheckBox(self.cropstrip, text="Full resolution", variable=self.fullres_var,
                        text_color="black").pack(side="left", padx=15)
        # Segment Anything re-finds the object on hard frames (a hand moving beside the ball):
        # more reliable starts, but seconds per hard frame on a CPU, so it is off by default
        self.assist_var = BooleanVar(value=False)
        ctk.CTkCheckBox(self.cropstrip, text="Assist (Segment Anything, slow)",
                        variable=self.assist_var, text_color="black").pack(side="left", padx=15)
        self.plugin_mgr.crop.on_apply = self._update_crop_status

        # Tracking screen: stop, manual correction of positions, and the zoom bars
        self._live_on = False
        self._live_frame = None
        self._stop_requested = False
        self.manual_mode = False
        self._track_thread = None
        self.trackstrip = ctk.CTkFrame(self.vidframe, fg_color="transparent")
        self.trackstatus = ctk.CTkLabel(self.trackstrip, text="", font=("Arial", 14, "bold"),
                                        text_color="black")
        self.trackstatus.pack(side="left", padx=10)
        self.stopbtn = ctk.CTkButton(self.trackstrip, text="Stop", width=90, fg_color="#e03131",
                                     hover_color="#c92a2a", command=self._request_stop)
        self.stopbtn.pack(side="left", padx=5)
        self.manualbtn = ctk.CTkButton(self.trackstrip, text="Manual Position: Off", width=190,
                                       command=self._toggle_manual)
        self.manualbtn.pack(side="left", padx=5)
        # Throws away the tracked positions, so tracking can start again from the beginning
        self._clear_after_stop = False  # Set when Clear Data is pressed during a run
        self.cleardatabtn = ctk.CTkButton(self.trackstrip, text="Clear Data", width=110,
                                          command=self._clear_track_data)
        self.cleardatabtn.pack(side="left", padx=5)
        ctk.CTkButton(self.trackstrip, text="Close", width=90,
                      command=self._close_track_view).pack(side="left", padx=5)

        # Dynamic access alias configs
        # TODO: Abstract the button into plugin manager and remove this direct reference
        self.btnlist = self.plugin_mgr.btnlist
        self.pluginsbtn = PluginsButton(self.scrollframe, command=self.plugins, size=self.btnsize,
                                        tooltip="Toggle Plugins")
        self.pluginsbtn.pack(padx=self.padx/4, pady=self.pady/4)
        
        self.logger.info("RigidApp UI system fully mapped and operational.")

        self._build_menu()
        self._ui_queue = queue.Queue()
        self._pump_ui_queue()

        if projectpath:
            self._open_project(projectpath)
        elif videopath:
            self.videopath = videopath
            self._create_project(videopath)
            self.loadvideo(videopath)
        self._update_title()

    def _update_title(self) -> None:
        """Window title: the app, then the project and the video being edited."""
        parts = ["PhysTrackX"]
        if self.projectpath:
            parts.append(os.path.splitext(os.path.basename(self.projectpath))[0])
        if self.videopath:
            parts.append(os.path.basename(self.videopath))
        self.root.title(" - ".join(parts))

    def _build_menu(self) -> None:
        """The File menu in the menu bar at the top of the screen (the system bar on macOS)."""
        mac = sys.platform == "darwin"
        shown = "Cmd" if mac else "Ctrl"       # The shortcut as the menu shows it
        key = "Command" if mac else "Control"  # The name Tk binds to
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Video...", command=self._open_video_dialog)
        filemenu.add_command(label="Open Project...", command=self._open_project_dialog,
                             accelerator=f"{shown}+O")
        self.recentmenu = tk.Menu(filemenu, tearoff=0, postcommand=self._fill_recent_menu)
        filemenu.add_cascade(label="Open Recent", menu=self.recentmenu)
        filemenu.add_separator()
        filemenu.add_command(label="Save Project", command=self.savedata, accelerator=f"{shown}+S")
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)
        self.root.bind(f"<{key}-o>", lambda e: self._open_project_dialog())
        self.root.bind(f"<{key}-s>", lambda e: self.savedata())

    def _fill_recent_menu(self) -> None:
        """Lists the recent projects, newest first. Each shows its name and its folder."""
        self.recentmenu.delete(0, "end")
        paths = recent.load()
        if not paths:
            self.recentmenu.add_command(label="No recent projects", state="disabled")
            return
        for path in paths:
            name = os.path.splitext(os.path.basename(path))[0]
            folder = os.path.basename(os.path.dirname(path))
            self.recentmenu.add_command(label=f"{name}   ({folder})",
                                        command=lambda p=path: self._open_recent(p))
        self.recentmenu.add_separator()
        self.recentmenu.add_command(label="Clear Menu", command=recent.forget_all)

    def _open_video_dialog(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.MP4 *.MOV")])
        if path:
            self._start_session(videopath=path)

    def _open_project_dialog(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("PhysTrackX project", f"*{PROJECT_EXTENSION}")])
        if path:
            self._start_session(projectpath=path)

    def _open_recent(self, path: str) -> None:
        if not os.path.isfile(path):
            messagebox.showerror("Open Recent", f"The project file is no longer there:\n{path}")
            return
        self._start_session(projectpath=path)

    def _start_session(self, videopath: str | None = None, projectpath: str | None = None) -> None:
        """Closes what is open and opens a video or a project in its place (File menu)."""
        if self._live_on:
            messagebox.showinfo("Tracking", "Stop or finish tracking before opening another file.")
            return
        if self.projectpath:
            answer = messagebox.askyesnocancel(
                "Open", "Save the current project before opening another one?")
            if answer is None:
                return
            if answer:
                try:
                    write_project(self.projectpath, self.project_state())
                except OSError as e:
                    messagebox.showerror("Save project", f"Could not save the project:\n{e}")
                    return

        self._cancel_active_tools()
        self._reset_workspace()
        if projectpath:
            self._open_project(projectpath)
        else:
            self.videopath = videopath
            self._create_project(videopath)
            self.loadvideo(videopath)
        self._update_title()

    def _reset_workspace(self) -> None:
        """Clears everything placed on the current video, ready for another file."""
        self.clearcomponents()
        self.trim_range = None
        self.scruler.placed = False
        self.videoapp.clear()
        self.ocrrects.clear()
        self.track_rects.clear()
        self.seekbar.clear()
        self.plugin_mgr.crop.clear()
        self.plugin_mgr.geometry.reset()
        self.saved_data = None
        self.loaded_data = None
        self.projectpath = None
        self.videopath = None
        session.set_project(None)
        self.view.reset()
        self._leave_trim_mode()
        self._close_track_view()

    # Two-finger trackpad scrolls pan, and Cmd +/- zoom around the pointer. Pointer position and
    # scrolling use their own bind tag, so the canvas's bindings for axes and rectangles are kept.
    VIEW_TAG = "PhysTrackView"
    WHEEL_PIXELS = 40  # Pixels moved per mouse-wheel notch
    ZOOM_STEP = 1.25

    def _bind_view_gestures(self) -> None:
        tags = self.videoview.bindtags()
        self.videoview.bindtags(tags[:1] + (self.VIEW_TAG,) + tags[1:])
        self._pointer = None  # Last pointer position over the view; kept after it leaves
        self.root.bind_class(self.VIEW_TAG, "<Motion>", self._on_view_pointer)
        self.root.bind_class(self.VIEW_TAG, "<MouseWheel>", self._on_wheel)
        self.root.bind_class(self.VIEW_TAG, "<Shift-MouseWheel>", self._on_wheel_sideways)
        self.root.bind_class(self.VIEW_TAG, "<Button-4>", lambda e: self._pan_view(0, self.WHEEL_PIXELS))
        self.root.bind_class(self.VIEW_TAG, "<Button-5>", lambda e: self._pan_view(0, -self.WHEEL_PIXELS))
        try:
            # Tk 9 on macOS sends trackpad scrolls as precise pixel deltas, packed as x and y
            self.root.bind_class(self.VIEW_TAG, "<TouchpadScroll>", self._on_touchpad)
        except tk.TclError:
            pass  # Older Tk: the mouse-wheel bindings still work
        for key in ("equal", "plus", "KP_Add"):
            self.root.bind(f"<Command-{key}>", lambda e: self._zoom_by(self.ZOOM_STEP))
            self.root.bind(f"<Control-{key}>", lambda e: self._zoom_by(self.ZOOM_STEP))
        for key in ("minus", "KP_Subtract"):
            self.root.bind(f"<Command-{key}>", lambda e: self._zoom_by(1 / self.ZOOM_STEP))
            self.root.bind(f"<Control-{key}>", lambda e: self._zoom_by(1 / self.ZOOM_STEP))
        for key in ("0", "KP_0"):  # Back to the whole picture, as Reset View
            self.root.bind(f"<Command-{key}>", lambda e: self._reset_zoom())
            self.root.bind(f"<Control-{key}>", lambda e: self._reset_zoom())

    def _on_view_pointer(self, event) -> None:
        self._pointer = (event.x, event.y)

    def _on_wheel(self, event) -> None:
        self._pan_view(0, self._notches(event.delta) * self.WHEEL_PIXELS)

    def _on_wheel_sideways(self, event) -> None:
        self._pan_view(self._notches(event.delta) * self.WHEEL_PIXELS, 0)

    @staticmethod
    def _notches(delta: int) -> float:
        """Windows sends 120 per notch; macOS mice send small counts. Both become notches."""
        return delta / 120 if abs(delta) >= 120 else float(delta)

    def _on_touchpad(self, event) -> None:
        """Packs the x scroll in the high 16 bits and the y scroll in the low 16 (as Tk does)."""
        packed = int(event.delta)
        dx = packed >> 16
        low = packed & 0xFFFF
        dy = low if low < 0x8000 else low - 0x10000
        self._pan_view(dx, dy)

    def _pan_view(self, dx: float, dy: float) -> None:
        if self.videoapp.fcount < 10 or (dx == 0 and dy == 0):
            return
        self.view.pan(dx, dy)
        self._redraw_soon()

    def _zoom_by(self, factor: float) -> None:
        """Zooms by factor around the pointer's last position on the view (the centre if unknown)."""
        if self.videoapp.fcount < 10:
            return
        x, y = self._pointer or (self.videoview.winfo_width() / 2, self.videoview.winfo_height() / 2)
        self.view.zoom_at(x, y, self.view.zoom * factor)
        self._redraw_soon()

    def _reset_zoom(self) -> None:
        """Cmd 0: the whole picture again, as the Reset View button."""
        if self.videoapp.fcount < 10:
            return
        self.view.reset()
        self._redraw_soon()

    def _redraw_soon(self) -> None:
        """Redraws once the queued input is handled. A trackpad sends about 60 scroll events a
        second; drawing for each one queues work faster than it is done, so the picture trails the
        fingers. The view moves with every event, and the picture is drawn once per batch."""
        if getattr(self, "_redraw_pending", False):
            return
        self._redraw_pending = True

        def redraw():
            self._redraw_pending = False
            self.viewcontrols.sync()
            self._on_view_change()

        self.root.after_idle(redraw)

    def _create_project(self, videopath: str) -> None:
        """A video opened without a project gets a new project file next to the video (or in
        projects/ if that folder is read-only), so Save writes there and nothing is overwritten."""
        try:
            # Next to the video, so a trial's files stay together; projects/ if that folder
            # cannot be written to
            try:
                self.projectpath = new_project(videopath, canvas=(self.vwidth, self.vheight),
                                               folder=os.path.dirname(os.path.abspath(videopath)))
            except OSError:
                self.projectpath = new_project(videopath, canvas=(self.vwidth, self.vheight))
        except OSError as e:
            self.logger.exception("Could not create a project file")
            messagebox.showerror("Project", f"Could not create a project file:\n{e}")
            return
        session.set_project(self.projectpath)
        recent.remember(self.projectpath)
        self.logger.info(f"New project: {self.projectpath}")

    def _ensure_video_loaded(self) -> bool:
        """Internal interceptor safeguarding core functions from uninitialized states."""
        if self.videoapp.fcount < 10:
            self.logger.warning("User attempted context command block activation without verified"
                                " video payload frames.")
            messagebox.showerror("Error", "Please upload a video file first!")
            return False
        return True

    def _ensure_video_trimmed(self) -> bool:
        """Internal interceptor safeguarding core functions from uninitialized states."""
        if not self.seekbar.trimmed:
            self.logger.warning("User attempted context command block activation without verified"
                                " video trimming operation.")
            messagebox.showerror("Error", "Please trim the video first!")
            return False
        return True

    def _post_to_ui(self, fn) -> None:
        """Queues a callable to run on the Tk main thread. Worker threads must never call Tk
        directly (root.after included), or Tcl can crash."""
        self._ui_queue.put(fn)

    def _pump_ui_queue(self) -> None:
        """Runs queued UI callables on the main thread and reschedules itself."""
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            fn()
        self.root.after(50, self._pump_ui_queue)

    def loadvideo(self, videopath: str, on_done=None) -> None:
        self.logger.info(f"Asynchronous load requested for source asset: {videopath}")
        if self._live_on:
            messagebox.showinfo("Tracking", "Stop or finish tracking before loading another video.")
            return
        self._loading = True
        self.view.reset()
        self.viewcontrols.hide()
        self._leave_trim_mode()
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        self.spinner = Spinner(self.videoview, self.videoapp.imgview)

        # Progress is written by the loader thread and polled by the progress bar on the UI thread
        progress = _LoadProgress()
        self.progressbar.progress = progress
        self.progressbar.pack()
        self.videoview.tag_raise(self.progressbar.bholder)
        self.videoview.tag_raise(self.progressbar.bar)
        self.progressbar.update()

        threading.Thread(target=self._load_in_background, args=(videopath, progress, on_done),
                         daemon=True).start()

    def _load_in_background(self, videopath: str, progress: "_LoadProgress", on_done=None) -> None:
        """Runs on a worker thread: shows a preview frame, then builds the proxy video."""
        try:
            frame = self._read_first_frame(videopath)
            if frame is not None:
                self._post_to_ui(lambda: self._show_preview(frame))
            self.videoapp.loadvideo(videopath, on_progress=lambda f: progress.set(int(f * 100)))
        except Exception as e:
            self.logger.exception(f"Failed to load video: {videopath}")
            progress.set(100)
            # Python clears `e` when the except block ends, so the callback needs its own reference
            error = e
            self._post_to_ui(lambda: self._finish_failed_load(error))
            return

        progress.set(100)
        self._post_to_ui(lambda: self._finish_load(on_done))

    def _read_first_frame(self, videopath: str):
        """Reads the first frame of the source file. Seeking the original is fast, so this previews
        the video while the proxy is still encoding."""
        cap = cv2.VideoCapture(videopath, cv2.CAP_FFMPEG)
        ok, frame = cap.read()
        cap.release()
        return frame if ok else None

    def _show_preview(self, frame) -> None:
        """Shows a frame scaled to fit the video view, until the proxy is ready."""
        h, w = frame.shape[:2]
        scale = min(self.vwidth / w, self.vheight / h)
        size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = Image.fromarray(cv2.cvtColor(cv2.resize(frame, size), cv2.COLOR_BGR2RGB))
        self._preview_img = ImageTk.PhotoImage(image=img)
        self.videoapp.canvas.itemconfig(self.videoapp.imgview, image=self._preview_img)
        self.videoapp.canvas.coords(self.videoapp.imgview, 0, 0)

    def _finish_load(self, on_done=None) -> None:
        self._loading = False
        self.spinner.destroy()
        self.progressbar.destroy()
        self.loadcomponents()
        self.logger.info("Video streaming channel successfully integrated on UI thread.")
        if on_done:
            on_done()

    def _finish_failed_load(self, error: Exception) -> None:
        self._loading = False
        self.spinner.destroy()
        self.progressbar.destroy()
        messagebox.showerror("Error", f"Could not load the video:\n{error}")

    def _current_crop_rect(self) -> tuple[int, int, int, int] | None:
        """The crop chosen in the trim step as (x, y, w, h), with even sizes for the encoder."""
        r = self.plugin_mgr.crop.croprect
        if r is None:
            return None
        w, h = int(r.width) - int(r.width) % 2, int(r.height) - int(r.height) % 2
        if w < 2 or h < 2:
            return None
        return int(r.xmin), int(r.ymin), w, h

    def trimvideo(self, startidx: int, endidx: int, on_done=None, crop=None) -> None:
        """Writes the trimmed (and optionally cropped) clip, then loads it.

        Args:
            crop (tuple, optional): (x, y, w, h) in proxy pixels. Defaults to the crop
                selected in the trim step.
        """
        if self._live_on:
            messagebox.showinfo("Tracking", "Stop or finish tracking before trimming.")
            return
        if crop is None:
            crop = self._current_crop_rect()
        self.logger.info(f"Targeted video clipping operation initialized. Frame coordinates range:"
                         f" [{startidx} -> {endidx}]" + (f", crop {crop}" if crop else ""))
        self.spinner = Spinner(self.videoview, self.videoapp.imgview, self.plugin_mgr.crop)

        # A trim of an existing clip counts frames and crop offsets from that clip. Record the
        # cumulative trim in full-video (proxy) terms, so reopening the project and full-resolution
        # tracking both see one trim that gives the same clip.
        base_start = self.videoapp.trimstart if self.videoapp.istrimmed else 0
        base_crop = self.trim_range["crop"] if self.videoapp.istrimmed and self.trim_range else None
        bx, by = (base_crop[0], base_crop[1]) if base_crop else (0, 0)
        if crop:
            cumcrop = [bx + crop[0], by + crop[1], crop[2], crop[3]]
        else:
            cumcrop = base_crop
        cumstart = base_start + startidx
        cumend = base_start + endidx

        def finish():
            self.trim_range = {"start": cumstart, "end": cumend,
                               "crop": list(cumcrop) if cumcrop else None}
            if crop:
                # The trimmed clip is already cropped, so the crop must not be applied again;
                # the clip itself is shown upscaled to fit the view
                self.plugin_mgr.crop.croprect = None
                self.plugin_mgr.crop.fitted = True
                self.plugin_mgr.crop.set(crop[2], crop[3])
            self.videoapp.set_trim_map(cumstart, (cumcrop[0], cumcrop[1]) if cumcrop else (0, 0))
            self.videoapp.loadvideo(self.videoapp.trimpath, True)
            self.seekbar.set_mode(SeekMode.VIEW, self.videoapp.fcount)
            self.loadcomponents()
            self.spinner.destroy()
            self._leave_trim_mode()
            self.logger.info("Asynchronous video trimming execution completed.")
            if on_done:
                on_done()

        def fail():
            self.spinner.destroy()
            self.logger.error("Trim failed; the current clip is unchanged.")
            messagebox.showerror("Trim", "Could not write the trimmed clip.\n"
                                         "The current clip is unchanged.")

        def work():
            ok = self.videoapp.trimvideo(startidx, endidx, crop)
            self._post_to_ui(finish if ok else fail)

        threading.Thread(target=work, daemon=True).start()

    def _enter_trim_mode(self) -> None:
        self.cropstrip.pack(side="bottom", fill="x", before=self.videoview, pady=5)
        self._update_crop_status()

    def _leave_trim_mode(self) -> None:
        self.cropstrip.pack_forget()

    def _start_trim_crop(self) -> None:
        self.plugin_mgr.crop.drawrect(None)

    def _clear_trim_crop(self) -> None:
        crop = self.plugin_mgr.crop
        crop.clear()
        crop.set(crop.fwidth, crop.fheight)  # Restore the full frame size
        self.updateframe()
        self._update_crop_status()

    def _update_crop_status(self) -> None:
        r = self.plugin_mgr.crop.croprect
        text = f"Crop: {int(r.width)} x {int(r.height)} px" if r is not None else "Crop: full frame"
        self.cropstatus.configure(text=text)

    def loadcomponents(self) -> None:
        self.seekbar.set_mode(SeekMode.VIEW, self.videoapp.fcount)
        self.tpoints.addpoints(self.videoapp.trackpts, self.plugin_mgr.crop.cropx,
                               self.plugin_mgr.crop.cropy)
        self.updateframe()

    def loadseek(self) -> None:
        if self._ensure_video_loaded():
            self.logger.info("Seeding timeline workspace frame navigation controls.")
            self.seekbar.set_mode(SeekMode.TRIM, self.videoapp.fcount)
            self._enter_trim_mode()

    def updateframe(self) -> None:
        # The tracker reads the video while it runs; the UI must not seek the same reader then
        if self._live_on:
            return
        # Note: Avoid high-frequency logger.info operations inside live frame renders. 
        # Scrubbing the timeline would write 60+ logs/second, causing disk I/O bottlenecks
        # and UI stutters.
        crop = self.plugin_mgr.crop
        self.view.origin = (crop.cropx, crop.cropy)
        self.view.fit = crop.fit
        self.videoapp.showframe(self.seekbar.idx, self.view)
        self.tpoints.drawpoints(self.seekbar.idx)

    def _scrub_soon(self) -> None:
        """The seek bar moved. A drag sends a motion event per pixel, and each frame costs a seek
        and a repaint, so drawing each one makes the picture trail the pointer. Draws once the
        queued motion is handled, at the bar's latest position (as _redraw_soon does for zoom)."""
        if getattr(self, "_scrub_pending", False):
            return
        self._scrub_pending = True

        def draw():
            self._scrub_pending = False
            self.updateframe()

        self.root.after_idle(draw)

    def _on_view_change(self) -> None:
        """Zoom or pan changed: redraw the frame and every overlay at the new view."""
        if self._live_on and self._live_frame is not None:
            self._draw_live(*self._live_frame)  # Keep showing the tracked frame while it runs
        else:
            self.updateframe()

    def _on_video_area_resized(self, _event=None) -> None:
        """The window changed size. The layout follows once the drag settles, so a drag lays out
        once rather than on every step."""
        if self._relayout_job is not None:
            self.root.after_cancel(self._relayout_job)
        self._relayout_job = self.root.after(120, self._relayout)

    def _relayout(self) -> None:
        """Gives the video area its new size. The picture is fitted to it again, and the ruler and
        axes are moved with it, so they stay on the same part of the picture."""
        self._relayout_job = None
        vw, vh = self.videoview.winfo_width(), self.videoview.winfo_height()
        if vw < 100 or vh < 100 or (vw, vh) == (self.vwidth, self.vheight):
            return
        if self._live_on or self._loading:
            # The tracker is drawing the picture, or the reader still points at the source file
            # (the proxy is being encoded): lay out again later
            self._relayout_job = self.root.after(500, self._relayout)
            return

        crop = self.plugin_mgr.crop
        old_origin = (crop.cropx, crop.cropy)
        self.vwidth, self.vheight = vw, vh
        for part in (self.videoapp, self.track_rects, self.ocrrects, self.tpoints, self.axes,
                     self.plugin_mgr.filters, self.plugin_mgr.geometry):
            part.vwidth, part.vheight = vw, vh
        self.scruler.set_canvas_size(vw, vh)
        crop.relayout(vw, vh)

        if self.videoapp.fcount >= 10:
            dx, dy = crop.cropx - old_origin[0], crop.cropy - old_origin[1]
            self.scruler.shift(dx, dy)
            self.axes.shift(dx, dy)
            self.updateframe()
            self.track_rects.refresh()
            self.ocrrects.refresh()
            self.viewcontrols.sync()
        self.logger.info(f"Video area resized to {vw}x{vh}")
        self.track_rects.refresh()
        self.ocrrects.refresh()
        if self.axes.placed:
            self.axes.rotate()
        if self.scruler.placed:
            self.scruler.draw()

    def _on_shape(self, shape: str) -> None:
        self.track_rects.shape = shape

    def _enter_marking(self, with_shape: bool = True) -> None:
        """Shows the zoom and pan controls while marking. The shape choice applies to objects only."""
        self.viewcontrols.show(before=self.videoview, with_shape=with_shape)
        self.viewcontrols.sync()

    def _cancel_active_tools(self) -> None:
        """Starting a tool ends the one in progress: an unfinished axis or ruler is cancelled,
        boxes being marked are applied, and an unapplied crop is dropped."""
        self.axes.cancelaxes()
        self.scruler.cancel()
        self.track_rects.cancel()
        self.ocrrects.cancel()
        self.plugin_mgr.crop.cancel()
        self.plugin_mgr.geometry.cancel()

    def markaxes(self) -> None:
        self._cancel_active_tools()
        self._enter_marking(with_shape=False)
        self.axes.markaxes()

    def _leave_marking(self) -> None:
        """Hides the controls once marking is applied. The zoom stays, so the next object can
        be marked at the same zoom; use Reset View to return to the full frame."""
        self.viewcontrols.hide()

    def scale(self) -> None:
        self.logger.info("Deploying coordinate scale rule overlay layer.")
        self._cancel_active_tools()
        self._enter_marking(with_shape=False)
        self.scruler.pack()

    def drawrect(self) -> None:
        self._cancel_active_tools()
        if self._ensure_video_loaded() and self._ensure_video_trimmed():
            self.logger.info("Activating workspace item tracking validation boxes.")
            self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
            self._enter_marking()
            self.track_rects.drawrect(self.plugin_mgr.crop.cropwidth, self.plugin_mgr.crop.cropheight,
                                      self.plugin_mgr.crop.cropx, self.plugin_mgr.crop.cropy)

    def apply_filter(self) -> None:
        self._cancel_active_tools()
        if self._ensure_video_loaded():
            self.logger.info("Opening dynamic filter modification matrix menu panel.")
            self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
            self.plugin_mgr.filters.spawnfilter()
            self.plugin_mgr.toggle()

    def drawcrop(self) -> None:
        self._cancel_active_tools()
        if self._ensure_video_loaded():
            self.logger.info("Initializing visual spatial geometric crop tool profiles.")
            self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
            self.plugin_mgr.crop.drawrect(self.videoapp.set_size)
            self.plugin_mgr.toggle()

    def drawocr(self) -> None:
        self._cancel_active_tools()
        if self._ensure_video_loaded():
            self.logger.info("Mapping optical text zone character digit capture constraints.")
            self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
            self._enter_marking()
            self.ocrrects.drawrect(self.plugin_mgr.crop.cropwidth, self.plugin_mgr.crop.cropheight,
                                   self.plugin_mgr.crop.cropx, self.plugin_mgr.crop.cropy)
            self.plugin_mgr.toggle()

    def dogeometry(self) -> None:
        self._cancel_active_tools()
        self.logger.info("Launching trace physics kinematic geometry tracking instruments.")
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.plugin_mgr.geometry.pack()
        self.plugin_mgr.toggle()

    def strack(self) -> None:
        self._cancel_active_tools()  # Box mode and any other tool end when tracking is asked for
        if not self._ensure_video_loaded() or not self._ensure_video_trimmed() or \
            (not self.track_rects.rects and not self.ocrrects.rects):
            self.logger.warning("Tracking execution bypassed: no nodes or bounding layers found on canvas.")
            messagebox.showerror("Error", "No nodes mapped to track. Select regions first!")
            return

        # Only one tracking run may read the video at a time; a second run corrupts the reader
        if self._track_thread is not None and self._track_thread.is_alive():
            self.logger.warning("Tracking is already running; ignoring the new Track request.")
            return

        self.logger.info("Kicking off optical flow and analytical tracking loops thread.")
        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        self.track_rects.cleartkrects()
        self.ocrrects.cleartkrects()
        # self.processanim.pack()
        progress = _LoadProgress()
        self.progressbar.progress = progress
        self.progressbar.pack()

        # Each processed frame is handed over as the newest "live" frame; the UI draws it on a timer
        self._live_frame = None
        self._live_on = True
        self._poll_live()
        self._stop_requested = False
        self._enter_track_view()
        # Read on the UI thread: Tk variables must not be touched from the worker thread
        fullres = self.fullres_var.get()
        filters = self.plugin_mgr.filters.snapshot()
        assist = self.assist_var.get()
        if fullres:
            self.trackstatus.configure(text="Preparing full-resolution copy...")
        self._track_thread = threading.Thread(target=self._track_in_background,
                                              args=(progress, fullres, filters, assist),
                                              daemon=True)
        self._track_thread.start()
        self.progressbar.update()

    def _track_in_background(self, progress: "_LoadProgress", fullres: bool = False,
                             filters=None, assist: bool = False) -> None:
        """Runs on a worker thread. Failures are reported to the user instead of stalling the UI.
        Nothing here may touch Tk (widgets or Tk variables): the filter comes in as a snapshot."""
        try:
            self.videoapp.track(self.track_rects, self.ocrrects, progress,
                                on_frame=self._on_tracked_frame,
                                should_stop=lambda: self._stop_requested,
                                fullres=fullres, filters=filters, assist=assist,
                                on_tracking=lambda: self._post_to_ui(self._show_tracking_text))
        except Exception as e:
            self.logger.exception("Tracking failed")
            progress.set(100)
            # Python clears `e` when the except block ends, so the callback needs its own reference
            error = e
            self._post_to_ui(lambda: self._finish_failed_track(error))
            return

        progress.set(100)
        self._post_to_ui(self._finish_track)

    def _on_tracked_frame(self, index: int, frame, boxes: list) -> None:
        """Worker thread: keeps only the newest frame, so the UI never falls behind."""
        self._live_frame = (index, frame, boxes)

    def _poll_live(self) -> None:
        """UI thread: shows the newest tracked frame and the ball positions found in it."""
        if not self._live_on:
            return
        item = self._live_frame
        if item is not None and item is not getattr(self, "_live_drawn", None):
            self._live_drawn = item
            self._draw_live(*item)
        # About 10 refreshes a second: drawing every frame slows the tracker itself by about half
        self.root.after(100, self._poll_live)

    def _draw_live(self, index: int, frame, boxes: list) -> None:
        self.videoapp.show_array(frame, self.view)
        self.videoview.delete("live")
        ox0, oy0 = self.view.origin
        for box in boxes:
            if box is None:
                continue
            x, y, w, h = box
            x1, y1 = self.view.to_canvas(ox0 + x, oy0 + y)
            x2, y2 = self.view.to_canvas(ox0 + x + w, oy0 + y + h)
            self.videoview.create_rectangle(x1, y1, x2, y2, outline="yellow", width=2, tags="live")
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            self.videoview.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="magenta",
                                       outline="black", tags="live")
        self.videoview.create_text(10, 10, anchor="nw", text=f"Frame {index}", fill="white",
                                   font=("Arial", 12, "bold"), tags="live")

    def _stop_live(self) -> None:
        self._live_on = False
        self.videoview.delete("live")

    def _enter_track_view(self) -> None:
        """Shows the stop button and zoom bars for the tracking screen."""
        self._set_manual(False)
        self.trackstrip.pack(side="bottom", fill="x", before=self.videoview, pady=5)
        self.viewcontrols.show(before=self.videoview, with_shape=False)
        self.viewcontrols.sync()
        self.stopbtn.configure(state="normal")
        self.manualbtn.configure(state="disabled")
        self.trackstatus.configure(text="Tracking...")

    def _show_tracking_text(self) -> None:
        """UI thread: the frames are being read now, after any full-resolution copy is ready."""
        if self._live_on and not self._stop_requested:
            self.trackstatus.configure(text="Tracking...")

    def _request_stop(self) -> None:
        if self._track_thread is None or not self._track_thread.is_alive():
            return  # Tracking already finished
        self._stop_requested = True
        self.stopbtn.configure(state="disabled")
        self.trackstatus.configure(text="Stopping...")

    def _finish_track_view(self, stopped: bool) -> None:
        """After tracking: the results can be corrected with manual positions."""
        self.stopbtn.configure(state="disabled")
        self.manualbtn.configure(state="normal")
        last = self._live_frame[0] if self._live_frame else 0
        self.trackstatus.configure(
            text=f"Stopped at frame {last}; results so far" if stopped else "Tracking complete")

    def _close_track_view(self) -> None:
        self._set_manual(False)
        self.trackstrip.pack_forget()
        self.viewcontrols.hide()

    def _toggle_manual(self) -> None:
        self._set_manual(not self.manual_mode)

    def _set_manual(self, on: bool) -> None:
        """Manual mode: clicking the frame sets the object's position for the frame shown."""
        self.manual_mode = on
        self.manualbtn.configure(text=f"Manual Position: {'On' if on else 'Off'}")
        if on:
            self.videoview.bind("<Button-1>", self._on_manual_click)
        else:
            self.videoview.unbind("<Button-1>")

    def _on_manual_click(self, event) -> None:
        if not self.videoapp.trackpts:
            return
        ox0, oy0 = self.view.origin
        bx, by = self.view.to_base(event.x, event.y)
        px, py = bx - ox0, by - oy0  # Stored in frame pixels, like the tracker's output
        idx = self.seekbar.idx
        j = self._nearest_object(idx, px, py)
        if j is None or idx >= len(self.videoapp.trackpts[j]):
            return
        self.videoapp.trackpts[j][idx] = [px, py]
        self.tpoints.undrawpoints()
        self.tpoints.addpoints(self.videoapp.trackpts, ox0, oy0)
        self.updateframe()
        self.logger.info(f"Manual position set: object {j}, frame {idx} -> ({px:.1f}, {py:.1f})")

    def _nearest_object(self, idx: int, px: float, py: float) -> int | None:
        """The object whose point on this frame is nearest the click (object 0 if none has one)."""
        best, best_d = None, float("inf")
        for j, pts in enumerate(self.videoapp.trackpts):
            if idx < len(pts) and len(pts[idx]) == 2:
                d = (pts[idx][0] - px) ** 2 + (pts[idx][1] - py) ** 2
                if d < best_d:
                    best, best_d = j, d
        if best is None and self.videoapp.trackpts:
            return 0
        return best

    def _finish_track(self) -> None:
        self._stop_live()
        self.progressbar.destroy()
        if self._clear_after_stop:  # Clear Data was pressed during the run: discard what it found
            self._clear_after_stop = False
            self._discard_track_data()
            self.logger.info("Tracking stopped and its data cleared.")
            return
        self.loadcomponents()
        self.logger.info("Background point tracking calculations wrapped cleanly.")
        self._finish_track_view(self._stop_requested)

    def _finish_failed_track(self, error: Exception) -> None:
        self._stop_live()
        self.progressbar.destroy()
        self._clear_after_stop = False
        self._close_track_view()
        messagebox.showerror("Tracking failed", str(error))

    def _clear_track_data(self) -> None:
        """Clear Data: during a run, the run is stopped and its results are discarded when it ends;
        otherwise the results are discarded now. The boxes and the video stay as they are."""
        if self._track_thread is not None and self._track_thread.is_alive():
            self._clear_after_stop = True
            self._request_stop()
            self.trackstatus.configure(text="Stopping, then clearing...")
            return
        self._discard_track_data()

    def _discard_track_data(self) -> None:
        """UI thread: forgets the tracked positions and OCR readings, and the points drawn for them."""
        self.videoapp.clear()
        self.tpoints.clear()
        self.pipeline_mgr.datamanager.clear()
        self._set_manual(False)
        self._live_frame = None
        self.videoview.delete("live")
        self.manualbtn.configure(state="disabled")
        self.stopbtn.configure(state="disabled")
        self.trackstatus.configure(text="Data cleared: track again to start over")
        self.updateframe()
        self.logger.info("Tracking data cleared.")

    def clearcomponents(self) -> None:
        self.plugin_mgr.filters.clear()
        self.axes.clear()
        self.tpoints.clear()
        self.scruler.clear()
        self.pipeline_mgr.datamanager.clear()

    def reset(self) -> None:
        self.logger.info("Resetting application workspace tracking layers back to default profiles.")
        self.clearcomponents()
        self.trim_range = None
        self.scruler.placed = False
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        self.track_rects.clear()
        self.seekbar.clear()

        self.plugin_mgr.crop.clear()
        self.plugin_mgr.geometry.reset()

        if self.videopath:
            self.loadvideo(self.videopath)

    def plot(self) -> None:
        self.logger.info("Requesting analytical kinematics plot data visualizations compilation.")
        self.title = TitleBar(self.videoview, self.vwidth, "Data Visualization")
        # Save plot starts in the project's folder, and names files after the video
        plotter = self.pipeline_mgr.plotter
        plotter.save_dir = os.path.dirname(self.projectpath) if self.projectpath else None
        plotter.save_prefix = (os.path.splitext(os.path.basename(self.videopath))[0]
                               if self.videopath else "")
        self.pipeline_mgr.compile_and_run(self, "plot")

    def savedata(self) -> None:
        """Save button: writes the project, then exports data if there is any to export."""
        if not self.videopath:
            messagebox.showerror("Save project", "Load a video before saving.")
            return

        if not self.projectpath:
            base = os.path.splitext(os.path.basename(self.videopath))[0]
            path = filedialog.asksaveasfilename(
                defaultextension=PROJECT_EXTENSION, initialfile=base + PROJECT_EXTENSION,
                filetypes=[("PhysTrackX project", f"*{PROJECT_EXTENSION}")])
            if not path:
                return
            self.projectpath = path
            session.set_project(path)
            recent.remember(path)
            self._update_title()

        try:
            write_project(self.projectpath, self.project_state())
        except OSError as e:
            messagebox.showerror("Save project", f"Could not save the project:\n{e}")
            return
        self.logger.info(f"Project saved: {self.projectpath}")

        if self.videoapp.trackpts or self.videoapp.ocrdata:
            self.title = TitleBar(self.videoview, self.vwidth, "Save Data")
            self.pipeline_mgr.compile_and_run(self, "save")
        else:
            messagebox.showinfo("Project saved", f"Saved project to:\n{self.projectpath}")

    def _on_data_saved(self, path: str) -> None:
        """A CSV was written: remember its folder (the next save starts there) and the file, and
        update the project so it can be plotted again when reopened."""
        files = list((self.saved_data or {}).get("files", []))
        files.append(path)
        self.saved_data = {"dir": os.path.dirname(path), "files": files}
        if self.projectpath:
            try:
                write_project(self.projectpath, self.project_state())
            except OSError as e:
                messagebox.showerror("Save project", f"Could not update the project:\n{e}")
        self.logger.info(f"Data saved to: {path}")

    def _load_saved_data(self, data: dict | None) -> None:
        """Pulls the project's last saved CSV in, so the data can be plotted, and starts the next
        save in its folder."""
        self.saved_data = data
        if not data:
            return
        folder = data.get("dir")
        if folder and os.path.isdir(folder):
            self.pipeline_mgr.saver.default_dir = folder
        existing = [f for f in data.get("files", []) if os.path.isfile(f)]
        if not existing:
            return
        try:
            self.loaded_data = load_csv(existing[-1])
            self.logger.info(f"Loaded saved data: {existing[-1]}")
        except (OSError, ValueError) as e:
            self.logger.exception("Could not load the saved data")
            messagebox.showinfo("Saved data", f"The project's saved data could not be read:\n{e}")

    def project_state(self) -> dict:
        """Everything needed to rebuild the current setup from the source video."""
        crop = self.plugin_mgr.crop.croprect
        return {
            "video": os.path.abspath(self.videopath),
            "canvas": [self.vwidth, self.vheight],
            "trim": self.trim_range if self.seekbar.trimmed else None,
            "crop": {"x": crop.xmin, "y": crop.ymin, "w": crop.width, "h": crop.height}
                    if crop is not None else None,
            "axes": self.axes.get_state() if self.axes.placed else None,
            "scale": self.scruler.get_state() if self.scruler.placed else None,
            "data": self.saved_data,
            "rects": {
                "track": [list(r.totuple()) for r in self.track_rects.rects],
                "track_shapes": self.track_rects.shapes,
                "ocr": [list(r.totuple()) for r in self.ocrrects.rects],
            },
        }

    def _open_project(self, path: str) -> None:
        """Loads a project file: video first, then trim, then the overlays."""
        try:
            state = read_project(path)
        except (OSError, ValueError) as e:
            messagebox.showerror("Open project", f"Could not open the project:\n{e}")
            return

        self.projectpath = path
        session.set_project(path)
        recent.remember(path)
        self._load_saved_data(state.get("data"))
        self.videopath = state["video"]
        if not os.path.isfile(self.videopath):
            messagebox.showerror("Open project", f"The project's video was not found:\n{self.videopath}")
            return

        # Without a trim, the crop must be in place before the video loads (loading sizes the frame
        # to it). With a trim, the trim applies its own crop, which is restored afterwards.
        crop = state.get("crop")
        if crop and not state.get("trim"):
            self.plugin_mgr.crop.croprect = PixelRect(crop["x"], crop["y"], crop["w"], crop["h"])

        self.logger.info(f"Opening project: {path}")
        self.loadvideo(self.videopath, on_done=lambda: self._restore_project(state))

    def _restore_project(self, state: dict) -> None:
        trim = state.get("trim")
        if trim:
            trim_crop = tuple(trim["crop"]) if trim.get("crop") else None
            self.trimvideo(trim["start"], trim["end"], on_done=lambda: self._apply_overlays(state),
                           crop=trim_crop)
        else:
            self._apply_overlays(state)

    def _apply_overlays(self, state: dict) -> None:
        """Restores the crop, axes, scale, and rectangles once the video (and trim) are in place."""
        if state.get("trim"):
            self.seekbar.mark_trimmed()
        saved_crop = state.get("crop")
        if saved_crop:
            crop = self.plugin_mgr.crop
            crop.croprect = PixelRect(saved_crop["x"], saved_crop["y"], saved_crop["w"], saved_crop["h"])
            crop.fitted = True
            crop.set()
        self.updateframe()

        if state.get("axes"):
            self.axes.restore_state(state["axes"])
        if state.get("scale"):
            self.scruler.restore_state(state["scale"])

        crop = self.plugin_mgr.crop
        rects = state.get("rects", {})
        self.track_rects.restore([NormalizedRect(*r) for r in rects.get("track", [])],
                                 crop.cropwidth, crop.cropheight, crop.cropx, crop.cropy,
                                 shapes=rects.get("track_shapes"))
        self.ocrrects.restore([NormalizedRect(*r) for r in rects.get("ocr", [])],
                              crop.cropwidth, crop.cropheight, crop.cropx, crop.cropy)
        self.logger.info("Project restored.")

    def plugins(self) -> None:
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.plugin_mgr.toggle()
        self.plugin_mgr.geometry.set_scale(self.scruler.scale, self.scruler.unit_label())
        self.logger.info("Extended dynamic components toolbox toggled.")