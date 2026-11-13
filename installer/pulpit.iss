#define MyAppName "Пульт"
#define MyAppVersion "1.9.0"
#define MyAppPublisher "Иван Воронцов"
#define MyAppExeName "Pulpit.exe"

[Setup]
AppId={{A1D4A6C2-4F17-49DA-97D1-1D67E0B41091}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Pulpit
DefaultGroupName={#MyAppName}
OutputDir=..\dist\installer
OutputBaseFilename=Pulpit-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\Pulpit.exe

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Files]
Source: "..\dist\Pulpit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Пульт"; Filename: "{app}\Pulpit.exe"
Name: "{autodesktop}\Пульт"; Filename: "{app}\Pulpit.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Pulpit.exe"; Description: "Запустить Пульт"; Flags: nowait postinstall skipifsilent
