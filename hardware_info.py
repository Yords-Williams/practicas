"""
Script para mostrar información detallada del hardware
Ejecuta: python hardware_info.py
"""

import torch
import psutil
import os
import platform

def print_header(text):
    """Imprimir encabezado"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + text.center(68) + "║")
    print("╚" + "="*68 + "╝")

def print_section(title):
    """Imprimir sección"""
    print("\n" + "─" * 70)
    print(f"  {title}")
    print("─" * 70)

def get_gpu_info():
    """Obtener información de GPU"""
    print_section("NVIDIA GPU")
    
    if not torch.cuda.is_available():
        print("✗ CUDA no disponible")
        return False
    
    print(f"✓ CUDA Available: True")
    print(f"✓ CUDA Version: {torch.version.cuda}")
    print(f"✓ cuDNN Version: {torch.backends.cudnn.version()}")
    
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"\n  GPU {i}: {props.name}")
        print(f"    Compute Capability: {props.major}.{props.minor}")
        print(f"    Total Memory: {props.total_memory / 1e9:.2f} GB")
        print(f"    Multi-Processor Count: {props.multi_processor_count}")
        
        # Memory info
        allocated = torch.cuda.memory_allocated(i) / 1e9
        reserved = torch.cuda.memory_reserved(i) / 1e9
        total = props.total_memory / 1e9
        
        print(f"\n  Memory Status:")
        print(f"    Total: {total:.2f} GB")
        print(f"    Allocated: {allocated:.2f} GB")
        print(f"    Reserved: {reserved:.2f} GB")
        print(f"    Free: {total - allocated:.2f} GB")
    
    return True

def get_cpu_info():
    """Obtener información de CPU"""
    print_section("CPU")
    
    print(f"✓ Processor: {platform.processor()}")
    print(f"✓ CPU Cores: {os.cpu_count()}")
    print(f"✓ Physical Cores: {psutil.cpu_count(logical=False)}")
    
    # Frecuencia
    freq = psutil.cpu_freq()
    print(f"✓ CPU Frequency: {freq.current:.2f} MHz")
    print(f"  - Base: {freq.min:.2f} MHz")
    print(f"  - Max: {freq.max:.2f} MHz")
    
    # Uso
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"✓ CPU Usage: {cpu_percent:.1f}%")
    
    # Por core
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    print(f"✓ Usage per Core:")
    for i, usage in enumerate(per_core):
        print(f"    Core {i}: {usage:.1f}%")

def get_memory_info():
    """Obtener información de memoria"""
    print_section("MEMORY (RAM)")
    
    memory = psutil.virtual_memory()
    print(f"✓ Total: {memory.total / 1024**3:.2f} GB")
    print(f"✓ Available: {memory.available / 1024**3:.2f} GB")
    print(f"✓ Used: {memory.used / 1024**3:.2f} GB ({memory.percent:.1f}%)")
    print(f"✓ Free: {memory.free / 1024**3:.2f} GB")
    
    # Swap
    swap = psutil.swap_memory()
    print(f"\n✓ Swap Memory:")
    print(f"    Total: {swap.total / 1024**3:.2f} GB")
    print(f"    Used: {swap.used / 1024**3:.2f} GB ({swap.percent:.1f}%)")
    print(f"    Free: {swap.free / 1024**3:.2f} GB")

def get_system_info():
    """Obtener información del sistema"""
    print_section("SYSTEM")
    
    print(f"✓ Operating System: {platform.system()} {platform.release()}")
    print(f"✓ Platform: {platform.platform()}")
    print(f"✓ Python Version: {platform.python_version()}")
    print(f"✓ PyTorch Version: {torch.__version__}")
    
    # PyTorch backends
    print(f"\n✓ PyTorch Backends:")
    print(f"    CUDA Enabled: {torch.cuda.is_available()}")
    print(f"    cuDNN Enabled: {torch.backends.cudnn.enabled}")
    print(f"    CPU Threads: {torch.get_num_threads()}")

def get_environment_vars():
    """Obtener variables de entorno optimizadas"""
    print_section("ENVIRONMENT VARIABLES (Optimization)")
    
    vars_to_check = [
        'OMP_NUM_THREADS',
        'MKL_NUM_THREADS',
        'OPENBLAS_NUM_THREADS',
        'OMP_DYNAMIC',
        'MKL_DYNAMIC',
        'CUDA_LAUNCH_BLOCKING',
    ]
    
    for var in vars_to_check:
        value = os.environ.get(var, "Not set")
        status = "✓" if value != "Not set" else "○"
        print(f"{status} {var}: {value}")

def get_pytorch_info():
    """Obtener información de PyTorch optimizations"""
    print_section("PYTORCH OPTIMIZATION STATUS")
    
    print(f"✓ Benchmark Mode: {torch.backends.cudnn.benchmark}")
    print(f"✓ Deterministic: {torch.backends.cudnn.deterministic}")
    print(f"✓ Enabled cuDNN: {torch.backends.cudnn.enabled}")
    
    if torch.cuda.is_available():
        print(f"\n✓ CUDA Status:")
        print(f"    Device: {torch.cuda.get_device_name(0)}")
        print(f"    Current Device: {torch.cuda.current_device()}")

def get_requirements_check():
    """Verificar dependencias instaladas"""
    print_section("DEPENDENCIES")
    
    deps = {
        'opencv-python': 'cv2',
        'torch': 'torch',
        'torchvision': 'torchvision',
        'ultralytics': 'ultralytics',
        'PySide6': 'PySide6',
        'numpy': 'numpy',
        'psutil': 'psutil',
    }
    
    for package, import_name in deps.items():
        try:
            mod = __import__(import_name)
            version = getattr(mod, '__version__', 'unknown')
            print(f"✓ {package}: {version}")
        except ImportError:
            print(f"✗ {package}: NOT INSTALLED")

def main():
    """Ejecutar diagnóstico completo"""
    print_header("CCTV AI PRO - HARDWARE DIAGNOSTICS")
    print("Quadro P1000 + i7-10700 Configuration")
    
    # Información del sistema
    get_system_info()
    get_requirements_check()
    
    # Hardware
    gpu_available = get_gpu_info()
    get_cpu_info()
    get_memory_info()
    
    # Optimizaciones
    get_environment_vars()
    get_pytorch_info()
    
    # Resumen
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + "RESUMEN".center(68) + "║")
    print("╚" + "="*68 + "╝")
    
    print("\n✓ Sistema listo para CCTV AI PRO")
    
    if gpu_available:
        print("✓ GPU (NVIDIA Quadro P1000) detectada")
        print("  Recomendación: Usar GPU para mejor rendimiento")
    else:
        print("⚠ GPU no detectada, usando CPU")
        print("  Rendimiento será limitado")
    
    print("\n📊 Para ver configuración actual: python config.py")
    print("📊 Para benchmark: python benchmark.py")
    print("🚀 Para iniciar app: python main.py\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
