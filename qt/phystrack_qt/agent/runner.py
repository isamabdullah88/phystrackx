"""
The model runner the assistant talks to (llm.py), and the app's hold on it.

- Ollama (the default, and any URL with port 11434): the app finds it, or installs it into its own
  folder when the user says yes. It starts `ollama serve` when the runner does not answer, and stops
  that server when the app quits. A server the app did not start (Ollama's own app, `brew services`)
  is left alone. The assistant's model is downloaded the same way, on the user's yes.
- Any other runner (PHYSTRACK_LLM_URL: Strata, llama-server...): the app only checks it.

The status says what the endpoint answers now. It is checked every POLL_SECONDS and before each
request, so "ready" means the runner answered a request, and "ready" for Ollama also means the
model is there. The statuses:
  checking | starting | ready | no_model (Ollama answers, the model is not downloaded)
  | not_installed | installing | downloading | down (nothing answers) | failed (the last attempt)
"""

import http.client
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile

from PySide6.QtCore import QObject, Signal

from .. import paths
from .llm import LLM

WINDOWS = os.name == "nt"
BINARY = "ollama.exe" if WINDOWS else "ollama"
POLL_SECONDS = 5.0
START_SECONDS = 30.0
# The official CLI archives (ollama.com/download): macOS and Windows, the app downloads and unpacks
# one into its own folder. Linux's installer needs root, so the app shows its command instead.
ARCHIVES = {
    "darwin": ("https://ollama.com/download/ollama-darwin.tgz", "about 180 MB"),
    "win32": ("https://ollama.com/download/ollama-windows-amd64.zip", "about 1.6 GB"),
}
LINUX_INSTALL = "curl -fsSL https://ollama.com/install.sh | sh"


def fixed_paths() -> list[str]:
    """Where Ollama's installers and Homebrew put it. A Finder or Dock launch has a short PATH,
    so these are looked at too."""
    if WINDOWS:
        return [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", BINARY)]
    return ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama",
            "/Applications/Ollama.app/Contents/Resources/ollama"]


def managed_binary() -> str | None:
    """Ollama as the app installed it (in paths.runner_dir())."""
    for folder, _, files in os.walk(paths.runner_dir()):
        if BINARY in files:
            return os.path.join(folder, BINARY)
    return None


def find_ollama() -> str | None:
    """The Ollama program: on the PATH, in a fixed place, or the app's own copy. None if not installed."""
    found = shutil.which(BINARY)
    if found:
        return found
    for path in fixed_paths():
        if os.path.isfile(path):
            return path
    return managed_binary()


def _spawn_flags() -> dict:
    """A server or download runs apart from the terminal (POSIX), or with no console window (Windows)."""
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if WINDOWS else {"start_new_session": True}


