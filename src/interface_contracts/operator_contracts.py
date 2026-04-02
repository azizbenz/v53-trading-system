"""Operator-governance contracts shared across monitoring, UI, and protocols."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .domain_types import RuntimeMode, TimestampedModel


class OperatorSafingAction(StrEnum):
    """Manual operator safing actions that can block or downgrade runtime exposure."""

    SET_HALTED = "set_halted"
    DOWNGRADE_TO_MICRO_LIVE = "downgrade_to_micro_live"
    DOWNGRADE_TO_SHADOW = "downgrade_to_shadow"


class OperatorSafingRequest(TimestampedModel):
    """Audit-ready operator safing request propagated into protocol gates."""

    request_id: str = Field(..., min_length=1)
    action: OperatorSafingAction
    source_runtime_mode: RuntimeMode
    target_runtime_mode: RuntimeMode | None = None
    requested_by: str = Field(default="operator", min_length=1)
    ui_channel: str = Field(default="local_operator_ui", min_length=1)
    reason: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_request(self) -> "OperatorSafingRequest":
        if self.source_runtime_mode == RuntimeMode.LOCAL_REPLAY:
            raise ValueError(
                "operator safing requests are forbidden from runtime_mode=LOCAL_REPLAY"
            )
        if not self.reason.strip():
            raise ValueError("operator safing requests require a non-empty reason")
        if self.action == OperatorSafingAction.SET_HALTED:
            if self.target_runtime_mode is not None:
                raise ValueError("set_halted must not declare a target_runtime_mode")
            return self
        if self.action == OperatorSafingAction.DOWNGRADE_TO_MICRO_LIVE:
            if self.source_runtime_mode != RuntimeMode.LIVE:
                raise ValueError(
                    "downgrade_to_micro_live requires source_runtime_mode=LIVE"
                )
            if self.target_runtime_mode != RuntimeMode.MICRO_LIVE:
                raise ValueError(
                    "downgrade_to_micro_live requires target_runtime_mode=MICRO_LIVE"
                )
            return self
        if self.action == OperatorSafingAction.DOWNGRADE_TO_SHADOW:
            if self.source_runtime_mode not in {RuntimeMode.MICRO_LIVE, RuntimeMode.LIVE}:
                raise ValueError(
                    "downgrade_to_shadow requires source_runtime_mode=MICRO_LIVE or LIVE"
                )
            if self.target_runtime_mode != RuntimeMode.SHADOW:
                raise ValueError(
                    "downgrade_to_shadow requires target_runtime_mode=SHADOW"
                )
            return self
        return self


__all__ = ["OperatorSafingAction", "OperatorSafingRequest"]
