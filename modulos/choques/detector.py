import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
import datetime
import json
import os

class AccidentDetectionSystem:
    def __init__(self, yolo_model_path="best.pt", damage_model_path="../detector_de_auto_con_dano.pt", video_source=None):
        """Inicializar el sistema de detección de choques.
        
        Args:
            yolo_model_path: Modelo YOLO para detección de vehículos (relativo a esta carpeta).
            damage_model_path: Modelo YOLO para detección de daños (relativo a esta carpeta).
            video_source: Fuente de video (int/str). None = modo frame-by-frame sin abrir cámara.
        """
        # Obtener directorio actual
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Rutas completas
        yolo_model_path = os.path.join(script_dir, yolo_model_path)
        damage_model_path = os.path.join(script_dir, damage_model_path)
        
        print(f"Cargando modelo YOLO de choques: {yolo_model_path}")
        print(f"Cargando modelo de daños: {damage_model_path}")
        
        self.yolo_model = YOLO(yolo_model_path)  # Modelo para detectar vehículos
        self.damage_model = YOLO(damage_model_path)  # Modelo para detectar daños
        
        # Clases de vehículos COCO: car=2, motorcycle=3, bus=5, truck=7
        self.vehicle_classes = [2, 3, 5, 7]
        
        self.video_source = video_source
        # Abrir captura solo si se provee una fuente de video
        self.cap = cv2.VideoCapture(video_source) if video_source is not None else None
        
        # Parámetros de detección
        self.confidence_threshold = 0.4
        self.max_distance = 50  # píxeles - distancia mínima entre vehículos
        self.deceleration_threshold = 0.7  # Cambio de velocidad significativo
        self.damage_confidence = 0.5
        
        # Tracking
        self.vehicle_tracks = {}  # ID -> lista de posiciones
        self.vehicle_bboxes = {}  # ID -> último bbox
        self.vehicle_velocities = {}  # ID -> velocidad actual
        self.vehicle_history = defaultdict(list)  # Historial completo
        self.next_id = 0
        
        # Registros
        self.accident_records = []
        
    def detect_vehicles(self, frame):
        """Detectar vehículos en el frame con YOLO"""
        results = self.yolo_model(frame, conf=self.confidence_threshold)
        detections = []
        
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                
                # Filtrar solo vehículos
                if cls in self.vehicle_classes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    label = self.yolo_model.names[cls]
                    
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'center': (center_x, center_y),
                        'confidence': conf,
                        'class': cls,
                        'label': label
                    })
        
        return detections
    
    def track_vehicles(self, detections):
        """Realizar tracking de vehículos"""
        if not detections:
            return
        
        # Actualizar tracks existentes
        for vehicle_id, history in list(self.vehicle_tracks.items()):
            if not history:
                del self.vehicle_tracks[vehicle_id]
                continue
            
            last_pos = history[-1]
            matched = False
            
            for detection in detections:
                center = detection['center']
                distance = np.sqrt((center[0] - last_pos[0])**2 + (center[1] - last_pos[1])**2)
                
                if distance < 100:  # Distancia máxima de tracking
                    self.vehicle_tracks[vehicle_id].append(center)
                    self.vehicle_bboxes[vehicle_id] = detection['bbox']  # Guardar bbox
                    
                    # Calcular velocidad (cambio de posición)
                    if len(history) > 1:
                        prev_pos = history[-2]
                        velocity = np.sqrt((center[0] - prev_pos[0])**2 + (center[1] - prev_pos[1])**2)
                        self.vehicle_velocities[vehicle_id] = velocity
                    
                    matched = True
                    detections.remove(detection)
                    break
        
        # Crear nuevos tracks para detecciones no emparejadas
        for detection in detections:
            self.vehicle_tracks[self.next_id] = [detection['center']]
            self.vehicle_bboxes[self.next_id] = detection['bbox']  # Guardar bbox
            self.vehicle_velocities[self.next_id] = 0
            self.next_id += 1
    
    def check_vehicles_close(self):
        """Verificar si los vehículos están muy cerca"""
        close_pairs = []
        vehicle_ids = list(self.vehicle_tracks.keys())
        
        for i, id1 in enumerate(vehicle_ids):
            for id2 in vehicle_ids[i+1:]:
                if self.vehicle_tracks[id1] and self.vehicle_tracks[id2]:
                    pos1 = self.vehicle_tracks[id1][-1]
                    pos2 = self.vehicle_tracks[id2][-1]
                    distance = np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                    
                    if distance < self.max_distance:
                        close_pairs.append((id1, id2, distance))
        
        return len(close_pairs) > 0, close_pairs
    
    def detect_sudden_deceleration(self):
        """Detectar desaceleración brusca"""
        sudden_decelerations = []
        
        for vehicle_id, velocities in self.vehicle_history.items():
            if len(velocities) >= 2:
                current_vel = velocities[-1]
                previous_vel = velocities[-2]
                
                if previous_vel > 0:
                    deceleration_rate = (previous_vel - current_vel) / previous_vel
                    
                    if deceleration_rate > self.deceleration_threshold:
                        sudden_decelerations.append((vehicle_id, deceleration_rate))
        
        return len(sudden_decelerations) > 0, sudden_decelerations
    
    def detect_vehicle_damage(self, frame, bbox):
        """Detectar daño en vehículos usando el modelo .pt"""
        x1, y1, x2, y2 = bbox
        vehicle_region = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
        
        if vehicle_region.size == 0:
            return False
        
        # Usar el modelo de detección de daños
        results = self.damage_model(vehicle_region, conf=self.damage_confidence)
        
        # Si hay detecciones, significa que detectó daño
        damage_detected = len(results) > 0 and len(results[0].boxes) > 0
        
        return damage_detected
    
    def analyze_accident(self, frame):
        """Analizar si hay un posible accidente"""
        vehicles_present = len(self.vehicle_tracks) > 0
        accident_probability = 0.0
        
        if not vehicles_present:
            return False, "Sin vehículos detectados", 0.0
        
        close_vehicles, pairs = self.check_vehicles_close()
        if not close_vehicles:
            return False, "Vehículos no están muy cerca", 0.0
        
        sudden_decel, decelerations = self.detect_sudden_deceleration()
        if not sudden_decel:
            return False, "Sin desaceleración brusca", 0.0
        
        # Calcular probabilidad de accidente basada en indicadores
        probability_factors = 0
        
        # Factor 1: Proximidad de vehículos (0-30%)
        if close_vehicles:
            probability_factors += 0.3
        
        # Factor 2: Desaceleración brusca (0-40%)
        if sudden_decel:
            probability_factors += 0.4
        
        # Factor 3: Daño detectado (0-30%)
        damage_detected = False
        for id1, id2, distance in pairs:
            if id1 in self.vehicle_bboxes and id2 in self.vehicle_bboxes:
                bbox1 = self.vehicle_bboxes[id1]
                bbox2 = self.vehicle_bboxes[id2]
                
                damage1 = self.detect_vehicle_damage(frame, bbox1)
                damage2 = self.detect_vehicle_damage(frame, bbox2)
                
                if damage1 or damage2:
                    damage_detected = True
                    probability_factors += 0.3
                    break
        
        accident_probability = min(1.0, probability_factors)
        
        # Es un accidente si probabilidad es muy alta
        accident_detected = accident_probability > 0.7
        
        return accident_detected, f"Proximidad: {len(pairs)}, Desaceleración: {len(decelerations)}, Daño: {damage_detected}", accident_probability
    
    def log_accident(self, frame, analysis_result):
        """Guardar registro de posible accidente"""
        timestamp = datetime.datetime.now().isoformat()
        
        is_accident, details, probability = analysis_result
        
        record = {
            'timestamp': timestamp,
            'is_accident': is_accident,
            'details': details,
            'probability': probability,
            'vehicle_count': len(self.vehicle_tracks),
            'vehicles_detected': list(self.vehicle_tracks.keys())
        }
        
        self.accident_records.append(record)
        
        # Guardar frame
        if is_accident:
            filename = f"accident_{timestamp.replace(':', '-')}.jpg"
            cv2.imwrite(filename, frame)
            record['image_path'] = filename
            print(f"✓ Imagen de accidente guardada: {filename}")
    
    def generate_alert(self, analysis_result):
        """Generar alerta si hay accidente"""
        is_accident, details, probability = analysis_result
        
        if is_accident:
            print("\n" + "="*60)
            print("⚠️  ALERTA DE POSIBLE ACCIDENTE ⚠️")
            print("="*60)
            print(f"Probabilidad: {probability*100:.1f}%")
            print(f"Detalles: {details}")
            print(f"Timestamp: {datetime.datetime.now()}")
            print("="*60 + "\n")
            return True
        return False
    
    def save_records(self, filename="accident_records.json"):
        """Guardar registros de accidentes"""
        with open(filename, 'w') as f:
            json.dump(self.accident_records, f, indent=4)
        print(f"✓ Registros guardados en: {filename}")
    
    def process_video(self, max_frames=None):
        """Procesar el video completo (requiere video_source en el constructor)."""
        if self.cap is None:
            raise RuntimeError("process_video() requiere video_source en el constructor. Usa analyze_accident(frame) para modo frame-by-frame.")
        frame_count = 0
        current_accident_probability = 0.0
        paused = False
        
        print("Iniciando procesamiento de video...")
        print("Presiona 'q' para salir, 'ESPACIO' para pausar/reanudar\n")
        
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                print("Fin del video")
                break
            
            frame_count += 1
            if max_frames and frame_count > max_frames:
                break
            
            # Redimensionar para procesamiento más rápido
            frame_small = cv2.resize(frame, (640, 480))
            
            # Paso 1: Detectar vehículos
            detections = self.detect_vehicles(frame_small)
            
            if detections:
                # Paso 2: Realizar tracking
                self.track_vehicles(detections)
                
                # Paso 3: Guardar velocidades en historial
                for vehicle_id, velocity in self.vehicle_velocities.items():
                    self.vehicle_history[vehicle_id].append(velocity)
                
                # Paso 4: Analizar accidente
                analysis = self.analyze_accident(frame_small)
                is_accident, details, probability = analysis
                current_accident_probability = probability
                
                # Paso 5: Guardar registro si es necesario
                self.log_accident(frame_small, analysis)
                
                # Paso 6: Generar alerta
                if self.generate_alert(analysis):
                    paused = True  # Pausar si hay accidente
            
            # Dibujar información en el frame
            self.draw_frame(frame_small, detections)
            
            # Dibujar probabilidad de accidente
            prob_color = (0, 0, 255) if current_accident_probability > 0.7 else (0, 255, 0)
            prob_text = f"Probabilidad Accidente: {current_accident_probability*100:.1f}%"
            cv2.putText(frame_small, prob_text, (10, 470),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, prob_color, 2)
            
            # Mostrar estado de pausa
            if paused:
                cv2.putText(frame_small, "PAUSADO - Presiona ESPACIO para continuar", (100, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            # Mostrar
            cv2.imshow('Detección de Accidentes', frame_small)
            
            # Control de keyboard
            if paused:
                # En pausa, esperar a que el usuario presione una tecla
                key = cv2.waitKey(0) & 0xFF
            else:
                # En reproducción, esperar 1ms
                key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                paused = not paused
            
            if frame_count % 30 == 0:
                print(f"Frames procesados: {frame_count}, Vehículos detectados: {len(self.vehicle_tracks)}")
        
        self.cleanup()
    
    def draw_frame(self, frame, detections):
        """Dibujar información en el frame"""
        # Dibujar bounding boxes de detecciones
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            center = detection['center']
            conf = detection['confidence']
            label = detection.get('label', 'Vehículo')
            
            # Dibujar bounding box verde
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, center, 5, (0, 0, 255), -1)
            
            # Dibujar etiqueta y confianza
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Dibujar información de tracking y velocidad
        for vehicle_id in self.vehicle_tracks:
            if vehicle_id in self.vehicle_bboxes:
                bbox = self.vehicle_bboxes[vehicle_id]
                x1, y1, x2, y2 = bbox
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                
                # Dibujar bounding box azul para tracked vehicles
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Obtener velocidad
                velocity = self.vehicle_velocities.get(vehicle_id, 0)
                
                # Dibujar información del vehículo
                info_text = f"ID:{vehicle_id} Vel:{velocity:.1f}px/f"
                cv2.putText(frame, info_text, (x1, y1 - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                # Dibujar línea de trayectoria
                history = self.vehicle_tracks[vehicle_id]
                if len(history) > 1:
                    for i in range(len(history) - 1):
                        pt1 = history[i]
                        pt2 = history[i + 1]
                        cv2.line(frame, pt1, pt2, (200, 200, 0), 1)
        
        # Información general
        cv2.putText(frame, f"Vehiculos: {len(self.vehicle_tracks)}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    def cleanup(self):
        """Limpiar recursos"""
        self.cap.release()
        cv2.destroyAllWindows()
        self.save_records()
        print("Sistema cerrado")


def main():
    """Función principal"""
    # Obtener directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ruta del video
    video_path = os.path.join(script_dir, "robo9.mp4")
    
    print(f"Procesando video: {video_path}")
    print(f"Archivo existe: {os.path.exists(video_path)}")
    
    system = AccidentDetectionSystem(
        yolo_model_path="yolov8n.pt",  # Modelo YOLO estándar para detectar vehículos
        damage_model_path="detector_de_auto_con_dano.pt",  # Modelo para detectar daños
        video_source=video_path  # Video
    )
    
    system.process_video(max_frames=None)


if __name__ == "__main__":
    main()
