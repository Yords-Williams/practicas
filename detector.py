from ultralytics import YOLO
import torch
import cv2
import os
import sys
import numpy as np
from config import DETECTION_CONFIG, INFERENCE_CONFIG, YOLO_GENERAL_MODEL

class DetectorIA:
    """Detector YOLO optimizado para NVIDIA Quadro P1000 de 4 GB."""

    def __init__(self):
        print("[IA] Inicializando detector YOLO optimizado...")
        self.backend = "cpu"
        self.device = "cpu"
        self.half_precision = False
        if not os.path.isfile(YOLO_GENERAL_MODEL):
            raise FileNotFoundError(
                "No se encontró el modelo YOLO. Coloca 'modulos\\best.pt' "
                "o 'yolov8n.pt' junto al ejecutable."
            )
        trained_model = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "modulos", "best.pt"
        )
        if os.path.basename(YOLO_GENERAL_MODEL) == "yolov8n.pt" and not os.path.isfile(
            trained_model
        ):
            print(
                "[IA] Advertencia: modulos\\best.pt no está disponible; "
                "se usará yolov8n.pt."
            )

        # OpenVINO se intenta primero: descarga la inferencia a la Intel UHD.
        # El modelo IR se genera durante el build y viaja dentro del .exe.
        if INFERENCE_CONFIG['backend'] == 'openvino_gpu':
            self._try_openvino_gpu()

        if self.backend == 'cpu' and torch.cuda.is_available():
            print("[IA] OpenVINO no disponible; usando CUDA como respaldo")
            self.model = YOLO(YOLO_GENERAL_MODEL)
            self.device = DETECTION_CONFIG['device']
            self.backend = "cuda"
            self.half_precision = DETECTION_CONFIG['half_precision']
            gpu_name = torch.cuda.get_device_name(self.device)
            gpu_memory = torch.cuda.get_device_properties(self.device).total_memory / 1e9
            print(f"[IA] ✓ GPU: {gpu_name}")
            print(f"[IA] ✓ VRAM: {gpu_memory:.1f}GB")
            
            # Reservar margen para CUDA/OpenCV y los detectores especializados.
            # Evita errores OOM cuando el sistema atiende 12 cámaras.
            torch.cuda.set_per_process_memory_fraction(0.75)
            torch.cuda.empty_cache()
        elif self.backend == 'cpu':
            print("[IA] OpenVINO/CUDA no disponibles; usando CPU")
            self.model = YOLO(YOLO_GENERAL_MODEL)

        print(f"[IA] Motor activo: {self.backend}")
        print("[IA] Modelos disponibles en modulos/:")
        modulos_path = "modulos"
        if os.path.exists(modulos_path):
            for file in os.listdir(modulos_path):
                if file.endswith(".pt"):
                    print(f"  ✓ {file}")

    def _try_openvino_gpu(self):
        """Cargar el IR empaquetado solo si la GPU Intel está disponible."""
        try:
            from openvino import Core
            core = Core()
            devices = core.available_devices
            if not any(device.startswith("GPU") for device in devices):
                print("[IA] OpenVINO no detectó una GPU Intel")
                return

            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(base_dir, INFERENCE_CONFIG['openvino_model_dir'])
            if not os.path.isdir(model_dir):
                print(f"[IA] Modelo OpenVINO no incluido: {model_dir}")
                return

            self.model = YOLO(model_dir)
            self.device = INFERENCE_CONFIG['openvino_device']
            self.backend = "openvino_gpu"
            print(f"[IA] ✓ OpenVINO GPU activo: {core.get_property('GPU', 'FULL_DEVICE_NAME')}")
        except Exception as e:
            print(f"[IA] OpenVINO GPU no disponible: {e}")

    def predict(self, frame):
        """Predicción general con optimizaciones para Quadro P1000"""
        results = self.model(
            frame,
            conf=DETECTION_CONFIG['confidence_threshold'],
            device=self.device,
            verbose=False,
            half=self.half_precision,
            iou=DETECTION_CONFIG['iou_threshold'],
            imgsz=384,  # Tamaño optimizado
        )

        return results[0].plot()
    
    def predict_with_boxes(self, frame):
        """Predicción retornando boxes para uso en otros sistemas"""
        results = self.model(
            frame,
            conf=DETECTION_CONFIG['confidence_threshold'],
            device=self.device,
            verbose=False,
            half=self.half_precision,
            iou=DETECTION_CONFIG['iou_threshold'],
            imgsz=384,
        )
        
        if results:
            return results[0]
        return None
    
    def warmup(self):
        """Calentar GPU antes de uso (reduce primera latencia)"""
        print("[IA] Calentando GPU...")
        dummy_frame = np.zeros(
            (DETECTION_CONFIG['frame_resize'][1], DETECTION_CONFIG['frame_resize'][0], 3),
            dtype=np.uint8,
        )
        self.model(dummy_frame, device=self.device, verbose=False, half=self.half_precision)
        
        print("[IA] ✓ GPU lista")
