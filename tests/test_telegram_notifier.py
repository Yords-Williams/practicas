import json
import tempfile
from pathlib import Path

from modulos.alarma.telegram_notifier import TelegramNotifier


def test_legacy_chat_id_is_normalized_to_chat_ids(tmp_path):
    config_path = tmp_path / "notifications_config.json"
    config_path.write_text(
        json.dumps(
            {
                "telegram": {
                    "enabled": True,
                    "token": "dummy-token",
                    "chat_id": "123456789"
                }
            }
        ),
        encoding="utf-8",
    )

    notifier = TelegramNotifier(config_file=str(config_path))

    assert notifier.chat_ids == ["123456789"]
    assert notifier.token == "dummy-token"


def test_telegram_generated_messages_do_not_include_time():
    notifier = TelegramNotifier.__new__(TelegramNotifier)

    message = notifier._build_message(
        camera="Entrada",
        alert_type="fire",
        severity="ALTO",
        details="Incendio detectado",
    )

    assert "Hora:" not in message


def test_send_alert_exposes_telegram_api_rejection_without_chat_id(monkeypatch):
    from types import SimpleNamespace
    import modulos.alarma.telegram_notifier as telegram_module

    notifier = TelegramNotifier.__new__(TelegramNotifier)
    notifier.token = "test-token"
    notifier.chat_ids = ["private-chat-id"]
    notifier.alerts_sent = []

    monkeypatch.setattr(
        telegram_module.requests,
        "post",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=400,
            json=lambda: {
                "ok": False,
                "description": "Bad Request: chat not found",
            },
        ),
    )

    assert notifier.send_alert(
        camera="Entrada",
        alert_type="prueba",
        message="Prueba",
    ) is False
    assert notifier.last_error == "Bad Request: chat not found"
    assert "private-chat-id" not in notifier.last_error
