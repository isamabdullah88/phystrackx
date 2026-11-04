# Agent plan: history, windows, tools, and the in-app assistant

Status (2026-10-23): parts 1–5 are built in the Qt app (`qt/`), quick-and-dirty on purpose (see
[Architecture notes](#architecture-notes-quick-and-dirty-now-robust-later)). Part 5 is the in-app
assistant on a local model: [Part 5](#part-5-the-in-app-assistant-on-a-local-model-built). A code
review of parts 1–4 found ten bugs, all fixed with tests: [Review](#review-2026-10-23).

The goal: process the first trial of a series by hand (trim, ruler, axes, ball, track, plots, fit,
saves). Everything done is logged, so the log is a cookbook. Then tell an assistant "do the same
things for trial 2". It opens trial 2 in a new window, the view follows it, and it does the steps
one by one, checking each. Space stops it; the user corrects things, then tells it to go on. It
reads what the user changed and continues.

## What exists (parts 1–4)

| Part | Where | What |
|---|---|---|
| 1. Event history | `qt/phystrack_qt/history.py`, History dock in `main_window.py` | Every change is an event (op, text, who, params, snapshot). Clicking an event goes back to it. The revert is logged too, so clicking a later event goes forward again. Undone events are grey; the agent's are blue. |
| 2. Windows | `qt/phystrack_qt/windows.py` | Any number of trials, ids `w1`, `w2`... (in the title), each a tab (`tab_window.py`). File > New Tab (Ctrl+T), New Window (Ctrl+N). `run.py a.mp4 b.mp4 c.phystrack` opens one tab per file. |
| 3. Recipe | `qt/phystrack_qt/agent/relocate.py`, `tools.recipe` | A window's work as tool calls: `copy_setup`, `track`, `plots`, then the saves and exports in the order they were done. `copy_setup` finds the ruler, axes, ball and trim again in the new video (below). |
| 4. Tools | `qt/phystrack_qt/agent/` (`specs.py`, `tools.py`, `bridge.py`, `mcp_server.py`, `ptx.py`) | 21 tools over a localhost bridge in the app. They are served to MCP clients by a stdio shim, and to shells and scripts by `ptx.py`. Space stops a working agent. |

Plot settings (kinds, fit model, fit range) are now part of the project state. They are saved in
`.phystrack` files and copied between trials, with the fit range moved by the trim offset.

### Using it

```sh
cd qt && ~/.venvs/phystrackx-qt/bin/python run.py "Air Trial 1.phystrack"   # bridge on 127.0.0.1:8765
# MCP (e.g. Claude Code):
claude mcp add phystrack -- ~/.venvs/phystrackx-qt/bin/python "$PWD/phystrack_qt/agent/mcp_server.py"
# Shell:
python phystrack_qt/agent/ptx.py tools
python phystrack_qt/agent/ptx.py open video="Air Trial 2"
python phystrack_qt/agent/ptx.py run_recipe src=w1 only='[2]'   # Only the ball (object 2): one call, ~30 s
```

`PHYSTRACK_BRIDGE=0` turns the bridge off. `PHYSTRACK_BRIDGE_PORT` picks the port; the app
writes the one it got to `qt/cache/bridge.port`. `PHYSTRACK_QT_CACHE` moves the proxy cache
(the tests use it).

### Tool design: cheap for a small model

- **Few tools, one way to do each thing.** The usual request is two calls: `open(video)`, then
  `run_recipe(src)`. All 21 tool schemas come to about 1.6k tokens.
- **No ids to juggle.** `w` is optional everywhere; tools act on the agent's current window, which
  `open` sets. Videos are named by file name (`"Air Trial 2"`, case and extension forgiven), never
  by iCloud paths. A source window (`src`) never becomes the current window by accident.
- **One request, one answer, however long the work.** `open`, `copy_setup`, `track` and `plots`
  block until done (the app stays live). There are no job handles and no polling to get wrong.
- **Compact results.** Rounded numbers, file names not paths, no prose. `state` is under 600
  characters for a tracked trial. `history` sends at most 40 rows.
- **Errors say what to do.** `"no ruler yet: give p1 and p2 (its ends)"`,
  `"mark: box must be box [x, y, w, h]"`, `"no video 'x': call videos for the names"`.
- **Checks are done by the tools, not the model.** `run_recipe` stops at the first doubtful step
  with a reason:
  - a match score below 0.75;
  - an object lost on more than 10% of frames;
  - R² more than 0.05 below the source's;
  - a period more than 25% off the source's;
  - a period whose error is larger than half the period.

  It returns each step's result, and `next` (for a track, the step itself, since it must be redone).
- **Every change has `ev`.** That is its history event, so `revert(n)` is exact.

### How copy_setup finds things in the next trial

The camera moved 50–120 px between the Air trials, and zoomed about 5%. Each placed thing is
found again by template matching a patch around it from the source frame:

- **Ruler and axes:** each ruler end, and the axes origin. The axes are turned by however much the
  ruler turned.
- **Timing:** both videos are aligned on the drop, the first frame where a ball-sized blob moves
  down the ball's column for three frames running. The trim moves by the offset between the drops.
- **Ball:** taken just before the drop (at the release point) and found again there.

Measured against the user's own setups of Air Trials 1–4 (`relocate.py`):

| | Result |
|---|---|
| Ruler ends | 1–16 px from where the user put them (ruler ≈ 600 px long) |
| Drop frame | within 0–6 frames of each trial's own drop, every pairing |
| Ball (source = trial 3) | 7 px from the user's tracked ball on trial 4 |
| Axes origin | 13–16 px from trials 2 and 4 when the source is trial 3. Trial 1's origin is ~50 px off the others because the user placed it differently, not a matching error. |
| Time | 2.5–5 s per copy, mostly two passes over the videos |

Matches from trial 1 are weaker: it was tracked from frame 640, after its drop, so it has no box
at the release point. Every match returns a score, and a low one becomes a warning, so the agent
asks rather than guesses. Trial 1's object 1, which is not the ball, matched at 0.56–0.66 and was
then lost when tracked; that set the warning threshold at 0.75.

**The fit range is anchored on the drop.** Each trial's drop takes a different time (about
0.5–0.6 s), so a fit range copied by the trim start fits part of the fall. A copied range counts
from the end of the initial drop (its low) instead, found on the new trial's own data when its
plots open. If the source's track starts after its drop (trial 1's does), the copy starts exactly
at the new trial's drop low. On your own tracking of trials 2–4, a damped_linear fit from the drop's
low gives R² 0.998–0.999. Recipe from trial 1, run by the tools:

| Trial | R² | T (agent) | T, your own fit (converted to capture time) |
|---|---|---|---|
| 2 | 0.9978 | 1.195 s | 1.214 s |
| 3 | 0.80 (check fired), 0.9976 once the range ends at 6.85 s | 1.181 s | 1.185 s |
| 4 | 0.9988 | 1.182 s | 1.152 s (both_exp model) |

Known limit: the **end** of clean data is not detected. Trial 3's motion is disturbed after
about 7.1 s, and you trimmed it at frame 822 for that. The recipe copies trial 1's "to the end"
trim, so trial 3's fit fails the R² check, and the agent must set the range or ask.

(Your fit files in Measurements give T ≈ 4.6–4.9 s. That is in playback time at 29.97 fps; the
videos were recorded at 120 fps, and the app now measures in capture time. 4.745 s × 29.97/120 =
1.185 s.)

### What the testers found (Haiku subagents, real Air trials, ~70 tool calls)

Four cheap testers drove isolated copies of the trials through `ptx.py`. One of them was stopped
mid-track by a scripted "user" (Space, then a correction), and resumed. Fixed after their reports:

- **Space during a track.** It was reported as "tracking stopped before the end" rather than
  `stopped`: a race between the track ending and the stop being seen.
- **`run_recipe` output.** It hid each step's results (copy_setup's scores, the files saved), and
  listed a step that failed its check as done.
- **Track start frame.** `track` started every object at the earliest marked frame; each now
  starts at its own (or where the user corrected it).
- **Stale plots.** After a revert, open plots and `state` kept showing fits of data that was gone.
- **Fit range.** It was copied from the trim start; trial 2 gave T = 43.5 ± 21000 s. Now anchored
  on the drop (above).
- **Labels.** Unlabelled numbers (`T` is now `T`/`dT`, `s` is `secs`), checks phrased as
  statements, missing types in errors, and a ruler zoom between trials that was not visible (now
  `src_px`).
- **Ball only.** Keeping just the ball took `copy_setup`, `remove`, then `run_recipe start=1`. Now
  `run_recipe only=[2]` does it in one call.

The last round, after these fixes: one Haiku tester did "the same as trial 1 on trials 2, 3 and 4"
in one app (four windows), in 27 tool calls (~120k tokens of Haiku, 7 minutes):

| Trial | T ± dT (s) | R² | Needed |
|---|---|---|---|
| 2 | 1.195 ± 0.0013 | 0.9978 | nothing (after leaving out the non-ball object) |
| 3 | 1.178 ± 0.0012 | 0.9986 | the fit end moved to 6.5 s, after the R² check fired |
| 4 | 1.182 ± 0.0007 | 0.9988 | nothing |

## Architecture notes: quick-and-dirty now, robust later

Each note is also in the code where it applies (search for `QUICK-AND-DIRTY`).

| Area | Now (quick) | Robust version | Where it breaks |
|---|---|---|---|
| History source | Hooks `MainWindow._touch()`, which every change already calls. Changes of one kind within 300 ms make one event (a drag). The label is the status-bar message. | A command layer: every action a typed, replayable command, with the same path for buttons and tools. | A change that forgets `_touch` is not logged. A label can be a stale status message if a path sets none. |
| Snapshots | The state per event, with each track as a shallow copy (frame → box tuple), plus one per pending change. | Diffs, or replaying commands from checkpoints. | Memory grows with events × tracked frames. Fine for hundreds of events; not for long sessions with many objects. |
| Revert | Puts the snapshot back with `_clear_setup` + `_apply_state`, and logs a revert event (append-only). | The same, but also redrawing open plot windows from the restored data. | Open plot windows get the restored model and range, but keep their old data until reopened. |
| Windows | A module-level registry (one per process). Ids are never reused. | An application/document model passed explicitly. | Several app processes do not see each other's windows. |
| Tools → app | Tools call MainWindow's private methods (`_apply_trim`, `_add_ruler`...). | Tools go through the command layer. | Renaming those methods breaks tools silently (`tests/test_agent.py` catches most). |
| Who did it | "agent" for a window while any agent call works on it (counted per window). | Each command carries its author. | A user edit in that window during a long agent call is marked as the agent's. |
| Agent gate | While a call runs (or the in-app assistant thinks), Space only stops the agent. Within 30 s after an outside agent's call, Space stops it and still plays. | Outside agents report when they are working. | An outside agent that thinks for over 30 s between calls cannot be stopped with Space in that gap. |
| Assistant session | One conversation per app, on a worker thread. Context trimmed by message count. A reply that announces a step without making the call gets a nudge (recognised by its words). | Token-based trimming; structured "plan" output. | A very long conversation, or a model that announces steps in other words. |
| Relocation | Template matching plus column motion; no learning. | The reference library and Segment Anything of BATCH_TRIALS_PLAN.md step 3. | A large camera move (over ~220 px), a very different zoom, or a release from somewhere else. The scores show it. |
| Plot settings | One fit setting per plot kind (every object's `r` plot shares it). | Per object and kind. | Two objects whose `r` fits need different ranges. |
| Fit anchor | A copied range counts from the first high-to-low in the data (`core.fit.initial_drop`), on the object that drops most. | An explicit "release" event, shared by the video scan and the fit. | An experiment with no single initial drop. |
| Track start frames | `track` runs MainWindow.start_track once per start frame, swapping `win.objects` for that group meanwhile. | Per-object start frames in TrackJob. | Code that reads `win.objects` during that brief swap. |
| Recipe resume | By step index (`start=next`). | A check of the state before each step ("already done?"). | Resuming at the wrong index after the user redid a step by hand repeats or skips it. |
| Bridge | Plain HTTP on 127.0.0.1, no auth. Waits poll every 100 ms. The port is written to a file. | A token in the port file, and signals instead of polling. | Any local process can drive the app. |
| MCP | JSON-RPC over stdio by hand: initialize, tools/list, tools/call, ping. | The official `mcp` SDK. | Newer protocol features (progress, cancellation) are missing. |
| Dialogs | Tools avoid every dialog path (they check first). | No dialogs below the UI layer. | An unexpected modal dialog holds a tool for up to 180 s, then it errors. |
| Test hook | `POST /user` on the bridge (Space, or a tool run as the user). | A proper test driver. | It is not in the tool list, but any local process could call it. |

## Part 5: the in-app assistant on a local model (built)

Each window has an **Assistant** dock under the History (`qt/phystrack_qt/agent/session.py`,
`chat_panel.py`, `llm.py`). Type a request ("do what I did in w1 on trials 2 to 4") and it works
through the tools while you watch:

- each call and its result show in the dock;
- each change shows in the history (blue);
- the window it works in comes to the front.

Its questions come with buttons. Space (outside the text box) or Stop cuts off the reply or the
tool call under way. Start, with a note typed if you like, tells it what you changed meanwhile and
goes on; End drops the request.

### The runner and the model

- **Strata** ([github.com/Niko1221/Strata](https://github.com/Niko1221/Strata)) does not run on
  this Mac. It runs one model family (a 125B mixture-of-experts Qwen3.8, and a 35B variant) on
  Windows, Linux or Apple Silicon. It needs at least 32 GB of RAM and VRAM together, a 12 GB+
  NVIDIA or AMD card on a PC, and ~80 GB of disk. This is an Intel i9-8950HK MacBook Pro with a
  4 GB Radeon. Strata serves an OpenAI-compatible API at `http://127.0.0.1:8080/v1`, so on a
  machine that runs it, set `PHYSTRACK_LLM_URL` to that.
- **Here: Ollama** (installed, llama.cpp underneath, CPU only). The assistant starts it if it is
  not running. The client speaks the OpenAI-compatible chat API, so llama-server, LM Studio and
  vLLM work too (`PHYSTRACK_LLM_URL`, `PHYSTRACK_LLM_MODEL`, or the dock's model list).

Measured on this machine:

| Model | One tool-calling turn | Why |
|---|---|---|
| `qwen3:4b-instruct` (default) | 2–3 s warm; first request ~40 s with the model load | No reasoning text. Prompts read at ~650 tokens/s, written at ~9 tokens/s, 15–23 tokens per call. |
| `qwen3:4b` | 60–125 s | Writes 500–950 tokens of reasoning first. `think: false`, `reasoning_effort` and `/no_think` did not stop it. |

Live test (`qt/tests/live_assistant.py`, synthetic clip): "do the same things I did in w1 on
<clip>". It opened the clip, ran the recipe, stopped at a check, asked a question with buttons,
went on from the next step, and ended with T and R². That took 7 tool calls in about 2 minutes.

### Its lifetime (kept simple, so a small model cannot get it wrong)

1. **One conversation per app**, run on a worker thread until the model answers without a tool
   call (or after 40 calls).
2. **Every turn:** the same system prompt and tool list (so Ollama reuses them from its cache),
   then the conversation, with tool results more than 12 messages old cut to 160 characters.
3. **Tools for the model:** `windows`, `videos`, `state`, `recipe`, `open`, `run_recipe`,
   `plots`, `data`, `revert`, plus `ask_user`. The fine-grained ones stay for MCP clients.
4. **Small-model habits handled in code:**
   - Window ids it makes up (`w="cur"`) mean the current window.
   - A reply that only announces the next step gets a nudge to make the call (at most twice).
   - Reading a window (`state w=w1`) never changes the window it works in.
5. **Stop and Start** use the same gate as MCP clients. Start sends the `resume` result (your
   history events since the stop) and your note as a user turn.

### Still to do

- Progress lines while `run_recipe` runs (a callback on the bridge).
- `look`: the frame with its overlays, for models that can see (`copy_setup` says "check it on
  frame 393", but a text-only model cannot look).
- Finding where a trial's clean motion ends (the fit range's end and the trim's), so the agent
  does not have to read `data` for it.
- Comparing small models with the tester harness: the scripted user (Space and corrections, via
  `POST /user`) works with any agent.

## Review (2026-10-23)

A code review of parts 1–4 found ten bugs. Each is fixed and covered by `tests/test_agent.py`,
`tests/test_retrack.py` or `tests/test_assistant.py`:

1. Plots of data that has since changed (a new track, video or setup) were brought up, saved and
   reported. They are now closed and replaced, keyed by their data.
2. After a correction was tracked, the agent's next `track` started again from the marked frame,
   undoing it. Now only objects that need it are tracked.
3. Tracking again kept old boxes from before a later trim.
4. A fit range wholly outside the data inverted. It now falls back to the whole data.
5. Going forward in the history left earlier events grey. "Undone" is now worked out from each
   event's parent.
6. Overlapping agent calls cleared each other's agent mark, so Space could not stop an agent's
   track. The mark is now counted per window, and the track owned by the agent is flagged.
7. Space up to 60 s after any agent call stopped the agent instead of playing. Now Space only
   stops while a call runs; otherwise it plays (and stops an agent between calls).
8. A pending change leaked into the next history.
9. A user edit just before an agent call was logged as the agent's.
10. Every drag move copied the whole state, tracks included. Snapshots are now shallow copies.
