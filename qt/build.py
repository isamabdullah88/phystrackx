#!/usr/bin/env python3
"""
Builds, installs and tests PhysTrackX. Run from qt/ through uv, which makes and updates the
environment from pyproject.toml and uv.lock, so no venv is set up by hand:

    uv run python build.py dev       Install `phystrackx` for development: on PATH, running this
                                     folder's code, so edits need no reinstall (rerun after a
                                     change to pyproject.toml, such as a new dependency or command)
    uv run python build.py test      Run the test scripts, several at once (PHYSTRACK_TEST_JOBS=1: one at a time)
    uv run python build.py models    Download the models the app ships with, if missing (the
                                     release build and the wheel need them)
    uv run --group build python build.py app
                                     Build the app and package it: macOS PhysTrackX-<v>-macos-<arch>.dmg,
                                     Windows .zip and PhysTrackX-Setup.exe (needs Inno Setup 6), Linux .tar.gz
                                     (and an AppImage if APPIMAGETOOL is set).
                                     On macOS it is signed first, if PHYSTRACK_CODESIGN_IDENTITY is set.
    uv run --group build python build.py build | package
                                     The two halves of app: build the app folder; package it. The release
                                     workflow signs Windows between them.
    uv run --group build python build.py install
                                     Build the app and install it (macOS: /Applications, and
                                     `phystrackx` on PATH; elsewhere the folder is printed)
    uv run --group build python build.py sign
                                     macOS: sign, notarize and staple the built app (needs the signing
                                     settings; see packaging/README.md)

Output goes to qt/build/ (not committed).
"""

import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

QT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(QT)
# Build output. Set PHYSTRACK_BUILD_DIR outside iCloud for a release: iCloud adds file attributes
# that make codesign refuse the app (packaging/README.md)
BUILD = os.environ.get("PHYSTRACK_BUILD_DIR") or os.path.join(QT, "build")
ICONS = os.path.join(BUILD, "icons")
DIST = os.path.join(BUILD, "dist")
APP_NAME = "PhysTrackX"
MACOS, WINDOWS = sys.platform == "darwin", sys.platform == "win32"


def version() -> str:
    with open(os.path.join(QT, "phystrack_qt", "version.py"), encoding="utf-8") as f:
        return re.search(r'__version__ = "([^"]+)"', f.read()).group(1)


def run(*command: str, cwd: str = QT) -> None:
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def arch() -> str:
    return {"arm64": "arm64", "aarch64": "arm64", "AMD64": "x64", "x86_64": "x64"}.get(platform.machine(), platform.machine())


def platform_name() -> str:
    return {"darwin": "macos", "win32": "windows"}.get(sys.platform, "linux")


# --- Commands -----------------------------------------------------------------------------------

def dev() -> None:
    """Installs `phystrackx` as a uv tool, editable: it runs this folder's code and is on PATH."""
    run("uv", "tool", "install", "--editable", "--force", "--python", "3.12", QT)
    print(f"Installed. Try: phystrackx --version  (version {version()})")


# Test files with checks on how long something takes: run alone, after the others, so a busy machine does not
# fail them
TIMED_TESTS = {"test_plots.py", "test_stop.py"}
TEST_TIMEOUT = 300   # s: one test file (PHYSTRACK_TEST_TIMEOUT); the longest takes about 30 s here, 2 min on CI


