"""
Configuración centralizada para CCTV AI PRO
Optimizada para: NVIDIA Quadro P1000 4 GB + Intel Core i7-10700 (12 cámaras)
"""

import os

# Directorios
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULOS_DIR = os.path.join(WORKSPACE_DIR, "modulos")
BUILD_DIR = os.path.join(WORKSPACE_DIR, "build")

# Un único modelo YOLO para todos los módulos de detección. En una instalación
# distribuida puede no existir el modelo entrenado, así que se usa el modelo
# base incluido como respaldo.
_TRAINED_MODEL = os.path.join(MODULOS_DIR, "best.pt")
_BASE_MODEL = os.path.join(WORKSPACE_DIR, "yolov8n.pt")
DETECTION_MODEL = (
    _TRAINED_MODEL if os.path.exists(_TRAINED_MODEL) else _BASE_MODEL
)
YOLO_GENERAL_MODEL = DETECTION_MODEL
ACCIDENT_DETECTION_MODEL = DETECTION_MODEL
FIRE_DETECTION_MODEL = DETECTION_MODEL
DAMAGE_DETECTION_MODEL = DETECTION_MODEL

# Verificar disponibilidad de modelos
AVAILABLE_MODELS = {
    "general": os.path.exists(YOLO_GENERAL_MODEL),
    "accident": os.path.exists(ACCIDENT_DETECTION_MODEL),
    "damage": os.path.exists(DAMAGE_DETECTION_MODEL),
    "fire": os.path.exists(FIRE_DETECTION_MODEL),
}

# Módulos Python especializados
ACCIDENT_DETECTION_MODULE = os.path.join(MODULOS_DIR, "choques", "detector.py")
PERSON_IDENTIFIER_MODULE  = os.path.join(MODULOS_DIR, "person_identifier.py")
ROBO_INFERENCE_MODULE     = os.path.join(MODULOS_DIR, "robo", "inference.py")
FIRE_DETECTION_MODULE     = os.path.join(MODULOS_DIR, "incendio", "detector.py")

# Configuración de cámaras RTSP (edita con tus URLs)
CAMERAS_CONFIG = [
    # {
    #     "url": "rtsp://usuario:contraseña@192.168.1.100:554/stream",
    #     "name": "Cámara Entrada"
    # },
    # {
    #     "url": "rtsp://usuario:contraseña@192.168.1.101:554/stream",
    #     "name": "Cámara Parqueo"
    # },
]

# ============================================================================
# PERFIL PARA NVIDIA QUADRO P1000 4 GB + i7-10700 / 12 CÁMARAS
# ============================================================================

# Hardware detectado
HARDWARE = {
    "gpu": "NVIDIA Quadro P1000 (4GB VRAM)",
    "cpu": "Intel Core i7-10700 (8 cores/16 threads)",
    "vram": 4096,  # MB
    "cpu_cores": 8,
}

# Parámetros de detección optimizados
DETECTION_CONFIG = {
    "confidence_threshold": 0.45,           # Balance velocidad/precisión
    "device": 0,                            # GPU: 0 (CUDA), CPU: "cpu"
    "device_type": "cuda",                  # "cuda" o "cpu"
    # La vista y captura se mantienen a 10 FPS; el trabajador IA muestrea
    # hasta 4 frames/s por cámara, sujeto al rendimiento real del equipo.
    "fps_limit": 10,
    "frame_resize": (384, 216),             # Optimizado (16:9, divisible por 32)
    "batch_size": 1,                        # Inferencia serial: evita picos de VRAM
    "workers": 4,                           # CPU workers (mitad de cores)
    "half_precision": True,                 # FP16 para acelerar GPU
    "iou_threshold": 0.45,                  # IoU para NMS
    "analysis_fps_per_camera": 4,            # Meta; puede bajar si la inferencia no alcanza
}

