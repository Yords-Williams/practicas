from modulos.alarma import gmail_notifier
from modulos.alarma.gmail_notifier import GmailNotifier


def test_gmail_test_message_does_not_include_time(monkeypatch):
    notifier = GmailNotifier.__new__(GmailNotifier)
    notifier.sender = "sender@example.com"
    notifier.password = "app-password"
    notifier.to_emails = ["recipient@example.com"]
    notifier.alerts_sent = []
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port):
            pass

        def starttls(self):
            pass

        def login(self, sender, password):
            pass

        def send_message(self, message):
            sent_messages.append(message.as_string())

        def quit(self):
            pass

    monkeypatch.setattr(gmail_notifier.smtplib, "SMTP", FakeSMTP)

    assert notifier.send_alert(
        camera="Prueba",
        alert_type="prueba",
        message="PRUEBA DE NOTIFICACIONES",
        severity="PRUEBA",
        details="Mensaje de prueba",
    )
    assert len(sent_messages) == 1
    assert "Hora:" not in sent_messages[0]
