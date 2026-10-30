from analysis_worker import CameraAnalysisWorker


class FakeCamera:
    name = "Entrada"
    settings = {
        "detect_fire": True,
        "detect_accident": True,
        "detect_theft": True,
    }


class FakeFireDetector:
    def __init__(self):
        self.detection_result = (False, 0.0, "Sin detección")

    def detect_fire(self, frame):
        return self.detection_result

    def analyze_frame(self, frame, camera_name, detection_result):
        assert camera_name == "Entrada"
        assert detection_result is self.detection_result
        return None


class FakeAccidentDetector:
    def analyze_accident(self, frame):
        return False, "Sin detección", 0.0


class FakeTheftDetector:
    def __init__(self):
        self.inference_calls = 0
        self.suspicious_model = None
        self.suspicious_model_loaded = False


class FakeTheftCameraState:
    alarm_threshold = 0.7
    suspicious_model = None
    suspicious_model_loaded = False

    def __init__(self):
        self.inference_calls = 0
        self.frame_count = 0

    def detect_people_and_objects(self, frame):
        self.inference_calls += 3
        return [], []

    def track_people(self, people, frame):
        return {}

    def track_objects(self, objects):
        return {}

    def match_objects_to_people(self, people, objects):
        return people, False

    def analyze_theft(self, people, suspicious_activity, object_transfer):
        return 0.0, "Sin indicios"


def test_worker_runs_all_enabled_modules_and_counts_extra_theft_passes():
    fire_detector = FakeFireDetector()
    worker = CameraAnalysisWorker([FakeCamera()], fire_detector)
    worker._accident_detector = FakeAccidentDetector()
    worker._theft_detector = FakeTheftDetector()
    worker._theft_camera_states = {0: FakeTheftCameraState()}
    results = []
    worker.frame_analyzed.connect(lambda index, scores: results.append((index, scores)))

    worker._analyze_camera(0, object())

    assert worker._inference_count == 5
    assert results == [
        (0, {"accident": 0.0, "fire": 0.0, "theft": 0.0})
    ]


def test_target_for_twelve_cameras_is_48_frames_and_144_base_module_passes():
    cameras = [FakeCamera() for _ in range(12)]
    worker = CameraAnalysisWorker(cameras, FakeFireDetector())

    assert worker.frames_per_camera == 4
    assert worker.frames_per_camera * len(cameras) == 48
    assert worker._target_base_inferences_per_second() == 144


def test_missing_optional_suspicious_activity_model_is_a_warning_not_analysis_error():
    class CameraState(FakeTheftCameraState):
        suspicious_model_error = "model file is missing"

        def detect_people_and_objects(self, frame):
            return [], [{"class": 0}]

        def track_people(self, people, frame):
            return {1: {"has_valuable": True}}

        def detect_suspicious_activity(self, frame):
            return {"fight": False, "running": False, "suspicious_activity": False}

    worker = CameraAnalysisWorker([FakeCamera()], FakeFireDetector())
    worker._accident_detector = FakeAccidentDetector()
    worker._theft_detector = FakeTheftDetector()
    worker._theft_detector.suspicious_model_error = "model file is missing"
    worker._theft_camera_states = {0: CameraState()}
    errors = []
    warnings = []
    worker.module_error.connect(errors.append)
    worker.module_warning.connect(warnings.append)

    worker._analyze_camera(0, object())

    assert errors == []
    assert len(warnings) == 1
    assert "Suspicious_Activities_nano.pt" in warnings[0]
