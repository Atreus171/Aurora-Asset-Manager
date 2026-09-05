; Aurora Asset Manager - Inno Setup Installer Script
; Compile with Inno Setup 6+

#define AppName "Aurora Asset Manager"
#define AppVersion "1.5.5.2"
#define AppPublisher "Atreus171"
#define AppURL "https://github.com/Atreus171/Aurora-Asset-Manager"
#define AppExeName "AuroraAssetManager.exe"

[Setup]
AppId={{A7B8C9D0-E1F2-4A3B-8C7D-6E5F4A3B2C1D}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=AuroraAssetManager_Setup_v{#AppVersion}
Compression=lzma
SolidCompression=yes
CompressionThreads=auto
InternalCompressLevel=ultra
SetupIconFile=assets\icon.ico
LicenseFile=LICENSE
InfoBeforeFile=README.md
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
DisableDirPage=no
DisableProgramGroupPage=no
DisableFinishedPage=no
DefaultDialogFontName=Segoe UI
CreateAppDir=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
AppCopyright=Copyright © 2024 Atreus171

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "{cm:CreateStartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[CustomMessages]
CreateStartMenuIcon=Create Start Menu shortcut

[Files]
Source: "dist\AuroraAssetManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "game_covers\*"; DestDir: "{app}\game_covers"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\game_covers"

[Registry]
Root: HKCU; Subkey: "Software\Atreus171\AuroraAssetManager"; ValueType: string; ValueName: "Version"; ValueData: "{#AppVersion}"; Flags: uninsdeletekey

[Code]
procedure InitializeWizard();
begin
  // Pré-seleciona "Eu aceito o acordo" na página de licença
  WizardForm.LicenseAcceptedRadio.Checked := True;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    // Create game_covers directory if it doesn't exist
    if not DirExists(ExpandConstant('{app}\game_covers')) then
      ForceDirectories(ExpandConstant('{app}\game_covers'));
  end;
end;