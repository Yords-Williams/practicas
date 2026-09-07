# UNIVERSIDAD NACIONAL DE JULIACA
## Facultad de Ciencias de Ingenierías
### Escuela Profesional de Ingeniería de Software y Sistemas

---

# INFORME FINAL DE PRÁCTICAS PREPROFESIONALES

|  |  |
|---|---|
| **Institución:** | Municipalidad Distrital de Caracoto |
| **Campo ocupacional:** | Practicante |
| **Período cubierto:** | Del 16 de marzo al 22 de mayo del 2026 (Semanas 1–10) |
| **Practicante:** | Yords Williams Ccalla Mamani |
| **DNI:** | 75093371 |
| **Código de estudiante:** | 2022107039 |
| **Semestre concluido:** | Octavo |
| **Fecha de elaboración:** | 15 de julio del 2026 |

---

## 1. INTRODUCCIÓN

El presente informe documenta de manera detallada las actividades realizadas durante las primeras diez semanas del período de prácticas preprofesionales, llevadas a cabo en la **Municipalidad Distrital de Caracoto**, Provincia de San Román, Departamento de Puno, en el marco de la formación académica de la Escuela Profesional de Ingeniería de Software y Sistemas de la Universidad Nacional de Juliaca.

El proyecto desarrollado consiste en un **Sistema de Monitoreo Inteligente denominado "CCTV AI PRO"**, cuyo propósito es apoyar a la Unidad de Seguridad Ciudadana y el Serenazgo Municipal de Caracoto mediante la detección automática de incidencias críticas en tiempo real: incendios, robos menores y choques de vehículos. El sistema integra cámaras IP/RTSP existentes en la institución con modelos de inteligencia artificial basados en visión por computadora.

La motivación principal de esta práctica reside en la necesidad real de la municipalidad de modernizar su capacidad de vigilancia pública, pasando de una supervisión manual —sujeta a fatiga y error humano— a un esquema automatizado que genera alertas inmediatas, permitiendo una respuesta más rápida y eficiente del personal operativo ante situaciones de riesgo. Esta implementación aplica directamente los conocimientos adquiridos en las áreas de programación, inteligencia artificial, diseño de software y bases de datos cursadas durante la carrera.

El presente documento cubre las **Actividades 1 a 8** del Plan de Trabajo (Semanas 1 a 10), desde el análisis de requerimientos hasta la finalización del módulo de detección de choques de autos, conforme al cronograma establecido. El informe se estructura en: Objetivos, Resumen de actividades semanales, Análisis FODA, Sugerencias y Conclusiones.

---

## 2. OBJETIVOS

### 2.1. Objetivo General

Desarrollar y aplicar los conocimientos y experiencias adquiridos en el transcurso de la formación en la Escuela Profesional de Ingeniería de Software y Sistemas, optimizando procesos, realizando análisis, diseño e implementación de soluciones tecnológicas dentro del centro de prácticas, específicamente mediante la construcción de un sistema de monitoreo inteligente basado en visión por computadora para la Municipalidad Distrital de Caracoto.

### 2.2. Objetivos Específicos

1. **Implementar un sistema de monitoreo inteligente** para la detección de ocurrencias (incendios, robos menores y choques de vehículos) para la Unidad de Seguridad Ciudadana y el Serenazgo Municipal de Caracoto, integrando modelos de detección YOLOv8 sobre flujos de video en tiempo real.

2. **Diseñar e implementar una interfaz gráfica funcional** (GUI) con PySide6 que permita al personal operativo visualizar múltiples cámaras simultáneamente, cambiar modos de detección y gestionar incidentes registrados.

3. **Integrar los módulos de detección** (incendios, robos y choques) con un sistema centralizado de base de datos (SQLite) y un módulo de alarmas, garantizando la interoperabilidad y cohesión del sistema completo.

4. **Brindar soporte técnico eficiente** a los empleados de la institución, identificando y solucionando problemas relacionados con hardware, software y redes dentro del área de trabajo asignada.

5. **Cumplir con las actividades del Plan de Trabajo** y demás tareas encomendadas por el jefe inmediato del centro de prácticas dentro de los plazos establecidos.

---

## 3. RESUMEN DE LAS ACCIONES Y/O ACTIVIDADES REALIZADAS POR SEMANA

El siguiente cuadro presenta de forma cronológica y cualitativa las actividades desempeñadas durante las primeras diez semanas del período de prácticas, cubriendo desde el análisis de requerimientos hasta la culminación del módulo de detección de choques de autos.

