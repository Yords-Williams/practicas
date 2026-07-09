import os
import argparse

VIDEO_DEFAULT = "videoga.mp4"

# Limitar threads para OpenBLAS / PyTorch en ambientes con memoria limitada
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('MKL_DYNAMIC', 'FALSE')
os.environ.setdefault('OMP_DYNAMIC', 'FALSE')
os.environ.setdefault('OMP_WAIT_POLICY', 'PASSIVE')

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from collections import defaultdict
import json
from datetime import datetime
from .person_identifier import PersonAppearanceTracker


def convert_bbox_to_z(bbox):
    """Convertir bbox [x1,y1,x2,y2] a espacio de medición z = [cx, cy, s, r]"""
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if h <= 0 or w <= 0:
        return np.array([0., 0., 0., 0.])
    x = bbox[0] + w / 2.0
    y = bbox[1] + h / 2.0
    s = w * h
    r = w / float(h)
    return np.array([x, y, s, r])


def convert_x_to_bbox(x):
    """Convertir estado x a bbox [x1,y1,x2,y2]"""
    if x[2] <= 0 or x[3] <= 0:
        return np.array([0., 0., 0., 0.])
    w = np.sqrt(x[2] * x[3])
    h = x[2] / w
    return np.array([
        x[0] - w / 2.0,
        x[1] - h / 2.0,
        x[0] + w / 2.0,
        x[1] + h / 2.0
    ])


def iou_batch(boxes1, boxes2):
    """Calcular IoU entre arrays de boxes"""
    if len(boxes1) == 0 or len(boxes2) == 0:
        return np.zeros((len(boxes1), len(boxes2)), dtype=np.float32)
    iou_matrix = np.zeros((len(boxes1), len(boxes2)), dtype=np.float32)
    for i, b1 in enumerate(boxes1):
        x1_min, y1_min, x1_max, y1_max = b1
        area1 = max(0, x1_max - x1_min) * max(0, y1_max - y1_min)
        for j, b2 in enumerate(boxes2):
            x2_min, y2_min, x2_max, y2_max = b2
            inter_xmin = max(x1_min, x2_min)
            inter_ymin = max(y1_min, y2_min)
            inter_xmax = min(x1_max, x2_max)
            inter_ymax = min(y1_max, y2_max)
            inter_w = max(0.0, inter_xmax - inter_xmin)
            inter_h = max(0.0, inter_ymax - inter_ymin)
            inter_area = inter_w * inter_h
            area2 = max(0, x2_max - x2_min) * max(0, y2_max - y2_min)
            union = area1 + area2 - inter_area
            iou_matrix[i, j] = inter_area / union if union > 0 else 0.0
    return iou_matrix


class KalmanBoxTracker:
    """Rastreador de caja basado en Kalman filter para SORT."""

    count = 0

    def __init__(self, bbox):
        self.x = np.zeros((7,), dtype=np.float32)
        z = convert_bbox_to_z(bbox)
        self.x[:4] = z
        self.P = np.eye(7, dtype=np.float32) * 10.0
        self.P[4:, 4:] *= 100.0
        self.F = np.eye(7, dtype=np.float32)
        self.F[0, 4] = 1.0
        self.F[1, 5] = 1.0
        self.F[2, 6] = 1.0
        self.H = np.zeros((4, 7), dtype=np.float32)
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        self.H[2, 2] = 1.0
        self.H[3, 3] = 1.0
        self.R = np.eye(4, dtype=np.float32) * 1.0
        self.Q = np.eye(7, dtype=np.float32) * 0.01
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 1
        self.hit_streak = 1
        self.age = 0
        self.bbox = bbox

    def predict(self):
        self.x = self.F.dot(self.x)
        self.P = self.F.dot(self.P).dot(self.F.T) + self.Q
        self.age += 1
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.x))
        return self.history[-1]

    def update(self, bbox):
        z = convert_bbox_to_z(bbox)
        y = z - self.H.dot(self.x)
        S = self.H.dot(self.P).dot(self.H.T) + self.R
        K = self.P.dot(self.H.T).dot(np.linalg.inv(S))
        self.x += K.dot(y)
        self.P = (np.eye(7, dtype=np.float32) - K.dot(self.H)).dot(self.P)
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        self.bbox = bbox
        self.history = []

    def get_state(self):
        return convert_x_to_bbox(self.x)


