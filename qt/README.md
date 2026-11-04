# PhysTrackX (Qt app)

The Qt app: measure motion in a video, track objects and fit the physics. It is the app to use; the
Tk app in the parent's `tk/` folder is deprecated and nothing here depends on it. It is built on the
parent's `core`, `media` and `experiments` packages, which it reads and never changes.

## Install and run

```sh
cd qt
uv run python build.py dev                # installs `phystrackx` on PATH, running this code
phystrackx "path/to/Air Trial 1.mp4"      # a video, or a .phystrack project
phystrackx --version
```

From the repo root, a single script installs the app and installs uv first if it is missing:
`sh install.sh` on macOS (PhysTrackX.app in /Applications, plus the `phystrackx` command; add
`--no-app` for the command alone), `sh install.sh` on Linux (the `phystrackx` command), or
`install.bat` on Windows (the command).

`build.py dev` needs [uv](https://docs.astral.sh/uv/) and nothing else: uv makes the Python 3.12 and
the dependencies, in its own folder, so no venv is set up by hand. Rerun it after changing
`pyproject.toml`. For a packaged app (macOS `.dmg`, Windows installer, Linux AppImage), see
`packaging/README.md`.

**Windows:** download [PhysTrackX-Setup.exe](https://github.com/xoth42/phystrackx/releases/latest/download/PhysTrackX-Setup.exe)
and run it. It installs for your user only (no administrator prompt), adds a desktop icon and a Start menu
entry, and uninstalls from Settings > Apps. Windows may say "Windows protected your PC" on a new release:
choose More info, then Run anyway.

Without installing, from this folder: `uv run python run.py [video or project]`. Tests:
`uv run python build.py test`.

## Notes for anyone working on it

- `qt/` lives in the parent repo's git. Its build output (`qt/build/`) and environment (`.venv`) are
  ignored. Keep the environment **outside iCloud**: `export UV_PROJECT_ENVIRONMENT=~/.venvs/phystrackx-dev`
  (iCloud sets the macOS "hidden" flag on files in dot-folders, Qt skips hidden plugin files, and the
  app then fails with "no Qt platform plugin could be initialized").
- It **imports the parent's `media`, `core` and `experiments` packages read-only**: from the repo root
  in a checkout, from site-packages when installed (`phystrack_qt/__init__.py`).
- It never writes into the install or the repo. Proxies, the agent bridge's port and projects of a
  read-only folder go to the user's cache and data folders (`phystrack_qt/paths.py`; the tests use
  `PHYSTRACK_QT_HOME`).
- Older projects: a Tk-app `.phystrack` is imported (the setup carried over; the rest named, not
  kept); a newer or other-format file is refused. See `packaging/README.md`.

## Setup notes

`opencv-python-headless` is pinned to the parent's OpenCV version: the 5.0 macOS wheel has no
FFmpeg backend, so `media.VideoReader` (which asks for FFmpeg) cannot open videos with it. The
parent's `opencv-python` (not headless) bundles its own Qt and clashes with PySide6. ffmpeg itself
comes with `imageio-ffmpeg`, so no system install is needed.

## What is in it

A window with a left sidebar of buttons, the video view, and a seek bar.

- **Import Video**: the first frame shows at once (about 0.3 s), read from the source. The proxy
  is made in the background by the parent's `media.proxyvideo` (cached in the user's cache folder), and
  reading switches to it when it is ready (about 10 s for a 39 s phone clip).
- **Trim**: choose start and end frames; the seek bar is limited to that range. Only a range, not
  a re-encoded clip as in the Tk app.
- **Place Axis**: click to place the origin. Drag a line to move the axes, drag the round handle
  at the end of the x axis to rotate them.
- **Mark Rectangle**: drag a box around each object; Escape when done. The object just marked is
  selected, so D removes it at once (a quick redo).
- **Fine-tuning a selection**: the selected object has a size line from its centre with a knob;
  drag the knob (or press [ and ]) to make it bigger or smaller about its centre. Move (M) lets a
  drag anywhere on the picture move it (a small ball's box is hard to grab); Escape or M ends it.
- **Track**: first asks for the method (`phystrack_qt/track_methods.py`; Enter takes the one used
  last): the whole-clip engine (recommended: reads the range, then picks the path over all of it;
  gets through covers and dirty lenses), the blob tracker with or without the still background
  (live), or NanoTrack (the neural model the Tk app uses), with options for the background, a
  physics fit at the end, and correcting a shiny ball's centre from the selection (best with an
  Auto Object outline, which the engines take as the selection). They are the parent's
  (`experiments/rigid`: `cliptrack.py`, `blobtracker.py`, `mltracker.py`). It runs from the
  current frame to the end of the trim, on a worker thread with its own reader; live methods are
  followed in the view, and scrubbing stays free. Press again to stop. Only objects that are new,
  moved or resized, or were tracked another way or over another range are tracked; the others keep
  their tracks. The status bar's bar fills once over the whole run (every object and pass), and it
  and the status say "frame n / last" of the whole video, as beside the seek bar. The centre option
  fits a circle to the ball's outline on every frame (the parent's `ringfit.py`), as a shiny ball's
  highlights, smeared by motion blur, pull a blob centre 1-3 px aside. The whole-clip method shows its
  best path so far while it reads (it can still change), and reads the next frame on a second
  thread while it works on the current one.