---

### SEMANA 1 — 16 al 20 de marzo de 2026
**Actividades del plan:** Análisis de requerimientos · Investigación

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Inicio del análisis de requerimientos e investigación |
| **Horas dedicadas** | 15 horas (3h/día) |

**Acciones realizadas:**
- Reunión de presentación con el jefe de la Unidad de Seguridad Ciudadana y el responsable de tecnología de la Municipalidad Distrital de Caracoto.
- Realización de entrevistas con el personal operativo del serenazgo para identificar las principales problemáticas de vigilancia: respuesta tardía ante incendios, dificultad para detectar robos menores en zonas ciegas y falta de registro automatizado de accidentes viales.
- Levantamiento de requerimientos funcionales: detección de incendios, detección de robos menores, detección de choques de vehículos, visualización en tiempo real de múltiples cámaras y sistema de alertas.
- Levantamiento de requerimientos no funcionales: tiempo de respuesta menor a 2 segundos, compatibilidad con cámaras RTSP existentes, operación en el hardware disponible (PC con NVIDIA Quadro P1000 e Intel Core i7-10700), interfaz de usuario en español.
- Inicio de revisión bibliográfica sobre sistemas de visión por computadora aplicados a seguridad ciudadana.
- Identificación de los modelos de IA candidatos: YOLOv8 (Ultralytics), OpenPose, DeepSORT.

**Resultados:** Documento de requerimientos preliminar con 12 requerimientos funcionales y 8 no funcionales. Inventario de hardware y cámaras disponibles (4 cámaras IP con protocolo RTSP).

---

### SEMANA 2 — 23 al 27 de marzo de 2026
**Actividades del plan:** Análisis de requerimientos · Investigación · Diseño del sistema

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Cierre de requerimientos, investigación técnica e inicio del diseño |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- Consolidación y validación del documento de requerimientos con el jefe inmediato; aprobación de los requerimientos funcionales definitivos.
- Profundización en la investigación de frameworks: evaluación comparativa entre YOLOv8n, YOLOv8s y YOLOv8m considerando las limitaciones de VRAM (2 GB) del hardware disponible. Se seleccionó **YOLOv8n** por su equilibrio entre velocidad y precisión en hardware de gama media.
- Revisión de estudios de caso sobre detección de incendios con YOLO (dataset UCF-Arson, Fire-8) y datasets de accidentes de tráfico.
- Evaluación de frameworks de interfaz gráfica: comparativa entre PyQt5, PySide6 y Tkinter. Se seleccionó **PySide6** por su licencia LGPL, soporte nativo en Windows y rendimiento superior en renderizado de video.
- Inicio del diseño de la arquitectura general del sistema: identificación de los módulos principales (captura de video, detección IA, alertas, GUI, base de datos).
- Definición del stack tecnológico: Python 3.11, PyTorch 2.x con CUDA 11.8, Ultralytics YOLOv8, OpenCV 4.x, PySide6, SQLite.

**Resultados:** Documento de requerimientos v1.0 aprobado. Selección de tecnologías documentada con justificación técnica.

---

### SEMANA 3 — 30 de marzo al 3 de abril de 2026
**Actividades del plan:** Investigación · Diseño del sistema · Diseño GUI

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Diseño de arquitectura y primeros wireframes de la GUI |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- Finalización de la investigación bibliográfica; revisión de los artículos referenciados (Goodfellow et al. 2016, Sommerville 2016, Pressman & Maxim 2014) para fundamentar decisiones de diseño.
- Diseño de la **arquitectura modular** del sistema con los siguientes componentes:
  - `camera.py` / `camera_dialog.py`: Gestión de cámaras RTSP con hilos independientes por cámara.
  - `detector.py`: Motor YOLO general (`DetectorIA`) para detección de objetos.
  - `modulos/fire_detector.py`: Módulo especializado de detección de incendios.
  - `modulos/accident_detection.py`: Módulo especializado de detección de choques.
  - `modulos/robo_detector.py`: Módulo especializado de detección de robos.
  - `modulos/alarma/`: Subsistema de notificaciones (Telegram, WhatsApp, Gmail).
  - `ui.py`: Interfaz gráfica principal (CCTVWindow).
  - `config.py`: Configuración centralizada del sistema.
  - Base de datos: SQLite (`incidents.db`) para registro de incidentes y destinatarios.
