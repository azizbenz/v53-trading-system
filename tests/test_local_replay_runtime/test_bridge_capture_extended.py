from __future__ import annotations

from dataclasses import dataclass

from local_replay_runtime.strategy_ladder_runner import (
    _extract_anti_revenge_one_hot,
    _extract_bridge_microstructure_scalars,
    _extract_build14_observed_values,
    _extract_engine_d_governance_scalars,
)


@dataclass(frozen=True)
class _Record:
    value: float


@dataclass(frozen=True)
class _Bridge:
    kyle_lambda_record: _Record | None = None
    realized_vol_current_record: _Record | None = None
    realized_vol_at_break_record: _Record | None = None
    vpin_record: _Record | None = None
    ofi_record: _Record | None = None
    queue_pressure_record: _Record | None = None


class _ShadowReport:
    def __init__(self, snapshots: list[dict[str, object]]) -> None:
        self._snapshots = snapshots

    def model_dump(self, *, mode: str = "json") -> dict[str, object]:
        assert mode == "json"
        return {"snapshots": list(self._snapshots)}


class _Build14Application:
    def __init__(self, snapshots: list[dict[str, object]]) -> None:
        self.shadow_report = _ShadowReport(snapshots)


def test_extract_bridge_extended_kyle_lambda() -> None:
    scalars = _extract_bridge_microstructure_scalars(
        _Bridge(kyle_lambda_record=_Record(0.0023))
    )
    assert scalars["kyle_lambda"] == 0.0023


def test_extract_bridge_realized_vol_current() -> None:
    scalars = _extract_bridge_microstructure_scalars(
        _Bridge(realized_vol_current_record=_Record(0.018))
    )
    assert scalars["realized_vol_current"] == 0.018


def test_extract_bridge_realized_vol_at_break() -> None:
    scalars = _extract_bridge_microstructure_scalars(
        _Bridge(realized_vol_at_break_record=_Record(0.012))
    )
    assert scalars["realized_vol_at_break"] == 0.012


def test_extract_bridge_uses_current_vol_as_at_break_fallback() -> None:
    scalars = _extract_bridge_microstructure_scalars(
        _Bridge(realized_vol_current_record=_Record(0.018))
    )
    assert scalars["realized_vol_current"] == 0.018
    assert scalars["realized_vol_at_break"] == 0.018


def test_extract_bridge_missing_records_return_none() -> None:
    scalars = _extract_bridge_microstructure_scalars(_Bridge())
    assert scalars == {
        "vpin": None,
        "cumulative_ofi": None,
        "queue_pressure": None,
        "kyle_lambda": None,
        "realized_vol_current": None,
        "realized_vol_at_break": None,
    }


def test_extract_engine_d_governance_scalars() -> None:
    scalars = _extract_engine_d_governance_scalars(
        {
            "history_score": 0.61,
            "marginal_value_score": 0.72,
            "reentry_lateness": 0.14,
            "concentration_headroom": 0.38,
        }
    )
    assert scalars == {
        "history_score": 0.61,
        "marginal_value_score": 0.72,
        "reentry_lateness": 0.14,
        "concentration_headroom": 0.38,
    }


def test_extract_build14_observed_values() -> None:
    application = _Build14Application(
        [
            {"reader_name": "micro_edge_exit_governor", "observed_value": 0.31},
            {"reader_name": "micro_edge_entry_timing_layer", "observed_value": 0.44},
        ]
    )
    observed = _extract_build14_observed_values(application)
    assert observed == {
        "micro_edge_exit_governor_observed": 0.31,
        "micro_edge_entry_timing_observed": 0.44,
    }


def test_extract_anti_revenge_one_hot_active() -> None:
    encoded = _extract_anti_revenge_one_hot({"anti_revenge_state": "active"})
    assert encoded == {
        "anti_revenge_state__active": True,
        "anti_revenge_state__cooling": False,
        "anti_revenge_state__idle": False,
    }


def test_extract_anti_revenge_one_hot_cooling() -> None:
    encoded = _extract_anti_revenge_one_hot({"anti_revenge_state": "cooling"})
    assert encoded == {
        "anti_revenge_state__active": False,
        "anti_revenge_state__cooling": True,
        "anti_revenge_state__idle": False,
    }


def test_extract_anti_revenge_one_hot_idle() -> None:
    encoded = _extract_anti_revenge_one_hot({"anti_revenge_state": "idle"})
    assert encoded == {
        "anti_revenge_state__active": False,
        "anti_revenge_state__cooling": False,
        "anti_revenge_state__idle": True,
    }


def test_extract_anti_revenge_one_hot_unknown_returns_all_none() -> None:
    encoded = _extract_anti_revenge_one_hot({"anti_revenge_state": "foobar"})
    assert encoded == {
        "anti_revenge_state__active": None,
        "anti_revenge_state__cooling": None,
        "anti_revenge_state__idle": None,
    }
