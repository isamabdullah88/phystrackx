@echo off
REM Installs PhysTrackX on Windows, from this folder: double-click it, or run it from a terminal.
REM Installs the phystrackx command. Installs uv first if it is missing (the uv project's installer, from
REM astral.sh). uv then makes the Python 3.12 and the dependencies in its own folders. Safe to run again:
REM it replaces the earlier install.
setlocal
cd /d "%~dp0qt" || goto :fail

REM The build environment is named for this clone's folder, so clones do not share one, and it stays out of
REM iCloud and OneDrive folders; see packaging\README.md
if not defined UV_PROJECT_ENVIRONMENT call :clone_env

where uv >nul 2>nul
if errorlevel 1 goto :install_uv
goto :have_uv

:install_uv
if exist "%USERPROFILE%\.local\bin\uv.exe" goto :path_uv
echo == Installing uv (from https://astral.sh/uv)
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if errorlevel 1 goto :fail

:path_uv
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

:have_uv
where uv >nul 2>nul
if errorlevel 1 (
    echo uv could not be found after installing it. See https://docs.astral.sh/uv/
    goto :fail
)

echo == The models the app ships with
uv run --no-project --with colorlog python build.py models
if errorlevel 1 goto :fail

echo == Installing the phystrackx command, with the versions in uv.lock (the ones CI tests)
if not exist build mkdir build
uv export --frozen --no-hashes --no-emit-project > build\constraints.txt
if errorlevel 1 goto :fail
uv tool install --python 3.12 --force --constraints build\constraints.txt .
if errorlevel 1 goto :fail

for /f "delims=" %%B in ('uv tool dir --bin') do set "BIN=%%B"

echo == Start menu entry and desktop icon
if not exist "%LOCALAPPDATA%\PhysTrackX" mkdir "%LOCALAPPDATA%\PhysTrackX"
copy /y "%~dp0assets\icon.ico" "%LOCALAPPDATA%\PhysTrackX\icon.ico" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = New-Object -ComObject WScript.Shell; foreach ($d in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop'))) { $l = $s.CreateShortcut((Join-Path $d 'PhysTrackX.lnk')); $l.TargetPath = Join-Path $env:BIN 'phystrackx-gui.exe'; $l.IconLocation = Join-Path $env:LOCALAPPDATA 'PhysTrackX\icon.ico'; $l.WorkingDirectory = $env:USERPROFILE; $l.Save(); Write-Output ('  ' + $l.FullName) }"
if errorlevel 1 echo Could not make the shortcuts; run phystrackx from a terminal instead.
echo == Done
"%BIN%\phystrackx.exe" --version
echo If phystrackx is not found in a new terminal, add %BIN% to your PATH.
echo.
if not defined PHYSTRACK_NO_PAUSE pause
exit /b 0

:fail
echo.
echo The install failed. The messages above say why.
if not defined PHYSTRACK_NO_PAUSE pause
exit /b 1

:clone_env
REM A short name from a hash of this folder's full path (the Windows PowerShell hash, 8 bytes of it)
for /f "delims=" %%H in ('powershell -NoProfile -Command "[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes((Get-Location).Path))).Substring(0,11)"') do set "CLONE=%%H"
set "UV_PROJECT_ENVIRONMENT=%USERPROFILE%\.venvs\phystrackx-build-%CLONE%"
goto :eof
