"""
modelfiles.py

Downloads and verifies the NanoTrack tracking models. Files are fetched from the upstream
SiamTrackers repository (https://github.com/HonglinChu/SiamTrackers, NanoTrack/models/nanotrackv2)
the first time tracking needs them, or on demand with `tk/phystrackx.py --download-models`.

Author: Isam Balghari
"""

import hashlib
import logging
import os
import tempfile
import time
import urllib.error
import urllib.request

from core import abspath

_BASE_URL = ("https://raw.githubusercontent.com/HonglinChu/SiamTrackers/master/"
             "NanoTrack/models/nanotrackv2")

# Local path (relative to the project folder) -> (download URL, SHA-256 of the file)
NANOTRACK_MODELS = {
    "models/nanotrack_backbone.onnx": (
        f"{_BASE_URL}/nanotrack_backbone_sim.onnx",
        "530bdd0cd00f19afab79a863e71ba71e3312395a5dc9151af675082bdaaa2fc4",
    ),
    "models/nanotrack_head.onnx": (
        f"{_BASE_URL}/nanotrack_head_sim.onnx",
        "0d8c0637be849f092cc7236cae02e55c8b9455ebe37ba50601d6115db4247cd9",
    ),
}

# Segment Anything (ViT-B) checkpoint, from Meta AI: finds objects from clicks or a box
SAM_MODELS = {
    "models/sam_vit_b_01ec64.pth": (
        "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
        "ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912",
    ),
}
# ViTTrack (OpenCV's TrackerVit), from the OpenCV model zoo: a stronger single-object tracker
VITTRACK_MODELS = {
    "models/object_tracking_vittrack_2023sep.onnx": (
        "https://huggingface.co/opencv/object_tracking_vittrack/resolve/main/"
        "object_tracking_vittrack_2023sep.onnx",
        "2990f0b7cd44d92afa48cd97db6de7be113fc1d9594fddb74e2725c10478e91d",
    ),
}
ALL_MODELS = {**NANOTRACK_MODELS, **VITTRACK_MODELS, **SAM_MODELS}

logger = logging.getLogger(__name__)


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: str, expected: str) -> None:
    """Streams `url` into `dest`, verified against the expected hash, via a temp file."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".part")
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(url, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            last_logged = -1
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total and done * 10 // total != last_logged:
                    last_logged = done * 10 // total
                    logger.info(f"Downloading {os.path.basename(dest)}: {last_logged * 10}%")

        actual = _sha256(tmp)
        if actual != expected:
            raise IOError(f"Checksum mismatch for {os.path.basename(dest)}: "
                          f"expected {expected}, got {actual}")
        os.replace(tmp, dest)
        os.chmod(dest, 0o644)  # mkstemp creates the file owner-only
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _download_retrying(url: str, dest: str, expected: str, attempts: int = 4) -> None:
    """_download, tried again after a network failure or a server error (5xx): a busy CDN can drop a
    large file part-way ("503: between bytes timeout"). Waits 5, 10, 20 s between tries."""
    for attempt in range(1, attempts + 1):
        try:
            return _download(url, dest, expected)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == attempts:
                raise
            reason = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == attempts:
                raise
            reason = str(e)
        wait = 5 * 2 ** (attempt - 1)
        logger.warning(f"Download of {os.path.basename(dest)} failed ({reason}); trying again in {wait} s")
        time.sleep(wait)


def missing_models(relpaths: list[str]) -> list[str]:
    """Returns the relative paths that are not present on disk."""
    return [p for p in relpaths if not os.path.isfile(abspath(p))]


def ensure_models(relpaths: list[str]) -> None:
    """Downloads any of the given model files that are not present. Safe to call from a
    worker thread (it does not touch Tk)."""
    for rel in missing_models(relpaths):
        if rel not in ALL_MODELS:
            raise FileNotFoundError(f"No download source is known for {rel}.")
        url, sha = ALL_MODELS[rel]
        logger.info(f"Tracking model not found; downloading {rel}")
        _download_retrying(url, abspath(rel), sha)
        logger.info(f"Saved {rel}")


def download_all() -> None:
    """Downloads every model that is missing (used by --download-models)."""
    ensure_models(list(ALL_MODELS))
