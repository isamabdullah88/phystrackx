# Plan: many trials, faster

Status: plan only. Nothing here is built yet.

## Goal

Run many trials, for example 4 Air trials and 4 Water 270 trials. Each trial is one video of a ball
falling and oscillating. For each trial the outputs are:

- the r(t) plot, with the fit and the range used,
- the **initial drop length** (first high to first low) and the **period** (best T), with errors,
- all of it in a folder per trial, plus one summary table per condition and one for everything.

Most of the time per trial today goes on setup: trim, crop, axes, ruler, ball box. Tracking and
fitting already take seconds. So the plan is mostly about doing the setup once, and reusing or
finding it in the other trials.

## Folder layout (input and output)

Input: one folder of videos, named `<Condition> Trial <n>.mp4`, for example `Air Trial 1.mp4` or
`water 270 Trial 1.mp4`. Names are read without regard to case.

Output, next to the inputs (matching the existing `Measurements/Air_trials/` folder):

```
Measurements/
  Air_trials/
    Air Trial 1/
      Air Trial 1.phystrack     project (setup, trim, ruler, axes, box)
      Air Trial 1.csv           t, x, y, r (full precision, with units)
      Air Trial 1_r.png         r plot with fit, drop markers, and range
      results.json              drop length, period, fit model and parameters, errors, range
    Air Trial 2/ ...
    summary.csv                 one row per trial: drop length, period, errors, fit R²
  Water_270_trials/ ...
  summary_all.csv               every condition, one row per trial
```

`results.json` is what the summary tables are built from, so a trial can be redone alone and the
summaries rebuilt.

## Steps, in order of value

### 1. Batch runner, reusing setup between trials (largest gain, least work)

Within one condition the camera usually doesn't move. So trial 1's crop, axes, ruler, and ball box
are already correct, or nearly correct, for trials 2–4.

- A **Batch** window: pick the input folder, and it lists the videos with their condition and trial
  number from the names, plus a status per trial (to do, needs review, done).
- **"Set up from another trial"**: copies the crop, axes, scale (with units), ball box, fit model,
  and plot range from a finished project into the new one. The user only checks it and adjusts the
  trim.
- Then track, fit, and export in one go, and write the folder above.
- Tracking runs in the background while the user sets up the next trial.

### 2. Automatic trim

The trim marks the drop: from the moment the ball is let go until it settles or leaves the frame.

- Start: the first frame where the ball's box starts moving (the ring-change measure from
  `experiments/rigid/assist.py`, on the ball's box).
- End: when the motion in the ball's column stays below a threshold for about a second, or at the
  end of the video.
- It is shown as a suggestion on the trim bar, and the user can drag it.

### 3. Experiment reference: find the ruler, axes, and ball in a new video

A **reference** is made once per experiment from one finished trial. It stores labelled image
patches, not fixed positions, so it still works when the camera moves a little.

- **Ruler:** an image patch of the ruler, its real length (`50 cm`), and which side to measure.
  In a new video: template matching (OpenCV, at a few scales and angles) finds it roughly, then
  Auto Ruler with Segment Anything snaps the ends. This one should be reliable, since the brown
  ruler stands out.
- **Axes:** these are harder to see directly. Store the origin and direction *relative to the
  ruler* (for example, origin at the ruler's bottom end and y along the ruler), plus an optional
  patch of an origin landmark such as the tube's bottom. Once the ruler is found, the axes follow
  from it.
- **Ball:** an image patch of the ball, and roughly where it starts relative to the ruler. In a new
  video, search near that point on the first frames: template matching, then a Segment Anything
  point prompt to get a clean box. The hand is the hard part, so the search runs on the frame where
  motion starts (from step 2), when the hand is moving away. The assist engine handles the rest.
- One Segment Anything image encoding per trial (about 11 s on this CPU) serves all three
  prompts: the encoder runs once, then each prompt is quick.

Stored as `references/<experiment>/reference.json` plus PNG patches, so it can be read and edited.

### 4. Review grid

The automatic steps will sometimes be wrong. A grid shows each trial with its key frame (ruler,
axes, and ball box drawn on it), its r plot thumbnail, and its drop length and period. A trial that
looks wrong opens in the normal editor with one click. Accepting writes its results.

### 5. Results and plots

- The r plot is saved as a PNG per trial, with the fit, the drop markers, and the range shaded.
- The summary tables give the mean and standard error per condition for the drop length and the
  period, which is what the write-up needs.

## Time estimate per trial

| Step | Now (by hand) | With steps 1–2 | With steps 1–4 |
|---|---|---|---|
| Setup (trim, crop, axes, ruler, box) | several minutes | about 30 s of checking | about 15 s of reviewing |
| Tracking (about 750 frames) | about 10–20 s | the same, in the background | the same |
| Fit and export | about 1 minute by hand | automatic | automatic |

## Questions that decide the design

1. Does the camera stay in place between trials of one condition, and between conditions?
2. Is the ruler always the same physical length, and in view in every video?
3. Which axis convention do you use: origin at the tube's bottom, at the ruler's end, or at the
   ball's starting point?
4. Which fit model is the default for these runs (damped + drift, or quadratic drag + drift)?
5. Which r range is used: from the release, or from the first high?

## What already exists to build on

- Initial drop and period on the plot (`gui/components/plot/fit.py`: `initial_drop`,
  `best_period`).
- Project files with setup and saved data (`core/project.py`).
- Auto Ruler with Segment Anything (`core/autoruler.py`, `media/segmenter.py`).
- The pixel-change gate and the Segment Anything hard engine (`experiments/rigid/assist.py`).
- CSV export with units (`gui/components/plot/save.py`).
