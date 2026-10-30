import cv2
from ultralytics import YOLO
import datetime
import json
import os
from config import ACCIDENT_DETECTION_MODEL


class AccidentDetectionSystem:
    """
    Sistema de detección de accidentes por DETECCIÓN PURA.

    En vez de combinar heurísticas (proximidad, desaceleración, daño),
    se usa un único modelo entrenado (YOLO u otro) que detecta/clasifica
    directamente "accidente" / "choque" en el frame. El modelo debe
    haber sido entrenado con imágenes/clips etiquetados como accidente
    vs. no-accidente (o con clases tipo "crash", "collision", etc.).
    """

    def __init__(self, accident_model_path=ACCIDENT_DETECTION_MODEL, video_source=None,
                 confidence_threshold=0.5, model=None):
        """
        Args:
            accident_model_path: Modelo entrenado para detectar accidentes directamente.
            video_source: Fuente de video (int/str). None = modo frame-by-frame.
            confidence_threshold: Confianza mínima para considerar una detección válida.
        """
        if model is None:
            print(f"Cargando modelo de detección de accidentes: {accident_model_path}")
            self.accident_model = YOLO(accident_model_path)
        else:
            self.accident_model = model

        self.video_source = video_source
        self.cap = cv2.VideoCapture(video_source) if video_source is not None else None

        # Único parámetro de detección: la confianza del modelo
        self.confidence_threshold = confidence_threshold

        # Registros (se mantiene igual que en la versión híbrida)
        self.accident_records = []

    # ------------------------------------------------------------------
    # DETECCIÓN PURA: el modelo entrenado decide, sin heurísticas extra
    # ------------------------------------------------------------------
    def detect_accident(self, frame):
        """Ejecutar el modelo entrenado sobre el frame.

        Returns:
            is_accident (bool)
            best_confidence (float)
            detections (list[dict]) con bbox, label y confianza de cada detección
        """
        results = self.accident_model(frame, conf=self.confidence_threshold)

        detections = []
        best_confidence = 0.0

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                label = self.accident_model.names[cls]
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'label': label,
                    'confidence': conf
                })

                if conf > best_confidence:
                    best_confidence = conf

        is_accident = len(detections) > 0
        return is_accident, best_confidence, detections

    def analyze_accident(self, frame):
        """Analizar el frame usando únicamente el modelo entrenado.

        Mantiene la misma firma de salida (is_accident, details, probability)
        que la versión híbrida, para no romper log_accident/generate_alert.
        """
        is_accident, confidence, detections = self.detect_accident(frame)

        if not detections:
            return False, "Sin detecciones del modelo", 0.0

        labels = [d['label'] for d in detections]
        details = f"Detecciones: {len(detections)} ({', '.join(labels)})"

        return is_accident, details, confidence

    # ------------------------------------------------------------------
    # REGISTRO Y ALERTAS: se mantienen igual que en la versión híbrida
    # ------------------------------------------------------------------
    def log_accident(self, frame, analysis_result):
        """Guardar registro de posible accidente"""
        timestamp = datetime.datetime.now().isoformat()
        is_accident, details, probability = analysis_result

        record = {
            'timestamp': timestamp,
            'is_accident': is_accident,
            'details': details,
            'probability': probability
        }

        self.accident_records.append(record)

        if is_accident:
            filename = f"accident_{timestamp.replace(':', '-')}.jpg"
            cv2.imwrite(filename, frame)
            record['image_path'] = filename
            print(f"✓ Imagen de accidente guardada: {filename}")

    def generate_alert(self, analysis_result):
        """Generar alerta si hay accidente"""
        is_accident, details, probability = analysis_result

        if is_accident:
            print("\n" + "=" * 60)
            print("⚠️  ALERTA DE POSIBLE ACCIDENTE ⚠️")
            print("=" * 60)
            print(f"Confianza del modelo: {probability * 100:.1f}%")
            print(f"Detalles: {details}")
            print(f"Timestamp: {datetime.datetime.now()}")
            print("=" * 60 + "\n")
            return True
        return False

    def save_records(self, filename="accident_records.json"):
        """Guardar registros de accidentes"""
        with open(filename, 'w') as f:
            json.dump(self.accident_records, f, indent=4)
        print(f"✓ Registros guardados en: {filename}")

    # ------------------------------------------------------------------
    # PROCESAMIENTO DE VIDEO: simplificado (ya no hay tracking)
    # ------------------------------------------------------------------
    def process_video(self, max_frames=None):
        """Procesar el video completo (requiere video_source en el constructor)."""
        if self.cap is None:
            raise RuntimeError(
                "process_video() requiere video_source en el constructor. "
                "Usa analyze_accident(frame) para modo frame-by-frame."
            )

        frame_count = 0
        current_confidence = 0.0
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

            frame_small = cv2.resize(frame, (640, 480))

            # Paso único: el modelo entrenado analiza el frame
            analysis = self.analyze_accident(frame_small)
            is_accident, details, confidence = analysis
            current_confidence = confidence

            # Registro y alerta (sin cambios respecto a la versión híbrida)
            self.log_accident(frame_small, analysis)
            if self.generate_alert(analysis):
                paused = True

            # Dibujar resultados
            self.draw_frame(frame_small, analysis)

            prob_color = (0, 0, 255) if current_confidence > 0.7 else (0, 255, 0)
            prob_text = f"Confianza Accidente: {current_confidence * 100:.1f}%"
            cv2.putText(frame_small, prob_text, (10, 470),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, prob_color, 2)

            if paused:
                cv2.putText(frame_small, "PAUSADO - Presiona ESPACIO para continuar", (100, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            cv2.imshow('Detección de Accidentes', frame_small)

            key = cv2.waitKey(0 if paused else 1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                paused = not paused

            if frame_count % 30 == 0:
                print(f"Frames procesados: {frame_count}")

        self.cleanup()

    def draw_frame(self, frame, analysis_result):
        """Dibujar las detecciones del modelo sobre el frame"""
        is_accident, details, confidence = analysis_result

        _, _, detections = self.detect_accident(frame)

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            color = (0, 0, 255) if is_accident else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{det['label']} {det['confidence']:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    def cleanup(self):
        """Limpiar recursos"""
        self.cap.release()
        cv2.destroyAllWindows()
        self.save_records()
        print("Sistema cerrado")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(script_dir, "robo9.mp4")

    print(f"Procesando video: {video_path}")
    print(f"Archivo existe: {os.path.exists(video_path)}")

    system = AccidentDetectionSystem(
        video_source=video_path,
        confidence_threshold=0.5
    )

    system.process_video(max_frames=None)


if __name__ == "__main__":
    main()