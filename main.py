import sys
import os
import cv2
from config import CPU_OPTIMIZATION, DETECTION_CONFIG
from PySide6.QtGui import QIcon

# Aplicar optimizaciones de CPU antes de importar librerías pesadas
for var, value in CPU_OPTIMIZATION.items():
    os.environ.setdefault(var, str(value))

# Limitar threads de OpenBLAS/PyTorch
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '2'
os.environ['MKL_NUM_THREADS'] = '2'

print("[BOOT] Optimizaciones de CPU aplicadas")
print(f"[BOOT] Threads OMP: {os.environ.get('OMP_NUM_THREADS', '?')}")
print(f"[BOOT] Threads MKL: {os.environ.get('MKL_NUM_THREADS', '?')}")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

def resource_path(relative_path: str) -> str:
    """Return absolute path to resource, works for dev and for PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)
from detector import DetectorIA
from camera import CamaraRTSP
from ui import CCTVWindow
from camera_dialog import CameraDialog
from modulos.accident_detection import AccidentDetectionSystem
from modulos.person_identifier import PersonAppearanceTracker
from modulos.robo_detector import TheftDetectionSystem
from modulos.fire_detector import FireDetectionSystem

def main():
    """Iniciar la aplicación CCTV AI PRO optimizada para Quadro P1000"""
    
    print("\n" + "="*70)
    print("CCTV AI PRO - SISTEMA OPTIMIZADO")
    print("Hardware: NVIDIA Quadro P1000 + Intel Core i7-10700")
    print("="*70 + "\n")
    
    # Cargar cámaras desde archivo JSON
    print("[MAIN] Cargando configuración de cámaras...")
    cameras_config = CameraDialog.get_cameras()
    
    # Crear instancias de cámaras
    CAMERAS = []
    for cam_config in cameras_config:
        try:
            cam = CamaraRTSP(cam_config["url"], cam_config["name"])
            # Attach camera-specific detection settings (with sensible defaults)
            cam.settings = {
                'detect_fire': cam_config.get('detect_fire', True),
                'detect_theft': cam_config.get('detect_theft', True),
                'detect_accident': cam_config.get('detect_accident', True)
            }
            CAMERAS.append(cam)
            print(f"[MAIN] ✓ Cámara agregada: {cam_config['name']}")
        except Exception as e:
            print(f"[MAIN] ✗ Error al agregar {cam_config['name']}: {e}")
    
    print(f"[MAIN] Total de cámaras cargadas: {len(CAMERAS)}")
    
    # Inicializar detector IA
    print("[MAIN] Inicializando detector IA...")
    detector = DetectorIA()
    
    # Calentar GPU
    try:
        detector.warmup()
    except Exception as e:
        print(f"[MAIN] Warmup: {e}")
    
    # Inicializar sistemas de detección especializados
    print("[MAIN] Inicializando sistemas de detección...")
    
    try:
        accident_detector = AccidentDetectionSystem()
        print("[MAIN] ✓ Sistema de detección de accidentes cargado")
    except Exception as e:
        print(f"[MAIN] ✗ Error al cargar detector de accidentes: {e}")
        accident_detector = None
    
    try:
        person_tracker = PersonAppearanceTracker()
        print("[MAIN] ✓ Rastreador de personas cargado")
    except Exception as e:
        print(f"[MAIN] ✗ Error al cargar rastreador de personas: {e}")
        person_tracker = None
    
    try:
        theft_detector = TheftDetectionSystem(video_source=0)
        print("[MAIN] ✓ Sistema de detección de robos cargado")
    except Exception as e:
        print(f"[MAIN] ✗ Error al cargar detector de robos: {e}")
        theft_detector = None

    try:
        fire_detector = FireDetectionSystem(db_path="incidents.db", config_file="fire_config.json")
        fire_detector.add_recipient("Administrador", "admin@example.com", "+1234567890")
        print("[MAIN] ✓ Sistema de detección de incendios cargado")
    except Exception as e:
        print(f"[MAIN] ✗ Error al cargar detector de incendios: {e}")
        fire_detector = None
    
    # Crear aplicación Qt y establecer nombre/icono
    print("[MAIN] Iniciando interfaz gráfica...")
    # Helper para ubicar recursos dentro del paquete o en desarrollo
    def resource_path(relative):
        if getattr(sys, 'frozen', False):
            return os.path.join(sys._MEIPASS, relative)
        return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative)

    app = QApplication(sys.argv)
    try:
        app.setApplicationName("Alertas tempranas")
        ico_path = resource_path('assets/app.ico')
        if not os.path.exists(ico_path):
            # fallback to png
            png_path = resource_path('assets/app.png')
            if os.path.exists(png_path):
                app.setWindowIcon(QIcon(png_path))
        else:
            app.setWindowIcon(QIcon(ico_path))
    except Exception as e:
        print(f"[MAIN] Warning setting app icon/name: {e}")
    # Nombre visible de la aplicación y icono
    app.setApplicationName("Alertas tempranas")
    icon_path = resource_path(os.path.join('assets', 'app.ico'))
    if os.path.exists(icon_path):
        try:
            app.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
    else:
        # fallback to png if .ico missing
        png_path = resource_path(os.path.join('assets', 'logo_64.png'))
        if os.path.exists(png_path):
            try:
                app.setWindowIcon(QIcon(png_path))
            except Exception:
                pass
    
    # Crear ventana principal con todos los sistemas
    window = CCTVWindow(CAMERAS, detector, accident_detector, person_tracker, theft_detector, fire_detector)
    window.show()
    
    print("[MAIN] ✓ Sistema CCTV AI PRO iniciado")
    print("\n💡 Configuración actual:")
    print(f"   Device: GPU {DETECTION_CONFIG['device']} (CUDA)")
    print(f"   Resolución: {DETECTION_CONFIG['frame_resize'][0]}x{DETECTION_CONFIG['frame_resize'][1]}")
    print(f"   FPS: {DETECTION_CONFIG['fps_limit']}")
    print(f"   Precisión: {'FP16' if DETECTION_CONFIG['half_precision'] else 'FP32'}")
    print(f"   Cámaras: {len(CAMERAS)}\n")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
