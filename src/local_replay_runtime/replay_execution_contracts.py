"""Typed execution-realism contracts for governed LOCAL_REPLAY."""

from __future__ import annotations

from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeGateConfig
from execution_backbone.slippage_model import ExecutionSlippageModel
from execution_backbone.spread_guard import ExecutionSpreadGuardModel
from pydantic import BaseModel, Field, model_validator

from local_replay_runtime.enums import ReplayExecutionProviderKind
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord

_SHADOW_PROVIDER_NAME = "shadow_execution_simulator_prudent_replay"
_SHADOW_PROVIDER_VERSION = "shadow_execution_simulator.v1"


class ParityTolerancePolicy(BaseModel, frozen=True):
    """Explicit parity policy for governed replay/shadow comparisons."""

    parity_scope: str = "logical_decision_with_prudent_score_cost_tolerance"
    decision_parity_kind: str = "logical_decision_state"
    score_parity_kind: str = "bounded_float64_score_tolerance"
    cost_parity_kind: str = "prudent_expected_cost_tolerance"
    float_precision: str = "binary64"
    minimum_compared_records: int = Field(default=1, ge=1)
    decision_match_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    score_match_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    score_tolerance: float = Field(default=0.03, ge=0.0)
    cost_tolerance: float = Field(default=0.0005, ge=0.0)


class ShadowExecutionSimulatorConfig(BaseModel, frozen=True):
    """Prudent execution assumptions for the default replay execution provider."""

    slippage_multiplier: float = Field(default=1.15, ge=1.0)
    latency_penalty_multiplier: float = Field(default=1.0, ge=1.0)
    phantom_fill_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    reduced_fill_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    economic_absurdity_buffer_bps: float = Field(default=0.50, ge=0.0)
    parity_policy: ParityTolerancePolicy = Field(default_factory=ParityTolerancePolicy)
    spread_guard_model: ExecutionSpreadGuardModel | None = None
    slippage_model: ExecutionSlippageModel | None = None
    fee_aware_edge_gate_config: FeeAwareEdgeGateConfig | None = None
    execution_runtime_projection_ref: str | None = None


class ReplayParityDiagnosticsSummary(BaseModel, frozen=True):
    """Typed parity diagnostics payload exported by governed LOCAL_REPLAY."""

    parity_status: str = Field(..., min_length=1)
    dataset_id: str = "unknown_dataset"
    decision_match_rate: float = Field(..., ge=0.0, le=1.0)
    score_match_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    baseline_status: str = "unknown"
    score_alignment: str = "unknown"
    cost_alignment: str = "unknown"
    mean_cost_gap: float = Field(default=0.0, ge=0.0)
    compared_records: int = Field(default=0, ge=0)
    missing_baseline_records: int = Field(default=0, ge=0)
    divergence_count: int = Field(default=0, ge=0)
    shared_core_match: bool = False
    book_depth_available: bool | None = None
    book_depth_levels: int | None = Field(default=None, ge=0)
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    book_depth_snapshot_count: int | None = Field(default=None, ge=0)
    book_depth_event_count: int | None = Field(default=None, ge=0)
    book_depth_missing_count: int | None = Field(default=None, ge=0)
    book_depth_staleness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_level_used: int | None = Field(default=None, ge=0)
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    shadow_extension_required: bool = True
    shadow_extension_reason: str | None = "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF"
    minimum_shadow_days_required: int | None = Field(default=None, ge=0)
    shadow_extension_status: str = "MICRO_LIVE_BLOCKED_BY_DEPTH"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_ratio_source: str = "UNKNOWN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    fill_source_status: str = "FILL_SOURCE_NOT_PROVEN"
    fill_model_name: str | None = None
    fill_model_version: str | None = None
    fill_ratio_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_ratio_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_latency_ms_expected: float | None = Field(default=None, ge=0.0)
    fill_latency_ms_observed: float | None = Field(default=None, ge=0.0)
    synthetic_fill_flag: bool = False
    measured_fill_flag: bool = False
    fill_provenance_ref: str | None = None
    fill_input_hash: str | None = None
    fill_policy_version: str | None = None
    realized_slippage_status: str = "NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    replay_cost_components: tuple[str, ...] = ()
    shadow_cost_components: tuple[str, ...] = ()
    live_cost_components: tuple[str, ...] = ()
    replay_fee_bps: float | None = Field(default=None, ge=0.0)
    shadow_fee_bps: float | None = Field(default=None, ge=0.0)
    live_fee_bps: float | None = Field(default=None, ge=0.0)
    replay_impact_bps: float | None = Field(default=None, ge=0.0)
    shadow_impact_bps: float | None = Field(default=None, ge=0.0)
    live_impact_bps: float | None = Field(default=None, ge=0.0)
    replay_slippage_bps: float | None = Field(default=None, ge=0.0)
    shadow_slippage_bps: float | None = Field(default=None, ge=0.0)
    live_slippage_bps: float | None = Field(default=None, ge=0.0)
    replay_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    live_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_drift_bps: float | None = None
    cost_drift_status: str = "NOT_PROVEN"
    parity_sample_count: int = Field(default=0, ge=0)
    parity_window_start: str | None = None
    parity_window_end: str | None = None
    parity_input_hash: str | None = None
    parity_policy_version: str | None = None
    parity_policy: dict[str, object] = Field(default_factory=dict)
    canonical_execution_backbone_status: str = "REPLAY_PROXY_ONLY"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    spread_guard_model_loaded: bool = False
    slippage_model_loaded: bool = False
    execution_runtime_projection_ref: str | None = None
    canonical_expected_cost_components: tuple[str, ...] = ()


class ReplayExecutionProviderRef(BaseModel, frozen=True):
    """Implementation metadata for the current replay execution provider."""

    provider_kind: ReplayExecutionProviderKind = ReplayExecutionProviderKind.SHADOW_SIMULATOR
    provider_name: str = Field(default=_SHADOW_PROVIDER_NAME, min_length=1)
    provider_version: str = Field(default=_SHADOW_PROVIDER_VERSION, min_length=1)


class ReplayExecutionEvaluationRequest(BaseModel, frozen=True):
    """Typed input for execution-realism evaluation inside LOCAL_REPLAY."""

    dataset: HistoricalReplayDataset
    execution_label: str = Field(default="shadow_fidelity_mode", min_length=1)
    execution_runtime_projection_path: str | None = None
    provider: ReplayExecutionProviderRef = Field(default_factory=ReplayExecutionProviderRef)
    simulator_config: ShadowExecutionSimulatorConfig = Field(
        default_factory=ShadowExecutionSimulatorConfig
    )


class ReplayExecutionEvaluationResult(BaseModel, frozen=True):
    """Typed output of the replay execution-realism seam."""

    request: ReplayExecutionEvaluationRequest
    dtr_records: tuple[DTRRecord, ...]
    parity_diagnostics: ReplayParityDiagnosticsSummary

    @model_validator(mode="after")
    def validate_record_count(self) -> "ReplayExecutionEvaluationResult":
        if len(self.dtr_records) != self.request.dataset.record_count:
            raise ValueError(
                "ReplayExecutionEvaluationResult dtr_records must match dataset record_count"
            )
        return self

    @property
    def parity_diagnostics_payload(self) -> dict[str, object]:
        return self.parity_diagnostics.model_dump(mode="json")


__all__ = [
    "ParityTolerancePolicy",
    "ReplayExecutionEvaluationRequest",
    "ReplayExecutionEvaluationResult",
    "ReplayExecutionProviderRef",
    "ReplayParityDiagnosticsSummary",
    "ShadowExecutionSimulatorConfig",
]
