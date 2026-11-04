@echo off
REM Uninstalls PhysTrackX from this computer, on Windows: the phystrackx command. Safe to run when nothing is installed.
REM   uninstall.bat           removes the program
REM   uninstall.bat --purge   also removes the cache, the recent-projects list and the build environments
REM Your projects and videos are never removed, nor is this folder (the clone).
setlocal

set "PURGE="
if "%~1"=="" goto :run
if /i "%~1"=="--purge" set "PURGE=1"
if defined PURGE goto :run
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage
echo unknown option: %~1
goto :usage

:usage
echo usage: uninstall.bat [--purge]
echo   --purge   also remove the cache, the recent-projects list and the build environments
exit /b 2

:run
REM uv, if install.bat put it in its folder and it is not on PATH in this window
where uv >nul 2>nul
if errorlevel 1 if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo == The phystrackx command
where uv >nul 2>nul
if errorlevel 1 goto :not_installed
uv tool list 2>nul | findstr /b /c:"phystrackx " >nul
if errorlevel 1 goto :not_installed
uv tool uninstall phystrackx
if errorlevel 1 goto :fail
goto :after_command

:not_installed
echo not installed with uv

:after_command
echo == Start menu entry and desktop icon
powershell -NoProfile -Command "foreach ($d in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop'))) { $f = Join-Path $d 'PhysTrackX.lnk'; if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f; Write-Output ('removed ' + $f) } }"
if not defined PURGE goto :done

echo == Cache, recent projects and build environments
call :remove "%LOCALAPPDATA%\PhysTrackX\Cache"
call :remove "%USERPROFILE%\.phystrackx\recent-qt.json"
powershell -NoProfile -Command "Get-ChildItem -Path (Join-Path $env:USERPROFILE '.venvs') -Filter 'phystrackx-*' -Directory -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ('removed ' + $_.FullName); Remove-Item -LiteralPath $_.FullName -Recurse -Force }"

:done
if defined PURGE (
    echo == Done. Your projects and videos were kept.
) else (
    echo == Done. Your projects and videos were kept. Run uninstall.bat --purge to also remove the cache,
    echo    the recent-projects list and the build environments.
)
if not defined PHYSTRACK_NO_PAUSE pause
exit /b 0

:fail
echo.
echo The uninstall failed. The messages above say why.
if not defined PHYSTRACK_NO_PAUSE pause
exit /b 1

:remove
REM remove PATH: deletes a folder or a file, if it exists
if not exist "%~1" goto :eof
echo removed %~1
rd /s /q "%~1" 2>nul
if exist "%~1" del /q "%~1" 2>nul
goto :eof
