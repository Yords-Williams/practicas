# build_exe.ps1
# Compila AlertasTempranas en una carpeta distribuible usando PyInstaller 6.x
# Ejecutar desde la raíz del proyecto:  .\build_exe.ps1

Set-Location $PSScriptRoot

$PYTHON = ".\.venv\Scripts\python.exe"
if (!(Test-Path $PYTHON)) {
    $PYTHON = ".\venv\Scripts\python.exe"
}
$DIST   = "dist\release\AlertasTempranas"
$DISTPATH = "dist\release"
$SPEC   = "Alertas tempranas.spec"
$OVMODEL = "yolov8n_openvino_model"
$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$INSTALLER = "dist\instalador\Instalar_Alertas_Tempranas.exe"

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  BUILD — Alertas Tempranas"                            -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

if (!(Test-Path $PYTHON)) {
    Write-Host "[ERROR] No se encontró Python en .venv ni en venv. Activa o crea el entorno virtual del proyecto." -ForegroundColor Red
    exit 1
}

if (!(Test-Path $ISCC)) {
    $ISCC_COMMAND = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($ISCC_COMMAND) {
        $ISCC = $ISCC_COMMAND.Source
    } else {
        Write-Host "[ERROR] No se encontró ISCC.exe de Inno Setup 6." -ForegroundColor Red
        exit 1
    }
}

if (!(Test-Path "yolov8n.pt")) {
    Write-Host "[ERROR] Falta yolov8n.pt, requerido para detección. No se puede crear el instalador." -ForegroundColor Red
    exit 1
}

# ── 0. Asegurar __init__.py en modulos/ (namespace package) ──────────────────
if (!(Test-Path "modulos\__init__.py")) {
    "" | Out-File -FilePath "modulos\__init__.py" -Encoding utf8
    Write-Host "[OK] Creado modulos\__init__.py" -ForegroundColor Green
}

# ── 1. Limpiar builds anteriores ─────────────────────────────────────────────
Write-Host "`n[1/4] Limpiando builds anteriores..." -ForegroundColor Yellow
if (Test-Path $DIST) { Remove-Item $DIST -Recurse -Force }
if (Test-Path "build\AlertasTempranas") { Remove-Item "build\AlertasTempranas" -Recurse -Force }

# ── 2. Exportar el modelo para la GPU Intel ──────────────────────────────────
Write-Host "`n[2/5] Preparando modelo OpenVINO para Intel UHD..." -ForegroundColor Yellow
if (!(Test-Path "$OVMODEL\yolov8n.xml")) {
    & $PYTHON -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='openvino', imgsz=384)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] No se pudo exportar el modelo OpenVINO." -ForegroundColor Red
        exit 1
    }
}

# ── 3. Compilar con PyInstaller ───────────────────────────────────────────────
Write-Host "`n[3/5] Compilando con PyInstaller (esto tarda 5-15 min)..." -ForegroundColor Yellow
$env:PYTHONIOENCODING = 'utf-8'
& $PYTHON -m PyInstaller $SPEC --noconfirm --clean --distpath $DISTPATH

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] PyInstaller falló. Revisa los mensajes anteriores." -ForegroundColor Red
    exit 1
}

if (!(Test-Path "$DIST\AlertasTempranas.exe")) {
    Write-Host "`n[ERROR] PyInstaller terminó, pero no se encontró $DIST\AlertasTempranas.exe." -ForegroundColor Red
    exit 1
}

# ── 4. Copiar archivos de datos editables al destino ─────────────────────────
Write-Host "`n[4/5] Copiando archivos de configuración..." -ForegroundColor Yellow

# cameras_config.json de ejemplo (vacío) — el usuario configura sus cámaras
@"
[]
"@ | Out-File -FilePath "$DIST\cameras_config.json" -Encoding utf8 -Force

# Copiar configs con valores por defecto si existen
foreach ($f in @("fire_config.json")) {
    if (Test-Path $f) {
        Copy-Item $f "$DIST\$f" -Force
        Write-Host "  Copiado: $f"
    }
}

