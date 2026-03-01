#ifndef APP_VERSION
  #define APP_VERSION "1.0.0"
#endif

[Setup]
AppName=Crosshair Overlay
AppVersion={#APP_VERSION}
AppPublisher=spuddermax
DefaultDirName={autopf}\Crosshair Overlay
DefaultGroupName=Crosshair Overlay
UninstallDisplayIcon={app}\CrosshairOverlay-{#APP_VERSION}.exe
OutputBaseFilename=CrosshairOverlay-{#APP_VERSION}-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=crosshair-overlay.ico
PrivilegesRequired=lowest

[Files]
Source: "dist\CrosshairOverlay-{#APP_VERSION}.exe"; DestDir: "{app}"; DestName: "CrosshairOverlay-{#APP_VERSION}.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\Crosshair Overlay"; Filename: "{app}\CrosshairOverlay-{#APP_VERSION}.exe"
Name: "{group}\Uninstall Crosshair Overlay"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Crosshair Overlay"; Filename: "{app}\CrosshairOverlay-{#APP_VERSION}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Start at login"; GroupDescription: "Startup:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CrosshairOverlay"; ValueData: """{app}\CrosshairOverlay-{#APP_VERSION}.exe"""; Flags: uninsdeletevalue; Tasks: startupicon

[UninstallRun]
Filename: "cmd.exe"; Parameters: "/c rmdir /s /q ""{userappdata}\crosshair-overlay"""; Flags: runhidden; RunOnceId: "RemoveConfig"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\crosshair-overlay"
