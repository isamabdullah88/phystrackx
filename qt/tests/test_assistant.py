"""
The in-app assistant (agent/session.py, agent/chat_panel.py), with a scripted model instead of a
real one: a request runs tools and ends with an answer; a question waits for the user's answer;
Space stops it while it thinks, and Start tells the model what the user changed meanwhile.

    ~/.venvs/phystrackx-qt/bin/python tests/test_assistant.py      (PHYSTRACK_QT_SHOW=1 to watch)
"""

import base64
import json
import time

import cv2
import numpy as np

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from phystrack_qt import windows  # noqa: E402
from phystrack_qt.agent.chat_panel import ChatPanel  # noqa: E402
from phystrack_qt.agent.llm import Cancelled, LLMError, _ThinkTags  # noqa: E402
from phystrack_qt.agent.session import AgentSession, is_context_limit_error  # noqa: E402
from test_tracking import make_clip  # noqa: E402


class ScriptedModel:
    """Plays the model: each turn is a dict {"think": reasoning, "say": text, "calls": [(tool, args)]}, or a function
    (messages, on_text, cancelled) -> reply (to look at what it was sent, or to be slow)."""

    def __init__(self, turns: list) -> None:
        self.turns, self.sent, self.sent_tools, self.max_tokens = list(turns), [], [], []
        self.url, self.model, self.is_ollama = "scripted", "scripted", False

    def models(self) -> list:
        return ["scripted"]

    def chat(self, messages, tools, on_text=None, cancelled=None, max_tokens=400, on_reasoning=None) -> dict:
        self.sent.append(messages)
        self.sent_tools.append(tools)
        self.max_tokens.append(max_tokens)
        turn = self.turns.pop(0)
        if callable(turn):
            return turn(messages, on_text, cancelled)
        if turn.get("think") and on_reasoning:
            on_reasoning(turn["think"])
        if turn.get("say") and on_text:
            on_text(turn["say"])
        return {"content": turn.get("say", ""), "reasoning": turn.get("think", ""), "tool_calls": [
            {"id": f"c{len(self.sent)}{i}", "name": name, "arguments": args}
            for i, (name, args) in enumerate(turn.get("calls", []))]}


def run_until(session, states, timeout=30.0) -> bool:
    return h.pump(lambda: session.state in states, timeout)