def _kill_tree(proc: subprocess.Popen) -> None:
    """Stops a test file and every process it started (an app it launched, a model runner)."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=30)
        else:
            os.killpg(proc.pid, 9)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc.kill()
        proc.wait(timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def test(jobs: int | None = None) -> int:
    """Runs each tests/test_*.py as a script (each exits non-zero on a failed check). The files run several at
    once (`jobs`; PHYSTRACK_TEST_JOBS, else half the CPUs), each in a test folder of its own; the timed ones
    (TIMED_TESTS) run after them, one at a time. A file's output is printed whole when it ends, with its time.
    A file still running after PHYSTRACK_TEST_TIMEOUT seconds (TEST_TIMEOUT) is stopped, with every process
    it started, and fails: its output so far is printed, so the log says where it hung. The output goes to
    a file, not a pipe: a process a test leaves behind could hold a pipe open, and the run wait on it."""
    from concurrent.futures import ThreadPoolExecutor
    import time

    jobs = jobs or int(os.environ.get("PHYSTRACK_TEST_JOBS") or 0) or max(1, (os.cpu_count() or 2) // 2)
    work = os.path.join(tempfile.gettempdir(), "phystrack_qt_tests")
    scripts = sorted(glob.glob(os.path.join(QT, "tests", "test_*.py")))
    timeout = float(os.environ.get("PHYSTRACK_TEST_TIMEOUT") or TEST_TIMEOUT)
    failed = []

    def run(script: str) -> None:
        name = os.path.basename(script)
        folder = os.path.join(work, os.path.splitext(name)[0])
        os.makedirs(folder, exist_ok=True)
        env = dict(os.environ, PHYSTRACK_QT_TEST_WORK=folder, PYTHONUNBUFFERED="1")   # Output so far, if stopped
        log_path = os.path.join(folder, "output.log")
        t0 = time.time()
        with open(log_path, "wb") as log:
            proc = subprocess.Popen([sys.executable, script], cwd=os.path.join(QT, "tests"), env=env,
                                    stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    start_new_session=sys.platform != "win32")
            try:
                code = proc.wait(timeout=timeout)
                verdict = ", FAILED" if code else ""
            except subprocess.TimeoutExpired:
                _kill_tree(proc)
                code, verdict = 1, f", TIMED OUT after {timeout:.0f} s: stopped"
        with open(log_path, encoding="utf-8", errors="replace") as f:
            output = f.read()
        print(f"== {name} ({time.time() - t0:.0f} s{verdict})\n{output}", flush=True)
        if code:
            failed.append(name)

    t0 = time.time()
    with ThreadPoolExecutor(jobs) as pool:
        list(pool.map(run, [s for s in scripts if os.path.basename(s) not in TIMED_TESTS]))
    for script in scripts:
        if os.path.basename(script) in TIMED_TESTS:
            run(script)
    print(f"{len(scripts)} test files in {time.time() - t0:.0f} s, {jobs} at a time")
    print("all test files passed" if not failed else f"failed: {', '.join(sorted(failed))}")
    return 1 if failed else 0


BUNDLED_MODELS = ["models/nanotrack_backbone.onnx", "models/nanotrack_head.onnx",
                  "models/object_tracking_vittrack_2023sep.onnx"]   # Shipped with the app (small; SAM is not)


def models() -> None:
    """Makes sure the models the app ships with are in the repo's models/ folder, downloading any missing
    one (checked against its SHA-256) with the parent's own downloader. Git does not hold them."""
    sys.path.insert(0, QT)
    from phystrack_qt.parent_imports import import_light
    import_light("experiments.rigid.modelfiles").ensure_models(BUNDLED_MODELS)


def icons() -> None:
    """The app icon in the form each platform takes: icon.icns (macOS, from the 512 px logo), and the
    PNG for Linux. Windows uses assets/icon.ico, which holds the sizes already."""
    os.makedirs(ICONS, exist_ok=True)
    logo = os.path.join(REPO, "assets", "logos", "logo.png")
    shutil.copy(logo, os.path.join(ICONS, "icon.png"))
    if MACOS:
        iconset = os.path.join(ICONS, "icon.iconset")
        shutil.rmtree(iconset, ignore_errors=True)
        os.makedirs(iconset)
        for size in (16, 32, 128, 256, 512):
            run("sips", "-z", str(size), str(size), logo, "--out", os.path.join(iconset, f"icon_{size}x{size}.png"))
            run("sips", "-z", str(size * 2), str(size * 2), logo,
                "--out", os.path.join(iconset, f"icon_{size}x{size}@2x.png"))
        run("iconutil", "-c", "icns", iconset, "-o", os.path.join(ICONS, "icon.icns"))


def pyinstaller() -> str:
    """Builds the app folder (dist/PhysTrackX, and PhysTrackX.app on macOS) with PyInstaller."""
    models()
    icons()
    run(sys.executable, "-m", "PyInstaller", os.path.join("packaging", "phystrackx.spec"),
        "--noconfirm", "--distpath", DIST, "--workpath", os.path.join(BUILD, "work"))
    return DIST


def app() -> str:
    """Builds the app, signs it on macOS if signing is set up, and packages it. Returns the package's path.
    (The release workflow runs the steps one by one, so Windows can be signed between them.)"""
    pyinstaller()
    if MACOS and os.environ.get("PHYSTRACK_CODESIGN_IDENTITY"):
        sign()
    return package()


