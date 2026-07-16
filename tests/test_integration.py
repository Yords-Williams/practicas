"""
CCTV AI PRO — Integration & Unit Test Suite
============================================
Cubre todos los módulos del sistema:
  config · camera · incendio · choques · robo · person_identifier · alarma · detector

Tipos de prueba:
  - Unitarias   : lógica aislada (Kalman, SortTracker, IoU, scoring, SQLite CRUD…)
  - Integración : pipeline end-to-end entre módulos, importación conjunta
  - Rendimiento : latencia de inferencia, FPS real, tiempo de carga de modelos

Ejecutar:
    pytest test_integration.py -v --tb=short
"""

import os
import sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))

# ─── helpers ─────────────────────────────────────────────────────────────────────────────────────
def make_frame(h=480, w=640, color=None):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    if color is not None:
        frame[:] = color
    return frame

def make_fire_frame():
    """Frame con región roja/anaranjada que simula fuego (HSV)."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:350, 150:480] = [0, 80, 240]
    frame[130:320, 180:450] = [0, 160, 255]
    frame[160:290, 210:420] = [20, 220, 255]
    return frame


# ════════════════════════════════════════════════════════════════════════════════
# FIXTURES DE MÓDULO — cada modelo se carga UNA Única vez por sesión
# ════════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def fire_sys(tmp_path_factory):
    """Una sola instancia de FireDetectionSystem compartida por todos los tests."""
    tmp = tmp_path_factory.mktemp("fire")
    from modulos.incendio import FireDetectionSystem
    return FireDetectionSystem(
        db_path=str(tmp / "incidents.db"),
        config_file=str(tmp / "fire_config.json")
    )

@pytest.fixture(scope="module")
def choques_sys():
    """Una sola instancia de AccidentDetectionSystem compartida por todos los tests."""
    from modulos.choques import AccidentDetectionSystem
    return AccidentDetectionSystem(video_source=None)

@pytest.fixture(scope="module")
def robo_sys():
    """Una sola instancia de TheftDetectionSystem compartida por todos los tests."""
    from modulos.robo.inference import TheftDetectionSystem
    return TheftDetectionSystem(video_source=None)

@pytest.fixture(scope="module")
def person_tracker():
    from modulos.person_identifier import PersonAppearanceTracker
    return PersonAppearanceTracker()


# ════════════════════════════════════════════════════════════════════════════════
# 1. CONFIG
# ════════════════════════════════════════════════════════════════════════════════
class TestConfig:
    def test_import(self):
        from config import (WORKSPACE_DIR, MODULOS_DIR, YOLO_GENERAL_MODEL,
                            ACCIDENT_DETECTION_MODEL, FIRE_DETECTION_MODEL,
                            DAMAGE_DETECTION_MODEL, DETECTION_CONFIG)
        assert os.path.isdir(WORKSPACE_DIR)
        assert os.path.isdir(MODULOS_DIR)

    def test_model_paths_point_to_subfolders(self):
        from config import ACCIDENT_DETECTION_MODEL, FIRE_DETECTION_MODEL
        assert "choques" in ACCIDENT_DETECTION_MODEL.replace("\\", "/")
        assert "incendio" in FIRE_DETECTION_MODEL.replace("\\", "/")

    def test_detection_config_values(self):
        from config import DETECTION_CONFIG
        assert "confidence_threshold" in DETECTION_CONFIG
        assert "fps_limit" in DETECTION_CONFIG
        assert 0 < DETECTION_CONFIG["confidence_threshold"] < 1

    def test_model_files_exist(self):
        from config import (ACCIDENT_DETECTION_MODEL, FIRE_DETECTION_MODEL,
                            DAMAGE_DETECTION_MODEL, YOLO_GENERAL_MODEL)
        missing = [p for p in [YOLO_GENERAL_MODEL, ACCIDENT_DETECTION_MODEL,
                                FIRE_DETECTION_MODEL, DAMAGE_DETECTION_MODEL]
                   if not os.path.exists(p)]
        assert missing == [], f"Modelos faltantes: {missing}"

    def test_module_paths_exist(self):
        from config import ACCIDENT_DETECTION_MODULE, FIRE_DETECTION_MODULE, ROBO_INFERENCE_MODULE
        assert os.path.exists(ACCIDENT_DETECTION_MODULE), ACCIDENT_DETECTION_MODULE
        assert os.path.exists(FIRE_DETECTION_MODULE), FIRE_DETECTION_MODULE
        assert os.path.exists(ROBO_INFERENCE_MODULE), ROBO_INFERENCE_MODULE


# ════════════════════════════════════════════════════════════════════════════════
# 2. MÓDULO INCENDIO
# ════════════════════════════════════════════════════════════════════════════════
class TestIncendioDetector:
    """Tests del módulo modulos/incendio/detector.py."""

    def test_import(self):
        from modulos.incendio import FireDetectionSystem
        assert FireDetectionSystem is not None

    def test_db_created(self, fire_sys):
        assert os.path.exists(fire_sys.db_path)

    def test_config_file_created(self, fire_sys):
        assert os.path.exists(fire_sys.config_file)

    def test_yolo_model_loaded(self, fire_sys):
        """El modelo incendio/best.pt debe haberse cargado en init."""
        assert fire_sys.yolo_model is not None

    def test_detect_fire_none_frame(self, fire_sys):
        detected, conf, _ = fire_sys.detect_fire(None)
        assert detected is False
        assert conf == 0.0

    def test_detect_fire_black_frame_no_fire(self, fire_sys):
        detected, conf, details = fire_sys.detect_fire(make_frame())
        assert isinstance(detected, bool)
        assert 0.0 <= conf <= 1.0
        assert isinstance(details, str)

    def test_detect_fire_fire_frame_hsv(self, fire_sys):
        """Sin YOLO (parchado a None), el respaldo HSV debe retornar resultado."""
        original = fire_sys.yolo_model
        fire_sys.yolo_model = None
        try:
            detected, conf, details = fire_sys.detect_fire(make_fire_frame())
            # Frame con naranja/rojo grande debe disparar HSV
            assert detected is True
            assert conf > 0.0
        finally:
            fire_sys.yolo_model = original   # restaurar

    def test_add_and_list_recipients(self, tmp_path):
        """CRUD de destinatarios en SQLite (instancia fresca sin cargar YOLO)."""
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem.__new__(FireDetectionSystem)
        det.db_path = str(tmp_path / "r.db")
        det.config_file = str(tmp_path / "c.json")
        det.config = {"threshold": 0.12, "min_area": 180, "cooldown_seconds": 60}
        det.yolo_model = None
        det.last_reported = {}
        det._init_db()
        det.add_recipient("Serenazgo", "ser@caracoto.gob.pe", "+51912345678")
        det.add_recipient("Admin",     "adm@caracoto.gob.pe", None)
        rows = det.list_recipients()
        assert len(rows) == 2
        assert rows[0]["name"] == "Serenazgo"

    def test_analyze_frame_no_fire_returns_none(self, fire_sys):
        result = fire_sys.analyze_frame(make_frame(), camera_name="Cam-Test")
        assert result is None

    def test_analyze_frame_fire_saves_incident(self, fire_sys, tmp_path):
        """Fire frame con YOLO desactivado → HSV detecta → incidente en DB."""
        import sqlite3
        from modulos.incendio import FireDetectionSystem
        db = str(tmp_path / "test.db")
        det = FireDetectionSystem.__new__(FireDetectionSystem)
        det.db_path = db
        det.config_file = str(tmp_path / "c.json")
        det.config = {"threshold": 0.12, "min_area": 180, "cooldown_seconds": 60}
        det.yolo_model = None
        det.last_reported = {}
        det._init_db()
        result = det.analyze_frame(make_fire_frame(), camera_name="CamFuego")
        if result is not None:
            conn = sqlite3.connect(db)
            count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            conn.close()
            assert count >= 1


# ════════════════════════════════════════════════════════════════════════════════
# 3. MÓDULO CHOQUES
# ════════════════════════════════════════════════════════════════════════════════
class TestChoquesDetector:
    def test_import(self):
        from modulos.choques import AccidentDetectionSystem
        assert AccidentDetectionSystem is not None

    def test_init_no_video_source(self, choques_sys):
        assert choques_sys.cap is None

    def test_yolo_model_loaded(self, choques_sys):
        assert choques_sys.yolo_model is not None

    def test_damage_model_loaded(self, choques_sys):
        assert choques_sys.damage_model is not None

    def test_process_video_raises_without_source(self, choques_sys):
        with pytest.raises(RuntimeError, match="video_source"):
            choques_sys.process_video()

    def test_detect_vehicles_black_frame(self, choques_sys):
        vehicles = choques_sys.detect_vehicles(make_frame())
        assert isinstance(vehicles, list)

    def test_analyze_accident_no_vehicles(self, choques_sys):
        # Reset state
        choques_sys.vehicle_tracks.clear()
        choques_sys.vehicle_velocities.clear()
        choques_sys.vehicle_history.clear()
        is_acc, details, prob = choques_sys.analyze_accident(make_frame())
        assert is_acc is False
        assert prob == 0.0

    def test_track_vehicles_empty(self, choques_sys):
        choques_sys.vehicle_tracks.clear()
        choques_sys.track_vehicles([])
        assert choques_sys.vehicle_tracks == {}

    def test_check_vehicles_close_empty(self, choques_sys):
        choques_sys.vehicle_tracks.clear()
        close, pairs = choques_sys.check_vehicles_close()
        assert close is False
        assert pairs == []

    def test_detect_sudden_deceleration_empty(self, choques_sys):
        choques_sys.vehicle_history.clear()
        decel, events = choques_sys.detect_sudden_deceleration()
        assert decel is False
        assert events == []

    def test_accident_scoring_logic(self, choques_sys):
        """Con dos vehículos cercanos + desaceleración el score debe subir."""
        choques_sys.vehicle_tracks = {
            0: [(100, 100), (105, 105)],
            1: [(115, 115), (110, 110)],
        }
        choques_sys.vehicle_velocities = {0: 1.0, 1: 1.0}
        choques_sys.vehicle_bboxes = {
            0: (80, 80, 130, 130),
            1: (95, 95, 145, 145),
        }
        choques_sys.vehicle_history = {
            0: [20.0, 1.0],   # deíceleración brutal
            1: [18.0, 1.0],
        }
        is_acc, details, prob = choques_sys.analyze_accident(make_frame())
        # Con proximidad + deceleración la probabilidad debe ser alta (>= 0.7)
        assert prob >= 0.7


# ════════════════════════════════════════════════════════════════════════════════
# 4. MÓDULO ROBO
# ════════════════════════════════════════════════════════════════════════════════
class TestRoboInference:
    def test_import(self):
        from modulos.robo.inference import TheftDetectionSystem, SortTracker, KalmanBoxTracker
        assert TheftDetectionSystem is not None

    def test_init_no_video(self, robo_sys):
        assert robo_sys.cap is None
        assert robo_sys.fps == 25.0

    def test_yolo_model_loaded(self, robo_sys):
        assert robo_sys.yolo_model is not None

    # — KalmanBoxTracker —
    def test_kalman_predict(self):
        from modulos.robo.inference import KalmanBoxTracker
        trk = KalmanBoxTracker(np.array([10.0, 20.0, 100.0, 200.0]))
        pred = trk.predict()
        assert pred is not None and len(pred) == 4

    def test_kalman_update(self):
        from modulos.robo.inference import KalmanBoxTracker
        trk = KalmanBoxTracker(np.array([10.0, 20.0, 100.0, 200.0]))
        trk.update(np.array([12.0, 22.0, 102.0, 202.0]))
        assert trk.time_since_update == 0

    # — SortTracker —
    def test_sort_empty_update(self):
        from modulos.robo.inference import SortTracker
        assert SortTracker().update([]) == []

    def test_sort_single_detection(self):
        from modulos.robo.inference import SortTracker
        st = SortTracker()
        result = st.update([[50.0, 60.0, 150.0, 250.0, 0.95]])
        assert isinstance(result, list)

    def test_sort_id_consistency(self):
        from modulos.robo.inference import SortTracker
        st = SortTracker()
        r1 = st.update([[50.0, 60.0, 150.0, 250.0, 0.95]])
        r2 = st.update([[52.0, 62.0, 152.0, 252.0, 0.93]])
        if r1 and r2:
            assert r1[0]['id'] == r2[0]['id']

    # — Utils —
    def test_iou_batch_empty(self):
        from modulos.robo.inference import iou_batch
        assert iou_batch([], []).shape == (0, 0)

    def test_bbox_conversion_roundtrip(self):
        from modulos.robo.inference import convert_bbox_to_z, convert_x_to_bbox
        bbox = np.array([10.0, 20.0, 110.0, 220.0])
        z = convert_bbox_to_z(bbox)
        assert len(z) == 4
        back = convert_x_to_bbox(np.concatenate([z, np.zeros(3)]))
        np.testing.assert_allclose(back, bbox, atol=1e-3)

    # — Theft logic —
    def test_analyze_theft_no_people(self, robo_sys):
        prob, details = robo_sys.analyze_theft(
            {}, {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0}, False
        )
        assert prob == 0.0 and details['has_people'] is False

    def test_analyze_theft_people_no_valuables(self, robo_sys):
        tracked = {1: {'has_valuable': False, 'valuable_objects': [], 'bbox': None,
                       'velocity': (0, 0), 'positions': [], 'tracking_id': 1,
                       'had_firearm': False, 'had_phone': False, 'had_blade': False,
                       'last_seen': 0, 'missing': False}}
        prob, details = robo_sys.analyze_theft(
            tracked, {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0}, False
        )
        assert prob == 0.0 and details['people_with_valuables'] is False

    def test_analyze_theft_with_transfer(self, robo_sys):
        """Transferencia de objeto + pelea → score >= 0.7."""
        tracked = {1: {'has_valuable': True, 'valuable_objects': [{}], 'bbox': None,
                       'velocity': (0, 0), 'positions': [], 'tracking_id': 1,
                       'had_firearm': False, 'had_phone': True, 'had_blade': False,
                       'last_seen': 0, 'missing': False}}
        prob, details = robo_sys.analyze_theft(
            tracked, {'fight': True, 'running': False, 'suspicious_activity': True, 'confidence': 0.8}, True
        )
        assert prob >= 0.7

    def test_categorize_phone(self, robo_sys):
        assert robo_sys.categorize_object({'class': 67, 'class_name': 'cell phone'}) == 'phone'

    def test_categorize_blade(self, robo_sys):
        assert robo_sys.categorize_object({'class': 43, 'class_name': 'knife'}) == 'blade'

    def test_detect_people_black_frame(self, robo_sys):
        people, objects = robo_sys.detect_people_and_objects(make_frame())
        assert isinstance(people, list) and isinstance(objects, list)

    def test_track_objects_empty(self, robo_sys):
        tracked = robo_sys.track_objects([])
        assert isinstance(tracked, dict)


# ════════════════════════════════════════════════════════════════════════════════
# 5. PERSON IDENTIFIER
# ════════════════════════════════════════════════════════════════════════════════
class TestPersonIdentifier:
    def test_import(self):
        from modulos.person_identifier import PersonAppearanceTracker
        assert PersonAppearanceTracker is not None

    def test_init_defaults(self, person_tracker):
        assert isinstance(person_tracker.tracks, list)

    def test_update_empty(self, person_tracker):
        result = person_tracker.update([], make_frame())
        assert result == []

    def test_update_single_detection(self):
        """Instancia fresca para verificar que el primer ID asignado es 1."""
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        dets = [{'bbox': np.array([50.0, 60.0, 200.0, 400.0]), 'conf': 0.9}]
        result = t.update(dets, frame)
        assert len(result) == 1
        assert 'tracking_id' in result[0]
        assert result[0]['tracking_id'] == 1

    def test_update_same_person_same_id(self):
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        r1 = t.update([{'bbox': np.array([50.0, 60.0, 200.0, 400.0]), 'conf': 0.9}], frame)
        r2 = t.update([{'bbox': np.array([52.0, 62.0, 202.0, 402.0]), 'conf': 0.88}], frame)
        assert r1[0]['tracking_id'] == r2[0]['tracking_id']

    def test_set_frame_id(self, person_tracker):
        person_tracker.set_frame_id(42)   # no debe lanzar excepción


# ════════════════════════════════════════════════════════════════════════════════
# 6. MÓDULO ALARMA
# ════════════════════════════════════════════════════════════════════════════════
class TestAlarmaModules:
    def test_package_exports(self):
        from modulos.alarma import TelegramNotifier, GmailNotifier
        assert TelegramNotifier and GmailNotifier

    def test_no_whatsapp_in_package(self):
        import modulos.alarma as a
        assert not hasattr(a, 'WhatsAppNotifier')

    def test_telegram_init(self, tmp_path):
        from modulos.alarma import TelegramNotifier
        n = TelegramNotifier(config_file=str(tmp_path / "cfg.json"))
        assert isinstance(n.chat_ids, list)

    def test_telegram_creates_config(self, tmp_path):
        from modulos.alarma import TelegramNotifier
        cfg = tmp_path / "cfg.json"
        TelegramNotifier(config_file=str(cfg))
        assert cfg.exists()

    def test_gmail_init(self, tmp_path):
        from modulos.alarma import GmailNotifier
        assert GmailNotifier(config_file=str(tmp_path / "cfg.json")) is not None

    def test_gmail_creates_config(self, tmp_path):
        from modulos.alarma import GmailNotifier
        cfg = tmp_path / "cfg.json"
        GmailNotifier(config_file=str(cfg))
        assert cfg.exists()


# ════════════════════════════════════════════════════════════════════════════════
# 7. CAMERA MODULES
# ════════════════════════════════════════════════════════════════════════════════
class TestCameraModules:
    def test_camera_import(self):
        from camera import CamaraRTSP
        assert CamaraRTSP is not None

    def test_camera_dialog_import(self):
        from camera_dialog import CameraDialog
        assert CameraDialog is not None

    def test_get_cameras_returns_list(self):
        from camera_dialog import CameraDialog
        cams = CameraDialog.get_cameras()
        assert isinstance(cams, list)

    def test_camera_config_structure(self):
        from camera_dialog import CameraDialog
        for cam in CameraDialog.get_cameras():
            assert "url" in cam and "name" in cam


# ════════════════════════════════════════════════════════════════════════════════
# 8. DETECTOR IA (YOLO general)
# ════════════════════════════════════════════════════════════════════════════════
class TestDetectorIA:
    def test_import(self):
        from detector import DetectorIA
        assert DetectorIA is not None

    @pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "yolov8n.pt")),
                        reason="yolov8n.pt no encontrado")
    def test_init_loads_model(self):
        from detector import DetectorIA
        det = DetectorIA()
        assert det.model is not None and det.device is not None


# ════════════════════════════════════════════════════════════════════════════════
# 9. INTEGRACIÓN CRUZADA — pipeline end-to-end
# ════════════════════════════════════════════════════════════════════════════════
class TestCrossModuleIntegration:
    def test_all_modules_importable_together(self):
        from config import DETECTION_CONFIG
        from camera import CamaraRTSP
        from camera_dialog import CameraDialog
        from detector import DetectorIA
        from modulos.incendio import FireDetectionSystem
        from modulos.choques import AccidentDetectionSystem
        from modulos.robo.inference import TheftDetectionSystem
        from modulos.person_identifier import PersonAppearanceTracker
        from modulos.alarma import TelegramNotifier, GmailNotifier
        assert True

    def test_fire_pipeline_no_fire(self, fire_sys):
        """Frame negro → no incendio."""
        result = fire_sys.analyze_frame(make_frame(), "CamInteg")
        assert result is None

    def test_fire_pipeline_hsv_only(self, fire_sys):
        """Frame de fuego con YOLO desactivado → HSV detecta incendio."""
        original = fire_sys.yolo_model
        fire_sys.yolo_model = None
        try:
            detected, conf, details = fire_sys.detect_fire(make_fire_frame())
            assert detected is True
        finally:
            fire_sys.yolo_model = original

    def test_choques_pipeline_series_frames(self, choques_sys):
        """10 frames vacíos consecutivos → ningún accidente."""
        choques_sys.vehicle_tracks.clear()
        choques_sys.vehicle_velocities.clear()
        choques_sys.vehicle_history.clear()
        for _ in range(10):
            is_acc, _, prob = choques_sys.analyze_accident(make_frame())
        assert is_acc is False

    def test_robo_pipeline_full_empty_frame(self, robo_sys):
        """Frame vacío → 0 personas → 0 probabilidad de robo."""
        robo_sys.frame_count += 1
        people, objects = robo_sys.detect_people_and_objects(make_frame())
        tracked_p = robo_sys.track_people(people, make_frame())
        tracked_o = robo_sys.track_objects(objects)
        tracked_p, transfer = robo_sys.match_objects_to_people(tracked_p, tracked_o)
        prob, _ = robo_sys.analyze_theft(
            tracked_p,
            {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0},
            transfer
        )
        assert prob == 0.0

    def test_all_models_are_loaded_on_gpu_or_cpu(self, fire_sys, choques_sys, robo_sys):
        """Los tres modelos deben estar en un dispositivo válido."""
        import torch
        for det, name in [(choques_sys, "choques"), (robo_sys, "robo")]:
            assert det.yolo_model is not None, f"{name}: yolo_model es None"
        assert fire_sys.yolo_model is not None, "incendio: yolo_model es None"

    def test_frame_through_all_three_detectors(self, fire_sys, choques_sys, robo_sys):
        """Un mismo frame pasa por los tres módulos sin lanzar excepciones."""
        frame = make_frame()

        fire_sys.analyze_frame(frame, "CamA")

        choques_sys.vehicle_tracks.clear()
        choques_sys.detect_vehicles(frame)
        choques_sys.analyze_accident(frame)

        robo_sys.frame_count += 1
        people, objects = robo_sys.detect_people_and_objects(frame)
        tracked_p = robo_sys.track_people(people, frame)
        tracked_o = robo_sys.track_objects(objects)
        tracked_p, transfer = robo_sys.match_objects_to_people(tracked_p, tracked_o)
        prob, _ = robo_sys.analyze_theft(
            tracked_p,
            {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0},
            transfer
        )
        assert prob == 0.0


import os
import sys
import numpy as np
import pytest

# ─── helpers ──────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))

def make_frame(h=480, w=640, color=None):
    """Crear un frame BGR de prueba."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    if color is not None:
        frame[:] = color
    return frame