def test_assistant() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)

    # A request: a tool call, then the answer
    model = ScriptedModel([{"calls": [("windows", {})]}, {"say": f"One window is open: {w.wid}."}])
    session = AgentSession(llm=model)
    panel = ChatPanel(session)
    session.send("Which windows are open?")
    h.check("a request ends", h.pump(lambda: session.state == "idle" and len(model.sent) == 2, 30))
    tool_result = model.sent[1][-1]
    h.check("the model gets the tool's result", tool_result["role"] == "tool" and w.wid in tool_result["content"],
            str(tool_result)[:200])
    h.check("the system prompt and the tool list are sent each turn",
            model.sent[0][0]["role"] == "system" and model.sent[1][0] == model.sent[0][0])
    text = panel.view.toPlainText()
    h.check("the dock shows the request, the tool call and the answer",
            "Which windows" in text and "windows()" in text and f"One window is open: {w.wid}" in text, text[-300:])

    def inspect_frame(messages, on_text, cancelled):
        frame_message = next((m for m in messages if m["role"] == "user" and
                              isinstance(m["content"], list)), None)
        inspect_frame.message = frame_message
        return {"content": "I can inspect this frame.", "tool_calls": []}

    model.turns = [{"calls": [("get_video_frame", {"frame": 0, "region": [10, 12, 32, 24]})]},
                   inspect_frame]
    session.send("Look at a crop of frame zero")
    h.check("the frame tool turn ends", h.pump(lambda: session.state == "idle" and not model.turns, 30))
    image_message = getattr(inspect_frame, "message", None)
    h.check("the assistant receives the returned frame as image content",
            image_message is not None and image_message["content"][1]["type"] == "image_url" and
            image_message["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,"),
            str(image_message)[:200])
    frame_tool_result = next(m for m in reversed(session.messages) if m["role"] == "tool" and
                             '"width":32' in m["content"])
    h.check("the tool reply carries crop dimensions without duplicating image bytes",
            "base64" not in frame_tool_result["content"], frame_tool_result["content"][:200])
    h.check("frame image context is discarded after the assistant answers",
            not any(m.get("_frame_image") for m in session.messages))

    ok, preview = cv2.imencode(".jpg", np.zeros((12, 18, 3), dtype=np.uint8))
    h.check("test Quick Look image encodes", ok)
    preview_id = "quick-look-preview-test"
    session.quick_look_ready.emit(preview_id, {"frame": "data:image/jpeg;base64," +
                                               base64.b64encode(preview).decode("ascii")})
    session._emit("quick_look_image", preview_id)
    result_text = "".join(text for kind, text in session.transcript if kind == "result")
    h.check("Quick Look renders inline in chat while the turn is active",
            "<img" in panel.view.toHtml() and f"quicklook:{preview_id}/frame" in panel.view.toHtml() and
            preview_id not in result_text,
            panel.view.toHtml()[-500:])

    prior_messages, prior_start = session.messages, session._request_start
    session.messages = [
        {"role": "user", "content": "Inspect and track the ball"},
        {"role": "user", "_frame_image": True, "content": [
            {"type": "text", "text": "Quick Look selection"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AA=="}},
        ]},
        {"role": "tool", "tool_call_id": "old-tool", "content": "large result"},
    ]
    session._request_start = 0
    first_compact = session._context(compact=True, compact_level=1)
    smaller_compact = session._context(compact=True, compact_level=2)
    h.check("progressive compacting drops prior image payloads",
            any(part.get("type") == "image_url" for part in first_compact[1]["content"]) and
            not any(part.get("type") == "image_url" for part in smaller_compact[1]["content"]))
    session.messages, session._request_start = prior_messages, prior_start

    def context_retry(messages, on_text, cancelled):
        context_retry.messages = messages
        return {"content": "The original request is complete.", "reasoning": "", "tool_calls": [
            {"id": "end-reprompts", "name": "end_reprompts", "arguments": {}}]}

    original_chat = model.chat
    attempts = []

    def reject_once(messages, tools, **kwargs):
        attempts.append((messages, tools))
        if len(attempts) < 3:
            raise LLMError("400: prompt tokens exceed the model context length")
        return original_chat(messages, tools, **kwargs)

    model.chat = reject_once
    model.turns = [context_retry]
    # Two context failures should compact progressively, then end only when the model calls the tool.
    session.send("Trigger the context retry")
    retried = h.pump(lambda: session.state == "idle" and not model.turns, 30)
    model.chat = original_chat
    h.check("the retry re-prompts with a compact current request",
            retried and len(attempts) == 3 and len(context_retry.messages) == 2 and
            "Trigger the context retry" in context_retry.messages[1]["content"][0]["text"],
            str(getattr(context_retry, "messages", None)))
    h.check("end_reprompts remains available through repeated overflow retries",
            all(any(tool["function"]["name"] == "end_reprompts" for tool in tools)
                for _, tools in attempts[1:]))
    h.check("end_reprompts terminates without another model turn",
            retried and model.sent[-1] is context_retry.messages and
            any(m.get("tool_call_id") == "end-reprompts" and m["content"] == "{\"ended\":true}"
            for m in session.messages[-3:]) and
            any(kind == "status" and "re-prompting ended" in text.lower() for kind, text in session.transcript[-8:]))
    h.check("the context retry is reported in chat status",
            any(kind == "status" and "retrying" in text for kind, text in session.transcript[-8:]))
    h.check("common context overflow messages are recognized",
            is_context_limit_error(LLMError("maximum input length exceeded")) and
            not is_context_limit_error(LLMError("connection refused")))

    # A question: the session waits for the answer, which goes back to the model
    def check_answer(messages, on_text, cancelled):
        answer = json.loads(messages[-1]["content"])
        return {"content": f"You said {answer.get('answer')}.", "tool_calls": []}
    model.turns = [{"calls": [("ask_user", {"question": "Which object?", "options": ["1", "2"]})]}, check_answer]
    session.send("Track the ball")
    h.check("a question waits for the user", run_until(session, ("waiting",)))
    h.check("the question's answers are buttons", panel.options.count() == 2)
    panel.options.itemAt(1).widget().click()
    h.check("the answer goes back to the model", h.pump(lambda: session.state == "idle", 30) and
            session.transcript[-1] == ("assistant", "You said 2."), str(session.transcript[-2:]))

    # Space while it thinks: the reply is cut off; the user changes the trim; Start goes on,
    # and the model is told about the change and the note
    def slow(messages, on_text, cancelled):
        while not cancelled():
            time.sleep(0.02)
        raise Cancelled()

    def told(messages, on_text, cancelled):
        told.message = messages[-1]["content"]
        return {"content": "Going on with your trim.", "tool_calls": []}
    model.turns = [slow, told]
    session.send("Do something slow")
    h.check("it is thinking", run_until(session, ("thinking",)))
    h.pump(lambda: windows.AGENT.session_busy, 5)
    w.activateWindow()
    h.pump(timeout=0.2)
    w._space()
    h.check("Space stops it while it thinks", run_until(session, ("stopped",)))
    h.check("while stopped, Start is offered", panel.stop_btn.text() == "Start")
    w._trim_marks = [3, 60]
    w._apply_trim()
    h.pump(timeout=0.5)
    panel.input.setText("I fixed the trim")
    panel.stop_btn.click()   # Start, with the note
    h.check("Start goes on to the end", h.pump(lambda: session.state == "idle", 30))
    message = getattr(told, "message", "")
    h.check("the model is told what the user changed, and their note",
            "trim" in message and "I fixed the trim" in message, message[:300])
    h.check("the gate is free again", not windows.AGENT.stopped and not windows.AGENT.session_busy)

    # A tool error goes back to the model as an error, and an unknown tool is refused
    model.turns = [{"calls": [("trim", {"start": 1})]}, {"calls": [("plots", {"kinds": ["nope"]})]},
                   {"say": "Done."}]
    session.send("Break things")
    h.pump(lambda: session.state == "idle" and not model.turns, 30)
    results = [m["content"] for m in session.messages if m["role"] == "tool"][-2:]
    h.check("errors and unknown tools are reported to the model, not raised",
            "no tool" in results[0] and "unknown kinds" in results[1], str(results))

    # Reasoning: hidden until the checkbox is on, and never sent back to the model
    model.turns = [{"think": "The user wants the windows listed.", "calls": [("windows", {})]}, {"say": "Listed."}]
    session.send("List them")
    h.check("a reasoning request ends", h.pump(lambda: session.state == "idle" and not model.turns, 30))
    h.check("reasoning goes to the transcript",
            ("reasoning", "The user wants the windows listed.") in session.transcript, str(session.transcript[-4:]))
    h.check("reasoning is hidden by default", "wants the windows" not in panel.view.toPlainText())
    other = ChatPanel(session)   # Another window's dock
    panel.reasoning_box.setChecked(True)
    h.check("the checkbox shows the reasoning, in every dock",
            "wants the windows" in panel.view.toPlainText() and other.reasoning_box.isChecked()
            and "wants the windows" in other.view.toPlainText())
    h.check("reasoning is not sent back to the model",
            all("wants the windows" not in json.dumps(m) for m in model.sent[-1]))
    panel.reasoning_box.setChecked(False)
    h.check("unchecked, it is hidden again", "wants the windows" not in other.view.toPlainText())
    other.deleteLater()   # On the Qt thread: a panel freed by Python's collector elsewhere warns about its timer
    h.pump(timeout=0.1)

    # The chat shows a tool's result whole (the model still gets it cut)
    from phystrack_qt.agent.session import _summary
    long_error = "x" * 500 + "END"
    h.check("an error is shown whole", _summary("plots", {"error": long_error}).endswith("END"))
    h.check("a result is shown whole", _summary("data", {"ok": {"rows": "y" * 500 + "END"}}).endswith('END"}'))
    h.check("a recipe's check is shown whole",
            _summary("run_recipe", {"ok": {"done": [], "check": [3, "fit", "z" * 300 + "END"]}}).endswith("END"))

    # <think> tags in the text are split out as reasoning, also when a tag is cut between pieces
    tags = _ThinkTags()
    pieces = [p for chunk in ["<th", "ink>plan it</thi", "nk>Hello <b", ">x"] for p in tags.feed(chunk)] + tags.flush()
    h.check("think tags split into reasoning and reply",
            "".join(t for r, t in pieces if r) == "plan it" and "".join(t for r, t in pieces if not r) == "Hello <b>x",
            str(pieces))

    # A click anywhere else takes the text box's selection away (not only a click on the video)
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    panel.input.setText("a draft")
    panel.input.selectAll()
    h.check("the text box has a selection to clear", panel.input.hasSelectedText())
    press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(2, 2), QPointF(2, 2), Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(panel.send_btn, press)
    h.check("a click on a button elsewhere clears the selection", not panel.input.hasSelectedText())
    panel.input.selectAll()
    QApplication.sendEvent(panel.view.viewport(), press)
    h.check("a click on the history clears the selection too", not panel.input.hasSelectedText())
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    test_assistant()
    h.finish()
