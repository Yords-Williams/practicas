#define MyAppName "Alertas Tempranas Videovigilancia"
#define MyAppVersion "1.0"
#define MyAppPublisher "Alertas Tempranas Videovigilancia"
#define MyAppExeName "AlertasTempranas.exe"

#if !FileExists("dist\release\AlertasTempranas\AlertasTempranas.exe")
  #error "Falta dist\release\AlertasTempranas\AlertasTempranas.exe. Ejecuta build_exe.ps1 primero y vuelve a compilar."
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
UninstallDisplayName={#MyAppName}
Uninstallable=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=dist\instalador
OutputBaseFilename=Instalar_Alertas_Tempranas
SetupIconFile=assets\app.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\release\AlertasTempranas\*"; DestDir: "{app}"; Excludes: "notifications_config.json,meta_whatsapp_config.json"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent
