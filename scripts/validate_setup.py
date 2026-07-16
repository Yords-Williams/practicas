"""
Script de Validación - Verificar que todo está optimizado correctamente
Ejecuta: python validate_setup.py
"""

import os
import sys
import torch
import psutil

def check_mark(condition):
    return "✓" if condition else "✗"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def validate_all():
    """Validar toda la configuración"""
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + "Alertas Tempranas - VALIDATION REPORT".center(68) + "║")
    print("║" + "Quadro P1000 + i7-10700".center(68) + "║")
    print("╚" + "="*68 + "╝")
    
    all_ok = True
    
    # 1. GPU
    print_section("1. GPU VALIDATION")
    
    cuda_available = torch.cuda.is_available()
    print(f"{check_mark(cuda_available)} CUDA Available: {cuda_available}")
    
    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        is_quadro = "Quadro" in gpu_name
        print(f"{check_mark(is_quadro)} GPU Model: {gpu_name}")
        
        # Memory
        total_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        has_enough_mem = total_mem >= 1.5  # At least 1.5GB VRAM
        print(f"{check_mark(has_enough_mem)} GPU Memory: {total_mem:.2f}GB (need ≥1.5GB)")
        
        all_ok = all_ok and cuda_available and is_quadro and has_enough_mem
    else:
        print("✗ CUDA not available - GPU acceleration disabled")
        all_ok = False
    
    # 2. CPU
    print_section("2. CPU VALIDATION")
    
    cpu_count = psutil.cpu_count()
    physical_cores = psutil.cpu_count(logical=False)
    is_octa = physical_cores == 8
    print(f"{check_mark(is_octa)} Physical Cores: {physical_cores} (expected 8 physical)")
    print(f"✓ Logical Cores: {cpu_count} (hyperthreading available)")
    
    # 3. Environment Variables
    print_section("3. ENVIRONMENT VARIABLES")
    
    omp_threads = os.environ.get('OMP_NUM_THREADS', '').strip()
    is_optimized = omp_threads in ['1', '2', '4'] or omp_threads == ''
    status = omp_threads if omp_threads else 'Auto'
    print(f"{check_mark(is_optimized)} OMP_NUM_THREADS: {status} (optimized: 1-4 or auto)")
    
    all_ok = all_ok and is_optimized
    
    # 4. Python Packages
    print_section("4. REQUIRED PACKAGES")
    
    packages = {
        'torch': 'PyTorch',
        'ultralytics': 'YOLOv8',
        'cv2': 'OpenCV',
        'PySide6': 'PySide6',
        'numpy': 'NumPy',
    }
    
    packages_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError:
            print(f"✗ {name} - NOT INSTALLED")
            packages_ok = False
    
    all_ok = all_ok and packages_ok
    
    # 5. Config Files
    print_section("5. CONFIGURATION FILES")
    
    config_file = "config.py"
    config_exists = os.path.exists(config_file)
    print(f"{check_mark(config_exists)} {config_file}")
    
    main_file = "main.py"
    main_exists = os.path.exists(main_file)
    print(f"{check_mark(main_exists)} {main_file}")
    
    ui_file = "ui.py"
    ui_exists = os.path.exists(ui_file)
    print(f"{check_mark(ui_exists)} {ui_file}")
    
    detector_file = "detector.py"
    detector_exists = os.path.exists(detector_file)
    print(f"{check_mark(detector_exists)} {detector_file}")
    
    all_files_ok = config_exists and main_exists and ui_exists and detector_exists
    all_ok = all_ok and all_files_ok
    
    # 6. Model Files
    print_section("6. MODEL FILES")
    
    yolo_model = "yolov8n.pt"
    yolo_exists = os.path.exists(yolo_model)
    print(f"{check_mark(yolo_exists)} {yolo_model}")
    
    accident_model = os.path.join("modulos", "choques", "best.pt")
    accident_exists = os.path.exists(accident_model)
    print(f"{check_mark(accident_exists)} {accident_model}")
    
    damage_model = os.path.join("modulos", "detector_de_auto_con_dano.pt")
    damage_exists = os.path.exists(damage_model)
    print(f"{check_mark(damage_exists)} {damage_model}")
    
    fire_model = os.path.join("modulos", "incendio", "best.pt")
    fire_exists = os.path.exists(fire_model)
    print(f"{check_mark(fire_exists)} {fire_model}")
    
    models_ok = yolo_exists and accident_exists and damage_exists and fire_exists
    all_ok = all_ok and models_ok
    
    # 7. Modules
    print_section("7. SPECIALIZED MODULES")
    
    accident_module = os.path.join("modulos", "choques", "detector.py")
    accident_mod_exists = os.path.exists(accident_module)
    print(f"{check_mark(accident_mod_exists)} choques/detector.py")
    
    person_module = os.path.join("modulos", "person_identifier.py")
    person_mod_exists = os.path.exists(person_module)
    print(f"{check_mark(person_mod_exists)} person_identifier.py")
    
    robo_module = os.path.join("modulos", "robo", "inference.py")
    robo_mod_exists = os.path.exists(robo_module)
    print(f"{check_mark(robo_mod_exists)} robo/inference.py")
    
    fire_module = os.path.join("modulos", "incendio", "detector.py")
    fire_mod_exists = os.path.exists(fire_module)
    print(f"{check_mark(fire_mod_exists)} incendio/detector.py")
    
    modules_ok = accident_mod_exists and person_mod_exists and robo_mod_exists and fire_mod_exists
    all_ok = all_ok and modules_ok
    
    # 8. Documentation
    print_section("8. DOCUMENTATION")
    
    docs = [
        ("QUICK_START.md", "Quick Start Guide"),
        ("OPTIMIZACIONES.md", "Optimization Details"),
        ("SETUP_CAMERAS.md", "Camera Setup"),
    ]
    
    docs_ok = True
    for doc_file, doc_name in docs:
        doc_exists = os.path.exists(doc_file)
        print(f"{check_mark(doc_exists)} {doc_name}")
        docs_ok = docs_ok and doc_exists
    
    all_ok = all_ok and docs_ok
    
    # 9. PyTorch Configuration
    print_section("9. PYTORCH OPTIMIZATION")
    
    cuda_bench = "optimized" if torch.backends.cudnn.benchmark else "not optimized"
    print(f"✓ Benchmark Mode: {cuda_bench}")
    print(f"✓ CUDA Version: {torch.version.cuda}")
    
    # Final Report
    print_section("VALIDATION REPORT")
    
    if all_ok:
        print("\n✓✓✓ ALL CHECKS PASSED ✓✓✓")
        print("\nYour system is ready to run Alertas Tempranas with optimal performance!")
        print("\nNext steps:")
        print("  1. python hardware_info.py       - See hardware details")
        print("  2. python benchmark.py           - Run performance test")
        print("  3. python main.py                - Start the application")
        return 0
    else:
        print("\n✗✗✗ SOME CHECKS FAILED ✗✗✗")
        print("\nPlease fix the issues above before running the application.")
        print("\nFor details, see:")
        print("  - QUICK_START.md")
        print("  - OPTIMIZACIONES.md")
        return 1

if __name__ == "__main__":
    try:
        exit_code = validate_all()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n✗ Validation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
