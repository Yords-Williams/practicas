# Alertas Tempranas — Sistema de Vigilancia Inteligente

Sistema de monitoreo en tiempo real para el **Serenazgo Municipal de la Municipalidad Distrital de Caracoto**. Detecta automáticamente incendios, accidentes vehiculares y robos mediante modelos YOLOv8 sobre cámaras RTSP, archivos de video y cámaras locales.

> Desarrollado por **Yords Williams Ccalla Mamani** — Prácticas Preprofesionales UNAJ (mar–jul 2026)

---

## Características

| Módulo | Descripción | Modelo |
|---|---|---|
| 🔥 Incendios | Detección híbrida YOLO + HSV | YOLOv8s (Fire-8 dataset, 25 epochs) |
| 🚗 Choques | Scoring por proximidad + deceleración + daño | YOLOv8n fine-tuned |
| 🚨 Robos | Anomaly detection (STEAD-tiny) | ROC-AUC 88.87% |
| 📷 Cámaras | RTSP, cámara local (USB/webcam) y archivo de video | — |
| 🔔 Alertas | Telegram Bot y Gmail con foto del incidente | — |

---

## Requisitos

### Hardware
- **GPU:** NVIDIA (recomendado Quadro P1000 o superior, Compute Capability ≥ 6.1)
- **RAM:** 8 GB mínimo (16 GB recomendado)
- **Almacenamiento:** 5 GB libres

### Software
- Python **3.11** (64-bit)
- Driver NVIDIA **≥ 522.06** (para CUDA 12.x)
- Windows 10/11 (64-bit)

---

## Instalación rápida

```powershell
# 1. Clonar el repositorio
git clone https://github.com/Yords-Williams/practicas.git
cd practicas

# 2. Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar cámaras (copiar ejemplo y editar)
Copy-Item cameras_config.json.example cameras_config.json
# Editar cameras_config.json con las IPs y credenciales reales

# 5. Ejecutar
python main.py
```

---

## Estructura del proyecto

```
practicas/
├── main.py                      # Punto de entrada
├── ui.py                        # Interfaz gráfica PySide6
├── camera.py                    # Captura RTSP / local / archivo
├── camera_dialog.py             # Diálogo de gestión de cámaras
├── detector.py                  # Motor YOLOv8 general
├── config.py                    # Configuración centralizada
├── style.py                     # Estilos visuales
├── notifications.py             # Sistema de notificaciones
│
├── modulos/
│   ├── incendio/
│   │   ├── detector.py          # FireDetectionSystem (YOLO + HSV)
│   │   └── best.pt              # Modelo entrenado
│   ├── choques/
│   │   ├── detector.py          # AccidentDetectionSystem
│   │   └── best.pt              # Modelo entrenado
│   ├── robo/
│   │   ├── inference.py         # TheftDetectionSystem (STEAD-tiny)
│   │   ├── test.py              # Evaluación ROC-AUC / PR-AUC
│   │   └── best.pkl             # Modelo entrenado
│   ├── alarma/
│   │   ├── telegram_notifier.py # Notificaciones Telegram
│   │   └── gmail_notifier.py    # Notificaciones Gmail
│   └── person_identifier.py    # Rastreo de personas
│
├── scripts/
│   ├── generar_informe_v4.py    # Genera informe de prácticas (.docx)
│   ├── generar_manual_v2.py     # Genera manual de usuario (.docx)
│   └── generar_reporte_tests.py # Genera reporte de pruebas (.docx)
│
├── assets/
│   ├── app.ico                  # Icono de la aplicación
│   └── app.png                  # Logo
│
├── docs/
│   └── MANUAL_USUARIO_v2.docx  # Manual de usuario completo
│
├── alertas_tempranas.spec       # Especificación PyInstaller
├── build_exe.ps1                # Script de compilación a .exe
├── requirements.txt             # Dependencias Python
└── cameras_config.json.example  # Ejemplo de configuración de cámaras
```

---

## Configuración de cámaras

Edita `cameras_config.json` con las IPs del sistema de cámaras de la institución:

```json
[
  {
    "name": "Cámara Entrada",
    "url": "rtsp://admin:Caracoto2025@192.168.18.200:554/Streaming/Channels/101",
    "source_type": "rtsp",
    "detect_fire": true,
    "detect_theft": true,
    "detect_accident": true
  }
]
```

**Tipos de fuente soportados:**

| `source_type` | Formato de `url` | Ejemplo |
|---|---|---|
| `rtsp` | `rtsp://user:pass@ip:554/...` | Cámara IP institucional |
| `local` | `0`, `1`, `local:0` | Webcam USB del servidor |
| `file` | `C:\videos\grabacion.mp4` | Archivo de video para pruebas |

---

## Configuración de notificaciones

Edita `notifications_config.json`:

```json
{
  "telegram": {
    "enabled": true,
    "token": "TU_BOT_TOKEN",
    "chat_ids": ["TU_CHAT_ID"]
  },
  "gmail": {
    "enabled": true,
    "sender": "alerta@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "to_emails": ["jefe@municipalidad.gob.pe"]
  }
}
```

---

## Generar ejecutable (.exe)

Para distribuir a otras PCs sin Python instalado:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\build_exe.ps1
```

El resultado se genera en `dist\AlertasTempranas\`. Comprimir en `.zip` y copiar a la PC de destino.

**Requisitos en PC de destino:** Windows 10/11 + Driver NVIDIA ≥ 522.06

---

## Pruebas automatizadas

```powershell
$env:PYTHONIOENCODING = 'utf-8'
.\venv\Scripts\python.exe -m pytest test_integration.py -v
# 70 passed in 23.37s
```

---

## Documentación

- 📖 [Manual de Usuario](docs/MANUAL_USUARIO_v2.docx) — Guía completa de operación

---

## Tecnologías

![Python](https://img.shields.io/badge/Python-3.11-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.11+cu128-orange)
![YOLOv8](https://img.shields.io/badge/YOLOv8-ultralytics-green)
![PySide6](https://img.shields.io/badge/PySide6-6.11-teal)
![CUDA](https://img.shields.io/badge/CUDA-12.8-76B900?logo=nvidia)

---

## Licencia

Proyecto de prácticas preprofesionales — Universidad Nacional de Juliaca (UNAJ), 2026.
