"""
The app's settings (the Settings window, settings_dialog.py), kept between runs: a small JSON file
in ~/.phystrackx beside the recent list. PHYSTRACK_QT_HOME moves the folder (the tests use it).

Each setting has a default, and a value read back that is missing or of the wrong kind falls back to
it. `changed` tells whoever shows a setting (such as the assistant's Reasoning checkbox) to show the
new value.
"""

import json
import logging
import os

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

DEFAULTS = {
    "show_reasoning": False,   # The assistant docks show a thinking model's reasoning
    "max_tokens": 400,         # The longest reply the assistant's model may write, reasoning included
    "retry_context_limit": True,  # Retry once with a compact current-request prompt on input overflow
}
MAX_TOKENS_RANGE = (100, 32768)


def settings_file() -> str:
    home = os.environ.get("PHYSTRACK_QT_HOME") or os.path.join(os.path.expanduser("~"), ".phystrackx")
    return os.path.join(home, "settings-qt.json")


def _valid(key: str, value) -> bool:
    if key == "max_tokens":
        return isinstance(value, int) and not isinstance(value, bool) and \
            MAX_TOKENS_RANGE[0] <= value <= MAX_TOKENS_RANGE[1]
    return isinstance(value, type(DEFAULTS[key]))


class Settings(QObject):
    changed = Signal(str)   # The key that changed

    def __init__(self) -> None:
        super().__init__()
        self._values = dict(DEFAULTS)
        try:
            with open(settings_file(), encoding="utf-8") as f:
                saved = json.load(f)
        except (OSError, ValueError):
            saved = {}
        if isinstance(saved, dict):
            for key, value in saved.items():
                if key in DEFAULTS and _valid(key, value):
                    self._values[key] = value

    def get(self, key: str):
        return self._values[key]

    def set(self, key: str, value) -> None:
        if not _valid(key, value):
            raise ValueError(f"bad value for setting {key!r}: {value!r}")
        if self._values[key] == value:
            return
        self._values[key] = value
        try:
            os.makedirs(os.path.dirname(settings_file()), exist_ok=True)
            with open(settings_file(), "w", encoding="utf-8") as f:
                json.dump(self._values, f, indent=2)
        except OSError:
            logger.exception("Could not save the settings")
        self.changed.emit(key)


_shared: Settings | None = None


def shared() -> Settings:
    """The app's settings (create them on the Qt thread)."""
    global _shared
    if _shared is None:
        _shared = Settings()
    return _shared
