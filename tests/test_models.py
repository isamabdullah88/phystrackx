"""Tracking model detection and download logic. Network downloads only with PHYSTRACK_TEST_NETWORK=1."""

import os

from tests import harness as h
h.setup_env()

from experiments.rigid import modelfiles  # noqa: E402
from core import abspath  # noqa: E402

PATHS = list(modelfiles.NANOTRACK_MODELS)


def test_missing_models_reports_absent_files():
    # A name that is not in the model registry and not on disk
    absent = modelfiles.missing_models(["models/does_not_exist.onnx"])
    h.check("unknown model is reported missing", absent == ["models/does_not_exist.onnx"])


def test_present_models_are_not_downloaded_again():
    present = all(os.path.isfile(abspath(p)) for p in PATHS)
    if not present:
        print("  SKIP models not present; run `uv run python phystrackx.py --download-models` first")
        return
    real_download = modelfiles._download
    calls = []
    modelfiles._download = lambda *a, **k: calls.append(a)
    try:
        modelfiles.ensure_models(PATHS)
    finally:
        modelfiles._download = real_download
    h.check("ensure_models does nothing when the models exist", not calls)


def test_download_writes_verified_files():
    if os.environ.get("PHYSTRACK_TEST_NETWORK") != "1":
        print("  SKIP network download (set PHYSTRACK_TEST_NETWORK=1 to run)")
        return
    modelfiles.download_all()
    h.check("both models are present after download", not modelfiles.missing_models(PATHS))


if __name__ == "__main__":
    h.run_tests([test_missing_models_reports_absent_files, test_present_models_are_not_downloaded_again,
                 test_download_writes_verified_files])
