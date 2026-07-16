"""
Script de Benchmark - Medir rendimiento real
Ejecuta: python benchmark.py
"""

import cv2
import time
import numpy as np
import torch
from detector import DetectorIA
from config import DETECTION_CONFIG, HARDWARE

def test_gpu_memory():
    """Probar memoria GPU disponible"""
    print("\n" + "="*70)
    print("TEST 1: GPU MEMORY")
    print("="*70)
    
    if torch.cuda.is_available():
        device = torch.device('cuda:0')
        total = torch.cuda.get_device_properties(device).total_memory / 1e9
        allocated = torch.cuda.memory_allocated(device) / 1e9
        reserved = torch.cuda.memory_reserved(device) / 1e9
        
        print(f"GPU Memory Total: {total:.2f} GB")
        print(f"GPU Memory Allocated: {allocated:.2f} GB")
        print(f"GPU Memory Reserved: {reserved:.2f} GB")
        print(f"GPU Memory Free: {total - allocated:.2f} GB")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        
        return total
    else:
        print("✗ CUDA no disponible")
        return 0

def test_cpu_cores():
    """Probar uso de CPU"""
    print("\n" + "="*70)
    print("TEST 2: CPU INFO")
    print("="*70)
    
    import os
    
    print(f"CPU Cores: {os.cpu_count()}")
    print(f"OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS', 'Not set')}")
    print(f"MKL_NUM_THREADS: {os.environ.get('MKL_NUM_THREADS', 'Not set')}")
    print(f"OPENBLAS_NUM_THREADS: {os.environ.get('OPENBLAS_NUM_THREADS', 'Not set')}")

def test_detector_latency():
    """Probar latencia del detector"""
    print("\n" + "="*70)
    print("TEST 3: DETECTOR LATENCY (Quadro P1000)")
    print("="*70)
    
    detector = DetectorIA()
    
    # Crear frame de prueba
    dummy_frame = np.zeros((DETECTION_CONFIG['frame_resize'][1], 
                           DETECTION_CONFIG['frame_resize'][0], 3), dtype=np.uint8)
    
    # Warmup
    print("Calentando GPU...")
    for _ in range(3):
        detector.predict(dummy_frame)
    
    torch.cuda.synchronize()
    
    # Medición
    print("Midiendo latencia (100 inferencias)...")
    times = []
    
    for i in range(100):
        start = time.time()
        detector.predict(dummy_frame)
        if DETECTION_CONFIG['device_type'] == 'cuda':
            torch.cuda.synchronize()
        times.append(time.time() - start)
        
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/100", end='\r')
    
    print("\n")
    times = np.array(times)
    
    print(f"Latencia promedio: {np.mean(times)*1000:.2f} ms")
    print(f"Latencia mín: {np.min(times)*1000:.2f} ms")
    print(f"Latencia máx: {np.max(times)*1000:.2f} ms")
    print(f"Latencia std: {np.std(times)*1000:.2f} ms")
    print(f"FPS: {1/np.mean(times):.1f} FPS")
    
    # Cálculo de frames esperados
    expected_fps = DETECTION_CONFIG['fps_limit']
    ms_per_frame = 1000 / expected_fps
    print(f"\nObjetivo: {expected_fps} FPS ({ms_per_frame:.1f} ms/frame)")
    print(f"Margen: {ms_per_frame - np.mean(times)*1000:.2f} ms disponible")

def test_camera_capture():
    """Probar captura de cámara"""
    print("\n" + "="*70)
    print("TEST 4: CAMERA CAPTURE (Fallback)")
    print("="*70)
    
    # Intentar abrir webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("✗ No hay cámara disponible")
        return
    
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    print("Capturando 30 frames...")
    times = []
    
    for i in range(30):
        start = time.time()
        ret, frame = cap.read()
        elapsed = time.time() - start
        times.append(elapsed)
        
        if not ret:
            print("✗ Error en captura")
            break
    
    cap.release()
    
    times = np.array(times)
    print(f"\nLatencia de captura promedio: {np.mean(times)*1000:.2f} ms")
    print(f"FPS real: {1/np.mean(times):.1f} FPS")

def test_memory_usage():
    """Probar uso de memoria"""
    print("\n" + "="*70)
    print("TEST 5: MEMORY USAGE")
    print("="*70)
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    
    print(f"Memoria RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
    print(f"Memoria VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
    
    # GPU memory
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        print(f"GPU Memory Allocated: {allocated:.2f} GB")
        print(f"GPU Memory Reserved: {reserved:.2f} GB")

def run_full_benchmark():
    """Ejecutar benchmark completo"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  Alertas Tempranas - BENCHMARK - Quadro P1000 + i7-10700".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    print(f"\nHardware Detectado:")
    print(f"  GPU: {HARDWARE['gpu']}")
    print(f"  CPU: {HARDWARE['cpu']}")
    print(f"  VRAM: {HARDWARE['vram']}MB")
    
    test_gpu_memory()
    test_cpu_cores()
    test_detector_latency()
    # test_camera_capture()  # Comentado porque requiere cámara
    test_memory_usage()
    
    print("\n" + "="*70)
    print("BENCHMARK COMPLETADO")
    print("="*70 + "\n")
    
    # Recomendaciones
    print("💡 RECOMENDACIONES:")
    print("\nPara 1-2 cámaras: Usar configuración actual (Excelente)")
    print("Para 3-4 cámaras: Reducir FPS a 20, considerar FP16")
    print("Para 5+ cámaras: Reducir resolución a 320x180, FPS a 15")
    
    print("\nEdita config.py para ajustar:")
    print("  - DETECTION_CONFIG['fps_limit']")
    print("  - DETECTION_CONFIG['frame_resize']")
    print("  - DETECTION_CONFIG['half_precision']")
    
    print("\n📊 Para monitoreo en tiempo real, ejecuta en otra terminal:")
    print("  nvidia-smi -l 1")
    
if __name__ == "__main__":
    try:
        run_full_benchmark()
    except Exception as e:
        print(f"\n✗ Error en benchmark: {e}")
        import traceback
        traceback.print_exc()
