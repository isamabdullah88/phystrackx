#!/bin/sh
# Installs PhysTrackX on macOS or Linux, from this folder:
#
#     sh install.sh              macOS: PhysTrackX.app in /Applications, and the `phystrackx` command
#                                Linux: the `phystrackx` command
#     sh install.sh --no-app     macOS: the `phystrackx` command only
#
# Installs uv first if it is missing (the uv project's installer, from astral.sh). uv then makes the
# Python 3.12 and the dependencies in its own folders, so nothing else is needed. Safe to run again:
# it replaces the earlier install.
set -eu

usage() {
    echo "usage: sh install.sh [--no-app]"
    echo "  --no-app   macOS: install the phystrackx command only, not PhysTrackX.app in /Applications"
    exit 2
}

# The app is the install on macOS; Linux has no app bundle yet (see packaging/README.md)
if [ "$(uname -s)" = "Darwin" ]; then APP=1; else APP=0; fi
for arg in "$@"; do
    case "$arg" in
        --no-app) APP=0 ;;
        -h|--help) usage ;;
        *) echo "unknown option: $arg" >&2; usage ;;
    esac
done

cd "$(dirname "$0")/qt" || exit 1   # The app and its build.py live in qt/

# The build environment is named for this clone's folder, so clones do not share one, and it stays out of
# iCloud (a dot-folder there breaks Qt's plugins); see packaging/README.md
: "${UV_PROJECT_ENVIRONMENT:=$HOME/.venvs/phystrackx-build-$(pwd | cksum | cut -d' ' -f1)}"
export UV_PROJECT_ENVIRONMENT

if ! command -v uv >/dev/null 2>&1; then
    if [ -x "$HOME/.local/bin/uv" ]; then
        PATH="$HOME/.local/bin:$PATH"
    else
        echo "== Installing uv (from https://astral.sh/uv)"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        PATH="$HOME/.local/bin:$PATH"
    fi
    export PATH
fi
if ! command -v uv >/dev/null 2>&1; then
    echo "uv could not be found after installing it. See https://docs.astral.sh/uv/" >&2
    exit 1
fi

if [ "$(uname -s)" = "Linux" ]; then
    # Qt needs these system libraries; the command starts without them, the window does not
    if ! ldconfig -p 2>/dev/null | grep -q 'libEGL.so.1' ||
       ! ldconfig -p 2>/dev/null | grep -q 'libxkbcommon.so.0'; then
        echo "Note: Qt needs system libraries for the window. On Debian or Ubuntu:"
        echo "  sudo apt-get install libegl1 libgl1 libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libxcb-cursor0"
    fi
fi

# Each step's output goes to this log
mkdir -p build
LOG=build/install.log
: > "$LOG"
TOTAL=$((2 + APP))   # the models, the command, and on macOS the app
DONE=0

# In a terminal, each step's whole output scrolls by, colored, above a progress bar with the percentage of
# the install: packaging/install_progress.py, with the enlighten bar and colorlog colors that uv fetches here.
# Without a terminal (a pipe, CI), or if they cannot be fetched, one line per step.
UI="uv run --quiet --no-project --with enlighten==1.14.1 --with colorlog==6.12.0 python"
FANCY=0
if [ -t 1 ] && [ "${TERM:-dumb}" != "dumb" ] && $UI -c 'import enlighten, colorlog' >/dev/null 2>&1; then
    FANCY=1
fi

# Runs one step; on failure, shows why and stops the install
step() {
    label=$1
    shift
    DONE=$((DONE + 1))
    if [ "$FANCY" = 1 ]; then
        $UI packaging/install_progress.py \
            --log "$LOG" --stats build/install-progress.json --step "$DONE" --steps "$TOTAL" --label "$label" \
            -- "$@" || { rc=$?; echo "The whole output is in $PWD/$LOG" >&2; exit "$rc"; }
        return 0
    fi
    echo "== $label ($DONE/$TOTAL)"
    "$@" >>"$LOG" 2>&1 || { tail -n 20 "$LOG" >&2; echo "failed: $label. The whole output is in $PWD/$LOG" >&2; exit 1; }
}

step "The models the app ships with" uv run --no-project --with colorlog python build.py models

step "Installing the phystrackx command, with the versions in uv.lock (the ones CI tests)" sh -c \
    'uv export --frozen --no-hashes --no-emit-project > build/constraints.txt &&
     uv tool install --python 3.12 --force --constraints build/constraints.txt .'

if [ "$APP" = 1 ]; then
    step "Building and installing PhysTrackX.app in /Applications" uv run --group build python build.py install
fi

BIN=$(uv tool dir --bin)
if [ "$FANCY" = 1 ]; then printf '\033[1;32mDone.\033[0m '; else echo "== Done"; fi
"$BIN/phystrackx" --version
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "Add $BIN to your PATH, for example in ~/.profile or ~/.zshrc:"
       echo "  export PATH=\"$BIN:\$PATH\"" ;;
esac
