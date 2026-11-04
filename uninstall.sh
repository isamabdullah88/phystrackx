#!/bin/sh
# Uninstalls PhysTrackX from this computer, on macOS or Linux: the `phystrackx` command, and on macOS
# PhysTrackX.app from /Applications (or ~/Applications). Safe to run when nothing is installed.
#
#     sh uninstall.sh            removes the program
#     sh uninstall.sh --purge    also removes the cache, the recent-projects list and the build environments
#
# Your projects and videos are never removed, nor is this folder (the clone).
set -eu

PURGE=0
for arg in "$@"; do
    case "$arg" in
        --purge) PURGE=1 ;;
        -h|--help)
            echo "usage: sh uninstall.sh [--purge]"
            echo "  --purge   also remove the cache, the recent-projects list and the build environments"
            exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

OS=$(uname -s)

remove() {   # remove PATH: deletes it if it exists
    if [ -e "$1" ] || [ -L "$1" ]; then
        rm -rf "$1"
        echo "removed $1"
    fi
}

# uv, if it was installed by install.sh and is not on PATH in this shell
if [ -x "$HOME/.local/bin/uv" ]; then
    PATH="$HOME/.local/bin:$PATH"
    export PATH
fi

echo "== The phystrackx command"
if command -v uv >/dev/null 2>&1 && uv tool list 2>/dev/null | grep -q '^phystrackx '; then
    uv tool uninstall phystrackx
else
    echo "not installed with uv"
fi

# build.py's link to the app's program, if an earlier install made one
LINK="$HOME/.local/bin/phystrackx"
if [ -L "$LINK" ]; then
    case "$(readlink "$LINK")" in
        *PhysTrackX.app*) remove "$LINK" ;;
    esac
fi

if [ "$OS" = "Darwin" ]; then
    echo "== PhysTrackX.app"
    remove /Applications/PhysTrackX.app
    remove "$HOME/Applications/PhysTrackX.app"
fi

if [ "$PURGE" = 1 ]; then
    echo "== Cache, recent projects and build environments"
    if [ "$OS" = "Darwin" ]; then
        remove "$HOME/Library/Caches/PhysTrackX"
    else
        remove "$HOME/.cache/PhysTrackX"
    fi
    remove "$HOME/.phystrackx/recent-qt.json"
    for env in "$HOME"/.venvs/phystrackx-build-* "$HOME/.venvs/phystrackx-dev"; do
        if [ -e "$env" ]; then
            remove "$env"
        fi
    done
    echo "== Done. Your projects and videos were kept."
else
    echo "== Done. Your projects and videos were kept. Run sh uninstall.sh --purge to also remove the cache,"
    echo "   the recent-projects list and the build environments."
fi
