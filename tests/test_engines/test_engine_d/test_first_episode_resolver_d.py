from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from engines.engine_d.first_episode_resolver_d import (
    ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_D_FIRST_EPISODE_PROFILE_ID,
    ENGINE_D_LOOKBACK_THRESHOLD_ID,
    ENGINE_D_MIN_GAP_REASON,
    ENGINE_D_MIN_GAP_THRESHOLD_ID,
    ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON,
    EngineDFirstEpisodeCallerThresholds,
    inspect_first_episode_gap,
    resolve_first_episode,
    resolve_first_episode_ref,
)
from interface_contracts import BetStructure, EngineId, ForecastHorizonClass, ForecastTargetClass, Side
from protocols.closed_episode_journal import ClosedEpisodeJournal, EpisodeCloseReason, EpisodeRef


_NOW_NS = 1_700_000_000_000_000_000


def _episode(
    suffix: int,
    *,
    pair: str = "BTCUSDT",
    side: Side = Side.BUY,
    close_reason: EpisodeCloseReason = EpisodeCloseReason.TAKE_PROFIT,
    closed_at_ns: int | None = None,
) -> EpisodeRef:
    return EpisodeRef(
        episode_id=UUID(f"10000000-0000-0000-0000-{suffix:012d}"),
        engine_id_of_origin=EngineId.A,
        pair=pair,
        side=side,
        entry_level=Decimal("100.0"),
        exit_level=Decimal("103.0"),
        bet_structure=BetStructure.DIRECTIONAL_LONG,
        forecast_horizon_class=ForecastHorizonClass.SHORT,
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        closed_at_ns=closed_at_ns or (_NOW_NS + suffix),
        close_reason=close_reason,
        realized_pnl_decimal=Decimal("3.0"),
    )


def test_resolve_first_episode_ref_returns_most_recent_d_eligible_episode() -> None:
    journal = ClosedEpisodeJournal()
    journal.append(_episode(1, close_reason=EpisodeCloseReason.TIME_STOP, closed_at_ns=_NOW_NS + 10))
    journal.append(_episode(2, close_reason=EpisodeCloseReason.STOP_OUT, closed_at_ns=_NOW_NS + 20))
    latest = _episode(3, close_reason=EpisodeCloseReason.TAKE_PROFIT, closed_at_ns=_NOW_NS + 30)
    journal.append(latest)

    resolved = resolve_first_episode_ref(journal, pair="btcusdt", side=Side.BUY)

    assert resolved is not None
    assert resolved.episode_id == latest.episode_id


def test_resolve_first_episode_respects_lookback_and_surfaces_not_found() -> None:
    journal = ClosedEpisodeJournal()
    journal.append(_episode(1, closed_at_ns=_NOW_NS))

    resolution = resolve_first_episode(
        journal,
        pair="BTCUSDT",
        side=Side.BUY,
        as_of_ns=_NOW_NS + 10_000,
        lookback_ns=100,
    )

    assert resolution.found is False
    assert resolution.episode_ref is None


def test_engine_d_first_episode_threshold_surface_is_typed_and_governed() -> None:
    thresholds = ENGINE_D_FIRST_EPISODE_CALLER_THRESHOLDS_TO_CALIBRATE

    assert isinstance(thresholds, EngineDFirstEpisodeCallerThresholds)
    assert thresholds.lookback_threshold_id == ENGINE_D_LOOKBACK_THRESHOLD_ID
    assert thresholds.min_gap_threshold_id == ENGINE_D_MIN_GAP_THRESHOLD_ID
    assert thresholds.calibration_profile_id == ENGINE_D_FIRST_EPISODE_PROFILE_ID
    assert thresholds.calibration_status == "TO_CALIBRATE"


def test_inspect_first_episode_gap_blocks_when_min_gap_not_elapsed() -> None:
    inspection = inspect_first_episode_gap(
        first_episode_ref=_episode(1, closed_at_ns=_NOW_NS - 5),
        evaluated_at_ns=_NOW_NS,
        min_gap_ns=10,
    )

    assert inspection is not None
    assert inspection.blocked is True
    assert inspection.reason_code == ENGINE_D_MIN_GAP_REASON
    assert inspection.elapsed_since_close_ns == 5


def test_inspect_first_episode_gap_fail_closes_when_timestamp_missing() -> None:
    inspection = inspect_first_episode_gap(
        first_episode_ref=object(),
        evaluated_at_ns=_NOW_NS,
        min_gap_ns=10,
    )

    assert inspection is not None
    assert inspection.blocked is True
    assert inspection.reason_code == ENGINE_D_MIN_GAP_TIMESTAMP_MISSING_REASON
