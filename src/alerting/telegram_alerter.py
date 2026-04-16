"""Bounded Telegram alert delivery over existing AlertRecord contracts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from pydantic import BaseModel, Field, ValidationError

from interface_contracts import AlertRecord, AlertSeverity
from secrets_manager import SecretManagerLoadError, load as load_sealed_mapping


LOGGER = logging.getLogger(__name__)

_SEALED_SUFFIXES = (".sealed.json", ".sealed.yml", ".sealed.yaml")
_SEVERITY_RANK = {
    AlertSeverity.INFO: 0,
    AlertSeverity.WARNING: 1,
    AlertSeverity.CRITICAL: 2,
    AlertSeverity.FATAL: 3,
}


class TelegramAlerterLoadError(RuntimeError):
    """Raised when Telegram alert configuration cannot be loaded safely."""


class TelegramAlerterSendError(RuntimeError):
    """Raised when Telegram alert delivery cannot be attempted safely."""


class TelegramAlerterConfig(BaseModel, frozen=True):
    """Typed runtime config for a personal send-only Telegram bot."""

    bot_token: str = Field(..., min_length=1)
    chat_id: str = Field(..., min_length=1)
    message_prefix: str = ""
    min_severity: AlertSeverity = AlertSeverity.WARNING
    disable_notification_below: AlertSeverity = AlertSeverity.CRITICAL
    api_base_url: str = Field(default="https://api.telegram.org", min_length=1)
    timeout_s: float = Field(default=5.0, gt=0.0)


class TelegramNotificationResult(BaseModel, frozen=True):
    """Audit-ready result of one delivery attempt."""

    alert_id: str = Field(..., min_length=1)
    severity: AlertSeverity
    delivered: bool = False
    skipped: bool = False
    reason: str = ""
    status_code: int = 0


TelegramPostFunc = Callable[[str, Mapping[str, object], float], tuple[int, str]]


def _severity_at_least(left: AlertSeverity, right: AlertSeverity) -> bool:
    return _SEVERITY_RANK[left] >= _SEVERITY_RANK[right]


def load_telegram_alerter_config(payload: Mapping[str, object]) -> TelegramAlerterConfig:
    """Validate Telegram alerter config from a mapping."""

    if not isinstance(payload, Mapping):
        raise TelegramAlerterLoadError("Telegram alerter payload must be a mapping")

    normalized_payload = dict(payload)
    if "message_prefix" not in normalized_payload and "prefix" in normalized_payload:
        normalized_payload["message_prefix"] = normalized_payload["prefix"]

    try:
        return TelegramAlerterConfig(**normalized_payload)
    except ValidationError as exc:
        raise TelegramAlerterLoadError(
            f"Telegram alerter payload is invalid: {exc}"
        ) from exc


def load_telegram_alerter_config_from_file(
    path: Path | str,
    *,
    key_path: Path | str | None = None,
) -> TelegramAlerterConfig:
    """Load Telegram alerter config from JSON/YAML or sealed mapping."""

    config_path = Path(path)
    if not config_path.exists():
        raise TelegramAlerterLoadError(
            f"Telegram config file {config_path} does not exist"
        )
    if not config_path.is_file():
        raise TelegramAlerterLoadError(
            f"Telegram config path {config_path} must be a file"
        )

    try:
        lower_name = config_path.name.lower()
        if lower_name.endswith(_SEALED_SUFFIXES):
            if key_path is None:
                raise TelegramAlerterLoadError(
                    f"Sealed Telegram config file {config_path} requires key_path"
                )
            payload = load_sealed_mapping(config_path, key_path=key_path)
        else:
            suffix = config_path.suffix.lower()
            text = config_path.read_text(encoding="utf-8")
            if suffix in {".yml", ".yaml"}:
                payload = yaml.safe_load(text)
            elif suffix == ".json":
                payload = json.loads(text)
            else:
                raise TelegramAlerterLoadError(
                    "Telegram config file "
                    f"{config_path} has unsupported suffix {config_path.suffix!r}"
                )
    except SecretManagerLoadError as exc:
        raise TelegramAlerterLoadError(str(exc)) from exc
    except TelegramAlerterLoadError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise TelegramAlerterLoadError(
            f"Telegram config file {config_path} could not be parsed: {exc}"
        ) from exc

    if not isinstance(payload, Mapping):
        raise TelegramAlerterLoadError(
            f"Telegram config file {config_path} must deserialize to a mapping"
        )
    return load_telegram_alerter_config(payload)


def build_telegram_message(
    alert: AlertRecord,
    *,
    message_prefix: str = "",
) -> str:
    """Build a bounded plain-text Telegram message from an AlertRecord."""

    lines: list[str] = []
    if message_prefix:
        lines.append(message_prefix)
    lines.append(
        f"[{alert.severity.value.upper()}][{alert.category.value.upper()}] {alert.message}"
    )
    if alert.module:
        lines.append(f"module={alert.module}")
    if alert.engine_id:
        lines.append(f"engine_id={alert.engine_id.value}")
    if alert.pair:
        lines.append(f"pair={alert.pair}")
    lines.append(f"alert_id={alert.alert_id}")
    lines.append(f"timestamp_ms={alert.timestamp_ms}")
    if alert.resolved:
        lines.append("resolved=true")
    if alert.resolved_ms is not None:
        lines.append(f"resolved_ms={alert.resolved_ms}")
    return "\n".join(lines)


def _default_telegram_post(
    url: str,
    payload: Mapping[str, object],
    timeout_s: float,
) -> tuple[int, str]:
    data = json.dumps(dict(payload)).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            return int(response.status), response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise TelegramAlerterSendError(
            f"Telegram request failed for {url}: {exc}"
        ) from exc


def send_telegram_alert(
    alert: AlertRecord,
    *,
    config: TelegramAlerterConfig,
    post_func: TelegramPostFunc | None = None,
) -> TelegramNotificationResult:
    """Deliver one AlertRecord to Telegram, or skip if below configured severity."""

    if not _severity_at_least(alert.severity, config.min_severity):
        return TelegramNotificationResult(
            alert_id=alert.alert_id,
            severity=alert.severity,
            skipped=True,
            reason="below_min_severity",
        )

    payload = {
        "chat_id": config.chat_id,
        "text": build_telegram_message(alert, message_prefix=config.message_prefix),
        "disable_notification": not _severity_at_least(
            alert.severity, config.disable_notification_below
        ),
    }
    url = f"{config.api_base_url.rstrip('/')}/bot{config.bot_token}/sendMessage"

    try:
        status_code, _ = (post_func or _default_telegram_post)(
            url,
            payload,
            config.timeout_s,
        )
    except TelegramAlerterSendError as exc:
        LOGGER.error("Telegram alert failed for %s: %s", alert.alert_id, exc)
        return TelegramNotificationResult(
            alert_id=alert.alert_id,
            severity=alert.severity,
            reason=str(exc),
        )

    delivered = status_code == 200
    if not delivered:
        LOGGER.error(
            "Telegram alert delivery returned status=%s for %s",
            status_code,
            alert.alert_id,
        )
    return TelegramNotificationResult(
        alert_id=alert.alert_id,
        severity=alert.severity,
        delivered=delivered,
        reason="" if delivered else f"http_{status_code}",
        status_code=status_code,
    )


def send_telegram_alerts(
    alerts: tuple[AlertRecord, ...] | list[AlertRecord],
    *,
    config: TelegramAlerterConfig,
    post_func: TelegramPostFunc | None = None,
) -> tuple[TelegramNotificationResult, ...]:
    """Deliver a bounded batch of AlertRecord values."""

    return tuple(
        send_telegram_alert(alert, config=config, post_func=post_func)
        for alert in alerts
    )


class TelegramAlerter:
    """Thin stateful wrapper around the bounded Telegram delivery helpers."""

    def __init__(
        self,
        config: TelegramAlerterConfig,
        *,
        post_func: TelegramPostFunc | None = None,
    ) -> None:
        self._config = config
        self._post_func = post_func

    @property
    def config(self) -> TelegramAlerterConfig:
        return self._config

    def send(self, alert: AlertRecord) -> TelegramNotificationResult:
        return send_telegram_alert(
            alert,
            config=self._config,
            post_func=self._post_func,
        )

    def send_many(
        self,
        alerts: tuple[AlertRecord, ...] | list[AlertRecord],
    ) -> tuple[TelegramNotificationResult, ...]:
        return send_telegram_alerts(
            alerts,
            config=self._config,
            post_func=self._post_func,
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
