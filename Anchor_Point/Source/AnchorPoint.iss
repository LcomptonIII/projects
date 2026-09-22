#define MyAppName "Anchor Point"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Anchor Point"
#define MyAppExeName "AnchorPoint.exe"

[Setup]
AppId={{F42E22DD-9C2B-4F8C-A885-7A6D9C5D72B7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Anchor Point
DefaultGroupName=Anchor Point
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer
OutputBaseFilename=AnchorPoint-1.0.0-Setup
SetupIconFile=anchorpointlogo.ico
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "dist\AnchorPoint.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Anchor Point"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Anchor Point"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Anchor Point"; Flags: nowait postinstall skipifsilent
