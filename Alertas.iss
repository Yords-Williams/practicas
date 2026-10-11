#define MyAppName "Alertas Tempranas"
#define MyAppVersion "1.0"
#define MyAppPublisher "Alertas Tempranas"
#define MyAppExeName "AlertasTempranas.exe"

#if !FileExists("dist\AlertasTempranas\AlertasTempranas.exe")
  #error "Falta dist\AlertasTempranas\AlertasTempranas.exe. Ejecuta build_exe.ps1 primero y vuelve a compilar."
#endif

[Setup]
AppId={{345D5114-C108-484C-804A-E48656172206}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Alertas-Setup
SetupIconFile=assets\app.ico
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\AlertasTempranas\*"; DestDir: "{app}"; Excludes: "notifications_config.json,meta_whatsapp_config.json"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar Alertas"; Flags: nowait postinstall skipifsilent
