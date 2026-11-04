"""
The models Ollama has on disk, found without asking a server: a server serves one folder, and the
models can be in several (the default, OLLAMA_MODELS, another drive). Each model is a manifest file
at <folder>/manifests/<host>/<namespace>/<model>/<tag>. Standard library only.
"""

import glob
import os

MANIFESTS = "manifests"
DEFAULT_HOST, DEFAULT_NAMESPACE = "registry.ollama.ai", "library"


def model_folders() -> list[str]:
    """Where Ollama keeps models: OLLAMA_MODELS, its default folders, and on Linux the same two
    places on mounted drives (<drive>/.ollama/models and <drive>/ollama/models)."""
    home = os.path.expanduser("~")
    candidates = [os.environ.get("OLLAMA_MODELS", ""),
                  os.path.join(home, ".ollama", "models"),
                  "/usr/share/ollama/.ollama/models", "/var/lib/ollama"]
    if os.name == "posix":
        for drives in ("/mnt/*", "/media/*", "/media/*/*", "/run/media/*/*"):
            for drive in glob.glob(drives):
                candidates += [os.path.join(drive, ".ollama", "models"), os.path.join(drive, "ollama", "models")]
    found = []
    for folder in candidates:
        if folder and os.path.isdir(os.path.join(folder, MANIFESTS)) and folder not in found:
            found.append(folder)
    return found


def models_in(folder: str) -> list[str]:
    """The names in one folder, as `ollama list` writes them: qwen3:4b, user/model:tag."""
    root = os.path.join(folder, MANIFESTS)
    names = []
    for current, _, files in os.walk(root):
        for tag in files:
            parts = os.path.relpath(os.path.join(current, tag), root).split(os.sep)
            if len(parts) < 4:
                continue
            host, namespace, name = parts[0], parts[1], "/".join(parts[2:-1])
            prefix = ""
            if host != DEFAULT_HOST:
                prefix = f"{host}/{namespace}/"
            elif namespace != DEFAULT_NAMESPACE:
                prefix = f"{namespace}/"
            names.append(f"{prefix}{name}:{parts[-1]}")
    return names


def on_disk() -> list[str]:
    """Every model in every folder, once each, sorted."""
    names = set()
    for folder in model_folders():
        try:
            names.update(models_in(folder))
        except OSError:
            continue
    return sorted(names)
