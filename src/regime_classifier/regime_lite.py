"""Typed three-state regime helper with bounded hysteresis and cooldown."""

from __future__ import annotations

from enum import StrEnum
import math
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from calibration_loader import CalibrationLoader
from calibration_loader.contracts import CalibrationArtifactCollection
from calibration_loader.loader import CalibrationArtifactValidationError


class RegimeLiteState(StrEnum):
    CALM = "calm"
    STRESSED = "stressed"
    EXTREME = "extreme"


_STATE_RANK: dict[RegimeLiteState, int] = {
    RegimeLiteState.CALM: 0,
    RegimeLiteState.STRESSED: 1,
    RegimeLiteState.EXTREME: 2,
}
_STATE_SEQUENCE: tuple[RegimeLiteState, ...] = (
    RegimeLiteState.CALM,
    RegimeLiteState.STRESSED,
    RegimeLiteState.EXTREME,
)


class RegimeLiteCalibrationConfig(BaseModel, frozen=True):
    """Opt-in calibration loader config for the documented THR-RG01..04 seam."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    stressed_vol_threshold_id: str = "THR-RG01"
    extreme_drop_threshold_id: str = "THR-RG02"
    downgrade_hysteresis_threshold_id: str = "THR-RG03"
    extreme_cooldown_threshold_id: str = "THR-RG04"
    # The current public catalog governs only THR-RG01..04.
    # The remaining classifier dimensions stay on bounded documented defaults until
    # their own threshold ids are formally promoted into the shared calibration seam.
    btc_realized_vol_24h_extreme: float = Field(default=0.08, ge=0.0)
    intraday_drawdown_stressed: float = Field(default=0.01, ge=0.0)
    intraday_drawdown_extreme: float = Field(default=0.02, ge=0.0)
    engine_return_dispersion_stressed: float = Field(default=0.02, ge=0.0)
    engine_return_dispersion_extreme: float = Field(default=0.05, ge=0.0)


class RegimeLiteThresholds(BaseModel, frozen=True):
    """Explicit thresholds, meant to be loaded from a calibration artifact."""

    btc_realized_vol_24h_stressed: float = Field(..., ge=0.0)
    btc_realized_vol_24h_extreme: float = Field(..., ge=0.0)
    btc_drop_1h_extreme: float = Field(..., ge=0.0)
    intraday_drawdown_stressed: float = Field(..., ge=0.0)
    intraday_drawdown_extreme: float = Field(..., ge=0.0)
    engine_return_dispersion_stressed: float = Field(..., ge=0.0)
    engine_return_dispersion_extreme: float = Field(..., ge=0.0)
    downgrade_hysteresis_s: int = Field(..., ge=0)
    extreme_cooldown_s: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_threshold_ordering(self) -> "RegimeLiteThresholds":
        if self.btc_realized_vol_24h_extreme < self.btc_realized_vol_24h_stressed:
            raise ValueError("extreme vol threshold must be >= stressed vol threshold")
        if self.intraday_drawdown_extreme < self.intraday_drawdown_stressed:
            raise ValueError(
                "extreme drawdown threshold must be >= stressed drawdown threshold"
            )
        if (
            self.engine_return_dispersion_extreme
            < self.engine_return_dispersion_stressed
        ):
            raise ValueError(
                "extreme engine dispersion threshold must be >= stressed threshold"
            )
        return self

    @classmethod
    def from_documented_defaults(cls) -> "RegimeLiteThresholds":
        return cls(
            btc_realized_vol_24h_stressed=0.04,
            btc_realized_vol_24h_extreme=0.08,
            btc_drop_1h_extreme=0.05,
            intraday_drawdown_stressed=0.01,
            intraday_drawdown_extreme=0.02,
            engine_return_dispersion_stressed=0.02,
            engine_return_dispersion_extreme=0.05,
            downgrade_hysteresis_s=7200,
            extreme_cooldown_s=86400,
        )


def resolve_regime_lite_thresholds(
    config: RegimeLiteCalibrationConfig | None = None,
) -> RegimeLiteThresholds:
    """Resolve the documented THR-RG01..04 artifact seam into typed thresholds.

    Only the thresholds explicitly cataloged for Regime Lite are artifact-governed here.
    Secondary dimensions remain on bounded documented defaults until the catalog promotes
    dedicated threshold ids for them.
    """

    calibration = config or RegimeLiteCalibrationConfig()
    loader = CalibrationLoader(calibration.calibration_root)
    collection = loader.load(version=calibration.calibration_version)

    stressed_vol = _resolve_non_negative_float_threshold(
        loader,
        collection,
        calibration.stressed_vol_threshold_id,
    )
    extreme_drop = _resolve_non_negative_float_threshold(
        loader,
        collection,
        calibration.extreme_drop_threshold_id,
    )
    downgrade_hysteresis_s = _resolve_non_negative_integral_threshold(
        loader,
        collection,
        calibration.downgrade_hysteresis_threshold_id,
    )
    extreme_cooldown_s = _resolve_non_negative_integral_threshold(
        loader,
        collection,
        calibration.extreme_cooldown_threshold_id,
    )

    if stressed_vol > calibration.btc_realized_vol_24h_extreme:
        raise CalibrationArtifactValidationError(
            "THR-RG01 exceeds the bounded regime_lite extreme volatility threshold; "
            "promote an explicit extreme-vol threshold before relaxing this seam"
        )

    return RegimeLiteThresholds(
        btc_realized_vol_24h_stressed=stressed_vol,
        btc_realized_vol_24h_extreme=calibration.btc_realized_vol_24h_extreme,
        btc_drop_1h_extreme=extreme_drop,
        intraday_drawdown_stressed=calibration.intraday_drawdown_stressed,
        intraday_drawdown_extreme=calibration.intraday_drawdown_extreme,
        engine_return_dispersion_stressed=(
            calibration.engine_return_dispersion_stressed
        ),
        engine_return_dispersion_extreme=(
            calibration.engine_return_dispersion_extreme
        ),
        downgrade_hysteresis_s=downgrade_hysteresis_s,
        extreme_cooldown_s=extreme_cooldown_s,
    )


class RegimeLiteInput(BaseModel, frozen=True):
    """Simple observed facts for the first bounded regime classifier."""

    as_of_ts: int = Field(..., ge=1)
    btc_realized_vol_24h: float = Field(default=0.0, ge=0.0)
    btc_drop_1h: float = 0.0
    intraday_drawdown: float = Field(default=0.0, ge=0.0)
    engine_return_dispersion: float = Field(default=0.0, ge=0.0)


class RegimeLiteMemory(BaseModel, frozen=True):
    """Persisted regime state across evaluations."""

    state: RegimeLiteState
    state_entered_ts: int = Field(..., ge=1)
    entries_blocked_until_ts: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_block_window(self) -> "RegimeLiteMemory":
        if (
            self.entries_blocked_until_ts
            and self.entries_blocked_until_ts < self.state_entered_ts
        ):
            raise ValueError(
                "entries_blocked_until_ts cannot predate state_entered_ts"
            )
        return self


class RegimeLiteAssessment(BaseModel, frozen=True):
    """Typed regime assessment plus next persisted memory."""

    state: RegimeLiteState
    candidate_state: RegimeLiteState
    previous_state: RegimeLiteState | None = None
    state_changed: bool = False
    state_entered_ts: int = Field(..., ge=1)
    entries_blocked_until_ts: int = Field(default=0, ge=0)
    entries_blocked: bool = False
    sudden_event: bool = False
    transition_path: tuple[RegimeLiteState, ...] = ()
    reason_codes: tuple[str, ...] = ()
    btc_realized_vol_24h: float = Field(default=0.0, ge=0.0)
    btc_drop_1h: float = 0.0
    intraday_drawdown: float = Field(default=0.0, ge=0.0)
    engine_return_dispersion: float = Field(default=0.0, ge=0.0)

    @property
    def memory(self) -> RegimeLiteMemory:
        return RegimeLiteMemory(
            state=self.state,
            state_entered_ts=self.state_entered_ts,
            entries_blocked_until_ts=self.entries_blocked_until_ts,
        )


def _derive_candidate_state(
    observation: RegimeLiteInput,
    thresholds: RegimeLiteThresholds,
) -> tuple[RegimeLiteState, tuple[str, ...], bool]:
    reason_codes: list[str] = []
    sudden_event = False

    if observation.btc_drop_1h <= (-1.0 * thresholds.btc_drop_1h_extreme):
        reason_codes.append("RG_EXTREME_BTC_DROP_1H")
        sudden_event = True
    if observation.intraday_drawdown >= thresholds.intraday_drawdown_extreme:
        reason_codes.append("RG_EXTREME_INTRADAY_DRAWDOWN")
        sudden_event = True
    if observation.btc_realized_vol_24h >= thresholds.btc_realized_vol_24h_extreme:
        reason_codes.append("RG_EXTREME_VOL_24H")
    if (
        observation.engine_return_dispersion
        >= thresholds.engine_return_dispersion_extreme
    ):
        reason_codes.append("RG_EXTREME_ENGINE_DISPERSION")
    if reason_codes:
        return RegimeLiteState.EXTREME, tuple(reason_codes), sudden_event

    if observation.btc_realized_vol_24h >= thresholds.btc_realized_vol_24h_stressed:
        reason_codes.append("RG_STRESSED_VOL_24H")
    if observation.intraday_drawdown >= thresholds.intraday_drawdown_stressed:
        reason_codes.append("RG_STRESSED_INTRADAY_DRAWDOWN")
    if (
        observation.engine_return_dispersion
        >= thresholds.engine_return_dispersion_stressed
    ):
        reason_codes.append("RG_STRESSED_ENGINE_DISPERSION")
    if reason_codes:
        return RegimeLiteState.STRESSED, tuple(reason_codes), False

    return RegimeLiteState.CALM, ("RG_CALM_BASELINE",), False


def _step_towards(
    previous: RegimeLiteState,
    candidate: RegimeLiteState,
) -> RegimeLiteState:
    previous_rank = _STATE_RANK[previous]
    candidate_rank = _STATE_RANK[candidate]
    if candidate_rank == previous_rank:
        return previous
    if candidate_rank > previous_rank:
        return _STATE_SEQUENCE[previous_rank + 1]
    return _STATE_SEQUENCE[previous_rank - 1]


def classify_regime_lite(
    observation: RegimeLiteInput,
    thresholds: RegimeLiteThresholds,
    previous: RegimeLiteMemory | None = None,
) -> RegimeLiteAssessment:
    """Classify a three-state regime with anti-flapping and extreme cooldown."""

    candidate_state, candidate_reasons, sudden_event = _derive_candidate_state(
        observation, thresholds
    )

    previous_state = previous.state if previous is not None else None
    next_state = candidate_state
    state_entered_ts = observation.as_of_ts
    carried_blocked_until = (
        previous.entries_blocked_until_ts if previous is not None else 0
    )
    reason_codes = list(candidate_reasons)
    transition_path: tuple[RegimeLiteState, ...] = (candidate_state,)
    state_changed = False

    if previous is not None:
        transition_path = (previous.state,)
        previous_rank = _STATE_RANK[previous.state]
        candidate_rank = _STATE_RANK[candidate_state]

        if candidate_rank == previous_rank:
            next_state = previous.state
            state_entered_ts = previous.state_entered_ts
        elif candidate_rank > previous_rank:
            next_state = candidate_state
            if candidate_rank - previous_rank > 1 and not sudden_event:
                next_state = _step_towards(previous.state, candidate_state)
                reason_codes.extend(
                    ("RG_NO_STATE_SKIP", "RG_ESCALATE_TO_STRESSED_FIRST")
                )
            elif candidate_rank - previous_rank > 1 and sudden_event:
                reason_codes.append("RG_DIRECT_EXTREME_EVENT")
            transition_path = (previous.state, next_state)
            state_changed = next_state != previous.state
        else:
            time_in_state_s = observation.as_of_ts - previous.state_entered_ts
            if time_in_state_s < thresholds.downgrade_hysteresis_s:
                next_state = previous.state
                state_entered_ts = previous.state_entered_ts
                reason_codes.append("RG_DOWNGRADE_HYSTERESIS_ACTIVE")
            else:
                next_state = candidate_state
                if previous_rank - candidate_rank > 1:
                    next_state = _step_towards(previous.state, candidate_state)
                    reason_codes.extend(("RG_NO_STATE_SKIP", "RG_STEP_DOWN_ONE_STATE"))
                transition_path = (previous.state, next_state)
                state_changed = next_state != previous.state

    entries_blocked_until_ts = carried_blocked_until
    if next_state == RegimeLiteState.EXTREME:
        entries_blocked_until_ts = max(
            entries_blocked_until_ts,
            observation.as_of_ts + thresholds.extreme_cooldown_s,
        )

    entries_blocked = observation.as_of_ts < entries_blocked_until_ts
    if entries_blocked:
        reason_codes.append("RG_EXTREME_COOLDOWN_ACTIVE")

    return RegimeLiteAssessment(
        state=next_state,
        candidate_state=candidate_state,
        previous_state=previous_state,
        state_changed=state_changed,
        state_entered_ts=state_entered_ts,
        entries_blocked_until_ts=entries_blocked_until_ts,
        entries_blocked=entries_blocked,
        sudden_event=sudden_event,
        transition_path=transition_path,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        btc_realized_vol_24h=observation.btc_realized_vol_24h,
        btc_drop_1h=observation.btc_drop_1h,
        intraday_drawdown=observation.intraday_drawdown,
        engine_return_dispersion=observation.engine_return_dispersion,
    )


def _resolve_non_negative_float_threshold(
    loader: CalibrationLoader,
    collection: CalibrationArtifactCollection,
    threshold_id: str,
) -> float:
    value = loader.get_value(collection, threshold_id)
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {threshold_id!r} must be numeric"
        )
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {threshold_id!r} must be finite and >= 0"
        )
    return numeric


def _resolve_non_negative_integral_threshold(
    loader: CalibrationLoader,
    collection: CalibrationArtifactCollection,
    threshold_id: str,
) -> int:
    numeric = _resolve_non_negative_float_threshold(loader, collection, threshold_id)
    if not numeric.is_integer():
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {threshold_id!r} must be an integer number of seconds"
        )
    return int(numeric)


__all__ = [
    "RegimeLiteAssessment",
    "RegimeLiteCalibrationConfig",
    "RegimeLiteInput",
    "RegimeLiteMemory",
    "RegimeLiteState",
    "RegimeLiteThresholds",
    "classify_regime_lite",
    "resolve_regime_lite_thresholds",
]
