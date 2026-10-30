import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from config import FIRE_DETECTION_MODEL
from app_storage import user_data_path
from modulos.alarma.secure_config import (
    protect_notification_secrets,
    unprotect_notification_secrets,
)




class FireDetectionSystem:
    """Detector de incendios para video en tiempo real.
    
    Usa exclusivamente el modelo compartido ``modulos/best.pt``.
    """

    DEFAULT_TELEGRAM_CHAT_ID = "7973977029"

    def __init__(
        self,
        db_path: Optional[str] = None,
        config_file: Optional[str] = None,
        yolo_model=None,
    ):
        self.db_path = db_path or user_data_path("incidents.db")
        self.config_file = config_file or user_data_path("fire_config.json")
        self.notifications_config_path = user_data_path("notifications_config.json")
        self.config = self._load_config()
        self._init_db()
        self.last_reported = {}

        # Cargar el único modelo compartido por todos los módulos.
        self.yolo_model = yolo_model
        _yolo_path = FIRE_DETECTION_MODEL
        if self.yolo_model is not None:
            print("[FireDetector] ✓ Usando el modelo YOLO compartido")
        elif os.path.exists(_yolo_path):
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO(_yolo_path)
                print(f"[FireDetector] ✓ Modelo YOLO cargado: {_yolo_path}")
            except Exception as e:
                print(f"[FireDetector] WARNING: No se pudo cargar YOLO ({e}).")
        else:
            print(f"[FireDetector] WARNING: Modelo no encontrado en {_yolo_path}.")

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        default_config = {
            "threshold": 0.12,
            "alert_threshold": 0.6,
            "min_area": 180,
            "notification_cooldown_seconds": 3600,
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
            telegram_chat_id TEXT,
            profile TEXT NOT NULL DEFAULT 'default',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)
        columns = {
            row[1] for row in cur.execute("PRAGMA table_info(recipients)").fetchall()
        }
        if "telegram_chat_id" not in columns:
            cur.execute("ALTER TABLE recipients ADD COLUMN telegram_chat_id TEXT")
        if "profile" not in columns:
            cur.execute(
                "ALTER TABLE recipients ADD COLUMN profile TEXT NOT NULL DEFAULT 'default'"
            )
        if "is_builtin" not in columns:
            cur.execute(
                "ALTER TABLE recipients ADD COLUMN is_builtin INTEGER NOT NULL DEFAULT 0"
            )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        conn.commit()
        conn.close()
        self._migrate_legacy_notification_recipients()
        self._sync_default_telegram_recipient()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE recipients SET name = 'Usuario' WHERE name = 'Administrador'"
            )

    def _sync_default_telegram_recipient(self):
        chat_id = self.DEFAULT_TELEGRAM_CHAT_ID
        if os.path.exists(self.notifications_config_path):
            try:
                with open(self.notifications_config_path, "r", encoding="utf-8") as file:
                    config = unprotect_notification_secrets(json.load(file))
                telegram = config.get("telegram", {})
                default_profile = telegram.get("profiles", {}).get("default", {})
                chat_id = str(
                    default_profile.get("chat_id")
                    or telegram.get("chat_id")
                    or chat_id
                ).strip()
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                print(f"[FireDetector] No se pudo sincronizar el usuario de Telegram: {error}")

        if not chat_id:
            return

        with sqlite3.connect(self.db_path) as conn:
            initialized = conn.execute(
                "SELECT value FROM app_state WHERE key = 'default_telegram_recipient_seeded'"
            ).fetchone()
            built_in = conn.execute(
                "SELECT id FROM recipients WHERE is_builtin = 1 ORDER BY id LIMIT 1"
            ).fetchone()
            if built_in:
                conn.execute(
                    """UPDATE recipients
                        SET telegram_chat_id = ?, profile = 'default'
                        WHERE id = ?""",
                    (chat_id, built_in[0]),
                )
                conn.execute(
                    """INSERT OR REPLACE INTO app_state (key, value)
                        VALUES ('default_telegram_recipient_seeded', '1')"""
                )
                return

            if initialized:
                return

            existing = conn.execute(
                "SELECT id FROM recipients WHERE telegram_chat_id = ? ORDER BY id LIMIT 1",
                (chat_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE recipients
                        SET is_builtin = 1
                        WHERE id = ?""",
                    (existing[0],),
                )
            else:
                conn.execute(
                    """INSERT INTO recipients
                        (name, telegram_chat_id, profile, active, created_at, is_builtin)
                        VALUES ('Usuario de Telegram', ?, 'default', 1, ?, 1)""",
                    (chat_id, datetime.now().isoformat(timespec="seconds")),
                )
            conn.execute(
                """INSERT OR REPLACE INTO app_state (key, value)
                    VALUES ('default_telegram_recipient_seeded', '1')"""
            )

    def _migrate_legacy_notification_recipients(self):
        """Move comma-separated legacy recipients into the recipient database."""
        if not os.path.exists(self.notifications_config_path):
            return
        try:
            with open(self.notifications_config_path, "r", encoding="utf-8") as file:
                config = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            print(f"[FireDetector] No se pudieron migrar destinatarios: {error}")
            return

        original_config = json.dumps(config, sort_keys=True)
        changed = False
        conn = sqlite3.connect(self.db_path)
        try:
            legacy_notification_credentials = False
            for section, secret_key in (
                ("telegram", "token"),
                ("gmail", "app_password"),
            ):
                channel = config.setdefault(section, {})
                legacy_secret = channel.pop(secret_key, None)
                if legacy_secret:
                    channel["enabled"] = False
                    channel["mode"] = "default"
                    changed = True
                    legacy_notification_credentials = True
            gmail = config.setdefault("gmail", {})
            legacy_sender = gmail.pop("sender", None)
            if legacy_sender:
                gmail["enabled"] = False
                gmail["mode"] = "default"
                changed = True
                legacy_notification_credentials = True
            if legacy_notification_credentials:
                print(
                    "[FireDetector] Se retiraron credenciales antiguas de la "
                    "configuración activa. Provisiona credenciales nuevas localmente."
                )

            for section, key, column, label in (
                ("telegram", "chat_ids", "telegram_chat_id", "Telegram migrado"),
                ("gmail", "to_emails", "email", "Correo migrado"),
            ):
                channel = config.get(section, {})
                had_legacy_key = key in channel
                values = channel.pop(key, [])
                if section == "telegram":
                    had_legacy_chat_id = "chat_id" in channel
                    legacy_id = channel.pop("chat_id", None)
                    if legacy_id:
                        values = list(values) if isinstance(values, list) else [values]
                        values.append(legacy_id)
                    changed = changed or had_legacy_chat_id
                changed = changed or had_legacy_key
                if isinstance(values, str):
                    values = values.split(",")
                for value in values or []:
                    address = str(value).strip()
                    if not address:
                        continue
                    exists = conn.execute(
                        f"SELECT 1 FROM recipients WHERE {column} = ? LIMIT 1",
                        (address,),
                    ).fetchone()
                    if not exists:
                        conn.execute(
                            f"""INSERT INTO recipients
                                (name, {column}, profile, active, created_at)
                                VALUES (?, ?, 'default', 1, ?)""",
                            (
                                f"{label} {address}",
                                address,
                                datetime.now().isoformat(timespec="seconds"),
                            ),
                        )
            conn.commit()
        finally:
            conn.close()

        config = protect_notification_secrets(config)
        changed = changed or json.dumps(config, sort_keys=True) != original_config
        if changed:
            with open(self.notifications_config_path, "w", encoding="utf-8") as file:
                json.dump(config, file, indent=2, ensure_ascii=False)

    def detect_fire(self, frame) -> Tuple[bool, float, str]:
        if frame is None:
            return False, 0.0, "Sin frame"

        if self.yolo_model is None:
            try:
                import cv2

                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hue = hsv[:, :, 0]
                sat = hsv[:, :, 1]
                val = hsv[:, :, 2]

                warm_mask = (((hue >= 0) & (hue <= 25)) | ((hue >= 160) & (hue <= 180)))
                warm_mask &= (sat > 40) & (val > 30)
                pixels = float(warm_mask.sum())
                total = float(frame.shape[0] * frame.shape[1])
                ratio = pixels / total if total else 0.0
                confidence = min(0.99, max(0.0, ratio * 6.0))
                if confidence >= self.config.get("threshold", 0.12):
                    return True, round(confidence, 3), (
                        f"Incendio/humo detectado por análisis de color: {confidence:.2f}"
                    )
                return False, round(confidence, 3), "No se detectó señal de incendio"
            except Exception as e:
                print(f"[FireDetector] Error fallback de color: {e}")
                return False, 0.0, "Modelo de detección no disponible"
        try:
            results = self.yolo_model(frame, verbose=False, conf=self.config.get("threshold", 0.12))
            boxes = results[0].boxes if results else None
            if boxes is None or len(boxes) == 0:
                return False, 0.0, "No se detectó señal de incendio"
            best_conf = float(max(boxes.conf).item())
            label = results[0].names[int(boxes.cls[0].item())]
            return True, round(best_conf, 3), f"Incendio/humo detectado por YOLO: {label} ({best_conf:.2f})"
        except Exception as e:
            print(f"[FireDetector] Error YOLO: {e}")
            return False, 0.0, "Error en el modelo de detección"

    def analyze_frame(
        self,
        frame,
        camera_name: str = "Cámara",
        detection_result=None,
    ) -> Optional[Dict]:
        detected, confidence, details = (
            detection_result if detection_result is not None else self.detect_fire(frame)
        )
        if not detected or confidence <= self.config.get("alert_threshold", 0.6):
            return None

        now = datetime.now()
        cooldown = self.config.get("notification_cooldown_seconds", 3600)
        if camera_name in self.last_reported:
            if (time.time() - self.last_reported[camera_name]) < cooldown:
                return None
        else:
            cutoff = (now - timedelta(seconds=cooldown)).isoformat(timespec="seconds")
            conn = sqlite3.connect(self.db_path)
            try:
                recent_incident = conn.execute(
                    """
                    SELECT 1 FROM incidents
                    WHERE camera_name = ? AND incident_type = 'fire' AND created_at >= ?
                    LIMIT 1
                    """,
                    (camera_name, cutoff),
                ).fetchone()
            finally:
                conn.close()
            if recent_incident:
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
        incident_id = self.save_incident(incident)
        self.send_report(incident, incident_id)
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
        incident_id = cur.lastrowid
        conn.commit()
        conn.close()
        return incident_id

    def add_recipient(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        profile: str = "default",
    ):
        if profile not in ("default", "manual"):
            raise ValueError(f"Perfil de notificación no válido: {profile}")
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO recipients
                (name, email, phone, telegram_chat_id, profile, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (
                name,
                email,
                phone,
                telegram_chat_id,
                profile,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        conn.close()

    def update_recipient(
        self,
        recipient_id: int,
        *,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> None:
        updates = {}
        if name is not None:
            updates["name"] = name.strip() or None
        if email is not None:
            updates["email"] = email.strip() or None
        if phone is not None:
            updates["phone"] = phone.strip() or None
        if not updates:
            raise ValueError("No se proporcionaron cambios para guardar.")
        if "name" in updates and not updates["name"]:
            raise ValueError("El nombre del destinatario no puede quedar vacío.")

        assignments = ", ".join(f"{column} = ?" for column in updates)
        values = list(updates.values()) + [recipient_id]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE recipients SET {assignments} WHERE id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise ValueError(f"No existe el destinatario con ID {recipient_id}.")

    def list_recipients(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """SELECT id, name, email, phone, telegram_chat_id, profile, active,
                      is_builtin
                FROM recipients ORDER BY id"""
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "telegram_chat_id": row[4],
                "profile": row[5],
                "active": bool(row[6]),
                "is_builtin": bool(row[7]),
            }
            for row in rows
        ]

    def delete_recipient(self, recipient_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT is_builtin, telegram_chat_id FROM recipients WHERE id = ?",
                (recipient_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"No existe el destinatario con ID {recipient_id}.")
            if row[0] and row[1]:
                self._clear_telegram_chat_id(row[1])
            conn.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))

    def _clear_telegram_chat_id(self, chat_id: str) -> None:
        if not os.path.exists(self.notifications_config_path):
            return
        try:
            with open(self.notifications_config_path, "r", encoding="utf-8") as file:
                raw_config = json.load(file)
            config = unprotect_notification_secrets(raw_config)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"No se pudo leer la configuración para eliminar el chat de Telegram: {error}"
            ) from error

        telegram = config.get("telegram", {})
        changed = False
        profiles = telegram.get("profiles", {})
        if isinstance(profiles, dict):
            for profile in profiles.values():
                if (
                    isinstance(profile, dict)
                    and str(profile.get("chat_id", "")).strip() == chat_id
                ):
                    profile.pop("chat_id")
                    changed = True
        if str(telegram.get("chat_id", "")).strip() == chat_id:
            telegram.pop("chat_id")
            changed = True
        legacy_chat_ids = telegram.get("chat_ids")
        if isinstance(legacy_chat_ids, list) and any(
            str(value).strip() == chat_id for value in legacy_chat_ids
        ):
            telegram["chat_ids"] = [
                value
                for value in legacy_chat_ids
                if str(value).strip() != chat_id
            ]
            changed = True
        if changed:
            try:
                with open(self.notifications_config_path, "w", encoding="utf-8") as file:
                    json.dump(
                        protect_notification_secrets(config),
                        file,
                        indent=2,
                        ensure_ascii=False,
                    )
            except OSError as error:
                raise RuntimeError(
                    f"No se pudo guardar la configuración sin el chat eliminado: {error}"
                ) from error

    def set_recipient_active(self, recipient_id: int, active: bool) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "UPDATE recipients SET active = ? WHERE id = ?",
                (int(active), recipient_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"No existe el destinatario con ID {recipient_id}.")
            conn.commit()
        finally:
            conn.close()

    def _dispatch_notifications(self, incident: Dict) -> Dict[str, Optional[bool]]:
        results = {"telegram": None, "gmail": None}
        self.last_notification_errors = {}
        try:
            with open(self.notifications_config_path, "r", encoding="utf-8") as f:
                notification_config = unprotect_notification_secrets(json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[FireDetector] No se pudo leer {self.notifications_config_path}: {e}")
            return {"telegram": False, "gmail": False}

        is_test = incident.get("is_test", False)
        message = (
            f"🧪 PRUEBA DE NOTIFICACIONES\n"
            if is_test
            else f"🚨 ALERTA DE INCENDIO\n"
        )
        message += (
            f"Cámara: {incident['camera_name']}\n"
            f"Severidad: {incident['severity']}\n"
            f"Confianza: {incident['confidence']:.2f}\n"
            f"Detalles: {incident['details']}"
        )

        telegram_config = notification_config.get("telegram", {})
        if telegram_config.get("enabled", False):
            try:
                from modulos.alarma.telegram_notifier import TelegramNotifier

                mode = telegram_config.get("mode", "manual")
                profile = telegram_config.get("profiles", {}).get(mode, {})
                token = profile.get("token")
                if not token:
                    raise ValueError(
                        f"No hay credenciales locales configuradas para Telegram ({mode})."
                    )
                notifier = TelegramNotifier(config_file=self.notifications_config_path)
                notifier.token = token
                recipients = self.list_recipients()
                active_chat_ids = [
                    recipient["telegram_chat_id"]
                    for recipient in recipients
                    if recipient.get("active")
                    and recipient.get("telegram_chat_id")
                ]
                raw_profile_chat_id = profile.get("chat_id")
                profile_chat_id = (
                    str(raw_profile_chat_id).strip()
                    if raw_profile_chat_id
                    else None
                )
                if profile_chat_id:
                    active_chat_ids.insert(0, profile_chat_id)
                notifier.chat_ids = list(dict.fromkeys(active_chat_ids))
                if not notifier.chat_ids:
                    raise ValueError(
                        "No hay usuarios activados para Telegram en el perfil activo."
                    )
                results["telegram"] = notifier.send_alert(
                    camera=incident["camera_name"],
                    alert_type="prueba" if is_test else "incendio",
                    message=message,
                    severity=incident["severity"],
                    details=incident["details"],
                )
                if not results["telegram"]:
                    self.last_notification_errors["Telegram"] = (
                        getattr(notifier, "last_error", None)
                        or "No se pudo enviar al destino de Telegram configurado."
                    )
            except Exception as e:
                print(f"[FireDetector] Error enviando Telegram: {e}")
                self.last_notification_errors["Telegram"] = str(e)
                results["telegram"] = False

        gmail_config = notification_config.get("gmail", {})
        if gmail_config.get("enabled", False):
            try:
                from modulos.alarma.gmail_notifier import GmailNotifier

                mode = gmail_config.get("mode", "manual")
                profile = gmail_config.get("profiles", {}).get(mode, {})
                if not profile.get("sender") or not profile.get("app_password"):
                    raise ValueError(
                        f"No hay credenciales locales configuradas para Gmail ({mode})."
                    )
                notifier = GmailNotifier(config_file=self.notifications_config_path)
                notifier.sender = profile["sender"]
                notifier.password = profile["app_password"]
                notifier.to_emails = list(dict.fromkeys(
                    recipient["email"]
                    for recipient in self.list_recipients()
                    if recipient.get("active")
                    and recipient.get("email")
                ))
                if not notifier.to_emails:
                    raise ValueError(
                        "No hay destinatarios válidos para Gmail en el perfil activo."
                    )
                results["gmail"] = notifier.send_alert(
                    camera=incident["camera_name"],
                    alert_type="prueba" if is_test else "incendio",
                    message=message,
                    severity=incident["severity"],
                    details=incident["details"],
                )
                if not results["gmail"]:
                    self.last_notification_errors["Correo"] = (
                        getattr(notifier, "last_error", None)
                        or "No se pudo enviar el correo."
                    )
            except Exception as e:
                print(f"[FireDetector] Error enviando correo: {e}")
                self.last_notification_errors["Correo"] = str(e)
                results["gmail"] = False

        return results

    def send_test_notifications(self) -> Dict[str, Optional[bool]]:
        incident = {
            "camera_name": "Prueba de notificaciones",
            "severity": "PRUEBA",
            "confidence": 1.0,
            "details": "Mensaje de prueba de Alertas Tempranas.",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "is_test": True,
        }
        return self._dispatch_notifications(incident)

    def send_report(self, incident: Dict, incident_id: Optional[int] = None) -> bool:
        results = self._dispatch_notifications(incident)
        sent = any(result is True for result in results.values())
        if incident_id is not None:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    "UPDATE incidents SET report_sent = ? WHERE id = ?",
                    (int(sent), incident_id),
                )
                conn.commit()
            finally:
                conn.close()
        return sent
