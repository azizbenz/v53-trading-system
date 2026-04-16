"""Bounded external alert delivery adapters."""

from __future__ import annotations

from alerting.telegram_alerter import (
    TelegramAlerter,
    TelegramAlerterConfig,
    TelegramAlerterLoadError,
    TelegramAlerterSendError,
    TelegramNotificationResult,
    build_telegram_message,
    load_telegram_alerter_config,
    load_telegram_alerter_config_from_file,
    send_telegram_alert,
    send_telegram_alerts,
)

__all__ = [
    "TelegramAlerter",
    "TelegramAlerterConfig",
    "TelegramAlerterLoadError",
    "TelegramAlerterSendError",
    "TelegramNotificationResult",
    "build_telegram_message",
    "load_telegram_alerter_config",
    "load_telegram_alerter_config_from_file",
    "send_telegram_alert",
    "send_telegram_alerts",
]
