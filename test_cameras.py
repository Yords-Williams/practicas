"""
Script para probar conexión a cámaras RTSP
Ejecuta: python test_cameras.py
"""

import cv2
import sys
from camera_dialog import CameraDialog

def test_single_camera(url, name):
    """Probar una cámara individual"""
    print(f"\n{'='*60}")
    print(f"Probando: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        
        if cap.isOpened():
            print("✓ Conexión exitosa")
            
            # Intentar leer un frame
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"✓ Frame capturado: {frame.shape[0]}x{frame.shape[1]} píxeles")
                cap.release()
                return True
            else:
                print("✗ Error: No se pudo capturar frame")
                cap.release()
                return False
        else:
            print("✗ Error: No se pudo abrir la cámara")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_all_cameras():
    """Probar todas las cámaras configuradas"""
    print("\n" + "="*60)
    print("CCTV AI PRO - TEST DE CÁMARAS")
    print("="*60)
    
    cameras = CameraDialog.get_cameras()
    
    if not cameras:
        print("\n✗ No hay cámaras configuradas")
        print("Abre la aplicación y usa '📹 Gestionar Cámaras' para agregar")
        return
    
    print(f"\nCámaras configuradas: {len(cameras)}")
    
    results = []
    for cam in cameras:
        success = test_single_camera(cam["url"], cam["name"])
        results.append({
            "name": cam["name"],
            "url": cam["url"],
            "success": success
        })
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    
    total = len(results)
    success = sum(1 for r in results if r["success"])
    
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"{status} {result['name']}")
    
    print(f"\nCámaras funcionales: {success}/{total}")
    
    if success == total:
        print("\n✓ ¡Todas las cámaras están funcionando!")
    elif success > 0:
        print("\n⚠ Algunas cámaras tienen problemas")
    else:
        print("\n✗ Ninguna cámara está funcionando")
    
    print("\nRecomendaciones:")
    print("- Verifica la URL RTSP")
    print("- Verifica usuario y contraseña")
    print("- Verifica conectividad de red (ping a la IP)")
    print("- Verifica firewall de la cámara")
    print("="*60)

def test_manual():
    """Probar una URL manual"""
    print("\n" + "="*60)
    print("PRUEBA MANUAL DE CÁMARA")
    print("="*60)
    
    url = input("\nIngresa la URL RTSP: ").strip()
    name = input("Ingresa el nombre de la cámara: ").strip()
    
    if not url:
        print("✗ URL vacía")
        return
    
    test_single_camera(url, name)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "manual":
            test_manual()
        else:
            print("Uso: python test_cameras.py [manual]")
            print("\nSin argumentos: prueba todas las cámaras configuradas")
            print("manual: prueba una URL ingresada manualmente")
    else:
        test_all_cameras()
