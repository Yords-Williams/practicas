import cv2
import os
import threading
import time
from config import CAPTURE_CONFIG

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

    def __init__(self, url, name):
        self.url   = url
        self.name  = name
        self.frame = None
        self.running = True
        self.cap   = None
        self.errors = 0
        self.frames_read = 0
        self.fps   = 0
        self.last_frame_time = time.time()
        self.source_type = _detect_source_type(url)

        self.connect()

        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    # ── Conexión ──────────────────────────────────────────────────────────────

    def connect(self):
        """Abrir la fuente de video según su tipo."""
        if self.cap:
            self.cap.release()
            self.cap = None

        print(f"[{self.name}] Conectando ({self.source_type})...")

        if self.source_type == SOURCE_LOCAL:
            self._connect_local()
        elif self.source_type == SOURCE_FILE:
            self._connect_file()
        else:
            self._connect_rtsp()

        if self.cap and self.cap.isOpened():
            print(f"[{self.name}] ✓ Conexión exitosa")
        else:
            print(f"[{self.name}] ✗ Error de conexión")

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
            self.cap.set(cv2.CAP_PROP_FPS, 25)

    def _connect_file(self):
        """Archivo de video local con soporte de bucle."""
        self.cap = cv2.VideoCapture(self.url.strip())
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_CONFIG['buffer_size'])

    def _connect_rtsp(self):
        """Stream de red (RTSP/HTTP) con timeout de 6 s."""
        result: list = [None]

        def _open():
            c = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            result[0] = c

        t = threading.Thread(target=_open, daemon=True)
        t.start()
        t.join(timeout=6.0)

        if not t.is_alive() and result[0] is not None:
            self.cap = result[0]
        else:
            self.cap = cv2.VideoCapture()   # cap vacío si hubo timeout

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_CONFIG['buffer_size'])
            self.cap.set(cv2.CAP_PROP_FPS, 25)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 384)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 216)

    # ── Loop de captura ───────────────────────────────────────────────────────

    def loop(self):
        """Loop de captura de frames en hilo separado."""
        while self.running:
            ret, frame = self.cap.read() if self.cap else (False, None)

            if not ret:
                if self.source_type == SOURCE_FILE and self.cap and self.cap.isOpened():
                    # Fin de archivo → reiniciar desde el principio
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.04)
                    continue

                self.errors += 1
                # Reconectar: inmediato para archivos/local, ~30 s para red
                threshold = 10 if self.source_type != SOURCE_RTSP else 300
                if self.errors > threshold:
                    print(f"[{self.name}] Reconectando...")
                    self.connect()
                    self.errors = 0
                time.sleep(0.1)
                continue

            self.errors = 0
            self.frame  = frame
            self.frames_read += 1

            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            if elapsed > 0:
                self.fps = 1.0 / elapsed
            self.last_frame_time = current_time

            time.sleep(0.04)   # ~25 FPS

    # ── API pública ───────────────────────────────────────────────────────────

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
            "fps_real":      f"{self.fps:.1f}",
        }

    def stop(self):
        """Detener captura."""
        self.running = False
        if self.cap:
            self.cap.release()