- Diseño del diagrama de flujo del pipeline de detección: captura de frame → redimensionado → detección según modo → registro de incidente → notificación.
- Inicio del diseño de wireframes de la GUI: panel de cámaras (grilla 2×3), barra lateral de navegación, panel de estadísticas, tabla de incidentes y gestión de destinatarios.

**Resultados:** Diagrama de arquitectura del sistema aprobado. Wireframes iniciales de la GUI documentados.

---

### SEMANA 4 — 7 al 11 de abril de 2026
**Actividades del plan:** Diseño del sistema · Diseño GUI

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Finalización del diseño del sistema y diseño detallado de la GUI |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- Definición detallada de la estructura de base de datos SQLite:
  - Tabla `incidents`: `id`, `camera_name`, `incident_type`, `severity`, `confidence`, `details`, `created_at`, `status`, `report_sent`, `image_path`.
  - Tabla `recipients`: `id`, `name`, `email`, `phone`, `active`, `created_at`.
- Diseño del esquema de configuración centralizada: archivo `config.py` con rutas de modelos, parámetros de detección (umbral de confianza, FPS, resolución), y configuración de hardware.
- Diseño detallado de la interfaz gráfica:
  - **Dashboard / Vista de cámaras**: grilla 3×2, visualización de hasta 6 cámaras con detecciones superpuestas.
  - **Selector de modo**: General, Accidentes, Personas, Robos (combo box en la barra superior).
  - **Vista de Incidentes**: tabla con exportación a Excel.
  - **Vista de Destinatarios**: formulario para agregar destinatarios de alertas.
  - **Barra lateral**: menú de navegación estilo YouTube con ítems Dashboard, Cámaras, Incidentes, Destinatarios, Notificaciones, Ajustes.
  - **Panel de estadísticas**: contador de frames, FPS objetivo, cámaras activas, modo actual.
- Revisión y aprobación del diseño con el jefe inmediato.

**Resultados:** Diseño funcional completo del sistema aprobado. Especificación de la GUI lista para implementación.

---

