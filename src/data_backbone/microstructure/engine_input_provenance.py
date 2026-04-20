"""
V5.3 - ENGINE INPUT MICROSTRUCTURE PROVENANCE
Additive provenance bundles that link canonical microstructure records to the
current Engine A / Engine C scalar input seams without inventing new score math.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from data_backbone.microstructure.kyle_lambda import KyleLambdaRecord
from data_backbone.microstructure.order_flow_imbalance import OrderFlowImbalanceRecord
from data_backbone.microstructure.queue_pressure import QueuePressureRecord
from data_backbone.microstructure.realized_kernel_vol import RealizedKernelVolRecord
from data_backbone.microstructure.vpin import VpinRecord


ENGINE_C_MICROSTRUCTURE_INPUT_FIELDS = frozenset(
    {
        "cumulative_ofi",
        "queue_pressure",
        "vpin",
        "kyle_lambda",
        "realized_vol_current",
        "realized_vol_at_break",
    }
)
ENGINE_D_MICROSTRUCTURE_INPUT_FIELDS = frozenset(
    {
        "realized_vol_current",
        "realized_vol_post_close",
    }
)


class EngineAMicrostructureProvenance(BaseModel):
    """Canonical-record provenance bundle for Engine A scalar microstructure seams."""

    pair: str = Field(..., min_length=1)
    ofi_record: OrderFlowImbalanceRecord | None = None
    ofi_flow_score: float | None = Field(default=None, ge=0.0, le=1.0)
    realized_kernel_record: RealizedKernelVolRecord | None = None
    realized_kernel_vol_scale: float | None = Field(default=None, ge=0.0, le=1.0)
    realized_vol_current: float | None = Field(default=None, ge=0.0)
    kyle_lambda_record: KyleLambdaRecord | None = None
    kyle_lambda_cost_uplift: float = Field(default=0.0, ge=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized

    @model_validator(mode="after")
    def _validate_record_alignment(self) -> "EngineAMicrostructureProvenance":
        if self.ofi_flow_score is not None and self.ofi_record is None:
            raise ValueError("ofi_record is required when ofi_flow_score is populated")
        if self.realized_kernel_vol_scale is not None and self.realized_kernel_record is None:
            raise ValueError(
                "realized_kernel_record is required when realized_kernel_vol_scale is populated"
            )
        if self.realized_vol_current is not None and self.realized_kernel_record is None:
            raise ValueError(
                "realized_kernel_record is required when realized_vol_current is populated"
            )
        if self.kyle_lambda_cost_uplift > 0.0 and self.kyle_lambda_record is None:
            raise ValueError(
                "kyle_lambda_record is required when kyle_lambda_cost_uplift is positive"
            )
        for record in (
            self.ofi_record,
            self.realized_kernel_record,
            self.kyle_lambda_record,
        ):
            if record is not None and record.pair != self.pair:
                raise ValueError("all canonical records must match provenance pair")
        return self

    def to_runner_updates(self) -> dict[str, float | None]:
        """Return additive updates for the current Engine A input seam."""

        return {
            "ofi_flow_score": self.ofi_flow_score,
            "realized_kernel_vol_scale": self.realized_kernel_vol_scale,
            "realized_vol_current": self.realized_vol_current,
            "kyle_lambda_cost_uplift": self.kyle_lambda_cost_uplift,
        }


class EngineCMicrostructureProvenance(BaseModel):
    """Canonical-record provenance bundle for Engine C scalar microstructure seams."""

    pair: str = Field(..., min_length=1)
    ofi_record: OrderFlowImbalanceRecord | None = None
    cumulative_ofi: float | None = None
    queue_pressure_record: QueuePressureRecord | None = None
    queue_pressure: float | None = Field(default=None, ge=-1.0, le=1.0)
    vpin_record: VpinRecord | None = None
    vpin: float | None = Field(default=None, ge=0.0, le=1.0)
    kyle_lambda_record: KyleLambdaRecord | None = None
    kyle_lambda: float | None = Field(default=None, ge=0.0)
    realized_vol_current_record: RealizedKernelVolRecord | None = None
    realized_vol_current: float | None = Field(default=None, ge=0.0)
    realized_vol_at_break_record: RealizedKernelVolRecord | None = None
    realized_vol_at_break: float | None = Field(default=None, ge=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized

    @model_validator(mode="after")
    def _validate_record_alignment(self) -> "EngineCMicrostructureProvenance":
        if self.cumulative_ofi is not None and self.ofi_record is None:
            raise ValueError("ofi_record is required when cumulative_ofi is populated")
        if self.queue_pressure is not None and self.queue_pressure_record is None:
            raise ValueError(
                "queue_pressure_record is required when queue_pressure is populated"
            )
        if self.vpin is not None and self.vpin_record is None:
            raise ValueError("vpin_record is required when vpin is populated")
        if self.kyle_lambda is not None and self.kyle_lambda_record is None:
            raise ValueError("kyle_lambda_record is required when kyle_lambda is populated")
        if self.realized_vol_current is not None and self.realized_vol_current_record is None:
            raise ValueError(
                "realized_vol_current_record is required when realized_vol_current is populated"
            )
        if self.realized_vol_at_break is not None and self.realized_vol_at_break_record is None:
            raise ValueError(
                "realized_vol_at_break_record is required when realized_vol_at_break is populated"
            )
        for record in (
            self.ofi_record,
            self.queue_pressure_record,
            self.vpin_record,
            self.kyle_lambda_record,
            self.realized_vol_current_record,
            self.realized_vol_at_break_record,
        ):
            if record is not None and record.pair != self.pair:
                raise ValueError("all canonical records must match provenance pair")
        return self

    def to_runner_updates(self) -> dict[str, float | None]:
        """Return additive updates for the current Engine C input seam."""

        return {
            "cumulative_ofi": self.cumulative_ofi,
            "queue_pressure": self.queue_pressure,
            "vpin": self.vpin,
            "kyle_lambda": self.kyle_lambda,
            "realized_vol_current": self.realized_vol_current,
            "realized_vol_at_break": self.realized_vol_at_break,
        }


class EngineDMicrostructureProvenance(BaseModel):
    """Canonical-record provenance bundle for Engine D volatility input seams."""

    pair: str = Field(..., min_length=1)
    realized_vol_current_record: RealizedKernelVolRecord | None = None
    realized_vol_current: float | None = Field(default=None, ge=0.0)
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None
    realized_vol_post_close: float | None = Field(default=None, ge=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized

    @model_validator(mode="after")
    def _validate_record_alignment(self) -> "EngineDMicrostructureProvenance":
        if self.realized_vol_current is not None and self.realized_vol_current_record is None:
            raise ValueError(
                "realized_vol_current_record is required when realized_vol_current is populated"
            )
        if self.realized_vol_post_close is not None and self.realized_vol_post_close_record is None:
            raise ValueError(
                "realized_vol_post_close_record is required when realized_vol_post_close is populated"
            )
        for record in (
            self.realized_vol_current_record,
            self.realized_vol_post_close_record,
        ):
            if record is not None and record.pair != self.pair:
                raise ValueError("all canonical records must match provenance pair")
        return self

    def to_runner_updates(self) -> dict[str, float | None]:
        """Return additive updates for the current Engine D input seam."""

        return {
            "realized_vol_current": self.realized_vol_current,
            "realized_vol_post_close": self.realized_vol_post_close,
        }


def build_engine_a_microstructure_provenance(
    *,
    pair: str,
    ofi_record: OrderFlowImbalanceRecord | None = None,
    ofi_flow_score: float | None = None,
    realized_kernel_record: RealizedKernelVolRecord | None = None,
    realized_kernel_vol_scale: float | None = None,
    realized_vol_current: float | None = None,
    kyle_lambda_record: KyleLambdaRecord | None = None,
    kyle_lambda_cost_uplift: float = 0.0,
) -> EngineAMicrostructureProvenance:
    """
    Build the Engine A provenance bundle without inventing score mappings.

    Engine A still relies on caller-governed scalar transforms. This helper only
    packages explicit scalar seam values alongside their canonical record sources.
    """

    return EngineAMicrostructureProvenance(
        pair=pair,
        ofi_record=ofi_record,
        ofi_flow_score=ofi_flow_score,
        realized_kernel_record=realized_kernel_record,
        realized_kernel_vol_scale=realized_kernel_vol_scale,
        realized_vol_current=realized_vol_current,
        kyle_lambda_record=kyle_lambda_record,
        kyle_lambda_cost_uplift=kyle_lambda_cost_uplift,
    )


def build_engine_a_runner_microstructure_updates(
    *,
    pair: str,
    ofi_record: OrderFlowImbalanceRecord | None = None,
    ofi_flow_score: float | None = None,
    realized_kernel_record: RealizedKernelVolRecord | None = None,
    realized_kernel_vol_scale: float | None = None,
    realized_vol_current: float | None = None,
    kyle_lambda_record: KyleLambdaRecord | None = None,
    kyle_lambda_cost_uplift: float = 0.0,
) -> dict[str, float | None]:
    """Caller-facing Engine A adapter with explicit scalar ownership."""

    return build_engine_a_microstructure_provenance(
        pair=pair,
        ofi_record=ofi_record,
        ofi_flow_score=ofi_flow_score,
        realized_kernel_record=realized_kernel_record,
        realized_kernel_vol_scale=realized_kernel_vol_scale,
        realized_vol_current=realized_vol_current,
        kyle_lambda_record=kyle_lambda_record,
        kyle_lambda_cost_uplift=kyle_lambda_cost_uplift,
    ).to_runner_updates()


def build_engine_c_microstructure_provenance(
    *,
    pair: str,
    ofi_record: OrderFlowImbalanceRecord | None = None,
    queue_pressure_record: QueuePressureRecord | None = None,
    vpin_record: VpinRecord | None = None,
    kyle_lambda_record: KyleLambdaRecord | None = None,
    realized_vol_current_record: RealizedKernelVolRecord | None = None,
    realized_vol_at_break_record: RealizedKernelVolRecord | None = None,
) -> EngineCMicrostructureProvenance:
    """
    Build the Engine C provenance bundle from canonical records only.

    Engine C's current scalar seam is already structurally aligned with the
    canonical record values, so this helper can truthfully populate the runner
    updates without introducing a second transformation layer.
    """

    return EngineCMicrostructureProvenance(
        pair=pair,
        ofi_record=ofi_record,
        cumulative_ofi=None if ofi_record is None else ofi_record.value,
        queue_pressure_record=queue_pressure_record,
        queue_pressure=None if queue_pressure_record is None else queue_pressure_record.value,
        vpin_record=vpin_record,
        vpin=None if vpin_record is None else vpin_record.value,
        kyle_lambda_record=kyle_lambda_record,
        kyle_lambda=None if kyle_lambda_record is None else kyle_lambda_record.value,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_current=(
            None if realized_vol_current_record is None else realized_vol_current_record.value
        ),
        realized_vol_at_break_record=realized_vol_at_break_record,
        realized_vol_at_break=(
            None if realized_vol_at_break_record is None else realized_vol_at_break_record.value
        ),
    )


def build_engine_c_runner_microstructure_updates(
    *,
    pair: str,
    ofi_record: OrderFlowImbalanceRecord | None = None,
    queue_pressure_record: QueuePressureRecord | None = None,
    vpin_record: VpinRecord | None = None,
    kyle_lambda_record: KyleLambdaRecord | None = None,
    realized_vol_current_record: RealizedKernelVolRecord | None = None,
    realized_vol_at_break_record: RealizedKernelVolRecord | None = None,
) -> dict[str, float | None]:
    """Caller-facing Engine C adapter from canonical record values."""

    return build_engine_c_microstructure_provenance(
        pair=pair,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        vpin_record=vpin_record,
        kyle_lambda_record=kyle_lambda_record,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_at_break_record=realized_vol_at_break_record,
    ).to_runner_updates()


def build_engine_d_microstructure_provenance(
    *,
    pair: str,
    realized_vol_current_record: RealizedKernelVolRecord | None = None,
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None,
) -> EngineDMicrostructureProvenance:
    """Build the Engine D volatility provenance bundle from canonical records only."""

    return EngineDMicrostructureProvenance(
        pair=pair,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_current=(
            None if realized_vol_current_record is None else realized_vol_current_record.value
        ),
        realized_vol_post_close_record=realized_vol_post_close_record,
        realized_vol_post_close=(
            None if realized_vol_post_close_record is None else realized_vol_post_close_record.value
        ),
    )


def build_engine_d_runner_microstructure_updates(
    *,
    pair: str,
    realized_vol_current_record: RealizedKernelVolRecord | None = None,
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None,
) -> dict[str, float | None]:
    """Caller-facing Engine D adapter from canonical record values."""

    return build_engine_d_microstructure_provenance(
        pair=pair,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_post_close_record=realized_vol_post_close_record,
    ).to_runner_updates()


def compose_engine_c_input_payload(
    base_payload: Mapping[str, object],
    *,
    pair: str,
    ofi_record: OrderFlowImbalanceRecord | None = None,
    queue_pressure_record: QueuePressureRecord | None = None,
    vpin_record: VpinRecord | None = None,
    kyle_lambda_record: KyleLambdaRecord | None = None,
    realized_vol_current_record: RealizedKernelVolRecord | None = None,
    realized_vol_at_break_record: RealizedKernelVolRecord | None = None,
) -> dict[str, object]:
    """
    Compose a caller-owned Engine C input payload with canonical microstructure updates.

    This is the first governed upstream caller surface for Engine C. It does not
    import engine modules; it only merges caller-provided base fields with the
    current Engine C microstructure seam and rejects conflicting ownership.
    """

    normalized_pair = pair.strip().upper()
    if not normalized_pair:
        raise ValueError("pair must not be blank")
    payload = dict(base_payload)
    payload_pair = payload.get("pair")
    if payload_pair is not None and str(payload_pair).strip().upper() != normalized_pair:
        raise ValueError("base_payload pair must match canonical microstructure pair")
    payload["pair"] = normalized_pair
    updates = build_engine_c_runner_microstructure_updates(
        pair=normalized_pair,
        ofi_record=ofi_record,
        queue_pressure_record=queue_pressure_record,
        vpin_record=vpin_record,
        kyle_lambda_record=kyle_lambda_record,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_at_break_record=realized_vol_at_break_record,
    )
    for field_name, value in updates.items():
        if field_name in payload and payload[field_name] is not None and value is not None:
            if payload[field_name] != value:
                raise ValueError(
                    f"base_payload already owns conflicting Engine C microstructure field: {field_name}"
                )
        elif field_name not in payload or payload[field_name] is None:
            payload[field_name] = value
    return payload


def compose_engine_d_input_payload(
    base_payload: Mapping[str, object],
    *,
    pair: str,
    realized_vol_current_record: RealizedKernelVolRecord | None = None,
    realized_vol_post_close_record: RealizedKernelVolRecord | None = None,
) -> dict[str, object]:
    """
    Compose a caller-owned Engine D input payload with canonical realized-vol updates.

    This keeps realized-vol assembly on the shared microstructure seam and rejects
    conflicting caller ownership instead of silently overwriting existing values.
    """

    normalized_pair = pair.strip().upper()
    if not normalized_pair:
        raise ValueError("pair must not be blank")
    payload = dict(base_payload)
    payload_pair = payload.get("pair")
    if payload_pair is not None and str(payload_pair).strip().upper() != normalized_pair:
        raise ValueError("base_payload pair must match canonical microstructure pair")
    payload["pair"] = normalized_pair
    updates = build_engine_d_runner_microstructure_updates(
        pair=normalized_pair,
        realized_vol_current_record=realized_vol_current_record,
        realized_vol_post_close_record=realized_vol_post_close_record,
    )
    for field_name, value in updates.items():
        if field_name in payload and payload[field_name] is not None and value is not None:
            if payload[field_name] != value:
                raise ValueError(
                    f"base_payload already owns conflicting Engine D microstructure field: {field_name}"
                )
        elif field_name not in payload or payload[field_name] is None:
            payload[field_name] = value
    return payload


__all__ = [
    "ENGINE_C_MICROSTRUCTURE_INPUT_FIELDS",
    "ENGINE_D_MICROSTRUCTURE_INPUT_FIELDS",
    "EngineAMicrostructureProvenance",
    "EngineCMicrostructureProvenance",
    "EngineDMicrostructureProvenance",
    "build_engine_a_microstructure_provenance",
    "build_engine_a_runner_microstructure_updates",
    "build_engine_c_microstructure_provenance",
    "build_engine_c_runner_microstructure_updates",
    "build_engine_d_microstructure_provenance",
    "build_engine_d_runner_microstructure_updates",
    "compose_engine_c_input_payload",
    "compose_engine_d_input_payload",
]
