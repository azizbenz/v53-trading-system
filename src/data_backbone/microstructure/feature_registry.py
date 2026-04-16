"""
V5.3 - MICROSTRUCTURE FEATURE REGISTRY
Canonical registry for governed microstructure features.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, unique
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
    promotion_state: MicrostructurePromotionState
    method_version: str = Field(..., min_length=1)
    method_version_hash: str = Field(..., min_length=8)
    quarantined_from: MicrostructurePromotionState | None = None
    lifecycle_reason: str | None = None

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


def promote_feature_spec(
    spec: MicrostructureFeatureSpec,
    target: MicrostructurePromotionState,
) -> MicrostructureFeatureSpec:
    """Return a copy with a governed state transition applied."""

    if not is_valid_feature_promotion_transition(spec.promotion_state, target):
        raise ValueError(
            f"invalid promotion transition: {spec.promotion_state.value} -> {target.value}"
        )
    return spec.model_copy(
        update={
            "promotion_state": target,
            "quarantined_from": None,
            "lifecycle_reason": None,
        }
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
    return spec.model_copy(
        update={
            "promotion_state": MicrostructurePromotionState.QUARANTINED,
            "quarantined_from": spec.promotion_state,
            "lifecycle_reason": reason,
        }
    )


def restore_quarantined_feature_spec(spec: MicrostructureFeatureSpec) -> MicrostructureFeatureSpec:
    """Rollback one quarantined feature to its last known active state."""

    if spec.promotion_state is not MicrostructurePromotionState.QUARANTINED:
        raise ValueError("restore is only valid from QUARANTINED")
    if spec.quarantined_from is None:
        raise ValueError("quarantined spec is missing quarantined_from")
    return spec.model_copy(
        update={
            "promotion_state": spec.quarantined_from,
            "quarantined_from": None,
            "lifecycle_reason": None,
        }
    )


def reject_feature_spec(
    spec: MicrostructureFeatureSpec,
    *,
    reason: str,
) -> MicrostructureFeatureSpec:
    """Mark a feature as explicitly rejected / not promotable."""

    if spec.promotion_state is MicrostructurePromotionState.REJECTED:
        return spec.model_copy(update={"lifecycle_reason": reason})
    return spec.model_copy(
        update={
            "promotion_state": MicrostructurePromotionState.REJECTED,
            "quarantined_from": None,
            "lifecycle_reason": reason,
        }
    )


def _spec(
    *,
    feature_id: str,
    reference_paper: str,
    default_window_events: int | None,
    default_window_seconds: float | None,
    calibration_seam_path: str,
    consumed_by: tuple[str, ...],
    method_version: str,
    method_version_hash: str,
) -> MicrostructureFeatureSpec:
    return MicrostructureFeatureSpec(
        feature_id=feature_id,
        reference_paper=reference_paper,
        default_window_events=default_window_events,
        default_window_seconds=default_window_seconds,
        calibration_seam_path=calibration_seam_path,
        consumed_by=consumed_by,
        promotion_state=MicrostructurePromotionState.DISCOVERED,
        method_version=method_version,
        method_version_hash=method_version_hash,
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
            "engine_c.continuation_validator_c",
            "engine_a.conviction_builder_a",
            "meta_learning.ml_enabler",
        ),
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
            "engine_c.continuation_validator_c",
            "engine_b.toxic_flow_fade",
        ),
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
            "engine_c.continuation_validator_c",
            "engine_a.cost_feasibility",
            "execution_backbone.slippage_pre_estimate",
        ),
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
            "portfolio_minimal.pair_selection",
            "scoring_backbone.cost_feasibility",
            "interface_contracts.pair_catalog",
        ),
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
            "meta_learning.cross_exchange_parity_checks",
        ),
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
            "engine_a.vol_scaling",
            "engine_c.structure_detector_c",
            "portfolio_minimal.vol_target_sizer",
            "risk_backbone.regime_shift_watcher",
        ),
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
            "engine_c.continuation_validator_c",
            "meta_learning.ml_enabler",
        ),
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
        consumed_by=("meta_learning.pair_selection_diagnostics",),
        method_version=PIN_METHOD_VERSION,
        method_version_hash=PIN_METHOD_VERSION_HASH,
    ),
    _spec(
        feature_id="queue_pressure.book_imbalance",
        reference_paper="Standard top-of-book / top-k book-imbalance practice for queue pressure.",
        default_window_events=1,
        default_window_seconds=None,
        calibration_seam_path="src/calibration_methods/queue_pressure_calibration.py",
        consumed_by=(
            "engine_a",
            "engine_b",
            "engine_c",
            "engine_d",
            "execution_backbone",
        ),
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
            "meta_minimal.cost_drift_monitor",
        ),
        method_version=REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION,
        method_version_hash=REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
    ),
)


def _build_registry(
    specs: tuple[MicrostructureFeatureSpec, ...],
) -> Mapping[str, MicrostructureFeatureSpec]:
    registry: dict[str, MicrostructureFeatureSpec] = {}
    for spec in specs:
        if spec.feature_id in registry:
            raise ValueError(f"duplicate microstructure feature_id: {spec.feature_id}")
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
