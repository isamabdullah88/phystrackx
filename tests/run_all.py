"""
run_all.py

Runs every tests/test_*.py module in its own process, several at a time, and prints a summary.
Each GUI module needs its own process: a second app in one process fails on cached button images.
Each module also gets its own run folder (clips, proxies and logs), so modules do not share files.
A passing module's folder is removed; a failing one's is kept and named in the output.

Usage (from the repo root):
    uv run python -m tests.run_all                  # everything, four at a time
    uv run python -m tests.run_all --jobs 1         # one at a time
    uv run python -m tests.run_all test_tracking    # one or more modules by name

Author: Isam Balghari
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from tests import harness


def run_module(name: str, module: str) -> dict:
    """Runs one test module (a dotted name such as tests.test_fit) in its own process and folder.
    Returns its exit code and output."""
    run_dir = tempfile.mkdtemp(prefix=f"phystrack_{name}_")
    env = dict(os.environ, PHYSTRACK_TEST_RUN_DIR=run_dir)
    started = time.time()
    proc = subprocess.run([sys.executable, "-m", module], cwd=harness.REPO, env=env,
                          capture_output=True, text=True)
    seconds = time.time() - started
    if proc.returncode == 0:
        shutil.rmtree(run_dir, ignore_errors=True)
        kept = None
    else:
        kept = run_dir
    return {"name": name, "rc": proc.returncode, "seconds": seconds, "kept": kept,
            "output": proc.stdout + proc.stderr}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PhysTrackX tests.")
    parser.add_argument("modules", nargs="*", help="module names, such as test_tracking")
    parser.add_argument("--jobs", type=int, default=4, help="modules run at the same time (default 4)")
    args = parser.parse_args()

    harness.setup_env()
    # The shared tests, and the Tk app's tests (tk/tests), each run as a module of its own
    modules = {}
    for folder, package in ((harness.TESTS_DIR, "tests"), (os.path.join(harness.REPO, "tk", "tests"), "tk.tests")):
        for p in glob.glob(os.path.join(folder, "test_*.py")):
            name = os.path.splitext(os.path.basename(p))[0]
            modules[name] = f"{package}.{name}"
    names = sorted(modules)
    if args.modules:
        names = [n for n in names if n in args.modules]

    results = {}
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {name: pool.submit(run_module, name, modules[name]) for name in names}
        for name in names:  # Printed in name order, each as it is ready
            result = futures[name].result()
            results[name] = result
            status = "OK  " if result["rc"] == 0 else "FAIL"
            print(f"{status} {name} ({result['seconds']:.0f} s)", flush=True)

    for name in names:
        result = results[name]
        if result["rc"] != 0:
            print(f"\n=== {name}: output", flush=True)
            print(result["output"], flush=True)
            print(f"(run folder kept: {result['kept']})", flush=True)

    print("\n=== summary")
    for name in names:
        result = results[name]
        print(f"  {'OK  ' if result['rc'] == 0 else 'FAIL'} {name}  {result['seconds']:.0f} s")
    total = sum(r["seconds"] for r in results.values())
    print(f"  {len(names)} modules, {total:.0f} s of test time")
    sys.exit(1 if any(r["rc"] != 0 for r in results.values()) else 0)


if __name__ == "__main__":
    main()