def package() -> str:
    """Packages the built app (see app()). Returns the package's path."""
    name = f"{APP_NAME}-{version()}-{platform_name()}-{arch()}"
    if MACOS:
        return make_dmg(os.path.join(DIST, f"{APP_NAME}.app"), name)
    folder = os.path.join(DIST, APP_NAME)
    archive = shutil.make_archive(os.path.join(BUILD, name), "zip" if WINDOWS else "gztar",
                                  root_dir=DIST, base_dir=APP_NAME)
    if sys.platform.startswith("linux") and os.environ.get("APPIMAGETOOL"):
        make_appimage(folder, name)
    if WINDOWS:
        make_installer(folder)
    print(f"Packaged: {archive}")
    return archive


def make_dmg(app_path: str, name: str) -> str:
    """A disk image with the app and a link to Applications, to drag the app across."""
    staging = tempfile.mkdtemp(prefix="dmg-", dir=BUILD)
    shutil.copytree(app_path, os.path.join(staging, os.path.basename(app_path)), symlinks=True)
    os.symlink("/Applications", os.path.join(staging, "Applications"))
    dmg = os.path.join(BUILD, name + ".dmg")
    if os.path.exists(dmg):
        os.remove(dmg)
    run("hdiutil", "create", "-volname", APP_NAME, "-srcfolder", staging, "-ov", "-format", "UDZO", dmg)
    shutil.rmtree(staging)
    print(f"Packaged: {dmg}")
    return dmg


def make_appimage(folder: str, name: str) -> str:
    """A Linux AppImage: the app folder under usr/, run by AppRun, with the desktop entry and icon."""
    appdir = os.path.join(BUILD, f"{APP_NAME}.AppDir")
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(folder, os.path.join(appdir, "usr", "bin"))
    with open(os.path.join(appdir, "AppRun"), "w", encoding="utf-8") as f:
        f.write('#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\n'
                'exec "$HERE/usr/bin/phystrackx" "$@"\n')
    os.chmod(os.path.join(appdir, "AppRun"), 0o755)
    with open(os.path.join(appdir, "phystrackx.desktop"), "w", encoding="utf-8") as f:
        f.write(f"[Desktop Entry]\nType=Application\nName={APP_NAME}\nExec=phystrackx %F\n"
                "Icon=phystrackx\nCategories=Science;Education;\nTerminal=true\n")
    shutil.copy(os.path.join(ICONS, "icon.png"), os.path.join(appdir, "phystrackx.png"))
    out = os.path.join(BUILD, name + ".AppImage")
    run(os.environ["APPIMAGETOOL"], appdir, out)
    print(f"Packaged: {out}")
    return out


