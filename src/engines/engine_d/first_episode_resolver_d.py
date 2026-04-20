"""Explicit Engine D first-episode resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from interface_contracts import Side


_MIN_EPOCH_NS = 1_000_000_000_000_000_000
_MAX_EPOCH_NS = 9_999_999_999_999_999_999
_NS_PER_HOUR = 3_600_000_000_000
_NS_PER_MINUTE = 60_000_000_000
ENGINE_D_LOOKBACK_THRESHOLD_ID = "THR-D_LOOKBACK"
ENGINE_D_MIN_GAP_THRESHOLD_ID = "THR-D_MIN_GAP"
ENGINE_D_FIRST_EPISODE_PROFILE_ID = "engine_d_first_episode.to_calibrate.v1"
ENGINE_D_MIN_GAP_REASON = "hard_block.d_min_gap_not_elapsed"
ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON = "hard_block.d_first_episode_timestamp_missing"


class EngineDFirstEpisodeCallerThresholds(BaseModel):
    """Caller-owned Engine D first-episode thresholds pending signed governance."""

    lookback_ns: int = Field(default=12 * _NS_PER_HOUR, gt=0)
    min_gap_ns: int = Field(default=15 * _NS_PER_MINUTE, gt=0)
    lookback_threshold_id: str = ENGINE_D_LOOKBACK_THRESHOLD_ID
    min_gap_threshold_id: str = ENGINE_D_MIN_GAP_THRESHOLD_ID
    calibration_profile_id: str = ENGINE_D_FIRST_EPISODE_PROFILE_ID
    calibration_status: str = "TO_CALIBRATE"

    model_config = ConfigDict(frozen=True, extra="forbid")


ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE = EngineDFirstEpisodeCallerThresholds()
ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS = ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE


class EpisodeJournalLike(Protocol):
    def most_recent_eligible_for_engine_d(
        self,
        *,
        pair: str,
        side: Side,
        as_of_ns: int | None = None,
        lookback_ns: int | None = None,
    ) -> object | None:
        ...


@dataclass(frozen=True)
class FirstEpisodeResolutionD:
    """Resolved Engine D historical linkage candidate from the closed-episode journal."""

    pair: str
    side: Side
    as_of_ns: int | None = None
    lookback_ns: int | None = None
    episode_ref: object | None = None

    def __post_init__(self) -> None:
        normalized_pair = self.pair.strip().upper()
        if not normalized_pair:
            raise ValueError("pair must not be blank")
        object.__setattr__(self, "pair", normalized_pair)
        if self.as_of_ns is not None and not (_MIN_EPOCH_NS <= self.as_of_ns <= _MAX_EPOCH_NS):
            raise ValueError("as_of_ns must be a nanosecond epoch when provided")
        if self.lookback_ns is not None and self.lookback_ns <= 0:
            raise ValueError("lookback_ns must be positive when provided")

    @property
    def found(self) -> bool:
        return self.episode_ref is not None


@dataclass(frozen=True)
class FirstEpisodeGapInspectionD:
    """Explicit Engine D first-episode minimum-gap evaluation."""

    applied: bool
    blocked: bool
    evaluated_at_ns: int
    min_gap_ns: int
    first_episode_closed_at_ns: int | None = None
    elapsed_since_close_ns: int | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not (_MIN_EPOCH_NS <= self.evaluated_at_ns <= _MAX_EPOCH_NS):
            raise ValueError("evaluated_at_ns must be a nanosecond epoch")
        if self.min_gap_ns <= 0:
            raise ValueError("min_gap_ns must be positive")
        if self.first_episode_closed_at_ns is not None and not (
            _MIN_EPOCH_NS <= self.first_episode_closed_at_ns <= _MAX_EPOCH_NS
        ):
            raise ValueError("first_episode_closed_at_ns must be a nanosecond epoch when provided")
        if self.elapsed_since_close_ns is not None and self.elapsed_since_close_ns < 0:
            raise ValueError("elapsed_since_close_ns must be non-negative when provided")


def resolve_first_episode_ref(
    journal: EpisodeJournalLike,
    *,
    pair: str,
    side: Side,
    as_of_ns: int | None = None,
    lookback_ns: int | None = None,
) -> object | None:
    """Resolve the most recent D-eligible closed A/C episode for the pair and side."""

    return journal.most_recent_eligible_for_engine_d(
        pair=pair,
        side=side,
        as_of_ns=as_of_ns,
        lookback_ns=lookback_ns,
    )


def resolve_first_episode(
    journal: EpisodeJournalLike,
    *,
    pair: str,
    side: Side,
    as_of_ns: int | None = None,
    lookback_ns: int | None = None,
) -> FirstEpisodeResolutionD:
    """Return the typed first-episode resolution result for Engine D."""

    return FirstEpisodeResolutionD(
        pair=pair,
        side=side,
        as_of_ns=as_of_ns,
        lookback_ns=lookback_ns,
        episode_ref=resolve_first_episode_ref(
            journal,
            pair=pair,
            side=side,
            as_of_ns=as_of_ns,
            lookback_ns=lookback_ns,
        ),
    )


def inspect_first_episode_gap(
    *,
    first_episode_ref: object | None,
    evaluated_at_ns: int,
    min_gap_ns: int | None,
) -> FirstEpisodeGapInspectionD | None:
    """Inspect whether the required minimum gap since first-episode close has elapsed."""

    if min_gap_ns is None:
        return None
    if first_episode_ref is None:
        return FirstEpisodeGapInspectionD(
            applied=True,
            blocked=False,
            evaluated_at_ns=evaluated_at_ns,
            min_gap_ns=min_gap_ns,
        )
    closed_at_ns = getattr(first_episode_ref, "closed_at_ns", None)
    if not isinstance(closed_at_ns, int):
        return FirstEpisodeGapInspectionD(
            applied=True,
            blocked=True,
            evaluated_at_ns=evaluated_at_ns,
            min_gap_ns=min_gap_ns,
            reason_code=ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON,
        )
    elapsed_since_close_ns = evaluated_at_ns - closed_at_ns
    if elapsed_since_close_ns < min_gap_ns:
        return FirstEpisodeGapInspectionD(
            applied=True,
            blocked=True,
            evaluated_at_ns=evaluated_at_ns,
            min_gap_ns=min_gap_ns,
            first_episode_closed_at_ns=closed_at_ns,
            elapsed_since_close_ns=max(0, elapsed_since_close_ns),
            reason_code=ENGINE_D_MIN_GAP_REASON,
        )
    return FirstEpisodeGapInspectionD(
        applied=True,
        blocked=False,
        evaluated_at_ns=evaluated_at_ns,
        min_gap_ns=min_gap_ns,
        first_episode_closed_at_ns=closed_at_ns,
        elapsed_since_close_ns=elapsed_since_close_ns,
    )


__all__ = [
    "ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS",
    "ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_D_FIRST_EPISODE_PROFILE_ID",
    "ENGINE_D_LOOKBACK_THRESHOLD_ID",
    "ENGINE_D_MIN_GAP_REASON",
    "ENGINE_D_MIN_GAP_THRESHOLD_ID",
    "ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON",
    "EngineDFirstEpisodeCallerThresholds",
    "FirstEpisodeGapInspectionD",
    "inspect_first_episode_gap",
    "FirstEpisodeResolutionD",
    "resolve_first_episode",
    "resolve_first_episode_ref",
]
