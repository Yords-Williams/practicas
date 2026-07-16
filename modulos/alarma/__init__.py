"""
Módulos de alarma y notificación para el sistema CCTV AI PRO.
Incluye notificadores por Telegram y Gmail.
"""

from .telegram_notifier import TelegramNotifier
from .gmail_notifier import GmailNotifier

__all__ = ["TelegramNotifier", "GmailNotifier"]
