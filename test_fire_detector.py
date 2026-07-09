import numpy as np

from modulos.fire_detector import FireDetectionSystem


def test_fire_detection_detects_flame_like_pixels(tmp_path):
    detector = FireDetectionSystem(db_path=str(tmp_path / "incidents.db"), config_file=str(tmp_path / "fire_config.json"))

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[80:160, 120:200] = [0, 80, 255]
    frame[90:150, 130:190] = [0, 180, 255]
    frame[100:140, 140:180] = [30, 255, 255]

    detected, confidence, details = detector.detect_fire(frame)

    assert detected is True
    assert confidence >= 0.1
    assert "incendio" in details.lower() or "fuego" in details.lower()
