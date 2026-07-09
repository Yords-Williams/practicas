"""
Ejemplos de integración de módulos especializados
Muestra cómo usar cada sistema de detección
"""

import cv2
import sys
sys.path.insert(0, 'modulos')

from detector import DetectorIA
from modulos.accident_detection import AccidentDetectionSystem
from modulos.person_identifier import PersonAppearanceTracker
from modulos.robo_detector import TheftDetectionSystem, SortTracker
from config import ACCIDENT_CONFIG, PERSON_TRACKING_CONFIG

# ============================================================================
# EJEMPLO 1: Detección de Accidentes
# ============================================================================
def ejemplo_deteccion_accidentes():
    """
    Ejemplo de cómo usar el sistema de detección de accidentes
    """
    print("\n[EJEMPLO 1] Detección de Accidentes")
    print("-" * 50)
    
    # Inicializar sistema
    accident_system = AccidentDetectionSystem(
        yolo_model_path="best.pt",
        damage_model_path="detector_de_auto_con_dano.pt",
        video_source=0  # Webcam o 0 para la primera cámara
    )
    
    print("✓ Sistema de accidentes inicializado")
    print(f"  Umbral de confianza: {accident_system.confidence_threshold}")
    print(f"  Clases de vehículos: {accident_system.vehicle_classes}")
    
    # Procesar frames (en un bucle real)
    # frame = cap.read()
    # detections = accident_system.detect_vehicles(frame)
    # accident_system.track_vehicles(detections)
    # accidents = accident_system.detect_accidents()

# ============================================================================
# EJEMPLO 2: Rastreo de Personas
# ============================================================================
def ejemplo_rastreo_personas():
    """
    Ejemplo de cómo usar el rastreador de personas
    """
    print("\n[EJEMPLO 2] Rastreo de Personas")
    print("-" * 50)
    
    # Inicializar tracker
    tracker = PersonAppearanceTracker(
        max_age=PERSON_TRACKING_CONFIG["max_age"],
        distance_threshold=PERSON_TRACKING_CONFIG["distance_threshold"],
        appearance_threshold=PERSON_TRACKING_CONFIG["appearance_threshold"]
    )
    
    print("✓ Rastreador de personas inicializado")
    print(f"  Max age: {tracker.max_age} frames")
    print(f"  Umbral de distancia: {tracker.distance_threshold}")
    print(f"  Umbral de apariencia: {tracker.appearance_threshold}")
    
    # Usar en loop:
    # detections = [{'bbox': [x1, y1, x2, y2], 'confidence': 0.9}, ...]
    # tracked = tracker.update(detections, frame)
    # for track in tracked:
    #     print(f"Persona {track['id']} detectada")

# ============================================================================
# EJEMPLO 3: Detección de Robos
# ============================================================================
def ejemplo_deteccion_robos():
    """
    Ejemplo de cómo usar el sistema de detección de robos
    """
    print("\n[EJEMPLO 3] Detección de Robos")
    print("-" * 50)
    
    # Inicializar sistema
    theft_system = TheftDetectionSystem()
    
    print("✓ Sistema de detección de robos inicializado")
    print(f"  Clases de persona: {theft_system.person_class}")
    print(f"  Clases valiosas detectables: {len(theft_system.valuable_classes)}")
    print(f"  Detectando armas de fuego...")
    
    # Usar en loop:
    # detections = detector.predict(frame)
    # threats = theft_system.analyze_threats(detections, frame)
    # for threat in threats:
    #     print(f"Alerta: {threat['type']}")

# ============================================================================
# EJEMPLO 4: Pipeline Completo Integrado
# ============================================================================
def ejemplo_pipeline_completo():
    """
    Ejemplo de cómo integrar todos los sistemas en un pipeline
    """
    print("\n[EJEMPLO 4] Pipeline Completo Integrado")
    print("-" * 50)
    
    print("✓ Inicializando componentes...")
    
    # Detector general
    detector_general = DetectorIA()
    
    # Sistemas especializados
    accident_detector = AccidentDetectionSystem()
    person_tracker = PersonAppearanceTracker()
    theft_detector = TheftDetectionSystem()
    sort_tracker = SortTracker()
    
    print("✓ Todos los sistemas cargados")
    
    # Pseudo-código de procesamiento
    print("\nPipeline de procesamiento:")
    print("1. Capturar frame de cámara")
    print("2. Detección general (YOLOv8n)")
    print("3. Tracking de vehículos (Accidentes)")
    print("4. Tracking de personas (Identificación)")
    print("5. Análisis de amenazas (Robos)")
    print("6. Generar alertas si es necesario")
    print("7. Registrar eventos")
    print("8. Mostrar frame procesado")

# ============================================================================
# EJEMPLO 5: Procesamiento por Modo
# ============================================================================
def procesar_segun_modo(frame, modo, detector, accident_det, person_track, theft_det):
    """
    Procesar frame según modo de detección seleccionado
    
    Args:
        frame: imagen a procesar
        modo: "general", "accidentes", "personas", "robos"
        detector: detector general
        accident_det: detector de accidentes
        person_track: tracker de personas
        theft_det: detector de robos
        
    Returns:
        frame procesado con anotaciones
    """
    
    if modo == "general":
        # Usar YOLOv8n general
        return detector.predict(frame)
    
    elif modo == "accidentes":
        # Procesar con detector de accidentes
        detections = accident_det.detect_vehicles(frame)
        accident_det.track_vehicles(detections)
        accidents = accident_det.detect_accidents()
        
        # Dibujar detecciones
        result_frame = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(result_frame, detection['label'], 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return result_frame
    
    elif modo == "personas":
        # Procesar con rastreador de personas
        # (necesita detecciones previas)
        detections = detector.predict(frame)
        # tracked = person_track.update(detections, frame)
        
        return detections
    
    elif modo == "robos":
        # Procesar con detector de robos
        detections = detector.predict(frame)
        # threats = theft_det.analyze_threats(detections, frame)
        
        return detections
    
    return frame

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("EJEMPLOS DE INTEGRACIÓN DE MÓDULOS ESPECIALIZADOS")
    print("="*50)
    
    # Ejecutar ejemplos
    ejemplo_deteccion_accidentes()
    ejemplo_rastreo_personas()
    ejemplo_deteccion_robos()
    ejemplo_pipeline_completo()
    
    print("\n" + "="*50)
    print("Para usar en producción, edita main.py")
    print("="*50 + "\n")
