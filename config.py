"""
Configuración centralizada para CCTV AI PRO
Optimizada para: NVIDIA Quadro P1000 + Intel Core i7-10700
"""

import os

# Directorios
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULOS_DIR = os.path.join(WORKSPACE_DIR, "modulos")
BUILD_DIR = os.path.join(WORKSPACE_DIR, "build")

# Modelos YOLO principales
YOLO_GENERAL_MODEL = os.path.join(WORKSPACE_DIR, "yolov8n.pt")

# Modelos especializados en modulos/
ACCIDENT_DETECTION_MODEL = os.path.join(MODULOS_DIR, "best.pt")
DAMAGE_DETECTION_MODEL = os.path.join(MODULOS_DIR, "detector_de_auto_con_dano.pt")

# Verificar disponibilidad de modelos
AVAILABLE_MODELS = {
    "general": os.path.exists(YOLO_GENERAL_MODEL),
    "accident": os.path.exists(ACCIDENT_DETECTION_MODEL),
    "damage": os.path.exists(DAMAGE_DETECTION_MODEL),
}

# Módulos Python especializados
ACCIDENT_DETECTION_MODULE = os.path.join(MODULOS_DIR, "accident_detection.py")
PERSON_IDENTIFIER_MODULE = os.path.join(MODULOS_DIR, "person_identifier.py")
ROBO_DETECTOR_MODULE = os.path.join(MODULOS_DIR, "robo_detector.py")

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
# OPTIMIZACIONES PARA NVIDIA QUADRO P1000 + i7-10700
# ============================================================================

# Hardware detectado
HARDWARE = {
    "gpu": "NVIDIA Quadro P1000 (2GB VRAM)",
    "cpu": "Intel Core i7-10700 (8 cores/16 threads)",
    "vram": 2000,  # MB
    "cpu_cores": 8,
}

# Parámetros de detección optimizados
DETECTION_CONFIG = {
    "confidence_threshold": 0.45,           # Balance velocidad/precisión
    "device": 0,                            # GPU: 0 (CUDA), CPU: "cpu"
    "device_type": "cuda",                  # "cuda" o "cpu"
    "fps_limit": 25,                        # 25 FPS para Quadro P1000
    "frame_resize": (384, 216),             # Optimizado (16:9, divisible por 32)
    "batch_size": 1,                        # Quadro P1000 con 2GB: procesar de a 1
    "workers": 4,                           # CPU workers (mitad de cores)
    "half_precision": True,                 # FP16 para acelerar GPU
    "iou_threshold": 0.45,                  # IoU para NMS
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
    "max_capture_threads": 6,               # Máximo 6 cámaras simultáneas
    "detector_threads": 1,                  # 1 thread para detector (GPU)
    "enable_async": True,                   # Captura asíncrona
}

# Optimizaciones para CPU
CPU_OPTIMIZATION = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "2",                 # Usar 2 threads (no todos los 8)
    "MKL_NUM_THREADS": "2",
    "MKL_DYNAMIC": "FALSE",
    "OMP_DYNAMIC": "FALSE",
    "OMP_WAIT_POLICY": "PASSIVE",
    "OMP_PLACES": "cores(2)",
}

def print_config():
    """Imprimir configuración actual"""
    print("=" * 70)
    print("CCTV AI PRO - CONFIGURACIÓN OPTIMIZADA")
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

