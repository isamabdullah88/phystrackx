# Packaging PhysTrackX

How the app is built into something people install, and what each piece does. Commands are run
from `qt/` through uv, which makes the build environment from `uv.lock`.

| Command | What it does |
|---|---|
| `uv run python build.py dev` | Installs `phystrackx` as an editable uv tool: on PATH, running this folder's code. Rerun after a change to `pyproject.toml`. |
| `uv run python build.py test` | Runs every `tests/test_*.py` |
| `uv run python build.py models` | Downloads the three small tracking models the app ships with, if missing (checked against SHA-256) |
| `uv run --group build python build.py app` | Builds the app and packages it (signs first on macOS if set up) |
| `uv run --group build python build.py install` | Builds and installs the app (macOS: `/Applications`, plus `phystrackx` on PATH) |

Packages land in `qt/build/` (or `PHYSTRACK_BUILD_DIR`), named `PhysTrackX-<version>-<os>-<arch>`:
a `.dmg` on macOS, a `.zip` and `PhysTrackX-Setup.exe` on Windows, a `.tar.gz` on Linux (plus an `.AppImage`
when `APPIMAGETOOL` points at the appimagetool). The Windows installer needs Inno Setup 6
(`choco install innosetup`, or <https://jrsoftware.org/isdl.php>).

## Parts

- `packaging/phystrackx.spec`: the PyInstaller recipe. One folder, not one file: the app starts
  faster (nothing is unpacked at each start), and signing works on each file. Its macOS `info_plist`
  sets what PyInstaller leaves out or gets wrong for a window app: `LSBackgroundOnly` false (else the
  app never comes to the front) and `NSSupportsAutomaticGraphicsSwitching` true. Without that one, a
  MacBook Pro with two GPUs counts the app as needing the discrete GPU and switches to it while the app
  starts; the display change can leave the app without a menu bar (the previous app's menus stay on
  screen). Check a bundle with `/usr/libexec/PlistBuddy -c 'Print :NSSupportsAutomaticGraphicsSwitching'
  PhysTrackX.app/Contents/Info.plist`, and a launch with
  `log show --last 1m --info --debug --predicate 'process == "kernel" AND eventMessage CONTAINS "AGC::"'`
  (the app should be logged as `mux-aware` only, with no `Switching from IGD to PEG`).
- `packaging/entry.py`: what the packaged program runs (the same as `phystrackx`). On Windows, which has
  no console, its output goes to `%LOCALAPPDATA%\PhysTrackX\Logs\phystrackx.log`.
- `packaging/PhysTrackX.iss`: the Windows installer (Inno Setup). Per user, so no administrator prompt; it
  installs to `%LOCALAPPDATA%\Programs\PhysTrackX`, adds a Start menu entry and a desktop icon (ticked by
  default), and an uninstaller in Settings > Apps. Its AppId never changes, so a new installer upgrades in place.
- `packaging/entitlements.plist`: the two hardened-runtime exceptions a bundled Python needs. Nothing else.
- `build.py icons`: makes `icon.icns` from `assets/logos/logo.png` (macOS) and the Linux PNG. Windows uses `assets/icon.ico`.
- `.github/workflows/qt-ci.yml` (repo root): on every change, installs the command on Windows, macOS
  and Linux, checks it runs, and runs the tests. Then it measures the app's speed on each OS
  (`qt/tests/perf_report.py`: start, opening a video or a project, scrubbing, tracking, the plots'
  libraries): a table on the run's summary page, and the numbers kept as an artifact (`perf-<OS>`, 90
  days). Informational: a slow number never fails the build. Locally: `uv run python tests/perf_report.py`.
- `.github/workflows/qt-release.yml` (repo root): on a tag `qt-v<version>`, builds on all three, signs
  where the secrets are set, and attaches the packages to a GitHub release.

## Versions

- The app's version is `qt/phystrack_qt/version.py`. Nothing else holds it: the wheel, the
  `--version` flag, the bundle's Info.plist and the file names all read it.
- A release is a tag `qt-v<that version>`. The release workflow refuses a tag that does not match.
- The project file's format has its own number (`VERSION` in `project_file.py`). Changing the
  app's version does not change it. Projects of an older format are converted on open (see below).

## Older projects

- A project from the Tk app (format 1) is **imported**, one way. Its setup is carried over: trim,
  axes, ruler (with its length), and the objects' marked boxes, scaled from the Tk canvas to the frame.
- What has no counterpart is **dropped** and named in the status bar: the crop (this app trims by
  range only), the saved data and fits, the OCR boxes. The Tk file keeps no tracks, so each object
  starts at its box, to track again.
- Nothing writes the Tk format. The imported project is unsaved; Save writes a new project of this
  app's format next to the video. The Tk file is never changed.
- A project whose video has moved is found beside the project, if a video of the same name is there.
- A project from another app, or a newer version of this format, is refused with a message.

## Before a release: keep the build out of iCloud

Build output in `Documents` (iCloud) picks up file attributes that make `codesign` refuse the app,
and iCloud's hidden flag on dot-folders breaks Qt's plugins. For a release, set a folder outside
iCloud:

