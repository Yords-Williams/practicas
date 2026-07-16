# -*- mode: python ; coding: utf-8 -*-
# alertas_tempranas.spec
# PyInstaller 6.x — bundle completo con PyTorch CUDA, PySide6 y modelos YOLOv8
#
# Uso:
#   .\practicas\Scripts\python.exe -m PyInstaller alertas_tempranas.spec --noconfirm
# O directamente con el script:
#   .\build_exe.ps1

import os, sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ROOT = os.path.abspath('.')

# ── Recopilar librerías pesadas ───────────────────────────────────────────────
torch_d, torch_b, torch_h = collect_all('torch')
ultralytics_d, ultralytics_b, ultralytics_h = collect_all('ultralytics')
pyside6_d, pyside6_b, pyside6_h = collect_all('PySide6')
cv2_d, cv2_b, cv2_h = collect_all('cv2')

# ── Archivos de datos propios del proyecto ────────────────────────────────────
own_datas = [
    # Modelos de IA
    ('modulos/incendio/best.pt',          'modulos/incendio'),
    ('modulos/choques/best.pt',           'modulos/choques'),
    ('modulos/robo/best.pkl',             'modulos/robo'),
    ('modulos/best.pt',                   'modulos'),
    ('modulos/detector_de_auto_con_dano.pt', 'modulos'),
    ('yolov8n.pt',                        '.'),
    # Configuraciones JSON
    ('cameras_config.json',               '.'),
    ('fire_config.json',                  '.'),
    ('notifications_config.json',         '.'),
    # Assets / icono
    ('assets/app.ico',                    'assets'),
    ('assets/app.png',                    'assets'),
]

# ── Hidden imports del proyecto ───────────────────────────────────────────────
project_hidden = [
    'detector', 'camera', 'ui', 'camera_dialog', 'config', 'style',
    'modulos.incendio.detector',
    'modulos.choques.detector',
    'modulos.robo.inference',
    'modulos.person_identifier',
    'modulos.alarma.gmail_notifier',
    'modulos.alarma.telegram_notifier',
    'modulos.alarma.whatsapp_notifier',
    'psutil', 'pynvml', 'sqlite3',
    'email.mime.text', 'email.mime.multipart', 'email.mime.base',
    'smtplib', 'requests',
]

a = Analysis(
    ['main.py'],
    pathex=[ROOT],
    binaries=torch_b + ultralytics_b + pyside6_b + cv2_b,
    datas=own_datas + torch_d + ultralytics_d + pyside6_d + cv2_d,
    hiddenimports=project_hidden + torch_h + ultralytics_h + pyside6_h + cv2_h
                  + collect_submodules('modulos'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', '_tkinter', 'matplotlib.tests', 'numpy.tests',
        'scipy', 'pandas', 'IPython', 'notebook', 'jupyter',
        'PIL.ImageTk',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AlertasTempranas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # UPX puede romper DLLs de CUDA — mejor desactivado
    console=False,    # sin ventana de consola negra al abrir
    icon='assets/app.ico',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='AlertasTempranas',
)
