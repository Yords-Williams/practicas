"""Módulos de alarma y notificación para el sistema CCTV AI PRO.

Se evita importar los notifiers al cargar el paquete para no romper la carga
cuando faltan dependencias opcionales o cuando solo se necesitan utilidades de
configuración seguras.
"""

__all__ = ["TelegramNotifier", "GmailNotifier"]


def __getattr__(name):
    if name == "TelegramNotifier":
        from .telegram_notifier import TelegramNotifier
        return TelegramNotifier
    if name == "GmailNotifier":
        from .gmail_notifier import GmailNotifier
        return GmailNotifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