# Motor de inferencia distribuible. OpenVINO usa la Intel UHD 630 mediante
# `intel:gpu`; si en otra PC no hay driver Intel/OpenVINO, se usa CUDA y luego
# CPU de manera automática. El modelo OpenVINO se incluye en el ejecutable.
INFERENCE_CONFIG = {
    "backend": "openvino_gpu",
    "openvino_device": "intel:gpu",
    "fallback_order": ("cuda", "cpu"),
    "openvino_model_dir": "yolov8n_openvino_model",
}

# Parámetros de captura de video optimizados
CAPTURE_CONFIG = {
    "buffer_size": 1,                       # Mínimo buffer (menos latencia)
    "read_timeout": 5000,                   # 5 segundos timeout
    "reconnect_attempts": 3,                # Intentos de reconexión
    "reconnect_delay": 2,                   # Segundos entre reconexiones
}

# Parámetros de accidentes
ACCIDENT_CONFIG = {
    "confidence_threshold": 0.4,
    "alert_cooldown_seconds": 60,
    "vehicle_classes": [2, 3, 5, 7],       # COCO: car, motorcycle, bus, truck
    "max_distance": 50,
    "deceleration_threshold": 0.7,
    "use_gpu": True,
    "track_batch_size": 1,
}

# Parámetros de rastreo de personas
PERSON_TRACKING_CONFIG = {
    "max_age": 12,
    "distance_threshold": 120,
    "appearance_threshold": 0.75,
    "compute_every_n_frames": 2,           # Procesar descriptor cada 2 frames
}

# Parámetros de detección de robos
THEFT_DETECTION_CONFIG = {
    "confidence_threshold": 0.5,
    "track_max_age": 30,
    "use_gpu": True,
    "batch_size": 1,
}

# Threading y paralelismo
THREADING_CONFIG = {
    "max_cameras": 12,                      # Límite total de fuentes configurables
    "grid_columns": 3,                      # Mosaico 4 × 3 con panel lateral
    "max_capture_threads": 12,              # Un hilo ligero de captura por cámara
    "detector_threads": 1,                  # 1 thread para detector (GPU)
    "enable_async": True,                   # Captura asíncrona
}

# Optimizaciones para CPU
CPU_OPTIMIZATION = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "4",
    "MKL_NUM_THREADS": "4",
    "MKL_DYNAMIC": "FALSE",
    "OMP_DYNAMIC": "FALSE",
    "OMP_WAIT_POLICY": "PASSIVE",
    "OMP_PLACES": "cores(4)",
}

def print_config():
    """Imprimir configuración actual"""
    print("=" * 70)
    print("Alertas Tempranas - CONFIGURACIÓN OPTIMIZADA")
    print("=" * 70)
    print("\n📊 HARDWARE DETECTADO:")
    print(f"  GPU: {HARDWARE['gpu']}")
    print(f"  CPU: {HARDWARE['cpu']}")
    print(f"  VRAM: {HARDWARE['vram']}MB")
    
    print("\n⚙️ CONFIGURACIÓN ACTUAL:")
    print(f"  Dispositivo: GPU {DETECTION_CONFIG['device']} (CUDA)")
    print(f"  Resolución: {DETECTION_CONFIG['frame_resize'][0]}x{DETECTION_CONFIG['frame_resize'][1]}")
    print(f"  FPS objetivo: {DETECTION_CONFIG['fps_limit']}")
    print(f"  Batch size: {DETECTION_CONFIG['batch_size']}")
    print(f"  Precisión: {'FP16 (rápido)' if DETECTION_CONFIG['half_precision'] else 'FP32 (preciso)'}")
    print(f"  Cámaras máx: {THREADING_CONFIG['max_capture_threads']}")
    
    print("\n📁 MODELOS DISPONIBLES:")
    for model_name, available in AVAILABLE_MODELS.items():
        status = "✓" if available else "✗"
        print(f"  {status} {model_name}")
    
    print(f"\n📍 CÁMARAS CONFIGURADAS: {len(CAMERAS_CONFIG)}")
    print("=" * 70)

if __name__ == "__main__":
    print_config()
