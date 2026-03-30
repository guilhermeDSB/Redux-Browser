; ============================================================
; Redux Browser — Inno Setup Installer Script
; ============================================================
; Compila com: ISCC.exe installer\redux_browser.iss
; Requer: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
; ============================================================

#define MyAppName "Redux Browser"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "CodeSpace"
#define MyAppURL "https://github.com/user/redux-browser"
#define MyAppExeName "ReduxBrowser.exe"

[Setup]
; ID único — NÃO alterar entre versões (garante upgrade in-place)
AppId={{B8F2E3A7-1C4D-4E5F-9A6B-7C8D9E0F1A2B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Diretórios
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Saída
OutputDir=..\dist\installer
OutputBaseFilename=ReduxBrowser_Setup_{#MyAppVersion}
SetupIconFile=redux_browser.ico
Compression=lzma2/ultra64
SolidCompression=yes

; Aparência
WizardStyle=modern
WizardSizePercent=120

; Permissões (instala por usuário, sem admin necessário)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Atualização (permite instalar sobre versão existente)
UsePreviousAppDir=yes
CloseApplications=force
RestartApplications=yes

; Aceitar instalação silenciosa (para auto-update)
AllowNoIcons=yes

; Versão mínima do Windows
MinVersion=10.0

[Languages]
Name: "brazilian_portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Copia TODA a pasta de saída do PyInstaller (onedir)
Source: "..\dist\ReduxBrowser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Registra a instalação para o auto-updater poder localizar
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; Registrar como navegador no Windows (opcional)
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpa arquivos gerados em runtime (cache, logs, etc.) na desinstalação
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
// Fecha o Redux Browser antes de instalar (para upgrade)
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Tenta fechar suavemente
  Exec('taskkill', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
