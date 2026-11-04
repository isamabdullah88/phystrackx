"""
The tracking methods Track offers, and the dialog that picks one before a run.

The methods are the parent repo's (experiments/rigid): the blob tracker and the whole-clip
(offline) engine from the tracker benchmarks, and NanoTrack, the neural model the app used so far.
Scores on the parent's benchmark (tests/bench_tracker.py; 1.05 is perfect; training clips /
unseen variations / held-out scenes / synthetic balls on real lab footage):

    Whole clip, background, physics    0.96 / 0.93 / 0.72 / 0.70
    Blob tracker, still background     0.79 / 0.71 / 0.62 / 0.83
    Blob tracker                       0.65 / 0.56 / 0.57 / 0.72
    NanoTrack                          fails the dirty-lens and cover scenes (most below 0.5)

Options (blob and whole-clip methods):
- background: take away the still background (a camera on a tripod), so static clutter that
  looks like the ball (lens dirt, the tube's edges, a clamp) no longer competes with it.
- physics: after tracking, drop positions that jump off the motion for a frame or two, fill
  hidden stretches with the motion on both sides, and smooth the jitter.
- centre: a shiny ball's highlights pull the found centre 1-3 px toward them, more when motion blur
  smears them; this moves every position to the centre of the ball's round outline (the parent's
  experiments/rigid/ringfit.py; 2.2 px off before, 0.2 px after on Air Trial 2), and keeps the
  selection's offset where the outline is not clear.
"""

from dataclasses import dataclass, field

from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QGroupBox,
                               QLabel, QRadioButton, QVBoxLayout)


@dataclass(frozen=True)
class Method:
    key: str
    title: str
    about: str
    engine: str                 # "offline", "blob" (experiments/rigid/cliptrack.py) or "nanotrack"
    live: bool                  # Positions appear as it runs (otherwise it reads the clip first)
    options: tuple = ()         # Which options apply (see OPTIONS)
    defaults: dict = field(default_factory=dict)  # Option -> on/off for this method


OPTIONS = {
    "background": ("Take away the still background (camera on a tripod)",
                   "Static clutter that looks like the ball (dirt, edges, clamps) stops competing with it."),
    "physics": ("Physics fit after tracking",
                "Drops one-frame jumps, fills hidden stretches from the motion around them, smooths jitter."),
    "centre": ("Find the centre from the ball's round edge",
               "A shiny ball's highlights, smeared when it moves fast, pull the found centre aside by a "
               "few pixels; this fits a circle to the ball's outline on every frame instead."),
}

METHODS = [
    Method("offline", "Whole clip (recommended)",
           "Reads the clip, finds candidates in every frame, and picks the path that fits the motion "
           "over the whole clip. Gets through covers, look-alikes and dirty lenses. Slower; the path "
           "shown while it reads is its best so far, and can still change.",
           "offline", False, ("background", "physics", "centre"),
           {"background": True, "physics": True, "centre": True}),
    Method("blob_background", "Blob tracker with still background (live)",
           "Follows the ball frame by frame as a round blob, after taking away what does not move. "
           "Fast, and best on real footage so far; can lose the ball behind a long cover.",
           "blob", True, ("background", "physics", "centre"),
           {"background": True, "physics": False, "centre": True}),
    Method("blob", "Blob tracker (live)",
           "The same, on the picture as it is. For a moving camera.",
           "blob", True, ("physics", "centre"), {"physics": False, "centre": True}),
    Method("nanotrack", "NanoTrack neural model (live)",
           "A small neural network that follows any object's look (not only balls). The method used "
           "so far; it struggles with small shiny balls, dirt and covers.",
           "nanotrack", True),
]
BY_KEY = {m.key: m for m in METHODS}
DEFAULT = "offline"


def engine_settings(method: Method, options: dict) -> dict:
    """The parent engine's settings for a method and its options (cliptrack / BlobSettings names)."""
    on = {k: options.get(k, method.defaults.get(k, False)) for k in method.options}
    values = {}
    if on.get("background"):
        values["background_mix"] = 1.0
    if on.get("physics"):
        values["physics"] = True
    if on.get("centre"):
        values["selection_offset"] = True
        values["ring_centre"] = True
    return values


class TrackDialog(QDialog):
    """Pick a method and its options; Track (Enter) starts the run."""

    def __init__(self, parent, method: str, options: dict, count: int, frames: int) -> None:
        super().__init__(parent)
        self.setWindowTitle("Track")
        self.options = dict(options)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Track {count} object{'s' if count != 1 else ''} over {frames} frames with:"))
        self.group = QButtonGroup(self)
        self.radios = {}
        for m in METHODS:
            radio = QRadioButton(m.title)
            radio.setToolTip(m.about)
            self.group.addButton(radio)
            self.radios[m.key] = radio
            layout.addWidget(radio)
            about = QLabel(m.about)
            about.setWordWrap(True)
            about.setContentsMargins(24, 0, 0, 6)
            layout.addWidget(about)
        box = QGroupBox("Options")
        inner = QVBoxLayout(box)
        self.checks = {}
        for key, (label, tip) in OPTIONS.items():
            check = QCheckBox(label)
            check.setToolTip(tip)
            check.toggled.connect(lambda on, k=key: self._set(k, on))
            self.checks[key] = check
            inner.addWidget(check)
        layout.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.track_btn = buttons.addButton("Track", QDialogButtonBox.ButtonRole.AcceptRole)
        self.track_btn.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for key, radio in self.radios.items():
            radio.toggled.connect(lambda on, k=key: on and self._choose(k))
        self.radios.get(method, self.radios[DEFAULT]).setChecked(True)
        self._choose(self.method)

    @property
    def method(self) -> str:
        for key, radio in self.radios.items():
            if radio.isChecked():
                return key
        return DEFAULT

    def _set(self, key: str, on: bool) -> None:
        self.options.setdefault(self.method, {})[key] = on

    def _choose(self, key: str) -> None:
        """Shows the options that apply to the method, set as last chosen for it (or its defaults)."""
        m = BY_KEY[key]
        chosen = self.options.get(key, {})
        for name, check in self.checks.items():
            check.blockSignals(True)
            check.setEnabled(name in m.options)
            check.setChecked(name in m.options and chosen.get(name, m.defaults.get(name, False)))
            check.blockSignals(False)

    def chosen(self) -> tuple[str, dict]:
        """(method key, its options) as picked."""
        m = BY_KEY[self.method]
        return m.key, {k: self.checks[k].isChecked() for k in m.options}
