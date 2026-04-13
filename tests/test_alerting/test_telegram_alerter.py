from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from alerting import (
    TelegramAlerter,
    TelegramAlerterConfig,
    TelegramAlerterLoadError,
    build_telegram_message,
    load_telegram_alerter_config,
    load_telegram_alerter_config_from_file,
    send_telegram_alert,
    send_telegram_alerts,
)
from interface_contracts import AlertCategory, AlertRecord, AlertSeverity
from secrets_manager.sealer import generate_master_key, seal_mapping


def _build_dir(label: str) -> Path:
    root = Path("build") / "test_alerting" / f"{label}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _alert(
    *,
    severity: AlertSeverity = AlertSeverity.CRITICAL,
    resolved: bool = False,
) -> AlertRecord:
    return AlertRecord(
        timestamp_ms=1_712_345_678_901,
        alert_id="alert-001",
        severity=severity,
        category=AlertCategory.RISK,
        message="Emergency kill switch is active",
        pair="BTCUSDT",
        module="monitoring",
        resolved=resolved,
        resolved_ms=1_712_345_679_901 if resolved else None,
    )


def test_load_telegram_alerter_config_validates_mapping() -> None:
    config = load_telegram_alerter_config(
        {
            "bot_token": "bot-token",
            "chat_id": "123456",
            "prefix": "[V5.3]",
            "min_severity": "critical",
        }
    )

    assert config.bot_token == "bot-token"
    assert config.chat_id == "123456"
    assert config.message_prefix == "[V5.3]"
    assert config.min_severity == AlertSeverity.CRITICAL


def test_load_telegram_alerter_config_rejects_non_mapping() -> None:
    with pytest.raises(TelegramAlerterLoadError):
        load_telegram_alerter_config(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_build_telegram_message_includes_operational_fields() -> None:
    message = build_telegram_message(_alert(resolved=True), message_prefix="[V5.3]")

    assert "[V5.3]" in message
    assert "[CRITICAL][RISK]" in message
    assert "pair=BTCUSDT" in message
    assert "module=monitoring" in message
    assert "alert_id=alert-001" in message
    assert "resolved=true" in message


def test_send_telegram_alert_skips_below_min_severity() -> None:
    result = send_telegram_alert(
        _alert(severity=AlertSeverity.INFO),
        config=TelegramAlerterConfig(
            bot_token="bot-token",
            chat_id="123456",
            min_severity=AlertSeverity.WARNING,
        ),
    )

    assert result.skipped is True
    assert result.reason == "below_min_severity"
    assert result.delivered is False


def test_send_telegram_alert_posts_expected_payload() -> None:
    captured: dict[str, object] = {}

    def _fake_post(url: str, payload: dict[str, object], timeout_s: float) -> tuple[int, str]:
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout_s"] = timeout_s
        return 200, '{"ok": true}'

    config = TelegramAlerterConfig(
        bot_token="bot-token",
        chat_id="123456",
        message_prefix="[V5.3]",
        min_severity=AlertSeverity.INFO,
        disable_notification_below=AlertSeverity.CRITICAL,
        timeout_s=7.5,
    )

    result = send_telegram_alert(
        _alert(severity=AlertSeverity.WARNING),
        config=config,
        post_func=_fake_post,
    )

    assert result.delivered is True
    assert captured["url"] == "https://api.telegram.org/botbot-token/sendMessage"
    assert captured["timeout_s"] == 7.5
    assert captured["payload"] == {
        "chat_id": "123456",
        "text": build_telegram_message(_alert(severity=AlertSeverity.WARNING), message_prefix="[V5.3]"),
        "disable_notification": True,
    }


def test_send_telegram_alert_marks_http_failure() -> None:
    result = send_telegram_alert(
        _alert(),
        config=TelegramAlerterConfig(
            bot_token="bot-token",
            chat_id="123456",
        ),
        post_func=lambda *_args: (500, '{"ok": false}'),
    )

    assert result.delivered is False
    assert result.reason == "http_500"
    assert result.status_code == 500


def test_send_telegram_alerts_batches_results() -> None:
    alerter = TelegramAlerter(
        TelegramAlerterConfig(
            bot_token="bot-token",
            chat_id="123456",
            min_severity=AlertSeverity.INFO,
        ),
        post_func=lambda *_args: (200, '{"ok": true}'),
    )

    results = alerter.send_many([
        _alert(severity=AlertSeverity.WARNING),
        _alert(severity=AlertSeverity.CRITICAL).model_copy(
            update={"alert_id": "alert-002"}
        ),
    ])

    assert len(results) == 2
    assert all(result.delivered for result in results)


def test_load_telegram_alerter_config_from_sealed_file() -> None:
    build_dir = _build_dir("sealed")
    key_path = build_dir / "master.key"
    sealed_path = build_dir / "telegram.sealed.json"
    try:
        generate_master_key(key_path)
        envelope = seal_mapping(
            {
                "bot_token": "sealed-bot-token",
                "chat_id": "987654",
                "message_prefix": "[SEALED]",
                "min_severity": "warning",
            },
            key_path=key_path,
            source_name="telegram.yml",
        )
        sealed_path.write_text(
            json.dumps(envelope.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        config = load_telegram_alerter_config_from_file(
            sealed_path,
            key_path=key_path,
        )
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    assert config.bot_token == "sealed-bot-token"
    assert config.chat_id == "987654"
    assert config.message_prefix == "[SEALED]"
    assert config.min_severity == AlertSeverity.WARNING
