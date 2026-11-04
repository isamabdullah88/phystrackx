# PhysTrackX tests

Run everything from the repo root:

    uv run python -m tests.run_all

Run one module:

    uv run python -m tests.run_all test_rect_editing

Modules run four at a time (`--jobs 1` runs them one after another). Each one gets its own run
folder for clips, proxies and logs, which is removed when it passes; a failing module's folder is
kept and named in the output.

## What is covered

| Module | Needs a window | Covers |
|---|---|---|
| `test_view_math` | no | zoom/pan transform, round trips, window bounds, zoom keeps the point under the pointer, pan follows the fingers |
| `test_project_io` | no | project file write/read, version and missing-video errors |
| `test_cli` | no | `--help`, `--video`/`--project` validation, `--download-models` present |
| `test_models` | no | model file detection; no download when files exist |
| `test_rect_editing` | yes | draw at zoom, circle shape, move, resize handle, tiny-click discard |
| `test_roundtrip` | yes (2 processes) | save a full setup, reopen it, compare every part |
| `test_trim_crop_zoom` | yes | trim crop size, zoom strip for axes and scale, strip hides on apply |
| `test_fit` | no | damped oscillator fit recovers known parameters; peak spacing and fit period agree; a range uses only its own data; the plot slider updates the fit |
| `test_crop_fit` | yes | applied crop fills the view at its ratio; overlays stay in frame pixels; clearing returns to 1:1 |
| `test_saved_data` | no | saved CSV round trip; save dialog starts in the saved folder; project keeps the data entry; plot from the reloaded CSV |
| `test_axis_geometry` | no | axis line keeps its angle at every zoom; endpoint lies on the canvas edge |
| `test_units` | yes (ruler only) | typed "50 cm" parses to value and unit; the ruler shows, saves and restores the unit; plot and fit labels carry the unit |
| `test_assist` | no | pixel-change gate quiet for a lone ball, fires for a hand beside it; hard engine cooldown; a run with the hard engine keeps points on the ball; real Segment Anything picks the ball, not the hand |
| `test_crash` | no (one check uses a window) | worker-thread exceptions reach the crash log with traceback and versions; a C-level crash still prints the Python stack; garbage collection runs only on the UI thread |
| `test_mode_switch` | yes | starting the axis or the ruler cancels an unfinished one of the other |
| `test_navigation` | yes | trackpad and wheel pan in both directions, Cmd +/- zoom around the pointer, Cmd 0 back to the whole picture, a scroll burst draws once, axes drag by the origin and keep their angle, window title shows project and video |
| `test_trim_again` | yes | a second trim (with crop) is recorded in full-video frames; a failed trim keeps the current clip |
| `test_tracking` | yes | live frames, refused second run, stop keeps results, manual positions |
| `test_overlay_geometry` | yes | a synthetic frame is drawn at many zooms, pans, window sizes and frame offsets, through both the proxy and the full-resolution path; each square's drawn centre must be within 1 px of where the overlay transform puts it |
| `test_overlay_alignment` | yes | the same check on a real rotated clip with two markers (the markers' positions are only known to about half a frame pixel, so it catches gross scale and offset errors) |
| `test_tracker_scenarios` | no | ten synthetic scenarios from easy (white screen) to extreme (camouflage with look-alikes and occluders), plus a hand drop; the circle-selected ball is tracked and compared with its true path. Two are marked as known weaknesses with a floor. The engine scored is NanoTrack unless `PHYSTRACK_TRACKER` names another (`vittrack`, `trackpy`) |
| `test_tracker_muddy` | no | fifteen harder scenarios: a chrome ball released from rest into a glass tube through clean, greasy, wet and filthy lenses, a tiny ball, and covers (a slab, a bar, a black glove, a second ball, a clamp arm) that hide it for a while. Scores count visible frames, plus frames to be back on the ball after a cover. Expected to fail with NanoTrack (the default engine; `PHYSTRACK_TRACKER` as above) |
| `test_start_view` | yes | a rotated phone-style clip opens whole: the drawn picture lies inside the video area, fills one side, and is the frame scaled by the view fit |
| `test_window_features` | yes | File menu and Open Recent; Clear Data; dark text on the cyan strips; resizing the window re-fits the picture and keeps the ruler on it; a .phystrack given as --video opens as a project |
| `test_tracker_accuracy` | no | tracker follows a synthetic ball with known path; pipeline keeps points on the ball at native size, when downscaled, and when tracking the full-resolution copy at a downscaled view; full-size region maps the crop |

Tools beside the tests (not run by `run_all`):
- `uv run python -m tests.benchmark_report` writes `temp/benchmark_report.html`: every scenario
  of both benchmarks with a player, the engines' positions, an error chart (hidden frames shaded)
  and the scores, NanoTrack beside the trackpy blob tracker (`--engines`, `--settings`).
- `uv run python -m tests.tune_tracker` searches the blob tracker's settings with Optuna and opens
  a live page (http://127.0.0.1:8765): a plot of every trial, the score's parts (accuracy, speed
  reward, regression penalty), the top five, which settings matter, and Pause, Stop and Show
  holdout buttons. It trains on two random draws of 20 scenario kinds (`build_scenarios(draw)`;
  draw 0 is what the tests use) and holds out an unseen draw of those, five other kinds, and
  synthetic balls on real Air Trial footage. Each run's study, best and top five go to
  `temp/tune_runs/<time>/` (the best also to `temp/tuned_blob_settings.json`), saved at every new
  best. `--minutes N` sets a time limit, `--focus N` runs stage two on the N most important
  settings of the last run, `--score` only scores, `--view` hosts the page for a run started
  elsewhere, `--resume` continues the last run. Clips are drawn once into `temp/tracker_frames`
  (about 2.8 GB).
- `uv run python -m tests.bench_tracker ENGINE[@SETTINGS.json][,name=value...]` scores a tracking
  engine (`blob` or `offline`, see `experiments/rigid/cliptrack.py`) on every cached clip and on
  the labelled real clips, per part, and keeps the result in `temp/bench/<label>.json`;
  `--compare` lists saved results side by side with the clips that changed most. The ball is
  selected with an automatic outline, as in the Qt app (`--selection box`: the circle's square).
- `uv run python -m tests.label_real VIDEO --start S --seconds N` opens a page for labelling the
  ball's centre in a stretch of a real video (Track pre-fills every frame; you fix it). Labels go to
  `tests/real_labels/*.json` (`tests/real_clips.py` reads them; the videos stay in
  `PHYSTRACK_REAL_FOOTAGE`).
- `uv run python -m tests.prelabel_real` pre-fills those labels without a person: two trackers
  follow the ball backward from where it rests at the end of each video, and frames where they agree
  get a label at the ball's geometric centre (a circle fitted to its edge). Such files say
  `"checked": "pre-filled"` until someone checks them in `label_real`.

## Notes

- The test clip is synthetic (`testsrc2`, 12 s, 540x960), made with ffmpeg into the system
  temp folder, so the tests do not depend on personal videos.
- Tests that open the app run in their own process. Put a new app test in its own module.
- Message boxes are recorded in `harness.DIALOGS` instead of shown.
- Network tests (downloading the models) only run with `PHYSTRACK_TEST_NETWORK=1`.
- Tcl/Tk: on macOS, `harness.setup_env()` points Tcl/Tk at the uv-managed Python if the venv
  cannot find them.

## Adding a test

1. Add a function `test_<something>()` to the module that covers the area.
2. Use `check(name, condition, detail)` for each expectation.
3. Add it to the module's `if __name__ == "__main__":` list.
4. For a new area, copy an existing `test_*.py` and add a row to the table above.
