# PyInstaller spec for the packaged app. Built by build.py (which passes the version, the icon
# folder and the output folder through the environment); see packaging/README.md.
#
#   uv run --group build python build.py app
#
# One-folder build: the app starts faster than a one-file build (nothing is unpacked at each start),
# and the signing and notarizing steps work on the folder's files one by one.

import os
import re
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_DIR = SPECPATH                                  # qt/packaging
QT = os.path.dirname(SPEC_DIR)                       # qt/
REPO = os.path.dirname(QT)                           # the repo root: core, media, experiments, filters, models
BUILD_DIR = os.environ.get("PHYSTRACK_BUILD_DIR") or os.path.join(QT, "build")
ICON_DIR = os.path.join(BUILD_DIR, "icons")

with open(os.path.join(QT, "phystrack_qt", "version.py"), encoding="utf-8") as f:
    VERSION = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)

MACOS = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"
ICON = os.path.join(ICON_DIR, "icon.icns") if MACOS else \
    (os.path.join(REPO, "assets", "icon.ico") if WINDOWS else os.path.join(ICON_DIR, "icon.png"))

# The tracking models the app uses by default (the big SAM model is not bundled; see README)
MODELS = [os.path.join(REPO, "models", name) for name in (
    "nanotrack_backbone.onnx", "nanotrack_head.onnx", "object_tracking_vittrack_2023sep.onnx")]

a = Analysis(
    [os.path.join(SPEC_DIR, "entry.py")],
    pathex=[QT, REPO],
    datas=collect_data_files("imageio_ffmpeg") + [(path, "models") for path in MODELS],   # ffmpeg is data here
    # Modules the app imports by name at run time (phystrack_qt/parent_imports.py), which PyInstaller
    # cannot see: the parent's core and media packages, and the trackers and fits the app uses
    hiddenimports=collect_submodules("core") + collect_submodules("media") + [
        "experiments.rigid.background", "experiments.rigid.blobtracker", "experiments.rigid.cliptrack",
        "experiments.rigid.mltracker", "experiments.rigid.physics", "experiments.rigid.ringfit"],
    # The parent repo's Tk GUI is not part of this app
    excludes=["tkinter", "_tkinter", "customtkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="phystrackx",
    debug=False,
    strip=False,
    upx=False,                 # UPX breaks macOS signing and slows startup
    # macOS keeps a console so the command line works (phystrackx video.mp4 in a terminal). Windows has none:
    # the program is its window, and its output goes to a log file (entry.py)
    console=not WINDOWS,
    icon=ICON,
    codesign_identity=os.environ.get("PHYSTRACK_CODESIGN_IDENTITY") or None,
    entitlements_file=os.path.join(SPEC_DIR, "entitlements.plist") if MACOS else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PhysTrackX",
)

if MACOS:
    app = BUNDLE(
        coll,
        name="PhysTrackX.app",
        icon=ICON,
        bundle_identifier="org.phystrackx.app",
        info_plist={
            "CFBundleName": "PhysTrackX",
            "CFBundleDisplayName": "PhysTrackX",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # The console above makes PyInstaller set LSBackgroundOnly; macOS then never makes the app
            # frontmost, so its keys go to the app behind it. A window app must be a normal app.
            "LSBackgroundOnly": False,
            # Without this a Mac with two GPUs counts the app as needing the discrete one, and switches to it
            # while the app is still starting. The display change that follows can leave the app without a
            # menu bar: the previous app's menus stay on screen. (Qt's own Info.plist template sets it too.)
            "NSSupportsAutomaticGraphicsSwitching": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
