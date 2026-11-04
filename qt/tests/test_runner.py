"""
The model runner (agent/runner.py): what its status says, the server the app starts and stops, the
model download, and the user's yes before an install. No real Ollama or model is needed: a fake
`ollama` script serves /v1/models, and its "pull" makes the model appear.

The fake runner's URL is on a free port, with is_ollama forced on (real Ollama is on 11434): the
code path is the same. The fake-program tests run on macOS and Linux only (a shebang script).

    ~/.venvs/phystrackx-dev/bin/python tests/test_runner.py
"""

import faulthandler
import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

faulthandler.enable()   # A native crash prints the Python stack where it happened, not a silent exit

from phystrack_qt.agent import runner as runner_mod  # noqa: E402
from phystrack_qt.agent.chat_panel import ChatPanel  # noqa: E402
from phystrack_qt.agent.llm import LLM  # noqa: E402
from phystrack_qt.agent.session import AgentSession  # noqa: E402

MODEL = "qwen3:4b-instruct"

FAKE_OLLAMA = '''#!PYTHON
import http.server, json, os, sys
MARKER = os.environ["FAKE_OLLAMA_MARKER"]   # "pull" creates it; the server lists the model once it exists
if sys.argv[1] == "pull":
    print("pulling manifest", flush=True)
    print("pulling 100%", flush=True)
    open(MARKER, "w").close()
    sys.exit(0)
host, port = os.environ["OLLAMA_HOST"].split(":")

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        models = ["MODEL"] if os.path.exists(MARKER) else []
        body = json.dumps({"data": [{"id": m} for m in models]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

http.server.ThreadingHTTPServer((host, int(port)), Handler).serve_forever()
'''


