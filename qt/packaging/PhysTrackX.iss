; Windows installer for PhysTrackX (Inno Setup 6). build.py package makes it from the app folder
; that PyInstaller builds (build/dist/PhysTrackX) and writes build/PhysTrackX-Setup.exe. It installs for the
; current user only (no administrator prompt), into %LOCALAPPDATA%\Programs, with a Start menu entry, a desktop
; icon (ticked by default), and an uninstaller in Settings > Apps. The AppId never changes, so a later
; installer replaces the earlier install in place.

#define AppName "PhysTrackX"
#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\build\dist\PhysTrackX"
#endif
#ifndef OutputDir
  #define OutputDir "..\build"
#endif

[Setup]
AppId={{92C5594B-2099-43BD-974C-0AF131EF4121}
AppName={#AppName}
AppVersion={#Version}
AppPublisher={#AppName}
DefaultDirName={userpf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
OutputDir={#OutputDir}
OutputBaseFilename=PhysTrackX-Setup
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\phystrackx.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; Flags: checkedonce

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\phystrackx.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\phystrackx.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\phystrackx.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
