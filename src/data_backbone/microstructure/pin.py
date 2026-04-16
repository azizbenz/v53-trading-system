"""
V5.3 - PIN
Canonical parameter-to-score PIN diagnostic helper.
"""

from __future__ import annotations

from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PIN_METHOD_VERSION = "pin.easley_kiefer_ohara_paperman.v1"
PIN_METHOD_VERSION_HASH = sha256(PIN_METHOD_VERSION.encode("utf-8")).hexdigest()


class PinParameterEstimate(BaseModel):
    """Estimated PIN latent-state parameters.

    This module does not perform the EM fit; it computes the diagnostic score from an
    already-estimated parameter set.
    """

    alpha: float = Field(..., ge=0.0, le=1.0)
    delta: float = Field(..., ge=0.0, le=1.0)
    mu: float = Field(..., ge=0.0)
    epsilon_b: float = Field(..., ge=0.0)
    epsilon_s: float = Field(..., ge=0.0)
    estimation_source: str = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("estimation_source")
    @classmethod
    def _normalize_source(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("estimation_source must not be blank")
        return normalized

    @model_validator(mode="after")
    def _validate_epsilon_total(self) -> "PinParameterEstimate":
        if self.alpha * self.mu + self.epsilon_b + self.epsilon_s <= 0.0:
            raise ValueError("PIN denominator must be > 0")
        return self


class PinRecord(BaseModel):
    """Audit-ready PIN score."""

    value: float = Field(..., ge=0.0, le=1.0)
    low_sample_confidence: bool = False
    parameter_warning: str | None = None
    parameter_source: str = Field(..., min_length=1)
    n_events_received: int = Field(..., ge=1)
    window_used: tuple[int | None, float | None]
    n_events_used: int = Field(..., ge=1)
    method_version_hash: str = Field(..., min_length=8)
    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    input_data_hash: str = Field(..., min_length=8)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized


def _hash_input(
    pair: str,
    estimate: PinParameterEstimate,
    window_used: tuple[int | None, float | None],
    n_events_used: int,
) -> str:
    payload = {
        "pair": pair,
        "window_used": list(window_used),
        "n_events_used": n_events_used,
        "estimate": estimate.model_dump(),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_pin_from_parameters(
    estimate: PinParameterEstimate,
    *,
    pair: str,
    window_used: tuple[int | None, float | None] = (None, 604_800.0),
    n_events_used: int = 1,
    computed_at_ns: int,
) -> PinRecord:
    """Compute PIN from a pre-estimated latent-state parameter set."""

    if computed_at_ns < 1:
        raise ValueError("computed_at_ns must be >= 1")
    if n_events_used < 1:
        raise ValueError("n_events_used must be >= 1")
    numerator = estimate.alpha * estimate.mu
    denominator = numerator + estimate.epsilon_b + estimate.epsilon_s
    pin_value = numerator / denominator
    parameter_warning: str | None = None
    if numerator <= 0.0:
        parameter_warning = "zero_informed_flow_component"
    return PinRecord(
        value=pin_value,
        low_sample_confidence=n_events_used < 5,
        parameter_warning=parameter_warning,
        parameter_source=estimate.estimation_source,
        n_events_received=n_events_used,
        window_used=window_used,
        n_events_used=n_events_used,
        method_version_hash=PIN_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=computed_at_ns,
        input_data_hash=_hash_input(pair, estimate, window_used, n_events_used),
    )


__all__ = [
    "PIN_METHOD_VERSION",
    "PIN_METHOD_VERSION_HASH",
    "PinParameterEstimate",
    "PinRecord",
    "compute_pin_from_parameters",
]
