"""
The local bridge: the app's agent tools over HTTP on 127.0.0.1, for the MCP shim (mcp_server.py),
the command line (ptx.py) and, later, the in-app chat (docs/AGENT_PLAN.md, part 5).

    POST /call  {"tool": name, "args": {...}}  ->  {"ok": result} | {"error": "..."} | {"stopped": "..."}
    GET  /tools                                ->  {name: [description, params, flags]}

Threads: the HTTP server answers on its own threads; every tool runs on the Qt thread (sent there
by a queued signal), so tools touch widgets safely, and the window stays live while a tool waits.
A tool's Wait is checked every 0.1 s and its Work runs on the caller's thread (tools.py).

The lifetime of a call, kept short so a small model cannot get it wrong: one request, one answer,
however long the work. No sessions, no handles, no polling. Space in any window stops the agent
(windows.AgentGate): calls are refused with "stopped" until it calls `resume`.

QUICK-AND-DIRTY (see docs/AGENT_PLAN.md, "Architecture notes"): no authentication (localhost
only), the port is written to cache/bridge.port for the command line to find, and waits poll.
"""

import json
import logging
import os
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QCoreApplication, QObject, Qt, QThread, Signal

from .. import paths, windows
from . import tools
from .specs import ALLOWED_WHEN_STOPPED, SPECS

log = logging.getLogger(__name__)
DEFAULT_PORT = 8765
PORT_FILE = os.path.join(paths.cache_dir(), "bridge.port")   # Read by mcp_server.py
GUI_TIMEOUT = 180.0     # s: one step on the Qt thread (a modal dialog would hold it up)
STOPPED = ("The user pressed Space to stop you. Do nothing more until they tell you to go on; "
           "then call resume (it lists what they changed).")


class Stopped(Exception):
    """The user pressed Space: the agent's call ends here."""


class _Invoker(QObject):
    """Runs functions on the Qt thread for the bridge's threads."""
    request = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.request.connect(self._run, Qt.ConnectionType.QueuedConnection)

    def _run(self, job) -> None:
        fn, box, done = job
        try:
            box["value"] = fn()
        except BaseException as e:   # Carried back to the caller's thread
            box["error"] = e
        finally:
            done.set()


_invoker: _Invoker | None = None
_server: ThreadingHTTPServer | None = None
port: int | None = None


def on_gui(fn, timeout: float = GUI_TIMEOUT):
    """fn() on the Qt thread; its result (or exception) back on this one."""
    app = QCoreApplication.instance()
    if _invoker is None or app is None or QThread.currentThread() == app.thread():
        return fn()
    box, done = {}, threading.Event()
    _invoker.request.emit((fn, box, done))
    if not done.wait(timeout):
        raise tools.ToolError("the app did not answer in time (is a dialog open in it?)")
    if "error" in box:
        raise box["error"]
    return box["value"]


def invoke(name: str, args: dict | None = None):
    """Runs tool `name` to the end, on any thread but the Qt one. Returns its result; raises
    tools.ToolError (with what to do instead) or Stopped (the user pressed Space)."""
    if name not in SPECS:
        raise tools.ToolError(f"no tool {name!r}; tools: {', '.join(SPECS)}")
    if windows.AGENT.stopped and name not in ALLOWED_WHEN_STOPPED:
        raise Stopped()
    on_gui(windows.AGENT.begin)
    touched: list = []   # The windows this call marks as the agent's (tools.run), unmarked at the end
    try:
        if "m" in SPECS[name][2]:
            return tools.MACROS[name](invoke, **tools.checked(name, args or {}))
        result = on_gui(lambda: tools.run(name, args or {}, touched))
        while isinstance(result, (tools.Wait, tools.Work)):
            step = result
            if isinstance(step, tools.Work):
                value = step.job()
                if windows.AGENT.stopped:   # Stopped during the work: its result is not applied
                    raise Stopped()
                result = on_gui(lambda: step.then(value))
                continue
            deadline = time.time() + step.timeout
            while not on_gui(step.until):
                if windows.AGENT.stopped:
                    raise Stopped()
                if time.time() > deadline:
                    raise tools.ToolError(f"{name} did not finish in {step.timeout:.0f} s")
                time.sleep(0.1)
            # Space ends a track at once, so the wait can end before the stop is seen: a stop is
            # always reported as one, never as a result that merely ended early
            if windows.AGENT.stopped:
                raise Stopped()
            result = on_gui(step.then)
        return result
    finally:
        on_gui(lambda: tools.finish(touched))
        on_gui(windows.AGENT.end)