```sh
export PHYSTRACK_BUILD_DIR="$HOME/Library/Caches/phystrackx-build"
```

Likewise the project's `.venv` should be outside iCloud: `export UV_PROJECT_ENVIRONMENT=~/.venvs/phystrackx-dev`.

## Signing

Without signing, the packages work, but macOS says the app "cannot be opened because the developer
cannot be verified" (right-click, Open, once), and Windows SmartScreen warns. Signing removes both.
The workflow skips each signing step whose secrets are missing, so a release without them is unsigned,
not broken. **None of the signing steps has run yet**: they need the certificates below, which are
not set up. Expect to fix small things on the first real run.

### macOS: Developer ID and notarization

Needs the Apple Developer Program ($99 a year).

1. In Xcode or the developer portal, create a **Developer ID Application** certificate. Export it,
   with its private key, as a `.p12` with a password.
2. In App Store Connect, create an API key with the Developer role (Users and Access, Integrations).
   Note its Key ID and the Issuer ID, and download the `.p8` file (once only).
3. Add these repository secrets (Settings, Secrets and variables, Actions):

| Secret | Value |
|---|---|
| `APPLE_CERTIFICATE` | `base64 -i certificate.p12` (the file, base64-encoded) |
| `APPLE_CERTIFICATE_PASSWORD` | the `.p12` password |
| `APPLE_SIGNING_IDENTITY` | e.g. `Developer ID Application: Your Name (TEAMID)` |
| `KEYCHAIN_PASSWORD` | any new random password (for the CI keychain) |
| `NOTARY_KEY_ID` | the API key's Key ID |
| `NOTARY_ISSUER_ID` | the Issuer ID |
| `NOTARY_KEY_P8` | the full text of the `.p8` file |

Locally, the same signing runs with `PHYSTRACK_CODESIGN_IDENTITY` and `PHYSTRACK_NOTARY_PROFILE` (a
profile made once with `xcrun notarytool store-credentials`).

What the signing does: each program and library in the app is signed with the hardened runtime and a
timestamp (deepest first), the app is signed, submitted to Apple's notary service and waited on, and
the notarization ticket is stapled to the app, so it opens offline too. `build.py sign` checks the
result with `spctl`.

### Windows: Azure Artifact Signing

Needs an Azure subscription. Azure Artifact Signing (formerly Trusted Signing) is the cheapest
route to a trusted signature for an app that is not from a large publisher: it signs in the cloud,
so no certificate file is stored.

1. Create a Trusted Signing account and a **Public Trust** certificate profile in Azure.
2. Create an app registration with a federated credential for this repository's GitHub Actions, and
   give it the "Trusted Signing Certificate Profile Signer" role on the certificate profile.
3. Add these repository secrets:

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | from the app registration and subscription |
| `AZURE_SIGNING_ACCOUNT` | the signing account's name |
| `AZURE_CERTIFICATE_PROFILE` | the certificate profile's name |

SmartScreen trusts a new signature only after the app has been downloaded by enough people; the
first releases can still warn.

### Linux

AppImages need no signing to run. GPG-signing the release files is optional (not set up).

## Known limits

- **macOS builds are for the Mac's own chip.** CI's `macos-latest` is Apple silicon, so its package
  is arm64 only. A universal build (both chips) is a later step.
- **Start-up time.** `packaging/entry.py` keeps matplotlib's font cache in the user's cache folder
  (PyInstaller's hook would rebuild it at every start: about 10 s). The install's hidden launch builds it,
  so a first start after `install.sh` is as fast as later ones; a `.dmg` drag-install builds it at its
  first start, once, in the background. Opening a project loads neither matplotlib nor scipy (2.4 s, in
  the first trial): a thread loads them once the last restored trial is open (`plot_warmup.py`). On the
  Intel MacBook Pro, restoring two projects: the trials start to open 1.7 s after the click (Python, Qt
  and the window: the floor for this design) and are all open 0.9 s later; the window freezes for no more
  than 0.5 s at a time (it froze 3.3 s). What is left: each trial opens on the UI thread, about 0.2 s plus
  its first paint (`open_trials` in `app.py` says how to avoid that); a restore of many tabs takes that
  long for each, unless the tabs behind the front one are opened only when they are shown.
- **Size.** The app is about 470 MB, most of it Qt. Trimming the unused Qt modules is a later step.
  ffmpeg is currently bundled twice (in `Frameworks` and `Resources`).
- **Windows installer, not yet run.** The release workflow builds and signs `PhysTrackX-Setup.exe`, but it
  has not run on Windows yet. The zip stays as the fallback. The installer's publisher name is `PhysTrackX`;
  it should match the certificate's name once signing is set up.
- **Opening a file from Finder** (double-clicking a `.phystrack` or video) is not wired yet: macOS
  passes such files as events, not as command-line arguments. The command line works.
- **The SAM model** is not bundled (375 MB). The Qt app does not use it (`agent/relocate.py`); the Tk app does.
- **No console on Windows.** The packaged program has no console window, so `phystrackx file.mp4` in a
  terminal is not available from the packaged app: use the command from `build.py dev` (or `install.sh`)
  for that. On macOS the console is kept.
