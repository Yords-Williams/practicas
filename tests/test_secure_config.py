from modulos.alarma import secure_config


def test_notification_secrets_are_transformed_and_legacy_values_are_preserved(
    monkeypatch,
):
    monkeypatch.setattr(
        secure_config,
        "_crypt",
        lambda data, protect: data[::-1],
    )
    config = {
        "telegram": {
            "token": "telegram-token",
            "chat_ids": ["123"],
            "profiles": {
                "default": {"token": "default-token"},
                "manual": {"token": "manual-token"},
            },
        },
        "gmail": {
            "app_password": "mail-password",
            "sender": "user@example.com",
            "profiles": {
                "default": {"app_password": "default-password"},
                "manual": {"app_password": "manual-password"},
            },
        },
    }

    protected = secure_config.protect_notification_secrets(config)
    restored = secure_config.unprotect_notification_secrets(protected)

    assert protected["telegram"]["token"].startswith("dpapi:")
    assert protected["gmail"]["app_password"].startswith("dpapi:")
    assert protected["telegram"]["profiles"]["default"]["token"].startswith("dpapi:")
    assert protected["gmail"]["profiles"]["manual"]["app_password"].startswith("dpapi:")
    assert "chat_ids" in protected["telegram"]
    assert restored == config
    assert secure_config.unprotect_secret("legacy-plaintext") == "legacy-plaintext"
