"""
The Assistant dock, under the History: the conversation with the in-app assistant (session.py),
a box to type in, and Stop / Start. Every window has one; they all show the one conversation.

While the assistant works, the main window's status bar says that Space stops it. After Send, the
keyboard goes back to the picture, so Space does that (in the text box, Space types a space). A
question from the assistant shows its answers as buttons. While it starts or thinks and no text has
come yet, a blinking cursor shows that it is working. Reasoning (a checkbox, the same in every
dock) shows a thinking model's reasoning, in italics, before each reply.
"""

import base64
import html
import json
import threading

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QTextBrowser, QVBoxLayout, QWidget)

STATES = {"setup": "setting up…", "thinking": "thinking…", "acting": "working…", "waiting": "asks you",
          "stopped": "stopped"}
# Idle, the label is the model runner's status (runner.py): "ready" only when the runner answered
RUNNER_TEXT = {"checking": "checking the model runner…", "starting": "starting Ollama…", "ready": "ready",
               "no_model": "model not downloaded", "not_installed": "Ollama not installed",
               "installing": "installing Ollama…", "downloading": "downloading the model…",
               "down": "model runner not answering", "failed": "model runner failed"}


class _ClickAway(QObject):
    """Takes the selection out of the text box when the mouse is pressed anywhere else in the app."""

    def __init__(self, box: QLineEdit, parent: QObject) -> None:
        super().__init__(parent)
        self.box = box

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress and watched is not self.box and self.box.hasSelectedText():
            self.box.deselect()
        return False