- **Playback of a track**: a dot marks each object's tracked centre on the frame shown, and the
  trail is bright up to it, so playing or scrubbing shows the track against the ball in the picture.
- **Saving asks nothing**: Save Project, Export Data and a plot's Save (the button or the toolbar's)
  write next to the video, named after it (`Air Trial 1.phystrack`, `Air Trial 1_data.csv`,
  `Air Trial 1_object1_y.png` / `.csv` / `_fit.txt`), never over an earlier file (" 2" is added),
  and the status bar shows the full path. Save Project As… still asks, for when another place is wanted.
- **View**: pinch or Cmd+scroll to zoom, scroll to pan, double-click the picture to fit it.
- **Seek**: drag the bar, or Left and Right arrows for one frame.
- **Correcting a track part-way**: stop, move the box back onto the object on that frame, and Track
  again. The track before that frame is kept; only the part from there on is tracked again.
- **History** (right bar, under the objects): every change is an event. Click one to go back to it;
  the revert is logged too, so clicking a later event goes forward again. The agent's events are blue.
- **Tabs**: one trial per tab, as many as wanted, in a tab bar named after each trial's project or video
  (`*` when unsaved). File > New Tab (Ctrl+T) adds one, Close Tab (Ctrl+W) or the tab's × closes one,
  Reopen Closed Tab (Ctrl+Shift+T) brings it back; Window > Next/Previous Tab (Control+Tab) and Ctrl+1..9
  switch. File > New Window (Ctrl+N) opens another window of tabs. Several files on the command line open
  one tab each. Each trial has an id (`w1`, `w2`...) in the window title and the tab's tooltip.
- **Agent tools**: the app serves its tools to agents (MCP, or `phystrack_qt/agent/ptx.py` from a
  shell) on 127.0.0.1. The usual request is `open` the next trial, then `run_recipe` from the one
  done by hand. Space stops a working agent. See `../docs/AGENT_PLAN.md`.
- **Assistant** (right bar, under the history): a local model (Ollama with `qwen3:4b-instruct` by
  default; any OpenAI-compatible runner through `PHYSTRACK_LLM_URL`) that uses those tools: "do what
  I did in w1 on trials 2 to 4". Space stops it; Start goes on. The app starts Ollama at launch and
  stops it when the app quits (a server it did not start is left alone). If Ollama is missing, or
  the model is not downloaded, the app asks (y or n) before installing or downloading anything
  (macOS and Windows: into the app's own folder; Linux: the command is shown). Its label says
  "ready" only when the runner answers. See `phystrack_qt/agent/runner.py`.

Overlays are children of the picture item, so they are in frame pixels and follow zoom and pan
without any coordinate code (in the Tk app, `ViewTransform` does this by hand).

## Tests

```sh
uv run python build.py test                                  # all of them
uv run python tests/test_tracking.py                         # one; PHYSTRACK_QT_SHOW=1 to watch
```

`tests/harness.py` runs Qt with no window (the `offscreen` platform) and a CPU viewport, and
`render_picture()` draws the picture with its overlays at frame pixels. That is how tests check
overlays: Qt cannot capture an OpenGL view on macOS (`grab()` gives black, offscreen gives garbage),
and checking frame pixels does not depend on the window, zoom or screen.

## Findings for the migration

- **OpenCV and Qt do not clash on macOS or Windows.** `opencv-python` only points Qt at its own
  plugins on Linux (see `cv2/config-3.py`); on macOS it uses Cocoa. Switching to
  `opencv-python-headless` is one line in requirements and only matters for Linux. Pin 4.11.x:
  the 5.0 macOS wheel has no FFmpeg backend.
- **The parent's package `__init__` files import Tk.** `experiments/__init__.py` imports `Rigid`
  (customtkinter, the Tk plugins, OCR), so importing the tracker pulls in Tk.
  `phystrack_qt/parent_imports.py` works around it; the fix in the migration is to make those
  `__init__` files import lazily, and to move `Crop`/`Filters` maths out of `gui/plugins`.
- **Keep Qt virtual environments out of iCloud** (see above).
- **Load time is decoding, not encoding.** Decoding the 1080p HEVC phone clip alone is about
  70% of the proxy time, and the hardware encoder is no faster on an Intel Mac. Showing the
  source at once, as here, removes the wait instead.
- **Tracking does not need to block the UI.** A second reader for the worker means the user can
  scrub during a run; the Tk app shares one reader and has to lock scrubbing.