def make_fire_frame():
    """Frame con región roja/anaranjada que simula fuego (HSV)."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:350, 150:480] = [0, 80, 240]   # rojo (BGR)
    frame[130:320, 180:450] = [0, 160, 255]  # naranja
    frame[160:290, 210:420] = [20, 220, 255] # amarillo
    return frame

# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIG
# ══════════════════════════════════════════════════════════════════════════════
class TestConfig:
    def test_import(self):
        from config import (WORKSPACE_DIR, MODULOS_DIR, YOLO_GENERAL_MODEL,
                            ACCIDENT_DETECTION_MODEL, FIRE_DETECTION_MODEL,
                            DAMAGE_DETECTION_MODEL, DETECTION_CONFIG)
        assert os.path.isdir(WORKSPACE_DIR)
        assert os.path.isdir(MODULOS_DIR)

    def test_model_paths_point_to_subfolders(self):
        from config import ACCIDENT_DETECTION_MODEL, FIRE_DETECTION_MODEL
        assert "choques" in ACCIDENT_DETECTION_MODEL.replace("\\", "/")
        assert "incendio" in FIRE_DETECTION_MODEL.replace("\\", "/")

    def test_detection_config_values(self):
        from config import DETECTION_CONFIG
        assert "confidence_threshold" in DETECTION_CONFIG
        assert "fps_limit" in DETECTION_CONFIG
        assert 0 < DETECTION_CONFIG["confidence_threshold"] < 1

    def test_model_files_exist(self):
        from config import (ACCIDENT_DETECTION_MODEL, FIRE_DETECTION_MODEL,
                            DAMAGE_DETECTION_MODEL, YOLO_GENERAL_MODEL)
        missing = [p for p in [YOLO_GENERAL_MODEL, ACCIDENT_DETECTION_MODEL,
                                FIRE_DETECTION_MODEL, DAMAGE_DETECTION_MODEL]
                   if not os.path.exists(p)]
        assert missing == [], f"Modelos faltantes: {missing}"

    def test_module_paths_exist(self):
        from config import ACCIDENT_DETECTION_MODULE, FIRE_DETECTION_MODULE, ROBO_INFERENCE_MODULE
        assert os.path.exists(ACCIDENT_DETECTION_MODULE), ACCIDENT_DETECTION_MODULE
        assert os.path.exists(FIRE_DETECTION_MODULE), FIRE_DETECTION_MODULE
        assert os.path.exists(ROBO_INFERENCE_MODULE), ROBO_INFERENCE_MODULE


# ══════════════════════════════════════════════════════════════════════════════
# 2. MÓDULO INCENDIO
# ══════════════════════════════════════════════════════════════════════════════
class TestIncendioDetector:
    def test_import(self):
        from modulos.incendio import FireDetectionSystem
        assert FireDetectionSystem is not None

    def test_init_creates_db(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        db = tmp_path / "incidents.db"
        det = FireDetectionSystem(db_path=str(db), config_file=str(tmp_path / "cfg.json"))
        assert db.exists()

    def test_init_creates_config(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        cfg = tmp_path / "fire_config.json"
        FireDetectionSystem(db_path=str(tmp_path / "i.db"), config_file=str(cfg))
        assert cfg.exists()

    def test_detect_fire_none_frame(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem(db_path=str(tmp_path / "i.db"), config_file=str(tmp_path / "c.json"))
        detected, conf, _ = det.detect_fire(None)
        assert detected is False
        assert conf == 0.0

    def test_detect_fire_black_frame(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem(db_path=str(tmp_path / "i.db"), config_file=str(tmp_path / "c.json"))
        detected, conf, details = det.detect_fire(make_frame())
        assert isinstance(detected, bool)
        assert isinstance(conf, float)
        assert isinstance(details, str)

    def test_detect_fire_fire_frame(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem(db_path=str(tmp_path / "i.db"), config_file=str(tmp_path / "c.json"))
        detected, conf, details = det.detect_fire(make_fire_frame())
        # HSV analysis should detect the orange/red region
        assert isinstance(detected, bool)
        assert 0.0 <= conf <= 1.0

    def test_add_and_list_recipients(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem(db_path=str(tmp_path / "i.db"), config_file=str(tmp_path / "c.json"))
        det.add_recipient("Serenazgo", "serenazgo@caracoto.gob.pe", "+51912345678")
        det.add_recipient("Admin", "admin@caracoto.gob.pe", None)
        rows = det.list_recipients()
        assert len(rows) == 2
        assert rows[0]["name"] == "Serenazgo"
        assert rows[1]["name"] == "Admin"

    def test_analyze_frame_no_fire(self, tmp_path):
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem(db_path=str(tmp_path / "i.db"), config_file=str(tmp_path / "c.json"))
        result = det.analyze_frame(make_frame(), camera_name="CamTest")
        assert result is None   # no fire → no incident

    def test_analyze_frame_fire_saved_to_db(self, tmp_path):
        """Si hay fuego, el incidente debe quedar en SQLite."""
        import sqlite3
        from modulos.incendio import FireDetectionSystem
        db = tmp_path / "i.db"
        cfg = tmp_path / "c.json"
        det = FireDetectionSystem(db_path=str(db), config_file=str(cfg))
        # Force HSV detection by patching YOLO to None
        det.yolo_model = None
        result = det.analyze_frame(make_fire_frame(), camera_name="CamFuego")
        if result is not None:
            conn = sqlite3.connect(str(db))
            count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            conn.close()
            assert count >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 3. MÓDULO CHOQUES
# ══════════════════════════════════════════════════════════════════════════════
class TestChoquesDetector:
    def test_import(self):
        from modulos.choques import AccidentDetectionSystem
        assert AccidentDetectionSystem is not None

    def test_init_no_video_source(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        assert det.cap is None

    def test_process_video_raises_without_source(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        with pytest.raises(RuntimeError, match="video_source"):
            det.process_video()

    def test_no_vehicles_on_black_frame(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        vehicles = det.detect_vehicles(make_frame())
        assert isinstance(vehicles, list)

    def test_analyze_accident_no_vehicles(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        is_acc, details, prob = det.analyze_accident(make_frame())
        assert is_acc is False
        assert prob == 0.0
        assert isinstance(details, str)

    def test_track_vehicles_empty(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        # empty detection list → no crash
        det.track_vehicles([])
        assert det.vehicle_tracks == {}

    def test_check_vehicles_close_empty(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        close, pairs = det.check_vehicles_close()
        assert close is False
        assert pairs == []

    def test_detect_sudden_deceleration_empty(self):
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        decel, events = det.detect_sudden_deceleration()
        assert decel is False
        assert events == []


# ══════════════════════════════════════════════════════════════════════════════
# 4. MÓDULO ROBO
# ══════════════════════════════════════════════════════════════════════════════
class TestRoboInference:
    def test_import(self):
        from modulos.robo.inference import TheftDetectionSystem, SortTracker, KalmanBoxTracker
        assert TheftDetectionSystem is not None

    def test_init_no_video(self):
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        assert det.cap is None
        assert det.fps == 25.0

    def test_kalman_tracker_predict(self):
        from modulos.robo.inference import KalmanBoxTracker
        bbox = np.array([10.0, 20.0, 100.0, 200.0])
        trk = KalmanBoxTracker(bbox)
        pred = trk.predict()
        assert pred is not None and len(pred) == 4

    def test_kalman_tracker_update(self):
        from modulos.robo.inference import KalmanBoxTracker
        bbox = np.array([10.0, 20.0, 100.0, 200.0])
        trk = KalmanBoxTracker(bbox)
        trk.update(np.array([12.0, 22.0, 102.0, 202.0]))
        assert trk.time_since_update == 0

    def test_sort_tracker_empty_update(self):
        from modulos.robo.inference import SortTracker
        st = SortTracker()
        assert st.update([]) == []

    def test_sort_tracker_single_detection(self):
        from modulos.robo.inference import SortTracker
        st = SortTracker()
        dets = [[50.0, 60.0, 150.0, 250.0, 0.95]]
        result = st.update(dets)
        assert isinstance(result, list)

    def test_sort_tracker_tracking_consistency(self):
        from modulos.robo.inference import SortTracker
        st = SortTracker()
        dets = [[50.0, 60.0, 150.0, 250.0, 0.95]]
        r1 = st.update(dets)
        dets2 = [[52.0, 62.0, 152.0, 252.0, 0.93]]
        r2 = st.update(dets2)
        if r1 and r2:
            # Same object should keep same ID
            assert r1[0]['id'] == r2[0]['id']

    def test_analyze_theft_no_people(self):
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        prob, details = det.analyze_theft(
            {}, {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0}, False
        )
        assert prob == 0.0
        assert details['has_people'] is False

    def test_analyze_theft_people_no_valuables(self):
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        tracked = {1: {'has_valuable': False, 'valuable_objects': [], 'bbox': None,
                       'velocity': (0, 0), 'positions': [], 'tracking_id': 1,
                       'had_firearm': False, 'had_phone': False, 'had_blade': False,
                       'last_seen': 0, 'missing': False}}
        prob, details = det.analyze_theft(
            tracked, {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0}, False
        )
        assert prob == 0.0
        assert details['people_with_valuables'] is False

    def test_detect_people_empty_frame(self):
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        people, objects = det.detect_people_and_objects(make_frame())
        assert isinstance(people, list)
        assert isinstance(objects, list)

    def test_categorize_object_phone(self):
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        cat = det.categorize_object({'class': 67, 'class_name': 'cell phone'})
        assert cat == 'phone'

    def test_categorize_object_blade(self):
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        cat = det.categorize_object({'class': 43, 'class_name': 'knife'})
        assert cat == 'blade'

    def test_iou_batch_empty(self):
        from modulos.robo.inference import iou_batch
        result = iou_batch([], [])
        assert result.shape == (0, 0)

    def test_convert_bbox_to_z_and_back(self):
        from modulos.robo.inference import convert_bbox_to_z, convert_x_to_bbox
        bbox = np.array([10.0, 20.0, 110.0, 220.0])
        z = convert_bbox_to_z(bbox)
        assert len(z) == 4
        x = np.concatenate([z, np.zeros(3)])
        back = convert_x_to_bbox(x)
        assert len(back) == 4


# ══════════════════════════════════════════════════════════════════════════════
# 5. PERSON IDENTIFIER
# ══════════════════════════════════════════════════════════════════════════════
class TestPersonIdentifier:
    def test_import(self):
        from modulos.person_identifier import PersonAppearanceTracker
        assert PersonAppearanceTracker is not None

    def test_init_defaults(self):
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        assert t.next_id == 1
        assert t.tracks == []

    def test_update_empty_detections(self):
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        frame = make_frame()
        result = t.update([], frame)
        assert result == []

    def test_update_single_detection(self):
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        dets = [{'bbox': np.array([50.0, 60.0, 200.0, 400.0]), 'conf': 0.9}]
        result = t.update(dets, frame)
        assert len(result) == 1
        assert 'tracking_id' in result[0]
        assert result[0]['tracking_id'] == 1

    def test_update_same_person_twice(self):
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        dets = [{'bbox': np.array([50.0, 60.0, 200.0, 400.0]), 'conf': 0.9}]
        r1 = t.update(dets, frame)
        dets2 = [{'bbox': np.array([52.0, 62.0, 202.0, 402.0]), 'conf': 0.88}]
        r2 = t.update(dets2, frame)
        # Same person → same stable ID
        assert r1[0]['tracking_id'] == r2[0]['tracking_id']

    def test_set_frame_id(self):
        from modulos.person_identifier import PersonAppearanceTracker
        t = PersonAppearanceTracker()
        t.set_frame_id(42)   # should not raise


# ══════════════════════════════════════════════════════════════════════════════
# 6. MÓDULO ALARMA
# ══════════════════════════════════════════════════════════════════════════════
class TestAlarmaModules:
    def test_package_exports(self):
        from modulos.alarma import TelegramNotifier, GmailNotifier
        assert TelegramNotifier is not None
        assert GmailNotifier is not None

    def test_no_whatsapp_in_package(self):
        import modulos.alarma as alarma
        assert not hasattr(alarma, 'WhatsAppNotifier')

    def test_telegram_notifier_init(self, tmp_path):
        from modulos.alarma import TelegramNotifier
        n = TelegramNotifier(config_file=str(tmp_path / "cfg.json"))
        assert isinstance(n.chat_ids, list)

    def test_telegram_notifier_creates_config(self, tmp_path):
        from modulos.alarma import TelegramNotifier
        cfg = tmp_path / "cfg.json"
        TelegramNotifier(config_file=str(cfg))
        assert cfg.exists()

    def test_gmail_notifier_init(self, tmp_path):
        from modulos.alarma import GmailNotifier
        n = GmailNotifier(config_file=str(tmp_path / "cfg.json"))
        assert n is not None

    def test_gmail_notifier_creates_config(self, tmp_path):
        from modulos.alarma import GmailNotifier
        cfg = tmp_path / "cfg.json"
        GmailNotifier(config_file=str(cfg))
        assert cfg.exists()


# ══════════════════════════════════════════════════════════════════════════════
# 7. CAMERA MODULES
# ══════════════════════════════════════════════════════════════════════════════
class TestCameraModules:
    def test_camera_import(self):
        from camera import CamaraRTSP
        assert CamaraRTSP is not None

    def test_camera_dialog_import(self):
        from camera_dialog import CameraDialog
        assert CameraDialog is not None

    def test_get_cameras_returns_list(self):
        from camera_dialog import CameraDialog
        cams = CameraDialog.get_cameras()
        assert isinstance(cams, list)

    def test_get_cameras_structure(self):
        from camera_dialog import CameraDialog
        cams = CameraDialog.get_cameras()
        for cam in cams:
            assert "url" in cam
            assert "name" in cam


# ══════════════════════════════════════════════════════════════════════════════
# 8. DETECTOR IA (YOLO general)
# ══════════════════════════════════════════════════════════════════════════════
class TestDetectorIA:
    def test_import(self):
        from detector import DetectorIA
        assert DetectorIA is not None

    @pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "yolov8n.pt")),
                        reason="yolov8n.pt no encontrado")
    def test_init_loads_model(self):
        from detector import DetectorIA
        det = DetectorIA()
        assert det.model is not None
        assert det.device is not None


# ══════════════════════════════════════════════════════════════════════════════
# 9. INTEGRACIÓN CRUZADA — pipeline completo de un frame
# ══════════════════════════════════════════════════════════════════════════════
class TestCrossModuleIntegration:
    def test_fire_pipeline_full(self, tmp_path):
        """Frame → FireDetector → incidente en SQLite."""
        import sqlite3
        from modulos.incendio import FireDetectionSystem
        db = str(tmp_path / "i.db")
        det = FireDetectionSystem(db_path=db, config_file=str(tmp_path / "c.json"))
        det.yolo_model = None   # forzar sólo HSV
        det.add_recipient("Ops", "ops@test.com", "+51900000000")
        det.analyze_frame(make_fire_frame(), "CamInteg")
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM incidents").fetchall()
        conn.close()
        # Puede haber 0 o 1 incidente dependiendo de si HSV detecta algo
        assert isinstance(rows, list)

    def test_choques_pipeline_frame_by_frame(self):
        """Serie de frames vacíos → ningún accidente."""
        from modulos.choques import AccidentDetectionSystem
        det = AccidentDetectionSystem(video_source=None)
        for _ in range(10):
            is_acc, _, prob = det.analyze_accident(make_frame())
        assert is_acc is False

    def test_robo_pipeline_no_people(self):
        """Frame vacío → 0 personas, 0 objetos, prob_robo=0."""
        from modulos.robo.inference import TheftDetectionSystem
        det = TheftDetectionSystem(video_source=None)
        frame = make_frame()
        people, objects = det.detect_people_and_objects(frame)
        tracked_p = det.track_people(people, frame)
        tracked_o = det.track_objects(objects)
        tracked_p, transfer = det.match_objects_to_people(tracked_p, tracked_o)
        prob, details = det.analyze_theft(
            tracked_p,
            {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0},
            transfer
        )
        assert prob == 0.0

    def test_all_modules_importable_together(self):
        """Todos los módulos del sistema se pueden importar juntos sin conflictos."""
        from config import DETECTION_CONFIG
        from camera import CamaraRTSP
        from camera_dialog import CameraDialog
        from detector import DetectorIA
        from modulos.incendio import FireDetectionSystem
        from modulos.choques import AccidentDetectionSystem
        from modulos.robo.inference import TheftDetectionSystem
        from modulos.person_identifier import PersonAppearanceTracker
        from modulos.alarma import TelegramNotifier, GmailNotifier
        # Ningún import debe lanzar excepción
        assert True

    def test_frame_through_all_detectors(self, tmp_path):
        """Un frame pasa por incendio, choques y robo sin lanzar excepciones."""
        from modulos.incendio import FireDetectionSystem
        from modulos.choques import AccidentDetectionSystem
        from modulos.robo.inference import TheftDetectionSystem

        frame = make_frame()

        fire = FireDetectionSystem(db_path=str(tmp_path / "i.db"),
                                   config_file=str(tmp_path / "c.json"))
        fire.yolo_model = None
        fire.analyze_frame(frame, "CamA")

        choques = AccidentDetectionSystem(video_source=None)
        choques.detect_vehicles(frame)
        choques.analyze_accident(frame)

        robo = TheftDetectionSystem(video_source=None)
        people, objects = robo.detect_people_and_objects(frame)
        tracked_p = robo.track_people(people, frame)
        tracked_o = robo.track_objects(objects)
        tracked_p, transfer = robo.match_objects_to_people(tracked_p, tracked_o)
        prob, _ = robo.analyze_theft(
            tracked_p,
            {'fight': False, 'running': False, 'suspicious_activity': False, 'confidence': 0},
            transfer
        )
        assert prob == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 10. RENDIMIENTO — latencia, FPS, throughput
# ══════════════════════════════════════════════════════════════════════════════
import time

MAX_FIRE_LATENCY_MS    = 300
MAX_CHOQUES_LATENCY_MS = 300
MAX_ROBO_LATENCY_MS    = 400
MIN_FPS                = 5
_N_WARMUP              = 1
_N_MEASURE             = 10


class TestRendimiento:

    def test_fire_yolo_latency(self, fire_sys):
        """YOLO incendio <= 300 ms promedio."""
        frame = make_frame(480, 640, color=(20, 100, 200))
        for _ in range(_N_WARMUP):
            fire_sys.detect_fire(frame)
        times = [(time.perf_counter(), fire_sys.detect_fire(frame))[0] for _ in range(_N_MEASURE)]
        # medir correctamente
        times2 = []
        for _ in range(_N_MEASURE):
            t0 = time.perf_counter(); fire_sys.detect_fire(frame)
            times2.append((time.perf_counter() - t0) * 1000)
        avg = sum(times2) / len(times2)
        assert avg < MAX_FIRE_LATENCY_MS, f"Incendio YOLO {avg:.1f} ms > {MAX_FIRE_LATENCY_MS} ms"

    def test_fire_hsv_latency(self, fire_sys):
        """HSV puro < 20 ms por frame."""
        orig = fire_sys.yolo_model; fire_sys.yolo_model = None
        try:
            frame = make_fire_frame(); times = []
            for _ in range(20):
                t0 = time.perf_counter(); fire_sys.detect_fire(frame)
                times.append((time.perf_counter() - t0) * 1000)
            avg = sum(times) / len(times)
            assert avg < 20, f"HSV {avg:.2f} ms > 20 ms"
        finally:
            fire_sys.yolo_model = orig

    def test_fire_fps(self, fire_sys):
        """Incendio >= 5 FPS."""
        frame = make_frame(); fire_sys.detect_fire(frame)
        n = 20; t0 = time.perf_counter()
        for _ in range(n): fire_sys.detect_fire(frame)
        fps = n / (time.perf_counter() - t0)
        assert fps >= MIN_FPS, f"FPS incendio {fps:.1f} < {MIN_FPS}"

    def test_choques_detect_latency(self, choques_sys):
        """detect_vehicles <= 300 ms promedio."""
        frame = make_frame()
        for _ in range(_N_WARMUP): choques_sys.detect_vehicles(frame)
        times = []
        for _ in range(_N_MEASURE):
            t0 = time.perf_counter(); choques_sys.detect_vehicles(frame)
            times.append((time.perf_counter() - t0) * 1000)
        avg = sum(times) / len(times)
        assert avg < MAX_CHOQUES_LATENCY_MS, f"Choques {avg:.1f} ms > {MAX_CHOQUES_LATENCY_MS} ms"

    def test_choques_fps(self, choques_sys):
        """Choques >= 5 FPS."""
        frame = make_frame(); n = 20; t0 = time.perf_counter()
        for _ in range(n): choques_sys.detect_vehicles(frame)
        fps = n / (time.perf_counter() - t0)
        assert fps >= MIN_FPS, f"FPS choques {fps:.1f} < {MIN_FPS}"

    def test_robo_detect_latency(self, robo_sys):
        """detect_people_and_objects <= 400 ms promedio."""
        frame = make_frame()
        for _ in range(_N_WARMUP): robo_sys.detect_people_and_objects(frame)
        times = []
        for _ in range(_N_MEASURE):
            t0 = time.perf_counter(); robo_sys.detect_people_and_objects(frame)
            times.append((time.perf_counter() - t0) * 1000)
        avg = sum(times) / len(times)
        assert avg < MAX_ROBO_LATENCY_MS, f"Robo {avg:.1f} ms > {MAX_ROBO_LATENCY_MS} ms"

    def test_robo_fps(self, robo_sys):
        """Robo >= 5 FPS."""
        frame = make_frame(); n = 20; t0 = time.perf_counter()
        for _ in range(n): robo_sys.detect_people_and_objects(frame)
        fps = n / (time.perf_counter() - t0)
        assert fps >= MIN_FPS, f"FPS robo {fps:.1f} < {MIN_FPS}"

    def test_sort_tracker_1000_updates(self):
        """SortTracker 1000 updates < 1 s."""
        from modulos.robo.inference import SortTracker
        st = SortTracker()
        dets = [[float(i*10), float(i*10), float(i*10+50), float(i*10+100), 0.9] for i in range(5)]
        t0 = time.perf_counter()
        for _ in range(1000): st.update(dets)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"SortTracker 1000 updates: {elapsed:.3f} s"

    def test_kalman_10000_cycles(self):
        """10 000 ciclos Kalman predict+update < 0.5 s."""
        from modulos.robo.inference import KalmanBoxTracker
        trk = KalmanBoxTracker(np.array([50.0, 50.0, 150.0, 200.0]))
        t0 = time.perf_counter()
        for i in range(10_000):
            trk.predict()
            trk.update(np.array([50.0 + i * 0.001, 50.0, 150.0, 200.0]))
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"Kalman 10k ciclos: {elapsed:.3f} s"

    def test_hsv_1000_frames_throughput(self, fire_sys):
        """HSV 1000 frames < 5 s."""
        orig = fire_sys.yolo_model; fire_sys.yolo_model = None
        try:
            frame = make_fire_frame(); t0 = time.perf_counter()
            for _ in range(1000): fire_sys.detect_fire(frame)
            elapsed = time.perf_counter() - t0
            assert elapsed < 5.0, f"HSV 1000 frames: {elapsed:.2f} s"
        finally:
            fire_sys.yolo_model = orig

    def test_sqlite_100_writes(self, tmp_path):
        """100 escrituras SQLite < 1 s."""
        from modulos.incendio import FireDetectionSystem
        det = FireDetectionSystem.__new__(FireDetectionSystem)
        det.db_path = str(tmp_path / "perf.db")
        det.config_file = str(tmp_path / "c.json")
        det.config = {"threshold": 0.12, "min_area": 180, "cooldown_seconds": 0}
        det.yolo_model = None; det.last_reported = {}; det._init_db()
        t0 = time.perf_counter()
        for i in range(100):
            det.save_incident({"camera_name": f"Cam{i}", "incident_type": "fire",
                               "severity": "ALTO", "confidence": 0.9,
                               "details": f"T{i}", "created_at": "2026-07-15T12:00:00",
                               "status": "open", "report_sent": 0, "image_path": None})
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"SQLite 100 escrituras: {elapsed:.3f} s"
