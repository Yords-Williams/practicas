import cv2
import threading
import time
from config import CAPTURE_CONFIG

class CamaraRTSP:
    """
    Clase para capturar video desde fuentes RTSP en un hilo separado.
    Optimizada para NVIDIA Quadro P1000 + i7-10700
    Soporta reconexión automática en caso de pérdida de conexión.
    """

    def __init__(self, url, name):
        self.url = url
        self.name = name
        self.frame = None
        self.running = True
        self.cap = None
        self.errors = 0
        self.frames_read = 0
        self.fps = 0
        self.last_frame_time = time.time()

        self.connect()

        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def connect(self):
        """Conectar a la fuente RTSP con optimizaciones"""
        if self.cap:
            self.cap.release()

        print(f"[{self.name}] Conectando...")

        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        
        # Optimizaciones para captura
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_CONFIG['buffer_size'])
        self.cap.set(cv2.CAP_PROP_FPS, 25)  # Limit FPS
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 384)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 216)

        if self.cap.isOpened():
            print(f"[{self.name}] ✓ Conexión exitosa")
        else:
            print(f"[{self.name}] ✗ Error de conexión")

    def loop(self):
        """Loop de captura de frames en hilo separado"""
        while self.running:
            ret, frame = self.cap.read()

            if not ret:
                self.errors += 1

                if self.errors > 50:
                    print(f"[{self.name}] Reconectando...")
                    self.connect()
                    self.errors = 0

                time.sleep(0.1)
                continue

            self.errors = 0
            self.frame = frame
            self.frames_read += 1
            
            # Calcular FPS real
            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            if elapsed > 0:
                self.fps = 1.0 / elapsed
            self.last_frame_time = current_time

            # Control de FPS (25 FPS para Quadro P1000)
            time.sleep(0.04)  # ~25 FPS

    def read(self):
        """Obtener último frame capturado"""
        return self.frame
    
    def get_stats(self):
        """Obtener estadísticas de la cámara"""
        return {
            "nombre": self.name,
            "frames_leidos": self.frames_read,
            "errores": self.errors,
            "conectada": self.cap.isOpened() if self.cap else False,
            "fps_real": f"{self.fps:.1f}"
        }

    def stop(self):
        """Detener captura"""
        self.running = False
        if self.cap:
            self.cap.release()

