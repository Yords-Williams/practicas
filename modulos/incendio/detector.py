import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import cv2
import numpy as np


class FireDetectionSystem:
    """Detector de incendios para video en tiempo real.
    
    Usa detección híbrida:
    - Modelo YOLO entrenado en incendio/best.pt (principal)
    - Análisis de color/textura HSV como respaldo
    """

    def __init__(self, db_path: str = "incidents.db", config_file: str = "fire_config.json"):
        self.db_path = db_path
        self.config_file = config_file
        self.config = self._load_config()
        self._init_db()
        self.last_reported = {}

        # Cargar modelo YOLO para incendios (best.pt en esta misma carpeta)
        self.yolo_model = None
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _yolo_path = os.path.join(_script_dir, "best.pt")
        if os.path.exists(_yolo_path):
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO(_yolo_path)
                print(f"[FireDetector] ✓ Modelo YOLO cargado: {_yolo_path}")
            except Exception as e:
                print(f"[FireDetector] ⚠ No se pudo cargar YOLO ({e}). Usando solo análisis de color.")
        else:
            print(f"[FireDetector] ⚠ Modelo no encontrado en {_yolo_path}. Usando solo análisis de color.")

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        default_config = {
            "threshold": 0.12,
            "min_area": 180,
            "cooldown_seconds": 60,
            "report_recipients": {
                "emails": ["admin@example.com"],
                "phones": ["+1234567890"]
            },
            "notifications": {
                "telegram": False,
                "email": False,
                "whatsapp": False
            }
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            confidence REAL NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            report_sent INTEGER NOT NULL DEFAULT 0,
            image_path TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS recipients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)
        conn.commit()
        conn.close()

    def detect_fire(self, frame) -> Tuple[bool, float, str]:
        if frame is None:
            return False, 0.0, "Sin frame"

        # --- Detección principal: modelo YOLO entrenado ---
        if self.yolo_model is not None:
            try:
                results = self.yolo_model(frame, verbose=False, conf=self.config.get("threshold", 0.12))
                if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                    best_conf = float(max(results[0].boxes.conf).item())
                    label = results[0].names[int(results[0].boxes.cls[0].item())]
                    return True, round(best_conf, 3), f"Incendio/humo detectado por YOLO: {label} ({best_conf:.2f})"
            except Exception as e:
                print(f"[FireDetector] Error YOLO: {e}")

        # --- Detección de respaldo: análisis de color HSV ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_red1 = np.array([0, 80, 80], dtype=np.uint8)
        lower_red2 = np.array([170, 80, 80], dtype=np.uint8)
        upper_red1 = np.array([10, 255, 255], dtype=np.uint8)
        upper_red2 = np.array([180, 255, 255], dtype=np.uint8)

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Estimar intensidad amarilla/roja
        yellow_mask = cv2.inRange(hsv, np.array([15, 80, 80]), np.array([45, 255, 255]))
        combined = cv2.bitwise_or(mask, yellow_mask)
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return False, 0.0, "No se detectó señal de incendio"

        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        confidence = min(0.99, area / max(1.0, self.config.get("min_area", 180)))

        if area >= self.config.get("min_area", 180):
            details = f"Posible incendio detectado con área {int(area)} px (color HSV)"
            return True, round(confidence, 3), details

        return False, round(confidence, 3), f"Señal débil: área {int(area)} px"

    def analyze_frame(self, frame, camera_name: str = "Cámara") -> Optional[Dict]:
        detected, confidence, details = self.detect_fire(frame)
        if not detected:
            return None

        now = datetime.now()
        key = f"{camera_name}:{now.strftime('%Y%m%d%H%M')}"
        cooldown = self.config.get("cooldown_seconds", 60)
        if camera_name in self.last_reported:
            if (time.time() - self.last_reported[camera_name]) < cooldown:
                return None

        self.last_reported[camera_name] = time.time()

        incident = {
            "camera_name": camera_name,
            "incident_type": "fire",
            "severity": "ALTO" if confidence > 0.5 else "MEDIO",
            "confidence": confidence,
            "details": details,
            "created_at": now.isoformat(timespec="seconds"),
            "status": "open",
            "report_sent": 0,
            "image_path": None,
        }
        self.save_incident(incident)
        self.send_report(incident)
        return incident

    def save_incident(self, incident: Dict):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO incidents (camera_name, incident_type, severity, confidence, details, created_at, status, report_sent, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident["camera_name"],
                incident["incident_type"],
                incident["severity"],
                incident["confidence"],
                incident["details"],
                incident["created_at"],
                incident["status"],
                incident["report_sent"],
                incident.get("image_path"),
            ),
        )
        conn.commit()
        conn.close()

    def add_recipient(self, name: str, email: Optional[str] = None, phone: Optional[str] = None):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO recipients (name, email, phone, active, created_at) VALUES (?, ?, ?, 1, ?)",
            (name, email, phone, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        conn.close()

    def list_recipients(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, phone, active FROM recipients")
        rows = cur.fetchall()
        conn.close()
        return [
            {"id": row[0], "name": row[1], "email": row[2], "phone": row[3], "active": bool(row[4])}
            for row in rows
        ]

    def send_report(self, incident: Dict):
        recipients = self.list_recipients()
        if not recipients:
            return False

        message = (
            f"🚨 INCIDENTE DE INCENDIO\n"
            f"Cámara: {incident['camera_name']}\n"
            f"Severidad: {incident['severity']}\n"
            f"Confianza: {incident['confidence']:.2f}\n"
            f"Detalles: {incident['details']}\n"
            f"Hora: {incident['created_at']}"
        )

        for recipient in recipients:
            if recipient.get("email"):
                print(f"[FIRE] Correo simulado para {recipient['email']}: {message}")
            if recipient.get("phone"):
                print(f"[FIRE] SMS simulado para {recipient['phone']}: {message}")

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE incidents SET report_sent = 1 WHERE id = (SELECT MAX(id) FROM incidents)")
        conn.commit()
        conn.close()
        return True


if __name__ == "__main__":
    detector = FireDetectionSystem()
    detector.add_recipient("Admin", "admin@example.com", "+1234567890")

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[80:160, 120:200] = [0, 80, 255]
    frame[90:150, 130:190] = [0, 180, 255]
    frame[100:140, 140:180] = [30, 255, 255]
    print(detector.analyze_frame(frame, camera_name="Cámara 1"))
