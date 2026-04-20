"""Policy-governed upstream threshold resolver for Engine D coordination."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field


_NS_PER_HOUR = 3_600_000_000_000
_THR_X10 = "THR-X10"
_THR_X11 = "THR-X11"


class EngineDCoordinationThresholdResolverConfig(BaseModel, frozen=True):
    """Policy-governed config for Engine D anti-revenge/reset thresholds."""

    d_reset_failsafe_hours: float = Field(default=24.0, gt=0.0)
    d_consecutive_stop_limit: int = Field(default=1, ge=1)
    d_reset_failsafe_hours_hard_cap: float = Field(default=48.0, gt=0.0)
    d_consecutive_stop_limit_hard_cap: int = Field(default=3, ge=1)


class EngineDCoordinationThresholdResolution(BaseModel):
    """Resolved governed thresholds for the current Engine D coordination seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    d_reset_failsafe_hours: float = Field(..., gt=0.0)
    d_reset_failsafe_ns: int = Field(..., gt=0)
    d_consecutive_stop_limit: int = Field(..., ge=1)
    d_reset_failsafe_threshold_id: str = Field(default=_THR_X10, min_length=1)
    d_consecutive_stop_limit_threshold_id: str = Field(default=_THR_X11, min_length=1)
    governance_mode: str = Field(default="policy_governed", min_length=1)

    def to_engine_d_coordination_threshold_updates(self) -> dict[str, int]:
        """Return additive updates for Engine D coordination thresholds."""

        return {
            "d_reset_failsafe_ns": self.d_reset_failsafe_ns,
            "d_consecutive_stop_limit": self.d_consecutive_stop_limit,
        }


def resolve_engine_d_coordination_thresholds(
    config: EngineDCoordinationThresholdResolverConfig | None = None,
) -> EngineDCoordinationThresholdResolution:
    """Resolve policy-governed Engine D coordination thresholds."""

    effective_config = (
        EngineDCoordinationThresholdResolverConfig()
        if config is None
        else config
    )
    d_reset_failsafe_hours = _resolve_positive_float(
        effective_config.d_reset_failsafe_hours,
        field_name="d_reset_failsafe_hours",
    )
    if d_reset_failsafe_hours > effective_config.d_reset_failsafe_hours_hard_cap:
        raise ValueError(
            "THR-X10 value "
            f"{d_reset_failsafe_hours:.6f} exceeds Engine D reset failsafe hard cap "
            f"{effective_config.d_reset_failsafe_hours_hard_cap:.6f} hours"
        )
    d_consecutive_stop_limit = effective_config.d_consecutive_stop_limit
    if d_consecutive_stop_limit > effective_config.d_consecutive_stop_limit_hard_cap:
        raise ValueError(
            "THR-X11 value "
            f"{d_consecutive_stop_limit} exceeds Engine D consecutive-stop hard cap "
            f"{effective_config.d_consecutive_stop_limit_hard_cap}"
        )
    return EngineDCoordinationThresholdResolution(
        d_reset_failsafe_hours=d_reset_failsafe_hours,
        d_reset_failsafe_ns=int(d_reset_failsafe_hours * _NS_PER_HOUR),
        d_consecutive_stop_limit=d_consecutive_stop_limit,
    )


def build_engine_d_coordination_threshold_updates(
    config: EngineDCoordinationThresholdResolverConfig | None = None,
) -> dict[str, int]:
    """Caller-facing payload for injecting governed Engine D coordination thresholds."""

    return resolve_engine_d_coordination_thresholds(
        config
    ).to_engine_d_coordination_threshold_updates()


def _resolve_positive_float(raw_value: object, *, field_name: str) -> float:
    if isinstance(raw_value, bool):
        raise ValueError(f"{field_name} must be numeric, got boolean")
    if not isinstance(raw_value, int | float | str):
        raise ValueError(f"{field_name} must be numeric, got {raw_value!r}")
    numeric = float(raw_value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{field_name} must be a finite positive float")
    return numeric


__all__ = [
    "EngineDCoordinationThresholdResolution",
    "EngineDCoordinationThresholdResolverConfig",
    "build_engine_d_coordination_threshold_updates",
    "resolve_engine_d_coordination_thresholds",
]
