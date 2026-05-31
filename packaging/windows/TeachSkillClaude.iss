#define MyAppName "Teach Skill Claude"
#define MyAppExeName "TeachSkillClaude.exe"
#define MyAppVersion "0.1.0"

[Setup]
AppId={{8DCD3F75-A943-4D5C-9C43-9B2DF72FAF59}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Teach Skill Claude
DefaultGroupName={#MyAppName}
OutputDir=..\..\dist\installer
OutputBaseFilename=TeachSkillClaudeSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "..\..\dist\TeachSkillClaude\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Teach Skill Claude"; Filename: "{app}\{#MyAppExeName}"; Parameters: "launch"
Name: "{autodesktop}\Teach Skill Claude"; Filename: "{app}\{#MyAppExeName}"; Parameters: "launch"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "launch"; Description: "Open Teach Skill Claude"; Flags: nowait postinstall skipifsilent
