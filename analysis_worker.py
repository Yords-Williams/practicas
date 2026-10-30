import copy
import threading
import time
from collections import defaultdict

from PySide6.QtCore import QObject, Signal

from config import ACCIDENT_CONFIG, DETECTION_CONFIG


class CameraAnalysisWorker(QObject):
    """Run enabled camera detectors serially without blocking the Qt UI."""

    frame_analyzed = Signal(int, object)
    stats_updated = Signal(object)
    module_error = Signal(str)
    module_warning = Signal(str)

    def __init__(self, cameras, fire_detector):
        super().__init__()
        self.cameras = cameras
        self.fire_detector = fire_detector
        self.frames_per_camera = DETECTION_CONFIG["analysis_fps_per_camera"]
        self._stop_event = threading.Event()
        self._thread = None
        self._reported_errors = set()
        self._last_accident_alert = {}
        self._last_theft_alert = {}
        self._theft_detector = None
        self._theft_camera_states = {}
        self._accident_detector = None
        self._accident_load_attempted = False
        self._theft_load_attempted = False
        self._inference_count = 0

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="camera-analysis",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout=None):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout)
            return not self._thread.is_alive()
        return True

    def _report_error_once(self, key, message):
        if key not in self._reported_errors:
            self._reported_errors.add(key)
            self.module_error.emit(message)

    def _create_theft_camera_state(self, detector):
        from modulos.person_identifier import PersonAppearanceTracker
        from modulos.robo.inference import SortTracker

        state = copy.copy(detector)
        state.person_tracks = defaultdict(detector.person_tracks.default_factory)
        state.object_tracks = defaultdict(detector.object_tracks.default_factory)
        state.person_sort = SortTracker(max_age=30, min_hits=1, iou_threshold=0.25)
        state.person_identifier = PersonAppearanceTracker(
            max_age=12,
            distance_threshold=120,
            appearance_threshold=0.75,
        )
        state.person_sort_to_stable = {}
        state.expired_persons = []
        state.next_person_label = 1
        state.next_person_id = 0
        state.next_object_id = 0
        state.frame_count = 0
        state.alerts = []
        return state

    def _load_detectors(self):
        needs_accident = any(
            getattr(camera, "settings", {}).get("detect_accident", True)
            for camera in self.cameras
        )
        needs_theft = any(
            getattr(camera, "settings", {}).get("detect_theft", True)
            for camera in self.cameras
        )

        if needs_accident:
            self._load_accident_detector()
        if needs_theft:
            self._load_theft_detector()

    def _load_accident_detector(self):
        if self._accident_load_attempted:
            return
        self._accident_load_attempted = True
        try:
            from modulos.choques.detector import AccidentDetectionSystem

            shared_model = getattr(self.fire_detector, "yolo_model", None)
            self._accident_detector = AccidentDetectionSystem(model=shared_model)
        except Exception as error:
            self._report_error_once(
                "accident-load",
                f"No se pudo cargar el detector de choques: {error}",
            )

    def _load_theft_detector(self):
        if self._theft_load_attempted:
            return
        self._theft_load_attempted = True
        try:
            from modulos.robo.inference import TheftDetectionSystem

            self._theft_detector = TheftDetectionSystem()
            self._theft_camera_states = {
                index: self._create_theft_camera_state(self._theft_detector)
                for index in range(len(self.cameras))
                if getattr(self.cameras[index], "settings", {}).get("detect_theft", True)
            }
        except Exception as error:
            self._theft_detector = None
            self._theft_camera_states = {}
            self._report_error_once(
                "theft-load",
                f"No se pudo cargar el detector de robos: {error}",
            )

    def _analyze_camera(self, index, frame):
        camera = self.cameras[index]
        settings = getattr(camera, "settings", {})
        camera_name = getattr(camera, "name", f"Cámara {index + 1}")
        scores = {}
        now = time.monotonic()

        if settings.get("detect_accident", True) and self._accident_detector is None:
            self._load_accident_detector()
        if settings.get("detect_theft", True) and self._theft_detector is None:
            self._load_theft_detector()

        if settings.get("detect_accident", True) and self._accident_detector is not None:
            try:
                is_accident, details, probability = self._accident_detector.analyze_accident(frame)
                scores["accident"] = probability
                if is_accident and (
                    now - self._last_accident_alert.get(index, 0)
                    >= ACCIDENT_CONFIG.get("alert_cooldown_seconds", 60)
                ):
                    result = (is_accident, details, probability)
                    self._accident_detector.log_accident(frame, result)
                    self._accident_detector.generate_alert(result)
                    self._last_accident_alert[index] = now
                self._inference_count += 1
            except Exception as error:
                self._report_error_once(
                    f"accident-{index}",
                    f"Error en detector de choques de {camera_name}: {error}",
                )

        if settings.get("detect_fire", True) and self.fire_detector is not None:
            try:
                detection_result = self.fire_detector.detect_fire(frame)
                scores["fire"] = detection_result[1]
                incident = self.fire_detector.analyze_frame(
                    frame,
                    camera_name=camera_name,
                    detection_result=detection_result,
                )
                if incident:
                    print(
                        f"[Análisis] Incendio detectado en {camera_name}: "
                        f"{incident['details']}"
                    )
                self._inference_count += 1
            except Exception as error:
                self._report_error_once(
                    f"fire-{index}",
                    f"Error en detector de incendios de {camera_name}: {error}",
                )

        if settings.get("detect_theft", True) and self._theft_detector is not None:
            state = self._theft_camera_states.get(index)
            if state is not None:
                try:
                    previous_inferences = self._theft_detector.inference_calls
                    state.inference_calls = self._theft_detector.inference_calls
                    state.suspicious_model = self._theft_detector.suspicious_model
                    state.suspicious_model_loaded = self._theft_detector.suspicious_model_loaded
                    state.suspicious_model_load_attempted = getattr(
                        self._theft_detector, "suspicious_model_load_attempted", False
                    )
                    state.suspicious_model_error = getattr(
                        self._theft_detector, "suspicious_model_error", None
                    )
                    state.frame_count += 1

                    people, objects_detected = state.detect_people_and_objects(frame)
                    tracked_people = state.track_people(people, frame)
                    tracked_objects = state.track_objects(objects_detected)
                    tracked_people, object_transfer = state.match_objects_to_people(
                        tracked_people, tracked_objects
                    )
                    people_with_valuables = sum(
                        1 for person in tracked_people.values()
                        if person.get("has_valuable")
                    )
                    if people_with_valuables:
                        suspicious_activity = state.detect_suspicious_activity(frame)
                        if state.suspicious_model_error:
                            warning = (
                                "El submódulo de actividad sospechosa del detector de robos "
                                "está desactivado porque falta su modelo "
                                f"Suspicious_Activities_nano.pt: {state.suspicious_model_error}"
                            )
                            if "theft-suspicious-model" not in self._reported_errors:
                                self._reported_errors.add("theft-suspicious-model")
                                self.module_warning.emit(warning)
                    else:
                        suspicious_activity = {
                            "fight": False,
                            "running": False,
                            "suspicious_activity": False,
                            "confidence": 0,
                        }
                    theft_probability, theft_details = state.analyze_theft(
                        tracked_people,
                        suspicious_activity,
                        object_transfer,
                    )

                    self._theft_detector.inference_calls = state.inference_calls
                    self._theft_detector.suspicious_model = state.suspicious_model
                    self._theft_detector.suspicious_model_loaded = state.suspicious_model_loaded
                    self._theft_detector.suspicious_model_load_attempted = state.suspicious_model_load_attempted
                    self._theft_detector.suspicious_model_error = state.suspicious_model_error
                    self._inference_count += (
                        self._theft_detector.inference_calls - previous_inferences
                    )
                    scores["theft"] = theft_probability
                    if (
                        theft_probability > state.alarm_threshold
                        and now - self._last_theft_alert.get(index, 0) >= 60
                    ):
                        print(
                            f"[Análisis] Posible robo en {camera_name}: "
                            f"{theft_probability:.2f} ({theft_details})"
                        )
                        self._last_theft_alert[index] = now
                except Exception as error:
                    self._report_error_once(
                        f"theft-{index}",
                        f"Error en detector de robos de {camera_name}: {error}",
                    )

        self.frame_analyzed.emit(index, scores)

    def _target_base_inferences_per_second(self):
        return self.frames_per_camera * sum(
            sum(
                bool(getattr(camera, "settings", {}).get(key, True))
                for key in ("detect_fire", "detect_accident", "detect_theft")
            )
            for camera in self.cameras
        )

    def _run(self):
        self._load_detectors()
        if not self.cameras:
            self.module_error.emit("No hay cámaras configuradas para analizar.")
            return

        interval = 1.0 / (self.frames_per_camera * len(self.cameras))
        next_run = time.monotonic()
        camera_index = 0
        last_stats_time = time.monotonic()
        last_stats_inferences = self._inference_count
        last_stats_frames = 0
        analyzed_frames = 0
        while not self._stop_event.is_set():
            delay = next_run - time.monotonic()
            if delay > 0 and self._stop_event.wait(delay):
                break

            frame = self.cameras[camera_index].read()
            if frame is not None:
                self._analyze_camera(camera_index, frame)
                analyzed_frames += 1

            camera_index = (camera_index + 1) % len(self.cameras)
            next_run += interval
            current_time = time.monotonic()
            if next_run < current_time:
                next_run = current_time

            elapsed = current_time - last_stats_time
            if elapsed >= 1.0:
                self.stats_updated.emit({
                    "frames_per_second": round(
                        (analyzed_frames - last_stats_frames) / elapsed, 1
                    ),
                    "inferences_per_second": round(
                        (self._inference_count - last_stats_inferences) / elapsed, 1
                    ),
                    "target_frames_per_second": self.frames_per_camera * len(self.cameras),
                    "target_base_inferences_per_second": self._target_base_inferences_per_second(),
                })
                last_stats_time = current_time
                last_stats_inferences = self._inference_count
                last_stats_frames = analyzed_frames