# ── 5. Crear README de instalación ───────────────────────────────────────────
Write-Host "`n[5/5] Creando README de instalación..." -ForegroundColor Yellow
@"
ALERTAS TEMPRANAS — Instalación
================================

REQUISITOS DE LA PC DE DESTINO:
  • Windows 10/11 (64 bits)
  • Driver Intel UHD 630 actualizado (OpenVINO para la GPU integrada)
  • Driver NVIDIA actualizado (respaldo CUDA para GPU Quadro P1000)
    Descargar en: https://www.nvidia.com/Download/index.aspx
  • Visual C++ Redistributable 2022 (si no está instalado)
    Descargar en: https://aka.ms/vs/17/release/vc_redist.x64.exe

INSTALACIÓN:
  1. Ejecuta Instalar_Alertas_Tempranas.exe y completa el asistente.
  2. Instala los drivers Intel/NVIDIA y el VC++ Redistributable si es necesario.
  3. Abre Alertas Tempranas desde el acceso directo creado.
  4. Para desinstalar, usa Configuración de Windows > Aplicaciones o el acceso
     directo de desinstalación del menú Inicio.

CONFIGURACIÓN DE CÁMARAS:
  • Al abrir la app por primera vez, ve a Gestionar Cámaras y agrega las
    cámaras RTSP de la institución (rtsp://admin:pass@192.168.18.x:554/…).
  • La configuración, destinatarios y base de datos se guardan en:
    %LOCALAPPDATA%\Alertas Tempranas Videovigilancia
  • Las credenciales configuradas en Notificaciones se protegen con DPAPI
    de Windows para el usuario actual; no se incluyen en el instalador.
  • En Notificaciones, elige Por defecto o Manual por canal y activa el canal.
    Si faltan credenciales para ese perfil, se solicitan una vez y se guardan
    cifradas para la cuenta de Windows actual. Los destinatarios se administran
    en la página Destinatarios y se asignan a Por defecto o Manual.

PRIMER ARRANQUE:
  • La app usa primero OpenVINO en la GPU Intel UHD; si no está disponible,
    usa CUDA en la Quadro y finalmente CPU.
  • La primera vez puede tardar 30-60 s mientras carga los modelos de IA.
  • Si las cámaras no conectan, verifica que la PC esté en la red 192.168.18.x.

SOPORTE:
  • Desarrollado por: Yords Williams Ccalla Mamani
  • Institución: Municipalidad Distrital de Caracoto — Serenazgo Municipal
"@ | Out-File -FilePath "$DIST\LEEME_INSTALACION.txt" -Encoding utf8

# ── 6. Crear instalador y desinstalador con Inno Setup ────────────────────────
Write-Host "`n[6/6] Compilando instalador de Inno Setup..." -ForegroundColor Yellow
& $ISCC /Qp "Alertas.iss"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Inno Setup no pudo compilar el instalador." -ForegroundColor Red
    exit 1
}
if (!(Test-Path $INSTALLER)) {
    Write-Host "`n[ERROR] No se encontró el instalador generado: $INSTALLER." -ForegroundColor Red
    exit 1
}

# ── Resumen ───────────────────────────────────────────────────────────────────
$size = (Get-ChildItem $DIST -Recurse | Measure-Object -Property Length -Sum).Sum
$sizeMB = [math]::Round($size / 1MB, 0)
$installerSizeMB = [math]::Round((Get-Item $INSTALLER).Length / 1MB, 0)

Write-Host "`n======================================================" -ForegroundColor Cyan
Write-Host "  BUILD E INSTALADOR COMPLETADOS" -ForegroundColor Green
Write-Host "  Carpeta de la aplicacion: $DIST ($sizeMB MB)"
Write-Host "  Instalador: $INSTALLER ($installerSizeMB MB)"
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "`nDistribuye '$INSTALLER'. Incluye instalacion y desinstalacion desde Windows.`n"
