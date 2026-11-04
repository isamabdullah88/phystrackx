# Qt build: TODO

Status of every feature the Tk app has or needs, for the Qt build. Done items are checked, and
each has a test in `tests/` unless noted. Tk is not touched; the parent's `docs/TODO.md` is the
Tk list.

## The five hardest (done this round)

Picked because each carries the most state, the most Tk-only logic, or a numerical method that must
match the Tk app:

1. **Projects.** Save and open a whole setup (video, trim, axes, ruler with length and unit, tracked
   boxes), with an unsaved-changes prompt. Hardest because every feature's state has to round-trip
   exactly. `tests/test_project.py`.
2. **Rulers.** Place, drag the ends and the bar, Auto Ruler, Undo. The ruler is drawn in screen
   pixels, so its size does not change with zoom. `tests/test_ruler.py`.
3. **Ruler length and unit.** Typed as "50 cm" (parsed by the parent's `core/units.py`). The scale is
   the real length over the picture length, and the unit flows into the labels, plots and CSV.
   `tests/test_ruler.py`, `tests/test_measure.py`.
4. **Plotting.** The eight plot kinds, one window each with matplotlib's toolbar (zoom, pan, Save),
   and CSV export. Positions are measured from the axes, in the axes' own frame, so rotated axes
   are right. `tests/test_measure.py`, `tests/test_plots.py`.
5. **Plot analysis.** Fit panel (four models, range slider), period from peaks, initial drop, and
   the results text. The numerics are the parent's `fit.py`; the panel and text follow the Tk plot.
   `tests/test_measure.py` (fit recovers omega), `tests/test_plots.py`.

Auto Ruler is in item 2 because it is the ruler's own snap: the logic is the parent's
`core/autoruler.py`, which is why it was not one of the five.

## Axes
- [x] The axis lines run across the whole picture; the arrow tips, labels and rotate handle sit
  at the axes' length.

## Projects
- [x] Save Project (Cmd+S), Save Project As, Open Project (Cmd+O). Files are `.phystrack` in the
  app's own format (version 2; the Tk app refuses them with a message), saved next to the video.
- [x] Unsaved-changes prompt on open, new video and quit. Title shows `*` when dirty.
- [x] Open Recent (last 8, its own list in `~/.phystrackx/recent-qt.json`, so the Tk app's menu
  stays clean), with Clear Recent.
- [x] Saved next to the video; `qt/projects/` when that folder is read-only (as the Tk app does).
  New projects never overwrite a file (the second is "clip 2.phystrack").
- [x] `run.py <file.phystrack>` opens the project.
- [x] Tk-app projects import one way into this format (the setup carried over; what cannot carry
  over is named). This format is never downgraded for Tk, and Tk's is never written. See the bottom.

## Panning
- [x] Drag the picture to pan when no tool is active (`ScrollHandDrag`).
- [x] Two-finger scroll pans (trackpad), as the Tk app.
- [ ] Shift + scroll pans sideways with a mouse wheel (check on a real mouse).
- [ ] Arrow keys pan when zoomed. Arrows currently step frames, so this needs a modifier.

## Gestures
- [x] Trackpad pinch zooms (`NativeGesture`).
- [x] Double-click fits the picture.
- [ ] Two-finger double-tap to fit (trackpad smart zoom).

## Zooming and zoom commands
- [x] Cmd + scroll zooms around the pointer, clamped to 1x-8x the fitted size.
- [x] Pinch zoom.
- [x] Zoom readout in the status bar.
- [x] Cmd 0 fits (Ctrl 0 on other systems, as in the Tk app).
- [x] Cmd = and Cmd - zoom in and out (added; not yet tried by hand).
- [ ] Zoom to the ruler or the axes, or to a tracked box.
- [ ] Undo or reset of a zoom to the last value.

## Rulers
- [x] Place Ruler: a bar with ends and a bar you drag, with ticks, rotated by dragging the ends.
- [x] Double-click the ruler, or Set Length, to give its real length.
- [x] Auto Ruler (snap to the object's ends, from the parent's `core/autoruler.py`) and Undo.
- [x] Apply Ruler (stops editing); Remove Ruler.
- [ ] Angle entry box (the Tk ruler has an angle control).
- [ ] Undo for manual moves (only Auto Ruler has Undo now).
- [x] Auto Ruler, exact: fixed in the shared `core/autoruler.py` (authorised), so the Tk app gets
  it too. Three changes: a vertical closing bridges pale tape across the object; each row's edge is
  snapped to the sharpest colour step near the mask (sub-pixel, so shadow and tape cannot pull it
  out); and the edge line is refitted without the rows that sit off it. On a synthetic bar it is
  within 0.1 px. On frame 0 of Air Trial 1 the ends now sit on the wood's corners to about a pixel,
  from three different starting lines.
- [ ] Auto Ruler: the ruler must lie over the object (its width covers the object). A ruler beside
  the object samples the object as the background, and the snap fails. Worth a hint in the UI.
- [ ] Auto Ruler on more footage (only Air Trial 1 frame 0 and synthetic bars so far).

## Axes
- [x] Auto Axis (new `core/autoaxis.py`) and Undo, in a panel under Place Axis once the axes are
  placed; the assistant's `axes` tool takes `auto` (and `axis`). It turns the axes by up to 10° so
  an axis lies along the strongest straight line near it (a tube, a track) and slides the origin
  onto it (an edge within 3% of the picture's smaller side; between a tube's two walls, their
  middle). Both axes are tried and the stronger line wins. On synthetic tubes it is within 0.05°
  and 0.1 px; on Air Trial 1 frame 0 (the glass tube, y axis) it gives -3.8° from three starts.
- [ ] Auto Axis: an x/y choice in the UI (the button picks the stronger line; the tool can name one).
- [ ] Auto Axis: a weak line (texture, a faint shelf) still passes the strength check when the axis
  named has nothing better; only the choice between x and y guards against it now.

## Ruler length and unit
- [x] Typed length and unit ("50 cm", "2.5 m"), parsed by `core/units.py`.
- [x] Scale = real length / picture length; the typed length is kept as the ruler moves or stretches.
- [x] Unit on the ruler's label, in the status bar, in the plots' axes and in the CSV headers.
- [ ] Unit picker (a list of common units instead of typing).

## Plotting
- [x] Eight kinds: x, y, r against time; trajectory; dx/dt, dy/dt; d²x/dt², d²y/dt².
- [x] One window per plot, with matplotlib's toolbar (zoom, pan, Save).
- [x] Legend placed automatically and draggable.
- [x] Export Data (CSV): one row per frame, with each object's x and y. In the sidebar and the File menu.
- [x] Each plot window: Save data (its points, with column names) and Save results (the fit's text,
  for the range the slider chose; fit plots only).
- [x] Distance against time is the plot shown by default.
- [ ] The Tk plots' `ggplot` style (theme) is not applied yet.
- [ ] Save the plot without the fit panel's controls (the toolbar's Save includes them).

