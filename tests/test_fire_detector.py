import numpy as np

from modulos.incendio.detector import FireDetectionSystem


def make_detector(tmp_path):
    detector = FireDetectionSystem.__new__(FireDetectionSystem)
    detector.db_path = str(tmp_path / "incidents.db")
    detector.config_file = str(tmp_path / "fire_config.json")
    detector.config = {
        "threshold": 0.12,
        "alert_threshold": 0.6,
        "notification_cooldown_seconds": 3600,
    }
    detector.notifications_config_path = str(tmp_path / "notifications_config.json")
    detector.yolo_model = None
    detector.last_reported = {}
    detector._init_db()
    return detector


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


def test_analyze_frame_ignores_confidence_at_or_below_alert_threshold(
    tmp_path, monkeypatch
):
    import sqlite3

    detector = make_detector(tmp_path)
    monkeypatch.setattr(detector, "detect_fire", lambda frame: (True, 0.6, "Humo"))
    monkeypatch.setattr(detector, "send_report", lambda *args: True)

    assert detector.analyze_frame(object(), "Entrada") is None
    with sqlite3.connect(detector.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    assert count == 0


def test_recipient_edits_persist_and_keep_builtin_telegram_data(tmp_path):
    detector = make_detector(tmp_path)
    builtin = next(
        recipient
        for recipient in detector.list_recipients()
        if recipient.get("telegram_chat_id")
        == FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID
    )

    detector.update_recipient(
        builtin["id"],
        name="Usuario principal",
        email="principal@example.com",
        phone="+51999999999",
    )

    restarted = make_detector(tmp_path)
    saved = next(
        recipient
        for recipient in restarted.list_recipients()
        if recipient["id"] == builtin["id"]
    )
    assert saved["name"] == "Usuario principal"
    assert saved["email"] == "principal@example.com"
    assert saved["phone"] == "+51999999999"
    assert saved["telegram_chat_id"] == FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID


def test_update_recipient_rejects_empty_name_and_unknown_id(tmp_path):
    detector = make_detector(tmp_path)
    recipient_id = detector.list_recipients()[0]["id"]

    import pytest

    with pytest.raises(ValueError, match="nombre"):
        detector.update_recipient(recipient_id, name=" ")
    with pytest.raises(ValueError, match="No existe"):
        detector.update_recipient(999999, email="missing@example.com")


def test_delete_recipient_removes_builtin_user_and_telegram_chat_id(tmp_path):
    import json

    import pytest

    config_path = tmp_path / "notifications_config.json"
    config_path.write_text(
        json.dumps(
            {
                "telegram": {
                    "enabled": True,
                    "profiles": {
                        "default": {
                            "token": "test-token",
                            "chat_id": FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID,
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    detector = make_detector(tmp_path)
    builtin = next(
        recipient for recipient in detector.list_recipients()
        if recipient["is_builtin"]
    )
    detector.add_recipient("Temporal", "temporal@example.com")

    detector.delete_recipient(builtin["id"])
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    assert "chat_id" not in config["telegram"]["profiles"]["default"]

    manual_id = next(
        recipient["id"] for recipient in detector.list_recipients()
        if recipient["email"] == "temporal@example.com"
    )
    detector.delete_recipient(manual_id)
    assert all(
        recipient["id"] not in (manual_id, builtin["id"])
        for recipient in detector.list_recipients()
    )
    restarted = make_detector(tmp_path)
    assert all(not recipient["is_builtin"] for recipient in restarted.list_recipients())


def test_analyze_frame_saves_high_confidence_incident_and_applies_one_hour_cooldown(
    tmp_path, monkeypatch
):
    import sqlite3
    import time

    detector = make_detector(tmp_path)
    monkeypatch.setattr(detector, "detect_fire", lambda frame: (True, 0.61, "Fuego"))
    monkeypatch.setattr(detector, "send_report", lambda *args: True)

    incident = detector.analyze_frame(object(), "Entrada")
    assert incident is not None
    assert detector.analyze_frame(object(), "Entrada") is None

    detector.last_reported["Entrada"] = time.time() - 3601
    assert detector.analyze_frame(object(), "Entrada") is not None

    restarted = make_detector(tmp_path)
    monkeypatch.setattr(restarted, "detect_fire", lambda frame: (True, 0.9, "Fuego"))
    monkeypatch.setattr(restarted, "send_report", lambda *args: True)
    assert restarted.analyze_frame(object(), "Entrada") is None

    with sqlite3.connect(detector.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    assert count == 2


def test_dispatch_notifications_uses_enabled_telegram_and_active_email_recipients(
    tmp_path, monkeypatch
):
    import json
    import sqlite3
    import modulos.alarma.gmail_notifier as gmail_module
    import modulos.alarma.telegram_notifier as telegram_module

    monkeypatch.chdir(tmp_path)
    (tmp_path / "notifications_config.json").write_text(
        json.dumps(
            {
                "telegram": {
                    "enabled": True,
                    "mode": "default",
                    "profiles": {"default": {"token": "telegram-test-token"}},
                },
                "gmail": {
                    "enabled": True,
                    "mode": "default",
                    "profiles": {
                        "default": {
                            "sender": "sender@example.com",
                            "app_password": "gmail-test-password",
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    detector = make_detector(tmp_path)
    detector.add_recipient(
        "Activo", "active@example.com", telegram_chat_id="123456"
    )
    detector.add_recipient(
        "Manual", "manual@example.com", telegram_chat_id="manual-chat", profile="manual"
    )
    detector.add_recipient("Inactivo", "inactive@example.com")
    with sqlite3.connect(detector.db_path) as conn:
        conn.execute("UPDATE recipients SET active = 0 WHERE name = 'Inactivo'")

    sent = {}

    class FakeTelegramNotifier:
        def __init__(self, config_file):
            self.chat_ids = []

        def send_alert(self, **kwargs):
            sent["telegram"] = (self.chat_ids, kwargs)
            return True

    class FakeGmailNotifier:
        def __init__(self, config_file):
            self.to_emails = ["configured@example.com"]

        def send_alert(self, **kwargs):
            sent["gmail"] = (self.to_emails, kwargs)
            return True

    monkeypatch.setattr(telegram_module, "TelegramNotifier", FakeTelegramNotifier)
    monkeypatch.setattr(gmail_module, "GmailNotifier", FakeGmailNotifier)

    results = detector.send_test_notifications()

    assert results == {"telegram": True, "gmail": True}
    assert len(detector.list_recipients()) == 4
    assert sent["telegram"][0] == [
        FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID,
        "123456",
        "manual-chat",
    ]
    assert sent["telegram"][1]["message"].startswith("🧪 PRUEBA DE NOTIFICACIONES")
    assert "Hora:" not in sent["telegram"][1]["message"]
    assert sent["telegram"][1]["alert_type"] == "prueba"
    assert sent["gmail"][0] == ["active@example.com", "manual@example.com"]
    assert "Hora:" not in sent["gmail"][1]["message"]
    assert "inactive@example.com" not in sent["gmail"][0]

    incident = {
        "camera_name": "Entrada",
        "incident_type": "fire",
        "severity": "ALTO",
        "confidence": 0.8,
        "details": "Incendio detectado",
        "created_at": "2026-10-11T21:00:00",
        "status": "open",
        "report_sent": 0,
        "image_path": None,
    }
    incident_id = detector.save_incident(incident)
    assert detector.send_report(incident, incident_id) is True
    assert sent["gmail"][0] == ["active@example.com", "manual@example.com"]
    with __import__("sqlite3").connect(detector.db_path) as conn:
        sent_flag = conn.execute(
            "SELECT report_sent FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()[0]
    assert sent_flag == 1


def test_dispatch_notifications_uses_manual_telegram_chat_id(tmp_path, monkeypatch):
    import json
    import modulos.alarma.telegram_notifier as telegram_module

    detector = make_detector(tmp_path)
    detector.notifications_config_path = str(tmp_path / "notifications_config.json")
    with open(detector.notifications_config_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "telegram": {
                    "enabled": True,
                    "mode": "manual",
                    "profiles": {
                        "manual": {
                            "chat_id": "manual-chat-id",
                            "token": "manual-token",
                        }
                    },
                }
            },
            file,
        )

    sent = {}

    class FakeTelegramNotifier:
        def __init__(self, config_file):
            self.chat_ids = []

        def send_alert(self, **kwargs):
            sent["chat_ids"] = self.chat_ids
            return True

    monkeypatch.setattr(telegram_module, "TelegramNotifier", FakeTelegramNotifier)

    assert detector.send_test_notifications() == {"telegram": True, "gmail": None}
    assert sent["chat_ids"] == [
        "manual-chat-id",
        FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID,
    ]


def test_dispatch_notifications_uses_configured_default_chat_id(tmp_path, monkeypatch):
    import json
    import modulos.alarma.telegram_notifier as telegram_module

    detector = make_detector(tmp_path)
    with open(detector.notifications_config_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "telegram": {
                    "enabled": True,
                    "mode": "default",
                    "profiles": {
                        "default": {
                            "token": "default-token",
                            "chat_id": "configured-chat",
                        }
                    },
                }
            },
            file,
        )
    sent = {}

    class FakeTelegramNotifier:
        def __init__(self, config_file):
            self.chat_ids = []

        def send_alert(self, **kwargs):
            sent["chat_ids"] = self.chat_ids
            return True

    monkeypatch.setattr(telegram_module, "TelegramNotifier", FakeTelegramNotifier)

    assert detector.send_test_notifications()["telegram"] is True
    assert sent["chat_ids"][0] == "configured-chat"


def test_configured_telegram_profile_sends_when_its_contact_is_inactive(
    tmp_path, monkeypatch
):
    import json
    import modulos.alarma.telegram_notifier as telegram_module

    detector = make_detector(tmp_path)
    builtin = next(
        recipient
        for recipient in detector.list_recipients()
        if recipient.get("is_builtin")
    )
    with open(detector.notifications_config_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "telegram": {
                    "enabled": True,
                    "mode": "default",
                    "profiles": {
                        "default": {
                            "token": "default-token",
                            "chat_id": builtin["telegram_chat_id"],
                        }
                    },
                }
            },
            file,
        )
    detector.set_recipient_active(builtin["id"], False)
    sent = {}

    class FakeTelegramNotifier:
        def __init__(self, config_file):
            self.chat_ids = []

        def send_alert(self, **kwargs):
            sent["chat_ids"] = self.chat_ids
            return True

    monkeypatch.setattr(telegram_module, "TelegramNotifier", FakeTelegramNotifier)

    assert detector.send_test_notifications()["telegram"] is True
    assert sent["chat_ids"] == [builtin["telegram_chat_id"]]


def test_active_telegram_chat_id_is_saved_and_included_in_send(tmp_path, monkeypatch):
    import json
    import modulos.alarma.telegram_notifier as telegram_module

    detector = make_detector(tmp_path)
    with open(detector.notifications_config_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "telegram": {
                    "enabled": True,
                    "mode": "default",
                    "profiles": {"default": {"token": "default-token"}},
                }
            },
            file,
        )
    detector.add_recipient(
        "Nuevo usuario",
        telegram_chat_id="930240476",
    )
    saved = next(
        recipient
        for recipient in detector.list_recipients()
        if recipient.get("telegram_chat_id") == "930240476"
    )
    sent = {}

    class FakeTelegramNotifier:
        def __init__(self, config_file):
            self.chat_ids = []

        def send_alert(self, **kwargs):
            sent["chat_ids"] = self.chat_ids
            return True

    monkeypatch.setattr(telegram_module, "TelegramNotifier", FakeTelegramNotifier)

    assert saved["active"] is True
    assert detector.send_test_notifications()["telegram"] is True
    assert "930240476" in sent["chat_ids"]


def test_recipient_can_be_paused_and_reactivated_without_deleting(tmp_path):
    detector = make_detector(tmp_path)
    detector.add_recipient("Persona", "person@example.com")
    recipient = next(
        item for item in detector.list_recipients() if item["name"] == "Persona"
    )

    detector.set_recipient_active(recipient["id"], False)
    paused = next(
        item for item in detector.list_recipients() if item["id"] == recipient["id"]
    )
    assert paused["id"] == recipient["id"]
    assert paused["active"] is False

    detector.set_recipient_active(recipient["id"], True)
    restored = next(
        item for item in detector.list_recipients() if item["id"] == recipient["id"]
    )
    assert restored["id"] == recipient["id"]
    assert restored["email"] == "person@example.com"
    assert restored["active"] is True


def test_disabling_all_telegram_recipients_stops_default_messages(tmp_path, monkeypatch):
    import json
    import modulos.alarma.telegram_notifier as telegram_module

    detector = make_detector(tmp_path)
    with open(detector.notifications_config_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "telegram": {
                    "enabled": True,
                    "mode": "default",
                    "profiles": {"default": {"token": "default-token"}},
                }
            },
            file,
        )

    recipients = detector.list_recipients()
    telegram_recipient = next(
        item
        for item in recipients
        if item.get("telegram_chat_id") == FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID
    )
    detector.set_recipient_active(telegram_recipient["id"], False)

    class FakeTelegramNotifier:
        calls = []

        def __init__(self, config_file):
            self.chat_ids = []

        def send_alert(self, **kwargs):
            self.calls.append(kwargs)
            return True

    monkeypatch.setattr(telegram_module, "TelegramNotifier", FakeTelegramNotifier)

    assert detector.send_test_notifications() == {"telegram": False, "gmail": None}
    assert FakeTelegramNotifier.calls == []


def test_default_telegram_recipient_state_survives_detector_restart(tmp_path):
    detector = make_detector(tmp_path)
    recipient = next(
        item
        for item in detector.list_recipients()
        if item.get("telegram_chat_id") == FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID
    )
    detector.set_recipient_active(recipient["id"], False)

    restarted = make_detector(tmp_path)
    restored = next(
        item
        for item in restarted.list_recipients()
        if item.get("telegram_chat_id") == FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID
    )

    assert restored["active"] is False


def test_administrator_recipient_is_renamed_to_user_on_reload(tmp_path):
    detector = make_detector(tmp_path)
    detector.add_recipient("Administrador", "admin@example.com")

    restarted = make_detector(tmp_path)

    user = next(
        item
        for item in restarted.list_recipients()
        if item["email"] == "admin@example.com"
    )
    assert user["name"] == "Usuario"


def test_legacy_notification_destinations_migrate_into_recipients(tmp_path):
    import json
    import sqlite3

    db_path = tmp_path / "incidents.db"
    notification_path = tmp_path / "notifications_config.json"
    notification_path.write_text(
        json.dumps(
            {
                "telegram": {
                    "enabled": True,
                    "token": "stored-token",
                    "chat_ids": ["123", "456"],
                },
                "gmail": {
                    "enabled": True,
                    "sender": "sender@example.com",
                    "app_password": "stored-password",
                    "to_emails": ["first@example.com", "second@example.com"],
                },
            }
        ),
        encoding="utf-8",
    )
    detector = FireDetectionSystem.__new__(FireDetectionSystem)
    detector.db_path = str(db_path)
    detector.notifications_config_path = str(notification_path)

    detector._init_db()

    recipients = detector.list_recipients()
    assert {item["telegram_chat_id"] for item in recipients if item["telegram_chat_id"]} == {
        "123",
        "456",
        FireDetectionSystem.DEFAULT_TELEGRAM_CHAT_ID,
    }
    assert {item["email"] for item in recipients if item["email"]} == {
        "first@example.com",
        "second@example.com",
    }
    migrated_config = json.loads(notification_path.read_text(encoding="utf-8"))
    assert "chat_ids" not in migrated_config["telegram"]
    assert "to_emails" not in migrated_config["gmail"]
    assert "token" not in migrated_config["telegram"]
    assert "sender" not in migrated_config["gmail"]
    assert "app_password" not in migrated_config["gmail"]
    assert migrated_config["telegram"]["enabled"] is False
    assert migrated_config["gmail"]["enabled"] is False
    assert migrated_config["telegram"]["mode"] == "default"
    assert migrated_config["gmail"]["mode"] == "default"
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM recipients").fetchone()[0] == 5