class Runner(QObject):
    changed = Signal(str, str)   # (status, detail), when either changes

    def __init__(self, llm: LLM) -> None:
        super().__init__()
        self.llm = llm
        self.status, self.detail = "checking", ""
        self._lock = threading.Lock()    # One start, install or download at a time
        self._server = None              # The server this app started
        self._download = None            # `ollama pull`, while it runs
        self._closing = False
        self._watching = False

    # --- Status ------------------------------------------------------------------------------------
    def start(self) -> None:
        """Checks the endpoint every POLL_SECONDS, so the status stays true."""
        if not self._watching:
            self._watching = True
            threading.Thread(target=self._watch, name="runner-watch", daemon=True).start()

    def refresh(self) -> None:
        """Checks now (in the background), e.g. after the model is changed."""
        threading.Thread(target=self.check, name="runner-check", daemon=True).start()

    def check(self) -> None:
        if self._lock.acquire(blocking=False):   # A start or install in progress sets the status itself
            try:
                self._set(*self._probe())
            finally:
                self._lock.release()

    def _watch(self) -> None:
        while True:
            time.sleep(POLL_SECONDS)
            self.check()

    def _probe(self) -> tuple[str, str]:
        """What the endpoint says now, as (status, detail). Changes nothing."""
        url, model = self.llm.url, self.llm.model
        try:
            models = self.llm.models()
        except (OSError, ValueError, http.client.HTTPException):
            if not self.llm.is_ollama:
                return "down", (f"no model runner answers at {url}: start it, or set PHYSTRACK_LLM_URL "
                                "to another (Strata, llama-server...)")
            if find_ollama() is None:
                return "not_installed", "Ollama is not installed"
            return "down", "Ollama is installed but not running"
        if self.llm.is_ollama and model not in models:
            return "no_model", f"{model} is not downloaded"
        return "ready", f"{model} at {url}"

    def _set(self, status: str, detail: str = "") -> None:
        if (status, detail) != (self.status, self.detail):
            self.status, self.detail = status, detail
            self.changed.emit(status, detail)

    def _answers(self) -> bool:
        try:
            self.llm.models()
            return True
        except (OSError, ValueError, http.client.HTTPException):
            return False

    def _host(self) -> str:
        return urllib.parse.urlsplit(self.llm.url).netloc or "127.0.0.1:11434"

    # --- Starting, installing, downloading (called from the assistant's worker thread) -------------
    def ensure(self) -> bool:
        """Makes the runner answer, starting Ollama if it is installed and not running. True when it
        is ready. Installs and downloads nothing: those need the user's yes (the session asks)."""
        with self._lock:
            status, detail = self._probe()
            binary = find_ollama() if status == "down" and self.llm.is_ollama else None
            if binary is not None:
                if not self._start_server(binary):
                    return False
                status, detail = self._probe()
            self._set(status, detail)
            return status == "ready"

    def _start_server(self, binary: str) -> bool:
        """Starts `ollama serve` and waits until it answers. The status is starting, or failed."""
        if self._closing:
            return False
        folder = paths.runner_dir()
        os.makedirs(folder, exist_ok=True)
        log_path = os.path.join(folder, "ollama.log")
        self._set("starting", f"starting Ollama ({binary})")
        env = {**os.environ, "OLLAMA_HOST": self._host(), "OLLAMA_KEEP_ALIVE": "30m"}
        with open(log_path, "ab") as log:
            self._server = subprocess.Popen([binary, "serve"], stdout=log, stderr=subprocess.STDOUT,
                                            env=env, **_spawn_flags())
        deadline = time.monotonic() + START_SECONDS
        while time.monotonic() < deadline and not self._closing:
            if self._server.poll() is not None:
                self._set("failed", f"Ollama stopped at once (exit code {self._server.returncode}); "
                                    f"its log: {log_path}")
                return False
            if self._answers():
                return True
            time.sleep(0.25)
        self._set("failed", f"Ollama did not answer within {START_SECONDS:.0f} s; its log: {log_path}")
        return False

    def install_prompt(self) -> str | None:
        """The question before an install, or None where the app cannot install it (Linux)."""
        if sys.platform not in ARCHIVES:
            return None
        _, size = ARCHIVES[sys.platform]
        return (f"Ollama, the model runner the assistant uses, is not installed. Download it ({size}) "
                "into PhysTrackX's own folder? Type y or n.")

    def install(self) -> bool:
        """Downloads Ollama into the app's own folder and unpacks it. After the user said yes."""
        with self._lock:
            if sys.platform not in ARCHIVES:
                self._set("not_installed", f"install Ollama in a terminal, then ask again: {LINUX_INSTALL}")
                return False
            url, size = ARCHIVES[sys.platform]
            folder = paths.runner_dir()
            os.makedirs(folder, exist_ok=True)
            archive = os.path.join(folder, os.path.basename(url))
            try:
                self._set("installing", f"downloading Ollama ({size})")
                with urllib.request.urlopen(url, timeout=60) as response, open(archive, "wb") as out:
                    total = int(response.headers.get("Content-Length") or 0)
                    done, shown = 0, -1
                    while chunk := response.read(1 << 16):
                        out.write(chunk)
                        done += len(chunk)
                        if total and done * 100 // total != shown:
                            shown = done * 100 // total
                            self._set("installing", f"downloading Ollama: {shown}% of {size}")
                self._set("installing", "unpacking Ollama")
                if archive.endswith(".zip"):
                    with zipfile.ZipFile(archive) as bundle:
                        bundle.extractall(folder)
                else:
                    with tarfile.open(archive) as bundle:
                        bundle.extractall(folder, filter="data")
                os.remove(archive)
            except (OSError, zipfile.BadZipFile, tarfile.TarError) as e:
                self._set("failed", f"installing Ollama failed: {e}")
                return False
            binary = managed_binary()
            if binary is None:
                self._set("failed", "the Ollama download had no ollama program in it")
                return False
            if not WINDOWS:
                os.chmod(binary, 0o755)
            self._set("checking", "Ollama installed")
            return True

    def pull_prompt(self) -> str:
        return f"The model {self.llm.model} is not downloaded. Download it now (a few GB)? Type y or n."

    def pull(self) -> bool:
        """Downloads the assistant's model into Ollama. After the user said yes, and the server answers."""
        with self._lock:
            binary, model = find_ollama(), self.llm.model
            if binary is None:
                self._set("not_installed", "Ollama is not installed")
                return False
            self._set("downloading", f"downloading {model}")
            env = {**os.environ, "OLLAMA_HOST": self._host()}
            self._download = subprocess.Popen([binary, "pull", model], stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, env=env, **_spawn_flags())
            # Progress comes as lines and as carriage returns (a bar redrawn in place): both split it
            while chunk := os.read(self._download.stdout.fileno(), 512):
                for piece in chunk.decode("utf-8", "replace").replace("\r", "\n").split("\n"):
                    if piece.strip():
                        self._set("downloading", f"downloading {model}: {piece.strip()[:100]}")
            code = self._download.wait()
            self._download.stdout.close()
            self._download = None
            if code != 0:
                self._set("failed", f"downloading {model} failed (exit code {code})")
                return False
            status, detail = self._probe()
            self._set(status, detail)
            return status == "ready"

    def stop(self) -> None:
        """At quit: stops the server and any download this app started. A server the app did not
        start is left alone."""
        self._closing = True
        self._terminate(self._download)
        if self._lock.acquire(timeout=5):   # A start still in its wait sees _closing, and ends
            self._lock.release()
        self._terminate(self._server)
        self._server = None

    @staticmethod
    def _terminate(proc) -> None:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