def make_installer(folder: str) -> str:
    """Windows: PhysTrackX-Setup.exe, which installs the app folder for the current user (packaging/PhysTrackX.iss).
    Needs Inno Setup 6: ISCC.exe on PATH, or in its default folder."""
    iscc = shutil.which("ISCC.exe") or os.path.join(
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Inno Setup 6", "ISCC.exe")
    if not os.path.exists(iscc):
        sys.exit("The installer needs Inno Setup 6 (https://jrsoftware.org/isdl.php, or `choco install innosetup`).")
    # No quotes around the paths: subprocess already quotes one that has spaces, and extra quotes would reach
    # Inno Setup as part of the path
    run(iscc, os.path.join(QT, "packaging", "PhysTrackX.iss"), f"/DVersion={version()}",
        f"/DSourceDir={folder}", f"/DOutputDir={BUILD}")
    out = os.path.join(BUILD, f"{APP_NAME}-Setup.exe")
    print(f"Packaged: {out}")
    return out


def install() -> None:
    """Builds the app and installs it where the platform keeps apps."""
    if not MACOS:
        pyinstaller()
        print(f"Built {os.path.join(DIST, APP_NAME)} (run phystrackx from that folder).")
        return
    pyinstaller()
    source = os.path.join(DIST, f"{APP_NAME}.app")
    target = os.path.join("/Applications", f"{APP_NAME}.app")
    if not os.access("/Applications", os.W_OK):
        target = os.path.join(os.path.expanduser("~/Applications"), f"{APP_NAME}.app")
        os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.lexists(target):
        shutil.rmtree(target)   # The earlier install, replaced; an error here stops the install
    shutil.copytree(source, target, symlinks=True)
    link_cli(os.path.join(target, "Contents", "MacOS", "phystrackx"))
    warm_launch(target)
    print(f"Installed {target}")


def warm_launch(app_path: str) -> None:
    """macOS: opens the installed app once, hidden, so its first real start is fast. The first time macOS
    opens a new app it checks each program and library as it loads (XProtect, syspolicyd), which held the
    window back about 5 s. Only a launch through LaunchServices (open, Finder, Spotlight) counts, not
    running the program from a shell. The app loads everything, shows nothing, and quits
    (app.warm_launch). A failure here only costs that wait, so it does not stop the install."""
    print("Opening the app once, hidden, so macOS checks it now rather than at its first start…", flush=True)
    try:
        subprocess.run(["open", "-W", "-n", "-g", "-j", "-a", app_path, "--args", "--warm-launch"],
                       check=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Skipped ({e}); the first start may take a few seconds longer.")


def link_cli(executable: str) -> None:
    """Puts `phystrackx` on PATH as a link to the app's own program (~/.local/bin, which is on PATH
    for most users; the note says so if it is not). An existing `phystrackx` there, such as the
    development install from `build.py dev`, is left alone: two installs must not share one name."""
    bin_dir = os.path.expanduser("~/.local/bin")
    os.makedirs(bin_dir, exist_ok=True)
    link = os.path.join(bin_dir, "phystrackx")
    if os.path.lexists(link) and not (os.path.islink(link) and os.readlink(link) == executable):
        print(f"Not linked: {link} already exists (the development install?). "
              f"Run the app as {executable}")
        return
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(executable, link)
    print(f"Command: {link}" + ("" if bin_dir in os.environ.get("PATH", "").split(":")
                                 else f"  (add {bin_dir} to PATH)"))


def sign() -> None:
    """macOS: signs every program and library in the app with the Developer ID and the hardened runtime
    (inside out: each file before the folder that holds it), then notarizes the app and staples the
    notarization ticket to it. Settings: PHYSTRACK_CODESIGN_IDENTITY (the Developer ID Application
    name) and PHYSTRACK_NOTARY_PROFILE (a notarytool keychain profile). See packaging/README.md."""
    if not MACOS:
        sys.exit("Signing is for macOS; Windows signing is in packaging/README.md.")
    identity = os.environ.get("PHYSTRACK_CODESIGN_IDENTITY")
    profile = os.environ.get("PHYSTRACK_NOTARY_PROFILE")
    if not identity or not profile:
        sys.exit("Set PHYSTRACK_CODESIGN_IDENTITY and PHYSTRACK_NOTARY_PROFILE (see packaging/README.md).")
    app_path = os.path.join(DIST, f"{APP_NAME}.app")
    entitlements = os.path.join(QT, "packaging", "entitlements.plist")
    sign_args = ["--force", "--options", "runtime", "--timestamp", "--entitlements", entitlements,
                 "--sign", identity]
    nested = []
    for path in glob.glob(os.path.join(app_path, "**", "*"), recursive=True):
        if os.path.isfile(path) and not os.path.islink(path) and is_macho(path):
            nested.append(path)
    # Deepest first, so each file is signed before the bundle that contains it
    for path in sorted(nested, key=lambda p: -p.count(os.sep)):
        run("codesign", *sign_args, path)
    run("codesign", *sign_args, app_path)
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", app_path)
    zipped = os.path.join(BUILD, f"{APP_NAME}-notarize.zip")
    run("ditto", "-c", "-k", "--keepParent", app_path, zipped)
    run("xcrun", "notarytool", "submit", zipped, "--keychain-profile", profile, "--wait")
    run("xcrun", "stapler", "staple", app_path)
    run("spctl", "--assess", "--type", "execute", "--verbose=2", app_path)
    os.remove(zipped)
    print(f"Signed and notarized {app_path}")


def is_macho(path: str) -> bool:
    with open(path, "rb") as f:
        return f.read(4) in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe",
                             b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe")


def main(argv: list[str]) -> int:
    commands = {"dev": dev, "test": test, "app": app, "build": pyinstaller, "package": package,
                "install": install, "sign": sign, "icons": icons, "models": models}
    if len(argv) != 2 or argv[1] not in commands:
        print(__doc__)
        return 2
    result = commands[argv[1]]()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