class ChatPanel(QWidget):
    _models_ready = Signal(list)

    def __init__(self, session, focus_after_send=None) -> None:
        super().__init__()
        self.session = session
        self.focus_after_send = focus_after_send   # Where the keyboard goes after Send (the picture)
        self._live = ""                            # The reply being written
        self._live_thought = ""                    # Its reasoning, as it is written
        self._quick_look_images: dict[str, dict[str, QImage]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        top = QHBoxLayout()
        top.addWidget(QLabel("Model"))
        self.model_box = QComboBox()
        self.model_box.setEditable(True)
        self.model_box.addItem(session.llm.model)
        self.model_box.setToolTip(f"The local model, from the runner at {session.llm.url} "
                                  "(PHYSTRACK_LLM_URL: Ollama here; Strata or llama-server elsewhere)")
        top.addWidget(self.model_box, 1)
        self.reasoning_box = QCheckBox("Reasoning")
        self.reasoning_box.setToolTip("Show the model's reasoning (thinking models only, such as qwen3:4b)")
        self.reasoning_box.setChecked(session.show_reasoning)
        self.reasoning_box.toggled.connect(session.set_show_reasoning)
        top.addWidget(self.reasoning_box)
        self.retry_context_box = QCheckBox("Retry on context limit")
        self.retry_context_box.setToolTip("Retry once with older conversation removed and tool results shortened")
        self.retry_context_box.setChecked(session.retry_context_limit)
        self.retry_context_box.toggled.connect(session.set_retry_context_limit)
        top.addWidget(self.retry_context_box)
        self.state_label = QLabel()
        top.addWidget(self.state_label)
        layout.addLayout(top)

        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        layout.addWidget(self.view, 1)

        self.options = QHBoxLayout()   # A question's answers, as buttons
        layout.addLayout(self.options)

        bottom = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask the assistant (e.g. do what I did in w1 on trials 2 to 4)")
        self.input.returnPressed.connect(self._send)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_or_start)
        self.end_btn = QPushButton("End")
        self.end_btn.setToolTip("Drop the stopped request")
        self.end_btn.clicked.connect(session.end)
        for w in (self.input, self.send_btn, self.stop_btn, self.end_btn):
            bottom.addWidget(w, 1 if w is self.input else 0)
        layout.addLayout(bottom)

        # Lives as long as the panel: Qt stops using an event filter once it is deleted
        QApplication.instance().installEventFilter(_ClickAway(self.input, self))

        session.event.connect(self._on_event)
        session.quick_look_ready.connect(self._on_quick_look_ready)
        session.state_changed.connect(self._on_state)
        session.runner.changed.connect(self._on_runner)
        session.view_changed.connect(self._on_view)
        self._models_ready.connect(self._fill_models)
        self._cursor_on = True
        self._blink = QTimer(self)   # The cursor while the assistant starts or thinks
        self._blink.timeout.connect(self._blink_cursor)
        self._blink.start(500)
        self._render()
        self._on_state(session.state)
        threading.Thread(target=self._load_models, daemon=True).start()

    # --- Actions -----------------------------------------------------------------------------------
    def _send(self) -> None:
        text = self.input.text()
        self.input.clear()
        model = self.model_box.currentText().strip()
        if model and self.session.state == "idle" and model != self.session.llm.model:
            self.session.llm.model = model
            self.session.runner.refresh()   # Is the new model downloaded?
        self.session.send(text)
        if self.focus_after_send is not None and self.session.state != "waiting":
            self.focus_after_send.setFocus()   # So Space stops the assistant, as the status bar says

    def _stop_or_start(self) -> None:
        if self.session.state == "stopped":
            self._send()
        else:
            self.session.stop()

    def _answer(self, text: str) -> None:
        self.session.send(text)

    # --- From the session --------------------------------------------------------------------------
    def _on_event(self, kind: str, text: str) -> None:
        if kind == "part":
            self._live += text
        elif kind == "thought_part":
            self._live_thought += text
            if not self.session.show_reasoning:
                return   # Nothing new to show
        else:
            if kind in ("assistant", "tool", "error", "status"):
                self._live = ""
            if kind in ("reasoning", "assistant", "tool", "error", "status"):
                self._live_thought = ""
            if kind == "ask":
                self._show_options(json.loads(text).get("options", []))
            elif kind in ("user", "status", "error"):
                self._show_options([])
        self._render()

    def _on_quick_look_ready(self, call_id: str, data_urls: dict) -> None:
        """Decode Quick Look images once per dock; the transcript stores only its short call id."""
        images = {}
        for name in ("frame", "selection"):
            data_url = data_urls.get(name)
            if not data_url:
                continue
            try:
                encoded = data_url.split(",", 1)[1]
                image = QImage.fromData(base64.b64decode(encoded, validate=True))
            except (IndexError, ValueError):
                continue
            if not image.isNull():
                images[name] = image
        if not images:
            return
        self._quick_look_images[call_id] = images
        self._render()

    def _on_state(self, state: str) -> None:
        self._refresh_label()
        self.stop_btn.setText("Start" if state == "stopped" else "Stop")
        self.stop_btn.setEnabled(state in ("thinking", "acting", "waiting", "stopped"))
        self.end_btn.setVisible(state == "stopped")
        self.send_btn.setEnabled(state in ("idle", "setup", "waiting", "stopped"))
        self.model_box.setEnabled(state == "idle")
        if state == "idle":
            self._live = self._live_thought = ""
            self._show_options([])
        self._render()   # The cursor comes and goes with the state

    def _on_view(self) -> None:
        self.reasoning_box.blockSignals(True)
        self.reasoning_box.setChecked(self.session.show_reasoning)
        self.reasoning_box.blockSignals(False)
        self.retry_context_box.blockSignals(True)
        self.retry_context_box.setChecked(self.session.retry_context_limit)
        self.retry_context_box.blockSignals(False)
        self._render()

    def _on_runner(self, status: str, detail: str) -> None:
        self._refresh_label()

    def _refresh_label(self) -> None:
        runner = self.session.runner
        if self.session.state == "idle":
            self.state_label.setText(RUNNER_TEXT.get(runner.status, runner.status))
            self.state_label.setToolTip(runner.detail)
        else:
            self.state_label.setText(STATES.get(self.session.state, self.session.state))
            self.state_label.setToolTip("")

    def _waiting_for_text(self) -> bool:
        """The assistant is starting or thinking, and no text has come yet."""
        return self.session.state in ("setup", "thinking") and not self._live

    def _blink_cursor(self) -> None:
        if self._waiting_for_text():
            self._cursor_on = not self._cursor_on
            self._render()

    def _show_options(self, options: list) -> None:
        while self.options.count():
            item = self.options.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for option in options:
            button = QPushButton(option)
            button.clicked.connect(lambda _=False, o=option: self._answer(o))
            self.options.addWidget(button)

    def _render(self) -> None:
        # No colours: the text uses the window's own text colour, so it reads in light and dark themes alike
        rows = []
        show_reasoning = self.session.show_reasoning
        for kind, text in self.session.transcript:
            if kind == "reasoning":
                if show_reasoning:
                    rows.append(f'<p style="margin: 2px 0;"><i>{html.escape(text).replace(chr(10), "<br>")}</i></p>')
                continue
            if kind == "ask":
                text = json.loads(text).get("q", "")
            if kind == "quick_look_image":
                images = self._quick_look_images.get(text, {})
                for name, label in (("frame", "Video crop"), ("selection", "Selection shape only")):
                    image = images.get(name)
                    if image is None:
                        continue
                    resource = QUrl(f"quicklook:{text}/{name}")
                    self.view.document().addResource(QTextDocument.ResourceType.ImageResource,
                                                     resource, image)
                    width = min(image.width(), max(120, self.view.viewport().width() - 28))
                    height = max(1, round(image.height() * width / image.width()))
                    background = "background-color:#555;" if name == "selection" else ""
                    rows.append(f'<p style="margin: 4px 0 2px 16px;"><b>{label}</b></p>'
                                f'<p style="margin: 0 0 8px 16px;{background}">'
                                f'<img src="{html.escape(resource.toString(), quote=True)}" '
                                f'width="{width}" height="{height}"></p>')
                continue
            body = html.escape(text).replace("\n", "<br>")
            prefix = {"user": "<b>You:</b> ", "assistant": "", "tool": "▸ ", "result": "&nbsp;&nbsp;",
                      "ask": "<b>?</b> ", "status": "", "error": "<b>!</b> "}.get(kind, "")
            rows.append(f'<p style="margin: 2px 0;">{prefix}{body}</p>')
        if show_reasoning and self._live_thought:
            cursor = "" if self._live else "▍"
            rows.append(f'<p style="margin: 2px 0;"><i>{html.escape(self._live_thought).replace(chr(10), "<br>")}'
                        f'</i>{cursor}</p>')
        if self._live:
            rows.append(f'<p style="margin: 2px 0;">{html.escape(self._live)}▍</p>')
        elif self._waiting_for_text() and not (show_reasoning and self._live_thought):
            # Off, a space keeps the line, so the text does not move up and down each blink
            cursor = "▍" if self._cursor_on else "&nbsp;"
            rows.append(f'<p style="margin: 2px 0;">{cursor}</p>')
        self.view.setHtml("".join(rows))
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    # --- Models ------------------------------------------------------------------------------------
    def _load_models(self) -> None:
        try:
            self._models_ready.emit(self.session.llm.available_models())
        except Exception:   # The runner is not up yet: it starts with the first request
            pass

    def _fill_models(self, models: list) -> None:
        current = self.model_box.currentText()
        self.model_box.blockSignals(True)
        self.model_box.clear()
        self.model_box.addItems(models if current in models else [current] + models)
        self.model_box.setCurrentText(current)
        self.model_box.blockSignals(False)