class OllamaLike(LLM):
    """An LLM whose URL the app treats as Ollama's."""

    @property
    def is_ollama(self) -> bool:
        return True


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(port: int, models: list) -> http.server.ThreadingHTTPServer:
    """A /v1/models endpoint on 127.0.0.1:port, in a thread: something the app did not start."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"data": [{"id": m} for m in models]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd



# Every session and panel a test makes stays referenced to the end: dropped, they are garbage in
# reference cycles, and Python's cycle collector can run on any thread (here the runner's status
# poller), which would destroy Qt objects off the Qt thread and crash
KEEP: list = []


def settle(session) -> None:
    """Waits for the request to end, and keeps the session alive (see KEEP)."""
    KEEP.append(session)
    h.pump(lambda: session.state == "idle", 30)

def test_status_is_what_the_endpoint_says() -> None:
    # Nothing answers at a custom URL: down, not ready, and quickly (no wait for a server)
    url = f"http://127.0.0.1:{free_port()}/v1"
    r = runner_mod.Runner(LLM(url=url, model=MODEL))
    t0 = time.monotonic()
    h.check("nothing answering is not ready", r.ensure() is False and r.status == "down", f"{r.status}: {r.detail}")
    h.check("a custom runner is not started by the app, and the message says so",
            url in r.detail and "PHYSTRACK_LLM_URL" in r.detail and time.monotonic() - t0 < 5, r.detail)

    # An answering runner that is not Ollama: ready as soon as it answers
    httpd = serve(free_port(), ["any-model"])
    port = httpd.server_address[1]
    r = runner_mod.Runner(LLM(url=f"http://127.0.0.1:{port}/v1", model=MODEL))
    h.check("a custom runner that answers is ready", r.ensure() is True and r.status == "ready", r.detail)
    httpd.shutdown()

    # Ollama answering without the model: no_model, not ready
    httpd = serve(free_port(), ["other:latest"])
    port = httpd.server_address[1]
    r = runner_mod.Runner(OllamaLike(url=f"http://127.0.0.1:{port}/v1", model=MODEL))
    original = runner_mod.find_ollama
    runner_mod.find_ollama = lambda: None   # Ollama is not needed to say the model is missing
    try:
        h.check("Ollama without the model is not ready: no_model", r.ensure() is False and r.status == "no_model",
                f"{r.status}: {r.detail}")
    finally:
        runner_mod.find_ollama = original
    httpd.shutdown()

    # The dock's label follows the status: it says ready only when the runner answers
    original = runner_mod.find_ollama
    runner_mod.find_ollama = lambda: None   # Not the Ollama on this Mac: no server is started here
    try:
        session = AgentSession(llm=OllamaLike(url=f"http://127.0.0.1:{free_port()}/v1", model=MODEL))
        panel = ChatPanel(session)
        KEEP.extend((session, panel))
        session.runner.check()
        h.check("the dock says so when Ollama is missing, and does not say ready",
                panel.state_label.text() == "Ollama not installed", panel.state_label.text())
    finally:
        runner_mod.find_ollama = original


def test_find_ollama() -> None:
    folder = tempfile.mkdtemp(prefix="runner_find_")
    fake = os.path.join(folder, runner_mod.BINARY)
    open(fake, "w").close()
    original_fixed, original_path = runner_mod.fixed_paths, os.environ.get("PATH")
    try:
        runner_mod.fixed_paths = lambda: [fake]
        os.environ["PATH"] = ""   # A Finder launch: the PATH has no Homebrew folder in it
        h.check("a program in a fixed place is found when the PATH does not have it",
                runner_mod.find_ollama() == fake, str(runner_mod.find_ollama()))
        runner_mod.fixed_paths = lambda: []
        h.check("none installed: nothing is found", runner_mod.find_ollama() is None)
    finally:
        runner_mod.fixed_paths = original_fixed
        os.environ["PATH"] = original_path


def test_the_server_the_app_starts() -> None:
    if os.name == "nt":
        print("  (skipped: the fake Ollama is a shell script)")
        return
    folder = tempfile.mkdtemp(prefix="runner_fake_")
    binary = os.path.join(folder, "ollama")
    with open(binary, "w") as f:
        f.write(FAKE_OLLAMA.replace("PYTHON", sys.executable).replace("MODEL", MODEL))
    os.chmod(binary, 0o755)
    os.environ["FAKE_OLLAMA_MARKER"] = os.path.join(folder, "pulled")
    original = runner_mod.find_ollama
    runner_mod.find_ollama = lambda: binary
    try:
        port = free_port()
        llm = OllamaLike(url=f"http://127.0.0.1:{port}/v1", model=MODEL)
        r = runner_mod.Runner(llm)
        h.check("starting the server: it answers, but the model is not downloaded yet",
                r.ensure() is False and r.status == "no_model", f"{r.status}: {r.detail}")
        proc = r._server
        h.check("the app owns the server it started", proc is not None and proc.poll() is None)

        h.check("the model download works, and then the runner is ready",
                r.pull() is True and r.status == "ready" and r.ensure() is True, f"{r.status}: {r.detail}")

        r.stop()
        h.check("quitting stops the server the app started", proc.poll() is not None)
        h.check("the stopped runner is down, not ready", not r._answers() and r._probe()[0] == "down")
    finally:
        runner_mod.find_ollama = original


def test_a_server_the_app_did_not_start_is_left_alone() -> None:
    port = free_port()
    httpd = serve(port, [MODEL])
    r = runner_mod.Runner(OllamaLike(url=f"http://127.0.0.1:{port}/v1", model=MODEL))
    h.check("an Ollama that is already answering is ready, and the app does not own it",
            r.ensure() is True and r._server is None, f"{r.status}: {r.detail}")
    r.stop()
    h.check("quitting leaves that server running", r._answers() is True)
    httpd.shutdown()


def test_the_user_says_yes_before_an_install() -> None:
    if runner_mod.ARCHIVES.get(sys.platform) is None:
        print("  (skipped: this platform's install is the command, not a download)")
        return
    original = runner_mod.find_ollama
    runner_mod.find_ollama = lambda: None
    try:
        session = AgentSession(llm=OllamaLike(url=f"http://127.0.0.1:{free_port()}/v1", model=MODEL))
        installs = []

        def declined_install() -> bool:
            installs.append(1)
            session.runner._set("failed", "installing Ollama failed: test")
            return False
        session.runner.install = declined_install

        session.send("What is the period?")
        h.check("before anything is installed, the dock asks", h.pump(lambda: session.state == "waiting", 30))
        h.check("the question offers y and n", session.transcript[-1][0] == "ask" and "y or n" in session.transcript[-1][1])
        session.send("n")
        settle(session)
        h.check("n: nothing is installed, and the request says why",
                installs == [] and "cannot answer without it" in session.transcript[-1][1], str(session.transcript[-1]))

        session.send("What is the period?")
        h.pump(lambda: session.state == "waiting", 30)
        session.send("y")
        settle(session)
        h.check("y: the install runs, and its failure is reported",
                installs == [1] and session.transcript[-1] == ("error", "installing Ollama failed: test"),
                str(session.transcript[-2:]))
    finally:
        runner_mod.find_ollama = original


def test_linux_shows_the_command_instead() -> None:
    original, original_archives = runner_mod.find_ollama, runner_mod.ARCHIVES
    runner_mod.find_ollama = lambda: None
    runner_mod.ARCHIVES = {}   # As on Linux: the install is a command the user runs, not a download
    try:
        session = AgentSession(llm=OllamaLike(url=f"http://127.0.0.1:{free_port()}/v1", model=MODEL))
        session.send("What is the period?")
        settle(session)
        h.check("on Linux nothing is asked, and the error carries the install command",
                session.transcript[-1] == ("error", f"install Ollama in a terminal, then ask again: {runner_mod.LINUX_INSTALL}"),
                str(session.transcript[-1:]))
    finally:
        runner_mod.find_ollama, runner_mod.ARCHIVES = original, original_archives


if __name__ == "__main__":
    h.app()
    test_status_is_what_the_endpoint_says()
    test_find_ollama()
    test_the_server_the_app_starts()
    test_a_server_the_app_did_not_start_is_left_alone()
    test_the_user_says_yes_before_an_install()
    test_linux_shows_the_command_instead()
    h.finish()