def call(name: str, args: dict | None = None) -> dict:
    """A tool call as the agent sees it: {"ok": result}, {"error": what to do}, or {"stopped"}."""
    try:
        return {"ok": invoke(name, args)}
    except Stopped:
        return {"stopped": STOPPED}
    except tools.ToolError as e:
        return {"error": str(e)}
    except Exception as e:   # A bug: the agent gets one line, the log the whole story
        log.error("tool %s failed:\n%s", name, traceback.format_exc())
        return {"error": f"{name} failed: {type(e).__name__}: {e}"}


def user_act(body: dict) -> dict:
    """TEST HARNESS ONLY (POST /user): acts as the user, so a script can play the person while an
    agent works: {"key": "space"} presses Space in the active window; {"tool", "args"} runs a tool
    as the user's own change (past the gate, logged as "u"). Not in the tool list."""
    if body.get("key") == "space":
        def press():
            win = windows.get() or next(iter(windows.all_windows().values()))
            win._space()
            return {"stopped": windows.AGENT.stopped}
        return {"ok": on_gui(press)}

    def run_as_user():
        everyone = list(windows.all_windows().values())
        for w in everyone:   # What is pending is committed as whoever did it
            w.history.flush()
            w.history.forced_who = "user"
        tools.as_user = True
        try:
            return tools.run(body["tool"], body.get("args") or {})
        finally:
            tools.as_user = False
            for w in windows.all_windows().values():   # An agent's call under way keeps its own
                w.history.flush()
                w.history.forced_who = None
    try:
        result = on_gui(run_as_user)
        return {"ok": result if not isinstance(result, (tools.Wait, tools.Work)) else "started"}
    except tools.ToolError as e:
        return {"error": str(e)}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/tools":
            self._send({name: list(spec) for name, spec in SPECS.items()})
        else:
            self._send({"error": "GET /tools, or POST /call"}, 404)

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        if path not in ("/call", "/user"):
            self._send({"error": "POST /call"}, 404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if path == "/user":
                self._send(user_act(body))
                return
            name, args = body["tool"], body.get("args") or {}
        except (ValueError, KeyError, TypeError):
            self._send({"error": 'send {"tool": name, "args": {...}}'}, 400)
            return
        self._send(call(name, args))

    def _send(self, obj, status: int = 200) -> None:
        data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:   # Quiet
        pass


def ensure_invoker() -> None:
    """Lets other threads run tools (call on the Qt thread): the HTTP server and the in-app
    assistant both need it, and the assistant works with the server off."""
    global _invoker
    if _invoker is None:
        _invoker = _Invoker()


def start(first_port: int | None = None) -> int:
    """Starts the bridge (call on the Qt thread, once the app exists). Returns its port: the first
    free one from PHYSTRACK_BRIDGE_PORT (default 8765)."""
    global _server, port
    if _server is not None:
        return port
    ensure_invoker()
    first = int(first_port or os.environ.get("PHYSTRACK_BRIDGE_PORT") or DEFAULT_PORT)
    for p in range(first, first + 20):
        try:
            _server = ThreadingHTTPServer(("127.0.0.1", p), _Handler)
            break
        except OSError:
            continue
    else:
        raise OSError(f"no free port from {first}")
    _server.daemon_threads = True
    port = _server.server_address[1]
    threading.Thread(target=_server.serve_forever, name="agent bridge", daemon=True).start()
    try:
        os.makedirs(os.path.dirname(PORT_FILE), exist_ok=True)
        with open(PORT_FILE, "w") as f:
            f.write(str(port))
    except OSError:
        pass
    log.info("agent bridge on http://127.0.0.1:%d", port)
    return port