class SortTracker:
    """Implementación mínima de SORT para tracking de personas."""

    def __init__(self, max_age=15, min_hits=1, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []

    def update(self, dets):
        """Actualizar tracks con las detecciones actuales."""
        if len(dets) == 0:
            for trk in self.trackers:
                trk.predict()
            self.trackers = [t for t in self.trackers if t.time_since_update <= self.max_age]
            return []

        trks = np.zeros((len(self.trackers), 4), dtype=np.float32)
        for t, trk in enumerate(self.trackers):
            trks[t] = trk.predict()

        dets_arr = np.asarray([d[:4] for d in dets], dtype=np.float32)
        if len(self.trackers) > 0:
            iou_matrix = iou_batch(trks, dets_arr)
        else:
            iou_matrix = np.zeros((0, len(dets_arr)), dtype=np.float32)

        matched, unmatched_trks, unmatched_dets = self._associate_detections_to_trackers(iou_matrix)

        for t, d in matched:
            self.trackers[t].update(dets_arr[d])

        for t in unmatched_trks:
            self.trackers[t].time_since_update += 1
            self.trackers[t].hit_streak = 0

        for d in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(dets_arr[d]))

        self.trackers = [t for t in self.trackers if t.time_since_update <= self.max_age]

        outputs = []
        for trk in self.trackers:
            if trk.hit_streak >= self.min_hits or trk.time_since_update == 0:
                outputs.append({'id': trk.id, 'bbox': trk.get_state(), 'time_since_update': trk.time_since_update})
        return outputs

    def _associate_detections_to_trackers(self, iou_matrix):
        matched = []
        unmatched_trks = list(range(iou_matrix.shape[0]))
        unmatched_dets = list(range(iou_matrix.shape[1]))

        if iou_matrix.size == 0:
            return matched, unmatched_trks, unmatched_dets

        pairs = []
        for t in range(iou_matrix.shape[0]):
            for d in range(iou_matrix.shape[1]):
                pairs.append((iou_matrix[t, d], t, d))
        pairs.sort(key=lambda x: x[0], reverse=True)

        assigned_trks = set()
        assigned_dets = set()
        for score, t, d in pairs:
            if score < self.iou_threshold:
                break
            if t in assigned_trks or d in assigned_dets:
                continue
            matched.append((t, d))
            assigned_trks.add(t)
            assigned_dets.add(d)

        unmatched_trks = [t for t in range(iou_matrix.shape[0]) if t not in assigned_trks]
        unmatched_dets = [d for d in range(iou_matrix.shape[1]) if d not in assigned_dets]
        return matched, unmatched_trks, unmatched_dets