## Plot analysis
- [x] Four fit models (damped, damped with drift, quadratic drag, quadratic drag with drift) and
  the range slider, with the previous fit as the starting guess.
- [x] Period from peaks, best period, initial drop, and the results text (same as Tk's).
- [ ] Fit results saved with the project (the plot's Save results writes them to a file).
- [ ] **Slow fits on non-oscillating data (urgent).** Fitting the damped-oscillator model to a
  position with no oscillation (a thrown ball's x, a parabola) takes 6 s, and with drift over 40 s,
  for every slider move. The app runs the fit on the UI thread, so the window freezes. The Tk app
  runs the same fit (`gui/components/plot/fit.py`). Fix in Qt: run `fit_model` on a worker thread
  with the latest request winning, and/or a time or `maxfev` budget. Tests use oscillating data
  until this is fixed.

## Tracking (not in the five; the Tk app has these)
- [x] Mark Rectangle (several), Track from the current frame to the trim's end, live view.
- [x] Stop is immediate (about 20 ms): the button changes at once, late results are dropped, and
  the view shows the tracker's own frames, so the UI thread does no decoding during a run.
- [x] Object manager (dock on the right): Remove (also Delete/Backspace), Clear Track, Remove All.
- [x] Drag the selected object's box on the picture (chosen in the list, drawn thicker): before tracking it
  moves where tracking starts; after it, the box on the frame shown. Other objects cannot be dragged.
  Numbers are never reused within a session: a new object takes the next free number.
- [x] Mark Circle: drag corner to corner, as a box (top-left to bottom-right). The object is tracked as the circle's
  bounding square (as the Tk app tracks balls) and drawn as the circle. Saved with the project.
- [x] Auto Object (built, confirm always): drag a loose box, or click, around anything. The outline
  is shown dashed; Accept Object tracks it, Try Again or Cancel. `phystrack_qt/autodetect.py`:
  GrabCut, seeded with the colour that differs from the wall around the box (the Auto Ruler's
  measure); an object with no colour of its own (grey on grey) falls back to the box alone. The
  outline is kept as fractions of its box, so it follows the box as the tracker moves it. Saved with
  projects. Tested: a ball (IoU 0.99), an irregular shape (0.99), grey on grey (0.99), empty wall
  refused. Limits found on frame 0 of Air Trial 1 (the wooden ruler): pale tape next to the object is
  taken in with it, and the outline can be a few pixels wide of the true edge. The confirm step is
  there for exactly this. Still to do: trim a piece off the outline (a brush), and check on more
  footage (balls in the tube, the stopper).
- [x] Auto Object tolerance slider (higher selects more). Lightness counts now, so grey and dark
  objects seed the search too (before, only colour did, and a grey stopper got a sliver).
- [x] Black edge under every selection line: boxes, circles, outlines, the rubber band, and trails.
- [ ] Auto Object brush: "keep" and "remove" strokes that feed GrabCut's mask. This is the fix for
  objects that share colour and lightness with their surroundings (the stopper disc on the glass:
  at any tolerance or box size the outline takes in the grey band or the glass beside it).
- [ ] Rename an object.
- [ ] Trim writes a trimmed (and cropped) clip, as `media.trimvideo` does. The Qt trim only limits
  the seek bar.
- [ ] Crop tool.
- [ ] Filters (contrast and the rest) before tracking.
- [ ] Tracker choice (NanoTrack, or the blob tracker once it is checked on real footage).
- [ ] Assist (Segment Anything re-finds the object on hard frames).
- [ ] Undo and redo for edits.

## Other Tk features (not started)
- [ ] Geometry plugins (triangle, line, arc, point).
- [ ] Non-rigid apps (balloon, interface, marangoni).
- [ ] Batch trials (see the parent's `docs/BATCH_TRIALS_PLAN.md`).
- [ ] Preferences and the Tk app's menu items that have no Qt equivalent yet.

## Known differences from the Tk app (kept on purpose)
- The ruler stays visible after Apply (the Tk app hides it), so it can be checked against the video.
  It is not editable until the ruler tool is used again.
- The time of each frame is frame / capture fps, the metadata's `com.android.capture.fps` when the
  file has one (a phone's slow-motion clip), else the container rate (`phystrack_qt/timing.py`).
  Playback follows the container rate, so slow-motion clips play slowed down, as recorded. The Tk
  app's time axis (`np.linspace(0, N/fps, N)`) runs one frame long over the clip, and the Tk app
  still floors the fps to a whole number.
- The plot margins are 5% of the data's range on each side. The Tk app multiplies the limits
  (`xmin * 0.90`), which pushes the margin the wrong way for negative data.
- Derivatives use the tracked frames only, so across a lost stretch the slope is taken between the
  frames either side.

## Found in the Tk app (report, not fixed; the Tk build is not touched)
- **Rotated axes measure wrongly.** `DataManager.transformxy` (gui/components/plot/datamanager.py)
  rotates by `-theta` after `canvas2reg`, but `Axes.rotate` draws
  the x axis along the direction it gets from `rotatez(vw, 0, -theta)`. For a point L along the
  drawn x axis at 30°, the transform gives L·cos(60°) = 0.5·L, not L. The error is cos(2θ): none at
  0°, and sign reversal past 45°. Found by reading the code and replicating its formulas; not yet
  checked in the running Tk app. The check: place the axes at 30°, track a point along the x axis,
  and compare with the axis length.

- **Auto Ruler (fixed in core, so both apps).** It used to stop short at pale tape and sit a few
  pixels off the object's edge (shadow and tape pulled the mask out). Fixed in `core/autoruler.py`;
  the Tk app's Auto Ruler gets the same change. Its tests (`tests/test_autoruler.py`) still pass.

## Decisions to make in the migration
- **Project files. Decided:** Tk-app files (format 1) import one way, in `phystrack_qt/tk_import.py`:
  canvas positions are scaled to the frame, and what has no Qt counterpart (crop, data and fits, OCR)
  is dropped and named. This format is never downgraded to fit the Tk app, and nothing writes the Tk
  format. Not yet checked: the frame each Tk object box was marked on (taken as the trim start; the
  status bar says so), and whether the imported boxes sit on the object.
- **Parent package imports.** `experiments/__init__.py` and `gui/components/__init__.py` import Tk
  code, so the Qt build imports the parent's modules through `phystrack_qt/parent_imports.py`.
  Making those `__init__` files lazy is the clean fix, once the tracker work in the parent settles.
- **Linux.** OpenCV's non-headless wheel points Qt at its own plugins, which clash with PySide6's.
  Use `opencv-python-headless` there. macOS needs neither (see the README).
