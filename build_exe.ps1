# build_exe.ps1
# Compila AlertasTempranas en una carpeta distribuible usando PyInstaller 6.x
# Ejecutar desde la raíz del proyecto:  .\build_exe.ps1

Set-Location $PSScriptRoot

$PYTHON = ".\practicas\Scripts\python.exe"
$DIST   = "dist\AlertasTempranas"

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  BUILD — Alertas Tempranas"                            -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# ── 0. Asegurar __init__.py en modulos/ (namespace package) ──────────────────
if (!(Test-Path "modulos\__init__.py")) {
    "" | Out-File -FilePath "modulos\__init__.py" -Encoding utf8
    Write-Host "[OK] Creado modulos\__init__.py" -ForegroundColor Green
}

# ── 1. Limpiar builds anteriores ─────────────────────────────────────────────
Write-Host "`n[1/4] Limpiando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "dist\AlertasTempranas") { Remove-Item "dist\AlertasTempranas" -Recurse -Force }
if (Test-Path "build\AlertasTempranas") { Remove-Item "build\AlertasTempranas" -Recurse -Force }

# ── 2. Compilar con PyInstaller ───────────────────────────────────────────────
Write-Host "`n[2/4] Compilando con PyInstaller (esto tarda 5-15 min)..." -ForegroundColor Yellow
$env:PYTHONIOENCODING = 'utf-8'
& $PYTHON -m PyInstaller alertas_tempranas.spec --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] PyInstaller falló. Revisa los mensajes anteriores." -ForegroundColor Red
    exit 1
}

# ── 3. Copiar archivos de datos editables al destino ─────────────────────────
Write-Host "`n[3/4] Copiando archivos de configuración..." -ForegroundColor Yellow

# cameras_config.json de ejemplo (vacío) — el usuario configura sus cámaras
@"
[]
"@ | Out-File -FilePath "$DIST\cameras_config.json" -Encoding utf8 -Force

# Copiar configs con valores por defecto si existen
foreach ($f in @("fire_config.json","notifications_config.json")) {
    if (Test-Path $f) {
        Copy-Item $f "$DIST\$f" -Force
        Write-Host "  Copiado: $f"
    }
}

# ── 4. Crear README de instalación ───────────────────────────────────────────
Write-Host "`n[4/4] Creando README de instalación..." -ForegroundColor Yellow
@"
ALERTAS TEMPRANAS — Instalación
================================

REQUISITOS DE LA PC DE DESTINO:
  • Windows 10/11 (64 bits)
  • Driver NVIDIA actualizado (para GPU Quadro P1000)
    Descargar en: https://www.nvidia.com/Download/index.aspx
  • Visual C++ Redistributable 2022 (si no está instalado)
    Descargar en: https://aka.ms/vs/17/release/vc_redist.x64.exe

INSTALACIÓN:
  1. Copia toda esta carpeta "AlertasTempranas" a la PC de destino.
  2. Instala los drivers NVIDIA y el VC++ Redistributable si es necesario.
  3. Ejecuta AlertasTempranas.exe

CONFIGURACIÓN DE CÁMARAS:
  • Al abrir la app por primera vez, ve a Gestionar Cámaras y agrega las
    cámaras RTSP de la institución (rtsp://admin:pass@192.168.18.x:554/…).
  • La configuración se guarda en cameras_config.json (editable).

PRIMER ARRANQUE:
  • La primera vez puede tardar 30-60 s mientras carga los modelos de IA.
  • Si las cámaras no conectan, verifica que la PC esté en la red 192.168.18.x.

SOPORTE:
  • Desarrollado por: Yords Williams Ccalla Mamani
  • Institución: Municipalidad Distrital de Caracoto — Serenazgo Municipal
"@ | Out-File -FilePath "$DIST\LEEME_INSTALACION.txt" -Encoding utf8

# ── Resumen ───────────────────────────────────────────────────────────────────
$size = (Get-ChildItem $DIST -Recurse | Measure-Object -Property Length -Sum).Sum
$sizeMB = [math]::Round($size / 1MB, 0)

Write-Host "`n======================================================" -ForegroundColor Cyan
Write-Host "  BUILD COMPLETADO" -ForegroundColor Green
Write-Host "  Carpeta: $DIST"
Write-Host "  Tamanio: $sizeMB MB"
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "`nPara distribuir: comprime la carpeta '$DIST' en un ZIP."
Write-Host "El usuario solo necesita descomprimirla y ejecutar AlertasTempranas.exe`n"
