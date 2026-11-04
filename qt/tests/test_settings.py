"""
The Settings window (settings_dialog.py) and the settings it keeps (settings.py): opened from the menu
(Settings…, in the app menu on macOS), a change is saved at once and read back on the next run, and the
assistant follows them: its Reasoning box and the reply length cap it asks the model for.

    ~/.venvs/phystrackx-dev/bin/python tests/test_settings.py      (PHYSTRACK_QT_SHOW=1 to watch)
"""

import json
import os
import tempfile

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

os.environ["PHYSTRACK_QT_HOME"] = tempfile.mkdtemp()   # Its own settings file: the tests run side by side

from PySide6.QtGui import QAction  # noqa: E402

from phystrack_qt import settings, windows  # noqa: E402
from phystrack_qt.agent.chat_panel import ChatPanel  # noqa: E402
from phystrack_qt.agent.session import AgentSession  # noqa: E402
from test_assistant import ScriptedModel  # noqa: E402


def test_settings() -> None:
    # Defaults, then a change saved at once and read back by the next run; a bad file is ignored
    s = settings.shared()
    h.check("defaults", s.get("show_reasoning") is False and s.get("max_tokens") == 400)
    s.set("max_tokens", 2000)
    h.check("a change is saved at once", json.load(open(settings.settings_file()))["max_tokens"] == 2000)
    h.check("the next run reads it back", settings.Settings().get("max_tokens") == 2000)
    with open(settings.settings_file(), "w") as f:
        json.dump({"max_tokens": "lots", "show_reasoning": 3, "unknown": 1}, f)
    h.check("bad values fall back to the defaults",
            settings.Settings().get("max_tokens") == 400 and settings.Settings().get("show_reasoning") is False)
    try:
        s.set("max_tokens", 5)
        h.check("a cap out of range is refused", False)
    except ValueError:
        h.check("a cap out of range is refused", True)

    # The menu: Settings… with the Preferences role (macOS puts it in the app menu) opens the window
    tab = windows.new_window(cache_dir=os.path.join(h.WORK, "cache"))
    host = tab.host
    action = host.settings_action
    h.check("the menu has Settings…, in the app menu's place",
            action.menuRole() == QAction.MenuRole.PreferencesRole and action.shortcut().toString() == "Ctrl+,")
    action.trigger()
    from phystrack_qt import settings_dialog
    dialog = settings_dialog._dialog
    h.check("Settings… opens the Settings window", dialog is not None and dialog.isVisible())
    h.check("it is not modal (the assistant's tools wait for the Qt thread)", not dialog.isModal())
    h.check("it shows the current values", dialog.max_tokens.value() == 2000 and not dialog.reasoning.isChecked())
    action.trigger()
    h.check("a second Settings… brings back the same window", settings_dialog._dialog is dialog)

    # The assistant follows the settings both ways, and asks the model for the cap
    model = ScriptedModel([{"say": "Hello."}])
    session = AgentSession(llm=model)
    panel = ChatPanel(session)
    dialog.reasoning.setChecked(True)
    h.check("the window's box ticks the panel's Reasoning box", panel.reasoning_box.isChecked())
    panel.reasoning_box.setChecked(False)
    h.check("and the panel's box unticks the window's", not dialog.reasoning.isChecked()
            and s.get("show_reasoning") is False)
    dialog.max_tokens.setValue(3000)
    session.send("Hi")
    h.check("a request ends", h.pump(lambda: session.state == "idle" and not model.turns, 30))
    h.check("the model is asked for at most the cap", model.max_tokens == [3000], str(model.max_tokens))

    dialog.close()
    panel.deleteLater()
    tab._dirty = False
    host.close()
    h.pump(timeout=0.2)


if __name__ == "__main__":
    h.app()
    test_settings()
    h.finish()