class TheftDetectionSystem:
    """Sistema de detección de posible robo menor según diagrama de flujo"""
    
    def __init__(self, video_source):
        self.video_source = video_source
        
        # Forzar GPU 0
        self.device = 0
        print(f"Usando GPU: 0 (RTX 3050)")
        
        # Cargar modelos
        print(f"Cargando modelo YOLO estándar para detección de personas y objetos...")
        self.yolo_model = YOLO("yolov8n.pt")
        
        # Lazy loading del modelo de actividades sospechosas (cargar solo si se necesita)
        self.suspicious_model = None
        self.suspicious_model_loaded = False
        
        # Clases COCO
        self.person_class = 0
        self.valuable_classes = {
            24: 'backpack',
            26: 'handbag',
            28: 'suitcase',
            43: 'knife',
            63: 'laptop',
            67: 'cell phone',
            73: 'book',
            39: 'umbrella',
            40: 'tie',
            41: 'suitcase',
            42: 'frisbee'
        }
        self.firearm_classes = {73: 'book', 39: 'umbrella', 40: 'tie', 41: 'suitcase', 42: 'frisbee'}
        self.phone_class_ids = {67}
        self.blade_class_ids = {43}
        self.firearm_keywords = ('gun', 'pistol', 'revolver', 'handgun', 'firearm', 'rifle', 'shotgun', 'weapon')
        self.blade_keywords = ('knife', 'dagger', 'sword', 'blade', 'machete', 'scalpel')
        self.default_object_conf = 0.10
        self.phone_conf = 0.02  # Reducido de 0.06 para mejor detección
        self.phone_second_pass_conf = 0.01  # Reducido de 0.04
        self.firearm_conf = 0.08
        self.person_tracks = defaultdict(lambda: {
            'positions': [],
            'bbox': None,
            'velocity': (0, 0),
            'has_valuable': False,
            'valuable_objects': [],
            'tracking_id': None,
            'had_firearm': False,
            'had_phone': False,
            'had_blade': False,
            'last_seen': 0,
            'missing': False
        })
        
        self.object_tracks = defaultdict(lambda: {
            'positions': [],
            'bbox': None,
            'velocity': (0, 0),
            'owner_id': None,
            'class_name': None,
            'class_id': None,
            'last_seen': 0,
            'missing': False,
            'owner_changed': False
        })
        
        self.person_sort = SortTracker(max_age=30, min_hits=1, iou_threshold=0.25)
        self.person_identifier = PersonAppearanceTracker(max_age=12, distance_threshold=120, appearance_threshold=0.75)
        self.person_sort_to_stable = {}
        self.expired_persons = []
        self.next_person_label = 1
        self.next_person_id = 0
        self.next_object_id = 0
        self.distance_threshold = 120
        self.track_max_age = 15
        self.alarm_threshold = 0.7
        
        # Abrir video
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir el video: {video_source}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = 0
        
        # Alertas
        self.alerts = []
        
    def load_suspicious_model(self):
        """Cargar modelo de actividades sospechosas solo cuando sea necesario"""
        if not self.suspicious_model_loaded:
            print("Cargando modelo de actividades sospechosas...")
            self.suspicious_model = YOLO("Suspicious_Activities_nano.pt")
            self.suspicious_model_loaded = True
    
    def categorize_object(self, obj):
        """Clasificar un objeto detectado en celular, arma de fuego o arma blanca."""
        class_id = obj.get('class')
        class_name = str(obj.get('class_name', '')).lower()

        if class_id in self.phone_class_ids or 'phone' in class_name:
            return 'phone'

        if class_id in self.blade_class_ids or any(keyword in class_name for keyword in self.blade_keywords):
            return 'blade'

        if any(keyword in class_name for keyword in self.firearm_keywords):
            return 'firearm'

        return None

    def count_object_categories(self, tracked_objects):
        """Contar celulares, armas de fuego y armas blancas en los objetos rastreados."""
        counts = {'phone': 0, 'firearm': 0, 'blade': 0}
        for obj in tracked_objects.values():
            category = self.categorize_object(obj)
            if category is not None:
                counts[category] += 1
        return counts

    def detect_people_and_objects(self, frame):
        """Detectar personas y objetos de valor dentro del mismo flujo de video"""
        relevant_classes = [0, 24, 26, 28, 43, 63, 67, 73, 39, 40, 41, 42]
        results = self.yolo_model(
            frame,
            verbose=False,
            device=self.device,
            conf=0.05,  # Reducido para detectar más objetos
            iou=0.30,
            max_det=800,
            imgsz=1280,
            classes=relevant_classes
        )
        
        people = []
        objects_detected = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                if cls == self.person_class and conf > 0.5:
                    people.append({
                        'bbox': bbox,
                        'conf': conf,
                        'center': self.get_center(bbox)
                    })
                
                elif cls in self.valuable_classes:
                    threshold = self.phone_conf if cls == 67 else self.default_object_conf
                    if conf > threshold:
                        objects_detected.append({
                            'bbox': bbox,
                            'conf': conf,
                            'center': self.get_center(bbox),
                            'class': cls,
                            'class_name': self.valuable_classes[cls]
                        })

        if len(objects_detected) < 5:
            firearm_results = self.yolo_model(
                frame,
                verbose=False,
                device=self.device,
                conf=self.firearm_conf,
                iou=0.25,
                max_det=200,
                imgsz=1600,
                classes=[39, 40, 41, 42]
            )
            for r in firearm_results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    bbox = box.xyxy[0].cpu().numpy()
                    if cls in self.firearm_classes and conf > self.firearm_conf:
                        objects_detected.append({
                            'bbox': bbox,
                            'conf': conf,
                            'center': self.get_center(bbox),
                            'class': cls,
                            'class_name': self.firearm_classes[cls]
                        })

        if people and len(objects_detected) < 3:
            phone_results = self.yolo_model(
                frame,
                verbose=False,
                device=self.device,
                conf=self.phone_second_pass_conf,
                iou=0.30,
                max_det=200,
                imgsz=1600,
                classes=[67]
            )

            for r in phone_results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    bbox = box.xyxy[0].cpu().numpy()
                    if cls == 67 and conf > self.phone_second_pass_conf:
                        objects_detected.append({
                            'bbox': bbox,
                            'conf': conf,
                            'center': self.get_center(bbox),
                            'class': cls,
                            'class_name': self.valuable_classes[cls]
                        })
        
        return people, objects_detected
    
    def detect_suspicious_activity(self, frame):
        """Detectar peleas, forcejeos, correr"""
        
        # Cargar modelo solo si es necesario
        if not self.suspicious_model_loaded:
            self.load_suspicious_model()
        
        results = self.suspicious_model(frame, verbose=False, device=self.device)
        
        suspicious = {
            'fight': False,
            'running': False,
            'suspicious_activity': False,
            'confidence': 0
        }
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                label = self.suspicious_model.names[int(box.cls[0])]
                
                # Detectar actividades sospechosas
                if 'fight' in label.lower() or 'forcejeo' in label.lower():
                    suspicious['fight'] = True
                    suspicious['confidence'] = max(suspicious['confidence'], conf)
                
                if 'running' in label.lower() or 'correr' in label.lower() or 'run' in label.lower():
                    suspicious['running'] = True
                    suspicious['confidence'] = max(suspicious['confidence'], conf)
                
                if conf > 0.6:
                    suspicious['suspicious_activity'] = True
        
        return suspicious
    
    def get_center(self, bbox):
        """Obtener centro de bounding box"""
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def distance(self, p1, p2):
        """Calcular distancia Euclidiana"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def point_in_bbox(self, point, bbox):
        """Verificar si un punto está dentro de un bounding box"""
        return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]
    
    def bbox_iou(self, bbox1, bbox2):
        """Calcular IoU entre dos bounding boxes"""
        xA = max(bbox1[0], bbox2[0])
        yA = max(bbox1[1], bbox2[1])
        xB = min(bbox1[2], bbox2[2])
        yB = min(bbox1[3], bbox2[3])
        interW = max(0, xB - xA)
        interH = max(0, yB - yA)
        interArea = interW * interH
        area1 = max(0, bbox1[2] - bbox1[0]) * max(0, bbox1[3] - bbox1[1])
        area2 = max(0, bbox2[2] - bbox2[0]) * max(0, bbox2[3] - bbox2[1])
        union = area1 + area2 - interArea
        return interArea / union if union > 0 else 0.0
    
    def find_stable_label(self, bbox):
        """Buscar un label estable para un nuevo track usando personas expiradas cercanas."""
        center = self.get_center(bbox)
        best = None
        best_dist = float('inf')
        now = self.frame_count
        for entry in self.expired_persons:
            if now - entry['last_seen'] > 60:
                continue
            dist = self.distance(center, entry['center'])
            if dist < best_dist and dist < 80:
                best_dist = dist
                best = entry
        if best is not None:
            self.expired_persons = [e for e in self.expired_persons if e is not best]
            return best['stable_id']
        return None
    
    def track_people(self, people, frame):
        """Tracking de personas usando SORT y re-identificación por apariencia"""
        tracked_people = {}
        dets = []

        for person in people:
            bbox = person['bbox']
            score = person.get('conf', 1.0)
            dets.append([bbox[0], bbox[1], bbox[2], bbox[3], score])

        sort_outputs = self.person_sort.update(dets)
        self.person_identifier.set_frame_id(self.frame_count)
        id_outputs = self.person_identifier.update([
            {'bbox': np.array([d[0], d[1], d[2], d[3]], dtype=np.float32), 'conf': d[4]} for d in dets
        ], frame)

        for track_data in self.person_tracks.values():
            track_data['missing'] = True

        for out in sort_outputs:
            track_id = out['id']
            bbox = out['bbox']
            center = self.get_center(bbox)

            if self.person_tracks[track_id]['positions']:
                last_pos = self.person_tracks[track_id]['positions'][-1]
                velocity = (center[0] - last_pos[0], center[1] - last_pos[1])
            else:
                velocity = (0, 0)

            stable_label = None
            for id_out in id_outputs:
                if np.allclose(id_out['bbox'], bbox, atol=5):
                    stable_label = id_out['tracking_id']
                    break

            if stable_label is None:
                stable_label = self.find_stable_label(bbox)
            if stable_label is None:
                stable_label = self.next_person_label
                self.next_person_label += 1

            self.person_tracks[track_id]['tracking_id'] = stable_label
            self.person_tracks[track_id]['positions'].append(center)
            self.person_tracks[track_id]['bbox'] = bbox
            self.person_tracks[track_id]['velocity'] = velocity
            self.person_tracks[track_id]['last_seen'] = self.frame_count
            self.person_tracks[track_id]['missing'] = False
            tracked_people[stable_label] = self.person_tracks[track_id]

        # Guardar tracks expirados para reuso de etiqueta estable
        for track_id, track_data in list(self.person_tracks.items()):
            if track_data['positions'] and track_data['missing'] and self.frame_count - track_data['last_seen'] > self.track_max_age:
                self.expired_persons.append({
                    'stable_id': track_data['tracking_id'],
                    'center': self.get_center(track_data['bbox']),
                    'last_seen': track_data['last_seen']
                })
                self.person_tracks[track_id] = {
                    'positions': [],
                    'bbox': None,
                    'velocity': (0, 0),
                    'has_valuable': False,
                    'valuable_objects': [],
                    'tracking_id': None,
                    'had_firearm': False,
                    'had_phone': False,
                    'had_blade': False,
                    'last_seen': 0,
                    'missing': False
                }

        return tracked_people
    
    def track_objects(self, objects_detected):
        """Seguimiento de objetos de valor"""
        tracked_objects = {}
        used_tracks = set()

        for track_data in self.object_tracks.values():
            track_data['missing'] = True
        
        for obj in objects_detected:
            center = obj['center']
            bbox = obj['bbox']
            best_id = None
            best_score = float('inf')
            
            for track_id, track_data in self.object_tracks.items():
                if track_id in used_tracks:
                    continue
                if not track_data['positions']:
                    continue
                if self.frame_count - track_data['last_seen'] > self.track_max_age:
                    continue
                
                last_pos = track_data['positions'][-1]
                predicted = last_pos
                if track_data['velocity'] != (0, 0):
                    vx, vy = track_data['velocity']
                    predicted = (last_pos[0] + vx, last_pos[1] + vy)
                
                dist = self.distance(center, predicted)
                overlap = self.bbox_iou(bbox, track_data['bbox'])
                score = dist - overlap * 120
                
                if score < best_score and dist < self.distance_threshold:
                    best_score = score
                    best_id = track_id
            
            if best_id is not None:
                track_data = self.object_tracks[best_id]
                last_pos = track_data['positions'][-1]
                velocity = (center[0] - last_pos[0], center[1] - last_pos[1])
                track_data['positions'].append(center)
                track_data['bbox'] = bbox
                track_data['velocity'] = velocity
                track_data['class_name'] = obj['class_name']
                track_data['class_id'] = obj['class']
                track_data['last_seen'] = self.frame_count
                tracked_objects[best_id] = track_data
                used_tracks.add(best_id)
            else:
                new_id = self.next_object_id
                self.next_object_id += 1
                self.object_tracks[new_id]['positions'] = [center]
                self.object_tracks[new_id]['bbox'] = bbox
                self.object_tracks[new_id]['velocity'] = (0, 0)
                self.object_tracks[new_id]['class_name'] = obj['class_name']
                self.object_tracks[new_id]['class_id'] = obj['class']
                self.object_tracks[new_id]['last_seen'] = self.frame_count
                self.object_tracks[new_id]['owner_id'] = None
                self.object_tracks[new_id]['missing'] = False
                self.object_tracks[new_id]['owner_changed'] = False
                tracked_objects[new_id] = self.object_tracks[new_id]

        # Mantener objetos detectados recientemente aún si se pierden temporalmente
        for track_id, track_data in self.object_tracks.items():
            if track_id in tracked_objects:
                continue
            if self.frame_count - track_data['last_seen'] <= self.track_max_age:
                tracked_objects[track_id] = track_data

        return tracked_objects
    
    def match_objects_to_people(self, tracked_people, tracked_objects):
        """Asociar objetos a personas. Una vez asignado, se mantiene a menos que otro propietario claro lo tome"""
        object_transfer = False
        
        # Reset ownership lists pero mantener propietarios previos
        for person_data in tracked_people.values():
            person_data['valuable_objects'] = []
            person_data['has_valuable'] = False
        
        for obj_id, obj_data in tracked_objects.items():
            closest_person = None
            min_distance = float('inf')
            closest_overlap = 0.0
            
            # Buscar la persona más cercana
            for person_id, person_data in tracked_people.items():
                if person_data['bbox'] is None:
                    continue
                person_center = self.get_center(person_data['bbox'])
                dist = self.distance(obj_data['positions'][-1], person_center)
                if len(person_data['positions']) > 1:
                    prev_pos = person_data['positions'][-2]
                    dist = min(dist, self.distance(obj_data['positions'][-1], prev_pos))
                overlap = self.bbox_iou(obj_data['bbox'], person_data['bbox'])
                if dist < min_distance or (dist == min_distance and overlap > closest_overlap):
                    min_distance = dist
                    closest_person = person_id
                    closest_overlap = overlap
            
            # Si el objeto ya tiene propietario
            threshold = 60 if obj_data['class_id'] in [39, 40, 41, 42] else 80 if obj_data['class_id'] == 67 else 100
            min_overlap = 0.15 if obj_data['class_id'] in [39, 40, 41, 42] else 0.08 if obj_data['class_id'] == 67 else 0.05
            if obj_data['owner_id'] is not None:
                if obj_data['owner_id'] not in tracked_people:
                    if closest_person is not None and (closest_overlap >= min_overlap or min_distance < threshold):
                        obj_data['owner_changed'] = True
                        object_transfer = True
                        obj_data['owner_id'] = closest_person
                else:
                    current_owner = tracked_people[obj_data['owner_id']]
                    owner_overlap = self.bbox_iou(obj_data['bbox'], current_owner['bbox'])
                    owner_dist = self.distance(obj_data['positions'][-1], self.get_center(current_owner['bbox']))
                    if self.point_in_bbox(obj_data['positions'][-1], current_owner['bbox']):
                        owner_overlap = max(owner_overlap, 0.3)
                    
                    if closest_person is not None and closest_person != obj_data['owner_id']:
                        if (closest_overlap > owner_overlap + 0.2 and closest_overlap >= min_overlap) or (min_distance + 20 < owner_dist and closest_overlap >= min_overlap):
                            obj_data['owner_changed'] = True
                            object_transfer = True
                            obj_data['owner_id'] = closest_person
            else:
                if closest_person is not None and (closest_overlap >= min_overlap or min_distance < threshold):
                    obj_data['owner_id'] = closest_person
            
            # Actualizar lista de objetos de la persona
            if obj_data['owner_id'] is not None and obj_data['owner_id'] in tracked_people:
                tracked_people[obj_data['owner_id']]['valuable_objects'].append(obj_data)
                tracked_people[obj_data['owner_id']]['has_valuable'] = True
                
                # Marcar permanentemente si tiene arma, celular o arma blanca
                if obj_data['class_id'] in [39, 40, 41, 42]:
                    tracked_people[obj_data['owner_id']]['had_firearm'] = True
                elif obj_data['class_id'] == 67:
                    tracked_people[obj_data['owner_id']]['had_phone'] = True
                elif obj_data['class_id'] == 43:
                    tracked_people[obj_data['owner_id']]['had_blade'] = True
                
                # Si el objeto cambió de propietario, quitar las etiquetas del anterior propietario
                if obj_data['owner_changed']:
                    for person_id, person_data in tracked_people.items():
                        if person_id != obj_data['owner_id']:
                            # Si es un arma y esta persona no la tiene en este frame
                            if obj_data['class_id'] in [39, 40, 41, 42] and person_data['had_firearm']:
                                has_firearm_now = any(o['class_id'] in [39, 40, 41, 42] 
                                                      for o in person_data['valuable_objects'])
                                if not has_firearm_now:
                                    person_data['had_firearm'] = False
                            
                            # Si es un celular y esta persona no lo tiene en este frame
                            elif obj_data['class_id'] == 67 and person_data['had_phone']:
                                has_phone_now = any(o['class_id'] == 67 
                                                   for o in person_data['valuable_objects'])
                                if not has_phone_now:
                                    person_data['had_phone'] = False
                            elif obj_data['class_id'] == 43 and person_data['had_blade']:
                                has_blade_now = any(o['class_id'] == 43 
                                                    for o in person_data['valuable_objects'])
                                if not has_blade_now:
                                    person_data['had_blade'] = False
        
        return tracked_people, object_transfer
    
    def analyze_theft(self, tracked_people, suspicious_activity, object_transfer):
        """Analizar si hay posible robo según diagrama"""
        
        theft_probability = 0.0
        theft_details = {
            'has_people': False,
            'people_with_valuables': False,
            'suspicious_activity': False,
            'object_transfer': False,
            'suspicious_running': False
        }
        
        # Condición 1: ¿Hay personas?
        if len(tracked_people) > 0:
            theft_details['has_people'] = True
        else:
            return 0.0, theft_details
        
        # Condición 2: ¿Las personas tienen objetos de valor?
        people_with_valuables = [p for p in tracked_people.values() if p['has_valuable']]
        if len(people_with_valuables) > 0:
            theft_details['people_with_valuables'] = True
        else:
            return 0.0, theft_details
        
        # Condición 3: ¿Hay pelea o forcejeo?
        if suspicious_activity['fight']:
            theft_details['suspicious_activity'] = True
            theft_probability += 0.3
        
        # Condición 4: ¿El objeto cambia de persona o desaparece?
        if object_transfer:
            theft_details['object_transfer'] = True
            theft_probability += 0.4
        
        # Condición 5: ¿El supuesto ladrón hulle (corre)?
        if suspicious_activity['running']:
            theft_details['suspicious_running'] = True
            theft_probability += 0.3
            
            # Aumentar si alguien corre rápido, no solo si el modelo detecta running
            max_speed = 0.0
            for person_data in tracked_people.values():
                vx, vy = person_data['velocity']
                speed = np.sqrt(vx**2 + vy**2)
                max_speed = max(max_speed, speed)
            if max_speed > 30:
                theft_details['fast_running'] = True
                theft_probability += 0.3
            else:
                theft_details['fast_running'] = False
        else:
            theft_details['fast_running'] = False
        
        # Si hay pelea o carrera y también transferencia/propiedad sospechosa
        if theft_details['suspicious_activity'] or theft_details['suspicious_running']:
            if theft_details['object_transfer']:
                theft_probability = min(1.0, theft_probability + 0.2)
        
        return min(theft_probability, 1.0), theft_details
    
    def draw_frame(self, frame, tracked_people, tracked_objects, suspicious_activity, theft_probability):
        """Dibujar información en frame"""
        
        # Dibujar personas
        for person_id, person_data in tracked_people.items():
            if person_data['bbox'] is not None:
                bbox = person_data['bbox'].astype(int)
                stable_label = person_data.get('tracking_id', person_id)
                
                # Usar registro persistente de objetos que ha tenido
                has_phone = person_data['had_phone']
                has_firearm = person_data['had_firearm']
                
                # Determinar color y etiqueta
                if theft_probability > 0.7:  # Es un ladrón probable
                    if has_phone:
                        label = f"P{stable_label}: LADRÓN CON CELULAR"
                        color = (0, 0, 200)  # Rojo oscuro
                    elif has_firearm:
                        label = f"P{stable_label}: PERSONA CON ARMA"
                        color = (0, 0, 255)  # Rojo puro
                    else:
                        label = f"P{stable_label}: LADRÓN"
                        color = (0, 0, 200)  # Rojo oscuro
                else:
                    if has_phone:
                        label = f"P{stable_label}: PERSONA CON CELULAR"
                        color = (0, 200, 0)  # Verde oscuro
                    elif has_firearm:
                        label = f"P{stable_label}: PERSONA CON ARMA"
                        color = (0, 0, 255)  # Rojo
                    else:
                        label = f"P{stable_label}"
                        color = (0, 165, 255)  # Naranja
                
                # Dibujar cuadro
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 3)
                
                # Información
                vx, vy = person_data['velocity']
                speed = np.sqrt(vx**2 + vy**2)
                
                # Dibujar etiqueta
                cv2.putText(frame, label, (bbox[0], bbox[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Trayectoria
                if len(person_data['positions']) > 1:
                    points = np.array(person_data['positions'][-20:], dtype=np.int32)
                    cv2.polylines(frame, [points], False, color, 1)
        
        # Dibujar objetos detectados (comentado - sin líneas naranjas)
        # for obj_id, obj_data in tracked_objects.items():
        #     if obj_data['bbox'] is None:
        #         continue
        #     bbox = obj_data['bbox'].astype(int)
        #     obj_color = (255, 215, 0)
        #     cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), obj_color, 2)
        #     owner_text = f"O{obj_id}:{obj_data['class_name']}"
        #     if obj_data['owner_id'] is not None:
        #         owner_text += f"->P{obj_data['owner_id']}"
        #     cv2.putText(frame, owner_text, (bbox[0], bbox[3] + 15),
        #                cv2.FONT_HERSHEY_SIMPLEX, 0.45, obj_color, 1)
        #     if obj_data['owner_changed']:
        #         cv2.putText(frame, "TRANSFERIDO", (bbox[0], bbox[1] - 25),
        #                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        
        # Información de alerta
        h, w = frame.shape[:2]
        alert_y = 30
        
        cv2.putText(frame, f"Personas: {len(tracked_people)}", (10, alert_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        alert_y += 25
        
        # Contadores persistentes basados en persona con objeto identificado
        phone_count = sum(1 for p in tracked_people.values() if p['had_phone'])
        firearm_count = sum(1 for p in tracked_people.values() if p['had_firearm'])
        blade_count = sum(1 for p in tracked_people.values() if p['had_blade'])

        cv2.putText(frame, f"Celulares: {phone_count}", (10, alert_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255) if phone_count > 0 else (160, 160, 160), 2)
        alert_y += 25

        cv2.putText(frame, f"Armas de fuego: {firearm_count}", (10, alert_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if firearm_count > 0 else (160, 160, 160), 2)
        alert_y += 25

        cv2.putText(frame, f"Armas blancas: {blade_count}", (10, alert_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255) if blade_count > 0 else (160, 160, 160), 2)
        alert_y += 25
        
        if suspicious_activity['fight']:
            cv2.putText(frame, "¡PELEA DETECTADA!", (10, alert_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            alert_y += 25
        
        if suspicious_activity['running']:
            cv2.putText(frame, "¡CORRIENDO!", (10, alert_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            alert_y += 25
        
        # Probabilidad de robo
        color_prob = (0, 0, 255) if theft_probability > 0.7 else (0, 255, 255)
        cv2.putText(frame, f"Probabilidad Robo: {theft_probability:.1%}", (10, alert_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_prob, 2)
        
        return frame
    
    def log_theft(self, frame, theft_details, theft_probability):
        """Guardar registro de posible robo"""
        
        timestamp = datetime.now().isoformat()
        
        # Guardar imagen
        img_filename = f"theft_{timestamp.replace(':', '-')}.jpg"
        cv2.imwrite(img_filename, frame)
        
        # Guardar registro JSON
        record = {
            'timestamp': timestamp,
            'probability': theft_probability,
            'details': theft_details,
            'image': img_filename,
            'frame_number': self.frame_count
        }
        
        # Agregar a archivo JSON
        records_file = "theft_records.json"
        if os.path.exists(records_file):
            with open(records_file, 'r') as f:
                records = json.load(f)
        else:
            records = []
        
        records.append(record)
        
        with open(records_file, 'w') as f:
            json.dump(records, f, indent=2)
        
        print(f"✓ Imagen guardada: {img_filename}")
        print(f"✓ Registros guardados en: {records_file}")
    
    def process_video(self):
        """Procesar video y detectar robos"""
        
        print(f"Procesando video: {self.video_source}")
        print(f"Archivo existe: {os.path.exists(self.video_source)}")
        print("Iniciando procesamiento de video...")
        print(f"Umbral de alarma: {self.alarm_threshold:.1%}")
        print("Presiona 'q' para salir, 'ESPACIO' para pausar/reanudar\n")
        
        paused = False
        
        while True:
            if not paused:
                ret, frame = self.cap.read()
                if not ret:
                    if self.frame_count == 0:
                        raise RuntimeError(f"No se pudo leer el primer frame del video: {self.video_source}")
                    print(f"Finalizó el video o se perdió la lectura en el frame {self.frame_count}.")
                    break
                
                self.frame_count += 1
            
            # Detecciones
            people, objects_detected = self.detect_people_and_objects(frame)
            
            # Tracking
            tracked_people = self.track_people(people, frame)
            tracked_objects = self.track_objects(objects_detected)
            
            # Asociar objetos a personas y detectar cambio de dueño
            tracked_people, object_transfer = self.match_objects_to_people(tracked_people, tracked_objects)
            
            # Detectar actividades sospechosas solo si hay personas con objetos
            people_with_valuables = sum(1 for p in tracked_people.values() if p['has_valuable'])
            
            if people_with_valuables > 0:
                suspicious_activity = self.detect_suspicious_activity(frame)
            else:
                suspicious_activity = {
                    'fight': False,
                    'running': False,
                    'suspicious_activity': False,
                    'confidence': 0
                }
            
            # Analizar si hay posible robo
            theft_probability, theft_details = self.analyze_theft(tracked_people, suspicious_activity, object_transfer)
            
            if object_transfer and suspicious_activity['running']:
                phone_transfer = any(
                    any(o['class_id'] == 67 for o in person_data['valuable_objects'])
                    for person_data in tracked_people.values()
                )
                if phone_transfer:
                    print("persona con celular cambio de dueño y ladron huye")
            
            # Dibujar
            frame_display = self.draw_frame(frame, tracked_people, tracked_objects, suspicious_activity, theft_probability)
            
            # Mostrar
            cv2.imshow("Detección de Robo Menor", frame_display)
            
            # Imprimir probabilidad si es mayor a cero
            if theft_probability > 0:
                print(f"Probabilidad de robo: {theft_probability:.1%}")

            # Alerta si hay alta probabilidad
            if theft_probability >= self.alarm_threshold:
                print("\n" + "="*60)
                print("⚠️  ALERTA DE POSIBLE ROBO MENOR ⚠️")
                print("="*60)
                print(f"Probabilidad: {theft_probability:.1%}")
                print(f"Detalles: {theft_details}")
                print(f"Timestamp: {datetime.now()}")
                print("="*60 + "\n")
                
                self.log_theft(frame, theft_details, theft_probability)
                
                # Pausar
                print("Presiona ESPACIO para reanudar...")
                paused = True
            
            # Controles
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                paused = not paused
                if not paused:
                    print("Reanudando video...")
                else:
                    print("Video pausado. Presiona ESPACIO para reanudar...")
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("Sistema cerrado")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Detecta robos menores en video usando YOLO.")
    parser.add_argument("video", nargs="?", default=VIDEO_DEFAULT, help="Ruta al archivo de video")
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        raise FileNotFoundError(f"No se encontró el video: {args.video}")
    
    system = TheftDetectionSystem(video_source=args.video)
    system.process_video()


if __name__ == "__main__":
    main()