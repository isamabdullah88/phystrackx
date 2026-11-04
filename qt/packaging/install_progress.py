"""Runs one install.sh step in a terminal: its whole output scrolls by as a colored log, above a progress
bar pinned to the bottom with the percentage of the whole install.

    python install_progress.py --log LOG --stats STATS --step 2 --steps 3 --label "..." -- command args...

Glue only: enlighten (https://github.com/Rockhopper-Technologies/enlighten) draws the pinned bar, and
colorlog colors the lines by level. install.sh runs this with `uv run --with enlighten --with colorlog`.
A step's percentage counts its lines against how many it printed on the last install (kept in STATS).
The plain output also goes to LOG. Exits with the step's exit code.
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys

import colorlog
import enlighten

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ERROR = re.compile(r"\b(error|failed|fatal|traceback|exception)\b", re.I)
WARNING = re.compile(r"\b(warn|warning|deprecated)\b", re.I)
FIRST_INSTALL_LINES = 200  # A step's guessed length when there is no last install to go by


def level(line):
    return logging.ERROR if ERROR.search(line) else logging.WARNING if WARNING.search(line) else logging.INFO


def main():
    parser = argparse.ArgumentParser()
    for name in ("--log", "--stats", "--label"):
        parser.add_argument(name, required=True)
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command

    handler = colorlog.StreamHandler(sys.stdout)
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(message)s", log_colors={"INFO": "white", "WARNING": "yellow", "ERROR": "bold_red"}))
    log = logging.getLogger("install")
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    try:
        with open(args.stats) as f:
            stats = json.load(f)
    except (OSError, ValueError):
        stats = {}
    expected = stats.get(args.label) or FIRST_INSTALL_LINES

    # The bar counts the whole install in thousandths; this step fills its share of it
    manager = enlighten.get_manager()
    bar = manager.counter(
        total=1000 * args.steps, count=1000 * (args.step - 1), leave=False,
        desc=f"{args.step}/{args.steps} {args.label}",
        bar_format="{desc}{desc_pad}{percentage:3.0f}%|{bar}| {elapsed}")

    env = dict(os.environ, PYTHONUNBUFFERED="1")
    env.pop("VIRTUAL_ENV", None)  # The step's own `uv run` should find its own environment, not this one
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    lines = 0
    with open(args.log, "a") as logfile:
        try:
            for raw in proc.stdout:
                line = ANSI.sub("", raw.decode(errors="replace").rstrip("\r\n").split("\r")[-1])
                logfile.write(line + "\n")
                log.log(level(line), line)
                lines += 1
                bar.count = 1000 * (args.step - 1) + min(1000 * lines // expected, 970)
                bar.refresh()
            rc = proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            rc = 130
    bar.close()
    manager.stop()

    if rc != 0:
        log.error(f"✗ {args.step}/{args.steps} {args.label}: failed (exit {rc})")
        return rc
    stats[args.label] = lines
    try:
        with open(args.stats, "w") as f:
            json.dump(stats, f, indent=1)
    except OSError:
        pass  # The next install's percentage is then only less exact
    print(f"{colorlog.escape_codes.escape_codes['bold_green']}✓ {args.step}/{args.steps} {args.label}"
          f"{colorlog.escape_codes.escape_codes['reset']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
