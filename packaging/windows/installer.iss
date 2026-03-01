[Setup]
AppName=Crosshair Overlay
AppVersion=0.6.0
AppPublisher=spuddermax
DefaultDirName={autopf}\Crosshair Overlay
DefaultGroupName=Crosshair Overlay
UninstallDisplayIcon={app}\CrosshairOverlay.exe
OutputBaseFilename=CrosshairOverlay-0.6.0-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=crosshair-overlay.ico
PrivilegesRequired=lowest

[Files]
Source: "dist\CrosshairOverlay.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Crosshair Overlay"; Filename: "{app}\CrosshairOverlay.exe"
Name: "{group}\Uninstall Crosshair Overlay"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Crosshair Overlay"; Filename: "{app}\CrosshairOverlay.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Start at login"; GroupDescription: "Startup:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CrosshairOverlay"; ValueData: """{app}\CrosshairOverlay.exe"""; Flags: uninsdeletevalue; Tasks: startupicon

[UninstallRun]
Filename: "cmd.exe"; Parameters: "/c rmdir /s /q ""{userappdata}\crosshair-overlay"""; Flags: runhidden; RunOnceId: "RemoveConfig"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\crosshair-overlay"
