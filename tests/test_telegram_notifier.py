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
