"""
The Settings window: PhysTrackX > Settings… (Cmd+,) on macOS, Settings > Settings… (Ctrl+,)
elsewhere. One window for the app, not modal (the assistant's tools wait for the Qt thread, and a
modal window would hold them up). A change applies and is saved at once, as macOS settings are.
"""

from PySide6.QtCore import QCoreApplication, QTranslator
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel,
                               QSpinBox, QVBoxLayout)

from . import settings as app_settings


class _SettingsName(QTranslator):
    """Qt names the app menu's settings item "Preferences...", as macOS did before Ventura (13); macOS
    apps now say "Settings…". Qt looks the name up through the translators, so this one answers it."""

    def translate(self, context, source, disambiguation=None, n=-1):
        if context == "MAC_APPLICATION_MENU" and source == "Preferences...":
            return "Settings…"
        return None   # Every other text: as Qt has it


_translator: _SettingsName | None = None


def name_settings_item(app: QCoreApplication) -> None:
    """Call once the app exists, before any menu is made."""
    global _translator
    if _translator is None:
        _translator = _SettingsName()
        app.installTranslator(_translator)


class SettingsDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Settings")
        self.settings = app_settings.shared()
        layout = QVBoxLayout(self)

        assistant = QGroupBox("Assistant")
        form = QFormLayout(assistant)
        self.reasoning = QCheckBox("Show the model's reasoning")
        self.reasoning.setToolTip("Thinking models only (such as qwen3:4b). The same as the Reasoning box "
                                  "in the Assistant panel.")
        self.reasoning.toggled.connect(lambda on: self.settings.set("show_reasoning", on))
        form.addRow(self.reasoning)
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(*app_settings.MAX_TOKENS_RANGE)
        self.max_tokens.setSingleStep(100)
        self.max_tokens.setSuffix(" tokens")
        self.max_tokens.valueChanged.connect(lambda n: self.settings.set("max_tokens", n))
        form.addRow("Reply length cap", self.max_tokens)
        note = QLabel("The longest reply the model may write in one turn, its reasoning included. "
                      "A thinking model needs more (2000 or so). A higher cap does not slow replies down: "
                      "the model stops when it is done.")
        note.setWordWrap(True)
        form.addRow(note)
        layout.addWidget(assistant)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        self.settings.changed.connect(self._show)
        self._show()

    def _show(self, _key: str = "") -> None:
        """Shows the current values (also when changed elsewhere, such as the panel's Reasoning box)."""
        for widget, value in ((self.reasoning, self.settings.get("show_reasoning")),
                              (self.max_tokens, self.settings.get("max_tokens"))):
            widget.blockSignals(True)
            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            else:
                widget.setValue(value)
            widget.blockSignals(False)


_dialog: SettingsDialog | None = None


def show() -> SettingsDialog:
    """Opens the Settings window, or brings it to the front if open."""
    global _dialog
    if _dialog is None:
        _dialog = SettingsDialog()
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()
    return _dialog