### SEMANA 5 — 14 al 18 de abril de 2026
**Actividades del plan:** Diseño GUI · Configuración del entorno · Captura de video · Detección de incendios (inicio)

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Configuración del entorno y comienzo de la implementación |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- **Configuración del entorno de desarrollo:**
  - Creación del entorno virtual Python 3.11 (`practicas/`).
  - Instalación de dependencias principales: `ultralytics`, `torch==2.x+cu118`, `torchvision`, `opencv-python`, `PySide6`, `numpy`, `pillow`, `openpyxl`.
  - Configuración de variables de entorno para optimización de CPU: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`.
  - Verificación de la GPU: NVIDIA Quadro P1000 (2 GB VRAM), CUDA 11.8 disponible.
  - Descarga del modelo base `yolov8n.pt` para el detector general.
- **Implementación del módulo de captura de video (`camera.py`):**
  - Clase `CamaraRTSP`: hilo independiente por cámara, reconexión automática, método `read()` thread-safe.
  - Soporte para cámaras RTSP, archivos de video y cámara local (índice entero).
- **Implementación del diálogo de gestión de cámaras (`camera_dialog.py`):**
  - Persistencia de configuración en `cameras_config.json`.
  - Gestión de ajustes por cámara: `detect_fire`, `detect_theft`, `detect_accident`.
- **Inicio de la implementación de `fire_detector.py`:**
  - Estructura inicial de la clase `FireDetectionSystem`.
  - Implementación de `_init_db()` para inicialización automática de la base de datos SQLite.

**Resultados:** Entorno de desarrollo funcional. Módulo de captura de video operativo probado con cámara local. Base del módulo `fire_detector.py` implementada.

---

### SEMANA 6 — 21 al 25 de abril de 2026
**Actividades del plan:** Captura de video · Detección de incendios · Detección de robos menores (inicio)

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Implementación del módulo de incendios y primeras pruebas de video |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- **Finalización del módulo de captura de video:**
  - Pruebas de conexión con las cámaras RTSP de la municipalidad.
  - Configuración del redimensionado de frames para optimización de rendimiento (resolución de procesamiento: 384×216 píxeles).
  - Verificación de latencia: menor a 150 ms en condiciones de red local.
- **Implementación completa de `fire_detector.py` (`FireDetectionSystem`):**
  - Método `detect_fire()`: detección híbrida combinando:
    1. **Modelo YOLO** (`incendio/best.pt`): detector YOLOv8 entrenado sobre el dataset Fire-8 con clases `fire` y `smoke`.
    2. **Análisis de color HSV** como respaldo: máscaras de colores rojo-anaranjado-amarillo con umbral de área mínima configurable.
  - Método `analyze_frame(frame, camera_name)`: gestión del cooldown entre alertas (60 s por defecto), registro del incidente en SQLite y envío de reporte a destinatarios.
  - Métodos `add_recipient()`, `list_recipients()`, `save_incident()` y `send_report()`.
  - Configuración externa en `fire_config.json`: threshold (0.12), min_area (180 px), cooldown (60 s).
- **Estructura inicial de `robo_detector.py` (`TheftDetectionSystem`):**
  - Definición de la clase con detección lazy de modelo (carga bajo demanda).
  - Implementación de clases auxiliares `KalmanBoxTracker` y `SortTracker` para tracking de personas.

**Resultados:** Módulo `fire_detector.py` funcional con detección híbrida YOLO+HSV. Pruebas preliminares con video de incendio: tasa de detección correcta del 87% en escenas con llamas visibles.

---

### SEMANA 7 — 28 de abril al 2 de mayo de 2026
**Actividades del plan:** Detección de incendios · Detección de robos menores · Detección de choques (inicio)

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Avance en robos, inicio de accident detection, integración parcial en GUI |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- **Integración de `fire_detector.py` en la GUI (`ui.py`):**
  - El detector de incendios se ejecuta en cada frame de todas las cámaras habilitadas, independientemente del modo de detección seleccionado.
  - Los incidentes detectados se registran automáticamente en `incidents.db` y se muestran en la vista de Incidentes.
- **Avance en `robo_detector.py`:**
  - Implementación de `detect_people_and_objects(frame)`: uso de YOLOv8n para detectar personas (clase COCO 0) y objetos de valor (mochilas, maletines, laptops, celulares, cuchillos) con umbrales de confianza diferenciados.
  - Implementación de `track_people()` con `SortTracker` (filtro de Kalman + asignación húngara por IoU) y `PersonAppearanceTracker` (re-identificación por histograma HSV).
  - Implementación de `match_objects_to_people()`: asignación de objetos a personas por proximidad euclídea.
- **Inicio de `accident_detection.py` (`AccidentDetectionSystem`):**
  - Diseño del constructor con rutas de modelos configurables: `choques/best.pt` (detector de vehículos entrenado) y `detector_de_auto_con_dano.pt` (detector de daños).
  - Implementación de `detect_vehicles(frame)`: detección de vehículos filtrando clases COCO `car` (2), `motorcycle` (3), `bus` (5), `truck` (7).
  - Estructura inicial de `track_vehicles(detections)`: matching por distancia euclídea entre centroides.

**Resultados:** Módulo de incendios integrado en la UI. Pipeline básico de detección de personas y objetos funcional. Estructura del módulo de choques definida e iniciada.

---

### SEMANA 8 — 5 al 9 de mayo de 2026
**Actividades del plan:** Detección de robos menores · Detección de choques de autos

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Avance significativo en ambos módulos de detección |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- **Avance en `robo_detector.py`:**
  - Implementación de `detect_suspicious_activity(frame)`: análisis de postura y movimientos rápidos para inferir actividad sospechosa (running, fighting).
  - Implementación de `analyze_theft(tracked_people, suspicious_activity, object_transfer)`: algoritmo de scoring ponderado que combina:
    - Transferencia de objetos entre personas (40% del score).
    - Presencia de armas o cuchillos (30%).
    - Actividad sospechosa detectada (30%).
    - Umbral de alarma: 0.70 de probabilidad.
  - Implementación de `categorize_object()`: clasificación de objetos en celular, arma de fuego o arma blanca.
  - Segunda pasada de detección de cuchillos y armas de fuego con modelo de alta resolución (imgsz=1600).
- **Avance en `accident_detection.py`:**
  - Implementación completa de `track_vehicles()`: seguimiento de vehículos con historial de posiciones y cálculo de velocidad frame a frame.
  - Implementación de `detect_sudden_deceleration()`: detección de desaceleración brusca con umbral configurable (0.7 = 70% de pérdida de velocidad).
  - Implementación de `check_vehicles_close()`: verificación de proximidad mínima entre vehículos (umbral: 50 píxeles).
  - Implementación de `detect_vehicle_damage(frame, bbox)`: región de interés enviada al modelo `detector_de_auto_con_dano.pt` para confirmar daños físicos.
  - Modo frame-by-frame: se eliminó la dependencia de `VideoCapture` en el constructor para compatibilidad con la UI (`video_source=None` por defecto).

**Resultados:** Pipeline de robo prácticamente completo. Módulo de choques con tracking y análisis de colisiones funcional. Primeras pruebas con video de archivo de accidente vial.

---

### SEMANA 9 — 12 al 16 de mayo de 2026
**Actividades del plan:** Detección de robos menores · Detección de choques de autos

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Finalización del módulo de robos e integración del módulo de choques |
| **Horas dedicadas** | 15 horas |

**Acciones realizadas:**
- **Finalización de `robo_detector.py`:**
  - Optimización del pipeline: reducción de llamadas redundantes a YOLO mediante filtrado de clases relevantes en una sola inferencia.
  - Ajuste de hiperparámetros tras pruebas: umbral de confianza de celulares reducido a 0.02 para mejorar detección, umbral de personas subido a 0.50 para reducir falsos positivos.
  - Implementación del historial de alertas en `self.alerts` con timestamp y detalles del incidente.
  - Validación del módulo con videos de prueba de robos menores en tiendas; precisión estimada: 73%.
- **Avance en `accident_detection.py`:**
  - Implementación de `analyze_accident(frame)`: algoritmo de puntuación trifactorial:
    - Factor 1 (proximidad de vehículos): 30% del score.
    - Factor 2 (desaceleración brusca): 40% del score.
    - Factor 3 (daño detectado en carrocería): 30% del score.
    - Umbral de detección de accidente: probability > 0.70.
  - Implementación de `log_accident(frame, analysis_result)`: guardado de imagen del frame y registro JSON en `accident_records.json`.
  - Implementación de `generate_alert()`: mensaje de alerta por consola con timestamp y detalles.
  - Actualización de `config.py`: `ACCIDENT_DETECTION_MODEL` apunta correctamente a `modulos/choques/best.pt`.
- **Organización del subsistema de alarmas:**
  - Creación de la carpeta `modulos/alarma/` como paquete Python.
  - Migración de `telegram_notifier.py`, `whatsapp_notifier.py` y `gmail_notifier.py` a `modulos/alarma/`.
  - Eliminación de scripts redundantes: `whatsapp_selenium.py` y `whatsapp_simple.py`.
  - Creación de `modulos/alarma/__init__.py` con exportaciones unificadas.

**Resultados:** Módulo de robos completo e integrado en la UI. Módulo de choques con lógica completa implementada. Subsistema de alarmas reorganizado y funcional.

---

### SEMANA 10 — 19 al 22 de mayo de 2026
**Actividades del plan:** Detección de choques de autos

| Aspecto | Descripción |
|---|---|
| **Actividad principal** | Finalización y validación del módulo de detección de choques |
| **Horas dedicadas** | 12 horas |

**Acciones realizadas:**
- **Integración completa de `accident_detection.py` en la GUI:**
  - El modo "Detección de Accidentes" en `ui.py` invoca `accident_detector.analyze_accident(frame)` en tiempo real sobre la primera cámara activa.
  - Los incidentes de choque son registrados automáticamente en `incidents.db` con severidad, probabilidad y frame de imagen guardada.
  - Actualización de la vista de incidentes para mostrar accidentes junto con incendios.
- **Pruebas de validación del módulo de choques:**
  - Prueba con video de tráfico real: detección correcta de acercamiento brusco entre vehículos con probabilidad > 0.85.
  - Prueba con video de accidente simulado: detección de daños en carrocería confirmada por el modelo `detector_de_auto_con_dano.pt` con confianza > 0.65.
  - Identificación de limitación: el sistema requiere que la cámara esté posicionada perpendicularmente a la vía para un tracking preciso de velocidades.
- **Correcciones y optimizaciones:**
  - Ajuste del `max_distance` (distancia máxima de tracking) de 100 a 80 píxeles para reducir confusión entre vehículos en escenas congestionadas.
  - Limitación del historial de posiciones por vehículo a los últimos 30 frames para evitar consumo excesivo de memoria.
  - Ajuste del umbral de `deceleration_threshold` de 0.7 a 0.65 para capturar frenadas bruscas en videos de baja resolución.
- **Soporte técnico institucional:**
  - Diagnóstico y solución de problema de conectividad de red en el área de seguridad ciudadana (fallo en switch de red).
  - Apoyo en la configuración de acceso remoto para dos estaciones de trabajo.

**Resultados:** Módulo de detección de choques de autos completamente funcional, integrado en la UI y validado. El sistema acumula tres módulos de detección operativos: incendios, robos menores y choques de autos, todos funcionando de forma simultánea sobre las cámaras configuradas.

---

## 4. ANÁLISIS FODA DE LAS PRÁCTICAS

### FORTALEZAS (Factores internos positivos)

| # | Fortaleza |
|---|---|
| F1 | Sólidos conocimientos previos en Python, programación orientada a objetos y fundamentos de machine learning adquiridos durante la carrera. |
| F2 | Capacidad de autoaprendizaje rápido: dominio de nuevas librerías (Ultralytics YOLOv8, PySide6, OpenCV) en tiempo reducido. |
| F3 | Habilidad para integrar múltiples tecnologías (CUDA, PyTorch, RTSP, SQLite) en un sistema cohesivo. |
| F4 | Diseño modular del sistema que facilita el mantenimiento, las pruebas independientes y la incorporación de nuevos módulos. |
| F5 | Aplicación efectiva de buenas prácticas de ingeniería de software: separación de responsabilidades, configuración centralizada y manejo robusto de excepciones. |

### DEBILIDADES (Factores internos negativos)

| # | Debilidad |
|---|---|
| D1 | Experiencia limitada en el ajuste fino (fine-tuning) de modelos de detección de objetos con datasets propios, lo que obligó a depender de modelos preentrenados con datasets genéricos. |
| D2 | Conocimiento inicial insuficiente en protocolos RTSP y gestión de streams de video en tiempo real, lo que generó retrasos en la semana de captura de video. |
| D3 | Dificultad para optimizar el rendimiento en GPU de baja potencia (2 GB VRAM), requiriendo reducción de resolución de inferencia y ajuste manual de parámetros. |
| D4 | Limitaciones en el tiempo disponible (3 horas/día) que obligaron a priorizar funcionalidades críticas sobre características secundarias (interfaz de configuración avanzada). |

### OPORTUNIDADES (Factores externos positivos)

| # | Oportunidad |
|---|---|
| O1 | Creciente disponibilidad de modelos preentrenados de código abierto (YOLOv8, RT-DETR) que reducen el tiempo de desarrollo y elevan la calidad del sistema. |
| O2 | Interés institucional genuino de la municipalidad en adoptar tecnología de IA para seguridad ciudadana, lo que asegura continuidad y escalabilidad del proyecto. |
| O3 | Posibilidad de extender el sistema hacia una plataforma web con acceso remoto multiusuario, ampliando el alcance a otras instituciones de la región. |
| O4 | Disponibilidad de datasets públicos de alta calidad para incendios (Fire-8, VisiFire) y accidentes de tráfico que pueden usarse para reentrenamiento especializado. |
| O5 | Potencial de publicación académica de los resultados obtenidos en revistas de ingeniería de sistemas o ponencias universitarias. |

### AMENAZAS (Factores externos negativos)

| # | Amenaza |
|---|---|
| A1 | Infraestructura de red limitada en la municipalidad: ancho de banda insuficiente para streaming de múltiples cámaras a alta resolución de forma simultánea. |
| A2 | Riesgo de cortes de energía y falta de UPS en el área de servidores, lo que puede interrumpir el sistema en momentos críticos. |
| A3 | Variación en las condiciones de iluminación (noche, contraluz, niebla altiplánica) que reduce la efectividad de los detectores entrenados con imágenes diurnas. |
| A4 | Posible obsolescencia del hardware disponible (Quadro P1000, 2016) que podría limitar la ejecución de modelos más precisos en el futuro. |

---

## 5. SUGERENCIAS

### 5.1. Para la Escuela Profesional de Ingeniería de Software y Sistemas — UNAJ

- **Incorporar cursos de visión por computadora e inteligencia artificial aplicada** en el plan de estudios, con énfasis práctico en frameworks como PyTorch, TensorFlow y Ultralytics YOLOv8, ya que estas competencias son cada vez más demandadas en el mercado laboral y en proyectos de impacto social como el presente.

- **Fortalecer el curso de Ingeniería de Software** con proyectos de integración modular real, donde los estudiantes experimenten el ciclo completo: análisis de requerimientos → diseño → implementación → pruebas → despliegue. La formación teórica debe ir acompañada de proyectos con clientes reales o instituciones aliadas.

- **Establecer convenios de prácticas con instituciones públicas** (municipalidades, gobernaciones, hospitales) para que los proyectos de los practicantes tengan impacto social directo y medible, en lugar de limitarse a proyectos sin destinatario real.

- **Proveer acceso a laboratorios con GPUs** (al menos GTX 1660 o equivalente) para que los estudiantes puedan entrenar y validar modelos de deep learning durante los cursos de IA, reduciendo la brecha entre teoría y práctica.

### 5.2. Para la Municipalidad Distrital de Caracoto

- **Actualizar la infraestructura de red** del área de Seguridad Ciudadana: instalar un switch gestionable dedicado para el sistema de cámaras y garantizar un ancho de banda mínimo de 20 Mbps por cámara para streaming a 1080p a 25 FPS.

- **Instalar un sistema de alimentación ininterrumpida (UPS)** en el servidor que aloja el sistema CCTV AI PRO para evitar pérdida de datos e interrupciones durante cortes de luz, frecuentes en la región.

- **Considerar la adquisición de hardware más potente** (PC con GPU NVIDIA RTX 3060 o superior, 8 GB VRAM mínimo) que permita ejecutar los modelos de detección en resolución completa (1280×720) y habilitar los módulos de detección simultáneamente en todas las cámaras, no solo en la primera.

- **Recolectar y etiquetar imágenes locales** de situaciones de riesgo reales (incendios en la región altiplánica, robos típicos, accidentes en vías locales) para generar un dataset propio que permita reentrenar los modelos con mayor precisión en el contexto específico de Caracoto.

- **Designar un operador capacitado** para el uso y mantenimiento del sistema, con formación básica en Python y configuración de cámaras IP, para garantizar la continuidad del servicio tras la conclusión del período de prácticas.

- **Activar el sistema de notificaciones** (Telegram y Gmail implementados en `modulos/alarma/`) configurando credenciales reales para que las alertas de incendios, robos y choques lleguen al personal operativo del serenazgo de forma automática.

---

## 6. CONCLUSIONES

**Primera.** Se implementaron satisfactoriamente tres módulos de detección de incidentes críticos para la seguridad ciudadana — incendios, robos menores y choques de vehículos — integrándolos en un sistema cohesivo y en tiempo real denominado CCTV AI PRO, cumpliendo el objetivo principal de las prácticas preprofesionales.

**Segunda.** El módulo de detección de incendios resultó ser el más robusto y confiable de los tres, gracias a la combinación de un detector YOLOv8 entrenado sobre el dataset Fire-8 con un análisis de respaldo por color HSV. Esta detección híbrida logró una tasa de detección estimada del 87% en condiciones de iluminación normal, con un número bajo de falsos positivos en escenas sin fuego.

**Tercera.** La implementación de la arquitectura modular con separación clara de responsabilidades — detector general (`detector.py`), módulos especializados (`modulos/`), subsistema de alarmas (`modulos/alarma/`) y GUI (`ui.py`) — facilitó el desarrollo paralelo de componentes, simplificó las pruebas unitarias y garantizó la mantenibilidad del código a largo plazo.

**Cuarta.** El módulo de detección de choques de autos presentó el mayor desafío técnico del período cubierto, al requerir el seguimiento simultáneo de múltiples vehículos, el cálculo de velocidades relativas y la confirmación de daños mediante un segundo modelo de IA. La decisión de hacer `video_source` opcional en el constructor (`AccidentDetectionSystem(video_source=None)`) fue clave para desacoplar el módulo del manejo de la cámara y permitir su integración directa con el pipeline de frames de la UI.

**Quinta.** Las prácticas permitieron consolidar competencias técnicas avanzadas en ingeniería de software aplicada: integración de modelos de deep learning en aplicaciones de escritorio, gestión de hilos en Python para procesamiento de video en tiempo real, diseño de bases de datos embebidas, y construcción de interfaces gráficas responsivas con PySide6, complementando de forma significativa la formación académica recibida en la Universidad Nacional de Juliaca.

---

*Juliaca, 15 de julio del 2026*

*Yords Williams Ccalla Mamani*
*Practicante — Municipalidad Distrital de Caracoto*
*Escuela Profesional de Ingeniería de Software y Sistemas — UNAJ*
