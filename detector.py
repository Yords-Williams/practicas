from ultralytics import YOLO
import torch
import cv2
import os
from config import DETECTION_CONFIG

class DetectorIA:
    """Detector YOLO optimizado para NVIDIA Quadro P1000"""

    def __init__(self):
        print("[IA] Inicializando detector YOLO optimizado...")
        print(f"[IA] GPU: {DETECTION_CONFIG['device_type'].upper()}")
        
        # Cargar modelo
        print("[IA] Cargando YOLOv8n...")
        self.model = YOLO("yolov8n.pt")
        
        # Configurar dispositivo
        if DETECTION_CONFIG['device_type'] == 'cuda' and torch.cuda.is_available():
            self.device = DETECTION_CONFIG['device']
            gpu_name = torch.cuda.get_device_name(self.device)
            gpu_memory = torch.cuda.get_device_properties(self.device).total_memory / 1e9
            print(f"[IA] ✓ GPU: {gpu_name}")
            print(f"[IA] ✓ VRAM: {gpu_memory:.1f}GB")
            
            # Optimizaciones CUDA para Quadro P1000
            torch.cuda.set_per_process_memory_fraction(0.8)  # Usar 80% VRAM
            torch.cuda.empty_cache()
        else:
            self.device = "cpu"
            print("[IA] ✓ CPU mode (CUDA no disponible)")
        
        # Mostrar modelos en modulos/
        print("[IA] Modelos disponibles en modulos/:")
        modulos_path = "modulos"
        if os.path.exists(modulos_path):
            for file in os.listdir(modulos_path):
                if file.endswith(".pt"):
                    print(f"  ✓ {file}")

    def predict(self, frame):
        """Predicción general con optimizaciones para Quadro P1000"""
        results = self.model(
            frame,
            conf=DETECTION_CONFIG['confidence_threshold'],
            device=self.device,
            verbose=False,
            half=DETECTION_CONFIG['half_precision'],  # FP16 mode
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
            half=DETECTION_CONFIG['half_precision'],
            iou=DETECTION_CONFIG['iou_threshold'],
            imgsz=384,
        )
        
        if results:
            return results[0]
        return None
    
    def warmup(self):
        """Calentar GPU antes de uso (reduce primera latencia)"""
        print("[IA] Calentando GPU...")
        dummy_input = torch.zeros(1, 3, 384, 384)
        if DETECTION_CONFIG['device_type'] == 'cuda':
            dummy_input = dummy_input.cuda()
        
        with torch.no_grad():
            self.model(dummy_input, verbose=False)
        
        print("[IA] ✓ GPU lista")