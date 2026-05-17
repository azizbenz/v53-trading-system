"""
V5.3 - MICROSTRUCTURE FEATURE REGISTRY
Canonical registry for governed microstructure features.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, unique
from hashlib import sha256
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from data_backbone.microstructure.amihud_illiquidity import (
    AMIHUD_METHOD_VERSION,
    AMIHUD_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.corwin_schultz_spread import (
    CORWIN_SCHULTZ_METHOD_VERSION,
    CORWIN_SCHULTZ_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.hawkes_intensity import (
    HAWKES_METHOD_VERSION,
    HAWKES_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.kyle_lambda import (
    KYLE_LAMBDA_METHOD_VERSION,
    KYLE_LAMBDA_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.order_flow_imbalance import (
    ORDER_FLOW_IMBALANCE_METHOD_VERSION,
    ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.pin import (
    PIN_METHOD_VERSION,
    PIN_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.queue_pressure import (
    QUEUE_PRESSURE_METHOD_VERSION,
    QUEUE_PRESSURE_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.realized_effective_spread import (
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION,
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.realized_kernel_vol import (
    REALIZED_KERNEL_METHOD_VERSION,
    REALIZED_KERNEL_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.roll_spread import (
    ROLL_SPREAD_METHOD_VERSION,
    ROLL_SPREAD_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.vpin import (
    VPIN_METHOD_VERSION,
    VPIN_METHOD_VERSION_HASH,
)
from data_backbone.microstructure.walls_and_spoofing import (
    WALLS_AND_SPOOFING_METHOD_VERSION,
    WALLS_AND_SPOOFING_METHOD_VERSION_HASH,
)


@unique
class MicrostructurePromotionState(str, Enum):
    """Doc 23 feature-promotion ladder for governed microstructure rollout."""

    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    CANDIDATE_VPS = "CANDIDATE_VPS"
    SHADOW_VPS = "SHADOW_VPS"
    LIVE_VPS = "LIVE_VPS"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class MicrostructureFeatureSpec(BaseModel):
    """Canonical feature metadata used before any calculator is admitted."""

    feature_id: str = Field(..., min_length=1)
    reference_paper: str = Field(..., min_length=1)
    default_window_events: int | None = Field(default=None, ge=1)
    default_window_seconds: float | None = Field(default=None, gt=0.0)
    calibration_seam_path: str = Field(..., min_length=1)
    consumed_by: tuple[str, ...] = Field(..., min_length=1)
    consumer_statuses: tuple[str, ...] = Field(default=("NOT_PROVEN",), min_length=1)
    runtime_lifecycle_status: str = "NOT_PROVEN"
    promotion_state: MicrostructurePromotionState
    method_version: str = Field(..., min_length=1)
    method_version_hash: str = Field(..., min_length=8)
    quarantined_from: MicrostructurePromotionState | None = None
    lifecycle_reason: str | None = None
    unit_status: str | None = None
    cross_pair_comparable: bool | None = None
    normalization_status: str | None = None
    normalized_seam_available: bool | None = None
    calibration_status: str | None = None
    registry_intent_status: str | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("feature_id")
    @classmethod
    def _normalize_feature_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("feature_id must not be blank")
        return normalized

    @field_validator("reference_paper", "method_version", "method_version_hash")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text fields must not be blank")
        return normalized

    @field_validator("lifecycle_reason")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("lifecycle_reason must not be blank when provided")
        return normalized

    @field_validator("calibration_seam_path")
    @classmethod
    def _normalize_calibration_path(cls, value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        if not normalized.startswith("src/") or not normalized.endswith(".py"):
            raise ValueError("calibration_seam_path must be a src/*.py path")
        return normalized

    @field_validator("consumed_by")
    @classmethod
    def _normalize_consumers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for consumer in value:
            stripped = consumer.strip()
            if not stripped:
                raise ValueError("consumed_by must not contain blank entries")
            normalized.append(stripped)
        if not normalized:
            raise ValueError("consumed_by must not be empty")
        return tuple(normalized)

    @field_validator("consumer_statuses")
    @classmethod
    def _normalize_consumer_statuses(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for status in value:
            stripped = status.strip().upper()
            if not stripped:
                raise ValueError("consumer_statuses must not contain blank entries")
            normalized.append(stripped)
        if not normalized:
            raise ValueError("consumer_statuses must not be empty")
        return tuple(normalized)

    @field_validator("runtime_lifecycle_status")
    @classmethod
    def _normalize_runtime_lifecycle_status(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("runtime_lifecycle_status must not be blank")
        return normalized

    @field_validator("registry_intent_status")
    @classmethod
    def _normalize_registry_intent_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("registry_intent_status must not be blank when provided")
        return normalized

    @model_validator(mode="after")
    def _validate_window_shape(self) -> "MicrostructureFeatureSpec":
        if self.default_window_events is None and self.default_window_seconds is None:
            raise ValueError("at least one default window dimension must be populated")
        if self.promotion_state is MicrostructurePromotionState.QUARANTINED:
            if self.quarantined_from is None:
                raise ValueError("quarantined specs must record quarantined_from")
            if self.quarantined_from in {
                MicrostructurePromotionState.QUARANTINED,
                MicrostructurePromotionState.REJECTED,
            }:
                raise ValueError("quarantined_from must point to an active ladder state")
        elif self.quarantined_from is not None:
            raise ValueError("quarantined_from is only valid when promotion_state=QUARANTINED")
        if self.promotion_state is MicrostructurePromotionState.REJECTED and self.lifecycle_reason is None:
            raise ValueError("rejected specs must carry lifecycle_reason")
        return self


_PROMOTION_ORDER: tuple[MicrostructurePromotionState, ...] = (
    MicrostructurePromotionState.DISCOVERED,
    MicrostructurePromotionState.VALIDATED,
    MicrostructurePromotionState.CANDIDATE_VPS,
    MicrostructurePromotionState.SHADOW_VPS,
    MicrostructurePromotionState.LIVE_VPS,
)
_PROMOTION_INDEX = {state: index for index, state in enumerate(_PROMOTION_ORDER)}

_IMPLEMENTATION_METHODS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "ofi.cont_kukanov": (
            ORDER_FLOW_IMBALANCE_METHOD_VERSION,
            ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH,
        ),
        "vpin.easley_lopez_ohara": (VPIN_METHOD_VERSION, VPIN_METHOD_VERSION_HASH),
        "kyle_lambda.kyle": (KYLE_LAMBDA_METHOD_VERSION, KYLE_LAMBDA_METHOD_VERSION_HASH),
        "amihud_illiquidity.amihud": (AMIHUD_METHOD_VERSION, AMIHUD_METHOD_VERSION_HASH),
        "roll_spread.roll": (ROLL_SPREAD_METHOD_VERSION, ROLL_SPREAD_METHOD_VERSION_HASH),
        "corwin_schultz_spread.corwin_schultz": (
            CORWIN_SCHULTZ_METHOD_VERSION,
            CORWIN_SCHULTZ_METHOD_VERSION_HASH,
        ),
        "realized_kernel_vol.barndorff_nielsen": (
            REALIZED_KERNEL_METHOD_VERSION,
            REALIZED_KERNEL_METHOD_VERSION_HASH,
        ),
        "hawkes_intensity.bacry_mastromatteo_muzy": (
            HAWKES_METHOD_VERSION,
            HAWKES_METHOD_VERSION_HASH,
        ),
        "pin.easley_kiefer_ohara_paperman": (PIN_METHOD_VERSION, PIN_METHOD_VERSION_HASH),
        "queue_pressure.book_imbalance": (
            QUEUE_PRESSURE_METHOD_VERSION,
            QUEUE_PRESSURE_METHOD_VERSION_HASH,
        ),
        "realized_effective_spread.live": (
            REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION,
            REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
        ),
        **{
            feature_id: (
                WALLS_AND_SPOOFING_METHOD_VERSION,
                WALLS_AND_SPOOFING_METHOD_VERSION_HASH,
            )
            for feature_id in (
                "wall_strength_bid",
                "wall_strength_ask",
                "wall_persistence_bid",
                "wall_persistence_ask",
                "wall_persistence_conditional_bid",
                "wall_persistence_conditional_ask",
                "wall_pullaway_bid",
                "wall_pullaway_ask",
                "near_touch_cancel_ratio_bid",
                "near_touch_cancel_ratio_ask",
                "executed_vs_displayed_bid",
                "executed_vs_displayed_ask",
                "book_shape_skew",
                "microprice_pressure",
                "real_wall_score_bid",
                "real_wall_score_ask",
                "spoof_suspicion_score_bid",
                "spoof_suspicion_score_ask",
                "deceptive_liquidity_score",
                "observation_coverage_ratio",
            )
        },
    }
)


def is_valid_feature_promotion_transition(
    current: MicrostructurePromotionState,
    target: MicrostructurePromotionState,
) -> bool:
    """Allow only idempotent or one-step-forward moves on the active ladder."""

    if current == target:
        return True
    if current in {
        MicrostructurePromotionState.QUARANTINED,
        MicrostructurePromotionState.REJECTED,
    }:
        return False
    if target in {
        MicrostructurePromotionState.QUARANTINED,
        MicrostructurePromotionState.REJECTED,
    }:
        return False
    return _PROMOTION_INDEX[target] == _PROMOTION_INDEX[current] + 1


def _validated_spec_copy(
    spec: MicrostructureFeatureSpec,
    **updates: object,
) -> MicrostructureFeatureSpec:
    data = spec.model_dump(mode="python")
    data.update(updates)
    return MicrostructureFeatureSpec.model_validate(data)


def promote_feature_spec(
    spec: MicrostructureFeatureSpec,
    target: MicrostructurePromotionState,
) -> MicrostructureFeatureSpec:
    """Return a copy with a governed state transition applied."""

    if not is_valid_feature_promotion_transition(spec.promotion_state, target):
        raise ValueError(
            f"invalid promotion transition: {spec.promotion_state.value} -> {target.value}"
        )
    return _validated_spec_copy(
        spec,
        promotion_state=target,
        quarantined_from=None,
        lifecycle_reason=None,
    )


def quarantine_feature_spec(
    spec: MicrostructureFeatureSpec,
    *,
    reason: str,
) -> MicrostructureFeatureSpec:
    """Temporarily withdraw a feature from the active ladder while preserving rollback target."""

    if spec.promotion_state in {
        MicrostructurePromotionState.QUARANTINED,
        MicrostructurePromotionState.REJECTED,
    }:
        raise ValueError(f"cannot quarantine feature from {spec.promotion_state.value}")
    return _validated_spec_copy(
        spec,
        promotion_state=MicrostructurePromotionState.QUARANTINED,
        quarantined_from=spec.promotion_state,
        lifecycle_reason=reason,
    )


def restore_quarantined_feature_spec(spec: MicrostructureFeatureSpec) -> MicrostructureFeatureSpec:
    """Rollback one quarantined feature to its last known active state."""

    if spec.promotion_state is not MicrostructurePromotionState.QUARANTINED:
        raise ValueError("restore is only valid from QUARANTINED")
    if spec.quarantined_from is None:
        raise ValueError("quarantined spec is missing quarantined_from")
    return _validated_spec_copy(
        spec,
        promotion_state=spec.quarantined_from,
        quarantined_from=None,
        lifecycle_reason=None,
    )


def reject_feature_spec(
    spec: MicrostructureFeatureSpec,
    *,
    reason: str,
) -> MicrostructureFeatureSpec:
    """Mark a feature as explicitly rejected / not promotable."""

    if spec.promotion_state is MicrostructurePromotionState.REJECTED:
        return _validated_spec_copy(spec, lifecycle_reason=reason)
    return _validated_spec_copy(
        spec,
        promotion_state=MicrostructurePromotionState.REJECTED,
        quarantined_from=None,
        lifecycle_reason=reason,
    )


def _spec(
    *,
    feature_id: str,
    reference_paper: str,
    default_window_events: int | None,
    default_window_seconds: float | None,
    calibration_seam_path: str,
    consumed_by: tuple[str, ...],
    consumer_statuses: tuple[str, ...] = ("NOT_PROVEN",),
    runtime_lifecycle_status: str = "NOT_PROVEN",
    method_version: str,
    method_version_hash: str,
    unit_status: str | None = None,
    cross_pair_comparable: bool | None = None,
    normalization_status: str | None = None,
    normalized_seam_available: bool | None = None,
    calibration_status: str | None = None,
    registry_intent_status: str | None = None,
) -> MicrostructureFeatureSpec:
    return MicrostructureFeatureSpec(
        feature_id=feature_id,
        reference_paper=reference_paper,
        default_window_events=default_window_events,
        default_window_seconds=default_window_seconds,
        calibration_seam_path=calibration_seam_path,
        consumed_by=consumed_by,
        consumer_statuses=consumer_statuses,
        runtime_lifecycle_status=runtime_lifecycle_status,
        promotion_state=MicrostructurePromotionState.DISCOVERED,
        method_version=method_version,
        method_version_hash=method_version_hash,
        unit_status=unit_status,
        cross_pair_comparable=cross_pair_comparable,
        normalization_status=normalization_status,
        normalized_seam_available=normalized_seam_available,
        calibration_status=calibration_status,
        registry_intent_status=registry_intent_status,
    )


_FEATURE_SPECS: tuple[MicrostructureFeatureSpec, ...] = (
    _spec(
        feature_id="ofi.cont_kukanov",
        reference_paper=(
            "Cont R., Kukanov A., Stoikov S. (2014) The Price Impact of Order Book "
            "Events, Journal of Financial Econometrics 12(1), 47-88."
        ),
        default_window_events=200,
        default_window_seconds=None,
        calibration_seam_path="src/calibration_methods/ofi_cont_kukanov_calibration.py",
        consumed_by=(
            "engines.engine_c.continuation_validator_c",
            "engines.engine_a.conviction_builder_a",
            "meta_learning",
        ),
        consumer_statuses=("ENGINE_CONSUMED",),
        runtime_lifecycle_status="ACTIVE_ENGINE_INPUT",
        unit_status="RAW_SIGNED_SIZE_IMBALANCE",
        cross_pair_comparable=False,
        normalization_status="ENGINE_LOCAL_THRESHOLDS",
        normalized_seam_available=True,
        method_version=ORDER_FLOW_IMBALANCE_METHOD_VERSION,
        method_version_hash=ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="vpin.easley_lopez_ohara",
        reference_paper=(
            "Easley D., Lopez de Prado M., O'Hara M. (2012) Flow Toxicity and "
            "Liquidity in a High-Frequency World, Review of Financial Studies 25(5), "
            "1457-1493."
        ),
        default_window_events=None,
        default_window_seconds=86_400.0,
        calibration_seam_path="src/calibration_methods/vpin_easley_lopez_ohara_calibration.py",
        consumed_by=(
            "engines.engine_c.continuation_validator_c",
            "engines.engine_b.excess_detector_b",
        ),
        consumer_statuses=("ENGINE_CONSUMED",),
        runtime_lifecycle_status="ACTIVE_ENGINE_INPUT",
        method_version=VPIN_METHOD_VERSION,
        method_version_hash=VPIN_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="kyle_lambda.kyle",
        reference_paper=(
            "Kyle A. (1985) Continuous Auctions and Insider Trading, Econometrica "
            "53(6), 1315-1335."
        ),
        default_window_events=500,
        default_window_seconds=None,
        calibration_seam_path="src/calibration_methods/kyle_lambda_calibration.py",
        consumed_by=(
            "engines.engine_c.continuation_validator_c",
            "engines.engine_a.cost_feasibility_a",
            "execution_backbone",
        ),
        consumer_statuses=("ENGINE_CONSUMED", "COST_GATE_CONSUMED"),
        runtime_lifecycle_status="ACTIVE_ENGINE_INPUT",
        unit_status="UNNORMALIZED_LOCAL_OLS_SLOPE",
        cross_pair_comparable=False,
        normalization_status="ENGINE_LOCAL_THRESHOLDS",
        normalized_seam_available=True,
        method_version=KYLE_LAMBDA_METHOD_VERSION,
        method_version_hash=KYLE_LAMBDA_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="amihud_illiquidity.amihud",
        reference_paper=(
            "Amihud Y. (2002) Illiquidity and stock returns: cross-section and "
            "time-series effects, Journal of Financial Markets 5(1), 31-56."
        ),
        default_window_events=None,
        default_window_seconds=86_400.0,
        calibration_seam_path="src/calibration_methods/amihud_illiquidity_calibration.py",
        consumed_by=(
            "portfolio_minimal",
            "scoring_backbone",
            "interface_contracts.pair_catalog",
        ),
        consumer_statuses=("RESEARCH_ONLY", "NOT_RUNTIME_CONSUMED"),
        runtime_lifecycle_status="RESEARCH_ONLY",
        registry_intent_status="PAIR_LIQUIDITY_REPORT",
        method_version=AMIHUD_METHOD_VERSION,
        method_version_hash=AMIHUD_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="roll_spread.roll",
        reference_paper=(
            "Roll R. (1984) A Simple Implicit Measure of the Effective Bid-Ask Spread "
            "in an Efficient Market, Journal of Finance 39(4), 1127-1139."
        ),
        default_window_events=None,
        default_window_seconds=3_600.0,
        calibration_seam_path="src/calibration_methods/roll_spread_calibration.py",
        consumed_by=("execution_backbone.execution_cost_meter",),
        consumer_statuses=("COST_GATE_CONSUMED",),
        runtime_lifecycle_status="FALLBACK_ONLY",
        registry_intent_status="MISSING_L2_SPREAD_FALLBACK",
        method_version=ROLL_SPREAD_METHOD_VERSION,
        method_version_hash=ROLL_SPREAD_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="corwin_schultz_spread.corwin_schultz",
        reference_paper=(
            "Corwin S. A., Schultz P. (2012) A Simple Way to Estimate Bid-Ask "
            "Spreads from Daily High and Low Prices, Journal of Finance 67(2), 719-760."
        ),
        default_window_events=None,
        default_window_seconds=86_400.0,
        calibration_seam_path="src/calibration_methods/corwin_schultz_spread_calibration.py",
        consumed_by=(
            "interface_contracts.pair_catalog",
            "meta_learning",
        ),
        consumer_statuses=("RESEARCH_ONLY", "NOT_RUNTIME_CONSUMED"),
        runtime_lifecycle_status="RESEARCH_ONLY",
        registry_intent_status="OHLC_FALLBACK",
        method_version=CORWIN_SCHULTZ_METHOD_VERSION,
        method_version_hash=CORWIN_SCHULTZ_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="realized_kernel_vol.barndorff_nielsen",
        reference_paper=(
            "Barndorff-Nielsen O. E., Hansen P. R., Lunde A., Shephard N. (2008) "
            "Designing Realized Kernels to Measure the Ex-Post Variation of Equity "
            "Prices in the Presence of Noise, Econometrica 76(6), 1481-1536."
        ),
        default_window_events=None,
        default_window_seconds=3_600.0,
        calibration_seam_path="src/calibration_methods/realized_kernel_vol_calibration.py",
        consumed_by=(
            "data_backbone.microstructure.engine_input_provenance",
            "engines.engine_a.structure_detector_a",
            "engines.engine_a.engine_a_runtime_support",
            "engines.engine_a.invalidation_mapper_a",
            "engines.engine_c.engine_c_runtime_forecast_support",
            "engines.engine_c.invalidation_mapper_c",
            "engines.engine_c.structure_resolver_c",
            "engines.engine_d.runtime_input_assembler_d",
            "engines.engine_d.engine_d_runtime_support",
            "engines.engine_d.invalidation_mapper_d",
        ),
        consumer_statuses=("ENGINE_CONSUMED",),
        runtime_lifecycle_status="ACTIVE_ENGINE_INPUT",
        method_version=REALIZED_KERNEL_METHOD_VERSION,
        method_version_hash=REALIZED_KERNEL_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="hawkes_intensity.bacry_mastromatteo_muzy",
        reference_paper=(
            "Bacry E., Mastromatteo I., Muzy J.-F. (2015) Hawkes Processes in "
            "Finance, Market Microstructure and Liquidity 1(1)."
        ),
        default_window_events=1000,
        default_window_seconds=None,
        calibration_seam_path="src/calibration_methods/hawkes_intensity_calibration.py",
        consumed_by=(
            "engines.engine_c.continuation_validator_c",
            "meta_learning",
        ),
        consumer_statuses=("FUTURE_RESERVED", "RESEARCH_ONLY", "NOT_RUNTIME_CONSUMED"),
        runtime_lifecycle_status="FUTURE_RESERVED",
        registry_intent_status="ENGINE_C_INTENSITY_RESEARCH",
        method_version=HAWKES_METHOD_VERSION,
        method_version_hash=HAWKES_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="pin.easley_kiefer_ohara_paperman",
        reference_paper=(
            "Easley D., Kiefer N., O'Hara M., Paperman J. (1996) Liquidity, "
            "Information, and Infrequently Traded Stocks, Journal of Finance 51(4), "
            "1405-1436."
        ),
        default_window_events=None,
        default_window_seconds=604_800.0,
        calibration_seam_path="src/calibration_methods/pin_calibration.py",
        consumed_by=("meta_learning",),
        consumer_statuses=("FUTURE_RESERVED", "RESEARCH_ONLY", "NOT_RUNTIME_CONSUMED"),
        runtime_lifecycle_status="FUTURE_RESERVED",
        registry_intent_status="OFFLINE_PARAMETER_SEAM",
        method_version=PIN_METHOD_VERSION,
        method_version_hash=PIN_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="queue_pressure.book_imbalance",
        reference_paper="Standard top-of-book / top-k book-imbalance practice for queue pressure.",
        default_window_events=1,
        default_window_seconds=None,
        calibration_seam_path="src/calibration_methods/queue_pressure_calibration.py",
        consumed_by=("engines.engine_c.continuation_validator_c",),
        consumer_statuses=("ENGINE_CONSUMED",),
        runtime_lifecycle_status="ACTIVE_ENGINE_INPUT",
        method_version=QUEUE_PRESSURE_METHOD_VERSION,
        method_version_hash=QUEUE_PRESSURE_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="realized_effective_spread.live",
        reference_paper=(
            "Standard market microstructure quoted/effective/realized spread "
            "definitions for live execution-cost monitoring."
        ),
        default_window_events=None,
        default_window_seconds=300.0,
        calibration_seam_path="src/calibration_methods/realized_effective_spread_calibration.py",
        consumed_by=(
            "execution_backbone.execution_cost_meter",
            "meta_minimal",
        ),
        consumer_statuses=("COST_GATE_CONSUMED",),
        runtime_lifecycle_status="ACTIVE_EXECUTION_GATE",
        method_version=REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION,
        method_version_hash=REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
    ),
    *tuple(
        _spec(
            feature_id=feature_id,
            reference_paper=(
                "Walls and spoof-like deceptive-liquidity detector for real-wall "
                "presence, pull-away near touch, executed-vs-displayed gap, and "
                "bounded deceptive-liquidity suspicion."
            ),
            default_window_events=None,
            default_window_seconds=5.0,
            calibration_seam_path="src/calibration_methods/walls_and_spoofing_calibration.py",
            consumed_by=(
                "local_replay_runtime",
                "meta_learning",
                "complete_enablers.regime_detector_runtime",
            ),
            consumer_statuses=("RUNTIME_CONSUMED",),
            runtime_lifecycle_status="ACTIVE_RUNTIME",
            calibration_status="CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM",
            method_version=WALLS_AND_SPOOFING_METHOD_VERSION,
            method_version_hash=WALLS_AND_SPOOFING_METHOD_VERSION_HASH,
        )
        for feature_id in (
            "wall_strength_bid",
            "wall_strength_ask",
            "wall_persistence_bid",
            "wall_persistence_ask",
            "wall_persistence_conditional_bid",
            "wall_persistence_conditional_ask",
            "wall_pullaway_bid",
            "wall_pullaway_ask",
            "near_touch_cancel_ratio_bid",
            "near_touch_cancel_ratio_ask",
            "executed_vs_displayed_bid",
            "executed_vs_displayed_ask",
            "book_shape_skew",
            "microprice_pressure",
            "real_wall_score_bid",
            "real_wall_score_ask",
            "spoof_suspicion_score_bid",
            "spoof_suspicion_score_ask",
            "deceptive_liquidity_score",
            "observation_coverage_ratio",
        )
    ),
)


def _build_registry(
    specs: tuple[MicrostructureFeatureSpec, ...],
) -> Mapping[str, MicrostructureFeatureSpec]:
    registry: dict[str, MicrostructureFeatureSpec] = {}
    for spec in specs:
        if spec.feature_id in registry:
            raise ValueError(f"duplicate microstructure feature_id: {spec.feature_id}")
        expected_method = _IMPLEMENTATION_METHODS.get(spec.feature_id)
        if expected_method is None:
            raise ValueError(f"unknown implementation mapping for feature_id: {spec.feature_id}")
        if (spec.method_version, spec.method_version_hash) != expected_method:
            raise ValueError(
                "registry method version drift detected for "
                f"{spec.feature_id}: {spec.method_version}/{spec.method_version_hash}"
            )
        expected_hash = sha256(spec.method_version.encode("utf-8")).hexdigest()
        if spec.method_version_hash != expected_hash:
            raise ValueError(
                f"method_version_hash mismatch for {spec.feature_id}: {spec.method_version_hash}"
            )
        registry[spec.feature_id] = spec
    return MappingProxyType(registry)


FEATURE_REGISTRY: Mapping[str, MicrostructureFeatureSpec] = _build_registry(_FEATURE_SPECS)


def get_feature_registry() -> Mapping[str, MicrostructureFeatureSpec]:
    """Return the immutable canonical feature registry."""

    return FEATURE_REGISTRY


def list_feature_specs() -> tuple[MicrostructureFeatureSpec, ...]:
    """Return registry specs in canonical declaration order."""

    return _FEATURE_SPECS


def get_feature_spec(feature_id: str) -> MicrostructureFeatureSpec:
    """Resolve one feature by canonical id."""

    normalized = feature_id.strip().lower()
    try:
        return FEATURE_REGISTRY[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown microstructure feature_id: {feature_id}") from exc


__all__ = [
    "FEATURE_REGISTRY",
    "MicrostructureFeatureSpec",
    "MicrostructurePromotionState",
    "get_feature_registry",
    "get_feature_spec",
    "is_valid_feature_promotion_transition",
    "list_feature_specs",
    "promote_feature_spec",
    "quarantine_feature_spec",
    "reject_feature_spec",
    "restore_quarantined_feature_spec",
]
