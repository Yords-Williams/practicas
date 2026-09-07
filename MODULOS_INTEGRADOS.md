# CCTV AI PRO - Sistema Integrado

Sistema de vigilancia con detección de IA usando múltiples modelos especializados.

## 📁 Estructura de Módulos

### Módulos Principales
- `main.py` - Punto de entrada de la aplicación
- `detector.py` - Clase DetectorIA para detecciones generales (YOLOv8n)
- `camera.py` - Clase CamaraRTSP para captura de video
- `ui.py` - Interfaz gráfica con PySide6
- `style.py` - Estilos CSS para la interfaz
- `config.py` - Configuración centralizada de modelos y parámetros

### Módulos Especializados (en carpeta `modulos/`)

#### 1. **Detección de Accidentes** (`accident_detection.py`)
- Clase: `AccidentDetectionSystem`
- Modelos: 
  - `best.pt` - Modelo YOLO para detección de vehículos
  - `detector_de_auto_con_dano.pt` - Modelo para detección de daños
- Funcionalidades:
  - Tracking de vehículos
  - Detección de colisiones
  - Análisis de velocidad y aceleración

#### 2. **Rastreador de Personas** (`person_identifier.py`)
- Clase: `PersonAppearanceTracker`
- Funcionalidades:
  - Re-identificación de personas por apariencia
  - Tracking basado en histograma de color HSV
  - Emparejamiento de detecciones con distancia espacial
  - Gestión de IDs persistentes

#### 3. **Detección de Robos** (`robo_detector.py`)
- Clases:
  - `KalmanBoxTracker` - Tracker con filtro de Kalman
  - `SortTracker` - Sistema SORT para tracking robusto
  - `TheftDetectionSystem` - Detección de actividades sospechosas
- Funcionalidades:
  - Detección de armas y objetos peligrosos
  - Tracking de personas con comportamiento sospechoso
  - Alertas en tiempo real

## 🚀 Cómo Usar

### Configuración Inicial

1. **Editar `config.py`** para agregar URLs de cámaras RTSP:
```python
CAMERAS_CONFIG = [
    {
        "url": "rtsp://usuario:contraseña@192.168.1.100:554/stream",
        "name": "Cámara Entrada"
    },
]
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3. **Ejecutar la aplicación**:
```bash
python main.py
```

### Cambiar Modo de Detección

En la interfaz gráfica, usa el selector de "Modo" en la barra superior:
- 🎯 **Detección General** - YOLOv8n estándar
- 🚗 **Detección de Accidentes** - Tracking de vehículos y colisiones
- 👤 **Rastreo de Personas** - Re-identificación y tracking
- 🚨 **Detección de Robos** - Alertas por actividades sospechosas

## 📊 Estadísticas

La aplicación muestra en tiempo real:
- Número de frames procesados
- Modo de detección activo
- Cámaras conectadas
- Detecciones encontradas

## 🔧 Parámetros Ajustables

Edita `config.py` para modificar:
- Umbrales de confianza
- Distancias de tracking
- Dispositivo (CPU/GPU)
- FPS objetivo
- Tamaño de frames

## 📝 Notas Técnicas

- Los modelos `.pt` se cargan automáticamente desde `modulos/`
- Cada sistema de detección tiene su propio hilo de procesamiento
- La interfaz se actualiza a 30 FPS
- Las detecciones se registran en logs internos

## 🐛 Solución de Problemas

**Modelo no encontrado:**
```
✗ Verificar que los archivos .pt existan en modulos/
✗ Verificar permisos de lectura
```

**Bajo rendimiento:**
```
✗ Reducir resolución de cámara
✗ Usar GPU en lugar de CPU
✗ Disminuir confianza mínima
```

**Cámara desconectada:**
```
✗ Verificar URL RTSP
✗ Verificar credenciales
✗ Verificar conexión de red
```

## 📦 Requisitos

Ver `requirements.txt` para lista completa de dependencias.

Dependencias principales:
- OpenCV (cv2)
- PyTorch
- Ultralytics YOLO
- PySide6
- NumPy

---
**Versión:** 1.0
**Última actualización:** 2024
