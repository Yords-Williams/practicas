import cv2
import os
import threading
import time
from config import CAPTURE_CONFIG, DETECTION_CONFIG

# Reducir timeout de FFMPEG a 5 s via variable de entorno
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "stimeout;5000000")

# ── Tipos de fuente ───────────────────────────────────────────────────────────
SOURCE_RTSP  = "rtsp"    # cámara IP / stream RTSP o HTTP
SOURCE_LOCAL = "local"   # webcam / cámara USB (índice numérico)
SOURCE_FILE  = "file"    # archivo de video local (.mp4, .avi, …)


def _detect_source_type(url: str) -> str:
    """Inferir el tipo de fuente a partir de la URL/ruta."""
    u = url.strip()
    if u.startswith(("rtsp://", "rtsps://", "http://", "https://", "rtmp://")):
        return SOURCE_RTSP
    if u.isdigit() or u.startswith("local:") or u.startswith("cam:"):
        return SOURCE_LOCAL
    # Si el archivo existe en disco → video file
    ext = os.path.splitext(u)[1].lower()
    if ext in (".mp4", ".avi", ".mkv", ".mov", ".flv", ".ts", ".wmv"):
        return SOURCE_FILE
    return SOURCE_RTSP   # fallback


class CamaraRTSP:
    """
    Captura de video unificada: RTSP/HTTP, archivo de video y cámara local.
    Corre en hilo daemon con reconexión automática.
    """

    def __init__(self, url, name, high_resolution_url=None):
        self.url   = url
        self.high_resolution_url = high_resolution_url or ""
        self.current_url = url
        self.name  = name
        self.frame = None
        self.running = True
        self.cap   = None
        self.errors = 0
        self.frames_read = 0
        self.fps   = 0
        self.last_frame_time = time.time()
        self.connection_state = "connecting"
        self.last_error = None
        self.source_type = _detect_source_type(url)
        self.display_size = DETECTION_CONFIG['frame_resize']
        self.active_profile = "mosaic"
        self.requested_profile = "mosaic"

        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    # ── Conexión ──────────────────────────────────────────────────────────────

    def connect(self):
        """Abrir la fuente de video según su tipo."""
        if self.cap:
            self.cap.release()
            self.cap = None

        self.connection_state = "connecting"
        print(f"[{self.name}] Conectando ({self.source_type})...")
        try:
            if self.source_type == SOURCE_LOCAL:
                self._connect_local()
            elif self.source_type == SOURCE_FILE:
                self._connect_file()
            else:
                self._connect_rtsp()

            if self.cap and self.cap.isOpened():
                self.connection_state = "connected"
                self.last_error = None
                print(f"[{self.name}] ✓ Conexión exitosa")
            else:
                self.connection_state = "disconnected"
                self.last_error = "No se pudo abrir la fuente de video."
                print(f"[{self.name}] ✗ Error de conexión")
        except Exception as error:
            self.connection_state = "disconnected"
            self.last_error = str(error)
            if self.cap:
                self.cap.release()
                self.cap = None
            print(f"[{self.name}] ✗ Error al conectar: {error}")

    def _connect_local(self):
        """Webcam / cámara USB por índice de dispositivo."""
        url = self.url.strip()
        # Soporta: "0", "1", "local:0", "cam:1"
        for prefix in ("local:", "cam:"):
            if url.startswith(prefix):
                url = url[len(prefix):]
        try:
            idx = int(url)
        except ValueError:
            idx = 0
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)  # DSHOW más rápido en Windows
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_CONFIG['buffer_size'])
            self.cap.set(cv2.CAP_PROP_FPS, DETECTION_CONFIG['fps_limit'])

    def _connect_file(self):
        """Archivo de video local con soporte de bucle."""
        self.cap = cv2.VideoCapture(self.url.strip())
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_CONFIG['buffer_size'])

    def _connect_rtsp(self):
        """Abrir stream de red en el hilo dedicado a esta cámara."""
        self.cap = cv2.VideoCapture(self.current_url, cv2.CAP_FFMPEG)

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_CONFIG['buffer_size'])
            self.cap.set(cv2.CAP_PROP_FPS, DETECTION_CONFIG['fps_limit'])

    # ── Loop de captura ───────────────────────────────────────────────────────

    def loop(self):
        """Loop de captura de frames en hilo separado."""
        self.connect()
        while self.running:
            self._apply_requested_profile()
            ret, frame = self.cap.read() if self.cap else (False, None)

            if not ret:
                if self.source_type == SOURCE_FILE and self.cap and self.cap.isOpened():
                    # Fin de archivo → reiniciar desde el principio
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.04)
                    continue

                self.errors += 1
                # Reconectar: inmediato para archivos/local, ~30 s para red
                threshold = 10 if self.source_type != SOURCE_RTSP else 50
                if self.errors > threshold:
                    print(f"[{self.name}] Reconectando...")
                    self.connect()
                    self.errors = 0
                time.sleep(0.1)
                continue

            self.errors = 0
            # Conservar solo el último cuadro escalado evita acumular cuadros
            # grandes; el tamaño cambia entre mosaico y vista individual.
            target_size = self.display_size
            if (frame.shape[1], frame.shape[0]) != target_size:
                frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
            self.frame = frame
            self.frames_read += 1

            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            if elapsed > 0:
                self.fps = 1.0 / elapsed
            self.last_frame_time = current_time

            time.sleep(1.0 / DETECTION_CONFIG['fps_limit'])

    # ── API pública ───────────────────────────────────────────────────────────

    def set_stream_profile(self, profile, display_size):
        """Solicitar el perfil de mosaico o el de vista individual."""
        if profile not in ("mosaic", "single"):
            raise ValueError(f"Perfil de cámara no válido: {profile}")
        self.display_size = display_size
        self.requested_profile = profile

    def _apply_requested_profile(self):
        if self.requested_profile == self.active_profile:
            return

        self.active_profile = self.requested_profile
        target_url = (
            self.high_resolution_url
            if self.active_profile == "single" and self.high_resolution_url
            else self.url
        )
        if target_url != self.current_url:
            self.current_url = target_url
            self.frame = None
            self.connect()

    def read(self):
        """Obtener último frame capturado."""
        return self.frame

    def get_stats(self):
        """Estadísticas de la cámara."""
        return {
            "nombre":        self.name,
            "tipo":          self.source_type,
            "frames_leidos": self.frames_read,
            "errores":       self.errors,
            "conectada":     self.cap.isOpened() if self.cap else False,
            "estado":        self.connection_state,
            "ultimo_error":  self.last_error,
            "fps_real":      f"{self.fps:.1f}",
        }

    def stop(self):
        """Detener captura."""
        self.running = False
        if self.cap:
            self.cap.release()
