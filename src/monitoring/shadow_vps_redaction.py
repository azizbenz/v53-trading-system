"""Local redaction helpers for Shadow VPS monitoring and event projection."""

from __future__ import annotations

from interface_contracts.shadow_vps_service_contracts import ShadowVpsServiceEvent


_SENSITIVE_MARKERS = (
    "api_key",
    "secret_key",
    "binance_api_key",
    "binance_api_secret",
    "binance_testnet_api_key",
    "binance_testnet_secret",
    "binance_secret",
    "v53_binance_",
    "ciphertext_b64",
    "master key",
    "master.key",
)


def redact_shadow_vps_text(text: str) -> str:
    """Redact potentially sensitive text before it reaches monitoring surfaces."""

    if not text:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return "sensitive content redacted"
    return text


def redact_shadow_vps_event(event: ShadowVpsServiceEvent) -> ShadowVpsServiceEvent:
    """Return a monitoring-safe copy of one Shadow VPS event."""

    return event.model_copy(
        update={
            "message": redact_shadow_vps_text(event.message),
            "error": redact_shadow_vps_text(event.error),
        }
    )


__all__ = ["redact_shadow_vps_event", "redact_shadow_vps_text"]
