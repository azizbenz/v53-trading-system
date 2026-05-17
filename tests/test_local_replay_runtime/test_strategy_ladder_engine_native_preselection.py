from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_engine_native_preselection import (
    B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
    B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY,
    B1_5_POLICY_STRICT_FAIL_CLOSED,
    build_strategy_ladder_engine_native_preselection,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent


def _event(
    *,
    candidate_id: str,
    engine_id: str = "engine_a",
    candidate_source: str,
    preliminary_reason_codes: tuple[str, ...] = (),
    compatibility_payload: dict[str, object] | None = None,
) -> StrategyLadderCandidateEvent:
    return StrategyLadderCandidateEvent(
        run_id="run-preselection",
        candidate_id=candidate_id,
        timestamp_ms=1_714_000_000_000,
        pair="BTCUSDT",
        timeframe="5m",
        engine_id=engine_id,
        strategy_id=engine_id,
        candidate_source=candidate_source,
        preliminary_reason_codes=preliminary_reason_codes,
        compatibility_payload=compatibility_payload or {},
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def test_conservative_hard_only_treats_build14_fragility_as_soft_advisory(
    tmp_path: Path,
) -> None:
    source_events = (
        _event(candidate_id="cand-soft", candidate_source="COMPAT_FEATURE_DISCOVERY"),
    )
    materialized_events = (
        _event(
            candidate_id="cand-soft",
            candidate_source="ENGINE_NATIVE",
            engine_id="engine_c",
            compatibility_payload={
                "engine_native_decision": "no_trade",
                "engine_native_builder_status": "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT",
                "engine_native_reason_codes": [
                    "BUILD14_READER:execution_fragility_score:ELEVATED",
                    "BUILD14_READER:false_breakout_model:ELEVATED",
                ],
            },
        ),
    )

    result = build_strategy_ladder_engine_native_preselection(
        run_dir=tmp_path,
        source_candidate_events=source_events,
        materialized_candidate_events=materialized_events,
        preselected_only=True,
        diagnostic_full_replay=False,
        b1_5_policy_mode=B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
    )

    assert result.status == "ENGINE_NATIVE_PRESELECTION_READY"
    assert result.preselection_hard_rejected_count == 0
    assert result.preselection_soft_flagged_count == 1
    assert result.preselection_passed_count == 1
    assert result.engine_native_preselected_count == 1
    assert result.b2_replay_candidate_count == 1
    assert result.preselection_rejection_count == 0

    preselected_rows = _read_jsonl(Path(result.preselection_candidates_path))
    assert len(preselected_rows) == 1
    payload = dict(preselected_rows[0]["compatibility_payload"])
    assert payload["preselection_decision"] == "PASSED_WITH_SOFT_ADVISORY"
    assert payload["soft_advisory_reason_codes"] == [
        "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT",
        "BUILD14_READER:execution_fragility_score:ELEVATED",
        "BUILD14_READER:false_breakout_model:ELEVATED",
    ]

    summary_payload = json.loads(
        Path(result.preselection_summary_path).read_text(encoding="utf-8")
    )
    assert summary_payload["b1_5_policy_mode"] == "conservative_hard_only"
    assert summary_payload["top_soft_advisory_reasons"][0]["reason_code"] == (
        "BUILD14_READER:execution_fragility_score:ELEVATED"
    )


def test_conservative_hard_only_treats_engine_d_missing_history_as_soft_advisory(
    tmp_path: Path,
) -> None:
    source_events = (
        _event(candidate_id="cand-history", candidate_source="COMPAT_FEATURE_DISCOVERY"),
    )
    materialized_events = (
        _event(
            candidate_id="cand-history",
            candidate_source="ENGINE_NATIVE",
            engine_id="engine_d",
            compatibility_payload={
                "engine_native_decision": "no_trade",
                "engine_native_builder_status": "ENGINE_D_INPUT_BUILDER_INSUFFICIENT_BARS",
                "engine_native_reason_codes": [
                    "engine_d.no_trade.history_weak",
                    "history_weak",
                    "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
                ],
            },
        ),
    )

    result = build_strategy_ladder_engine_native_preselection(
        run_dir=tmp_path,
        source_candidate_events=source_events,
        materialized_candidate_events=materialized_events,
        preselected_only=True,
        diagnostic_full_replay=False,
        b1_5_policy_mode=B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
    )

    assert result.preselection_hard_rejected_count == 0
    assert result.preselection_soft_flagged_count == 1
    assert result.preselection_passed_count == 1
    assert result.b2_replay_candidate_count == 1


def test_non_long_direction_remains_hard_rejection_for_spot_only(
    tmp_path: Path,
) -> None:
    source_events = (
        _event(candidate_id="cand-hard", candidate_source="COMPAT_FEATURE_DISCOVERY"),
        _event(candidate_id="cand-soft", candidate_source="COMPAT_FEATURE_DISCOVERY"),
    )
    materialized_events = (
        _event(
            candidate_id="cand-hard",
            candidate_source="ENGINE_NATIVE",
            compatibility_payload={
                "engine_native_decision": "no_trade",
                "engine_native_reason_codes": [
                    "engine_internal.engine_a.direction.non_long"
                ],
            },
        ),
        _event(
            candidate_id="cand-soft",
            candidate_source="ENGINE_NATIVE",
            compatibility_payload={
                "engine_native_decision": "no_trade",
                "engine_native_reason_codes": ["EXPECTED_EDGE_PROXY_BLOCKED"],
            },
        ),
    )

    result = build_strategy_ladder_engine_native_preselection(
        run_dir=tmp_path,
        source_candidate_events=source_events,
        materialized_candidate_events=materialized_events,
        preselected_only=True,
        diagnostic_full_replay=False,
        b1_5_policy_mode=B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
    )

    assert result.status == "ENGINE_NATIVE_PRESELECTION_READY"
    assert result.preselection_hard_rejected_count == 1
    assert result.preselection_soft_flagged_count == 1
    assert result.preselection_passed_count == 1
    assert result.engine_native_preselected_count == 1
    assert result.preselection_rejection_count == 1

    rejection_rows = _read_jsonl(Path(result.preselection_rejection_ledger_path))
    assert len(rejection_rows) == 1
    assert rejection_rows[0]["hard_rejection_reason_codes"] == [
        "engine_internal.engine_a.direction.non_long"
    ]


def test_strict_fail_closed_preserves_zero_preselected_behavior(
    tmp_path: Path,
) -> None:
    source_events = (
        _event(candidate_id="cand-1", candidate_source="COMPAT_FEATURE_DISCOVERY"),
        _event(candidate_id="cand-2", candidate_source="COMPAT_FEATURE_DISCOVERY"),
    )
    materialized_events = (
        _event(
            candidate_id="cand-1",
            candidate_source="ENGINE_NATIVE",
            compatibility_payload={
                "engine_native_reason_codes": [
                    "engine_internal.engine_a.direction.non_long"
                ]
            },
        ),
        _event(
            candidate_id="cand-2",
            candidate_source="ENGINE_NATIVE",
            engine_id="engine_d",
            compatibility_payload={
                "engine_native_builder_status": "ENGINE_D_INPUT_BUILDER_INSUFFICIENT_BARS",
                "engine_native_reason_codes": [
                    "engine_d.no_trade.history_weak",
                    "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
                ],
            },
        ),
    )

    result = build_strategy_ladder_engine_native_preselection(
        run_dir=tmp_path,
        source_candidate_events=source_events,
        materialized_candidate_events=materialized_events,
        preselected_only=True,
        diagnostic_full_replay=False,
        b1_5_policy_mode=B1_5_POLICY_STRICT_FAIL_CLOSED,
    )

    assert result.status == "ENGINE_NATIVE_PRESELECTION_EMPTY"
    assert result.preselection_hard_rejected_count == 1
    assert result.preselection_soft_flagged_count == 1
    assert result.preselection_passed_count == 0
    assert result.engine_native_preselected_count == 0
    assert result.b2_replay_candidate_count == 0
    assert result.preselection_rejection_count == 2


def test_diagnostic_full_replay_replays_all_candidates_even_with_hard_flags(
    tmp_path: Path,
) -> None:
    source_events = (
        _event(candidate_id="cand-1", candidate_source="COMPAT_FEATURE_DISCOVERY"),
        _event(candidate_id="cand-2", candidate_source="COMPAT_FEATURE_DISCOVERY"),
    )
    materialized_events = (
        _event(
            candidate_id="cand-1",
            candidate_source="ENGINE_NATIVE",
            compatibility_payload={
                "engine_native_reason_codes": [
                    "engine_internal.engine_a.direction.non_long"
                ]
            },
        ),
        _event(
            candidate_id="cand-2",
            candidate_source="ENGINE_NATIVE",
            compatibility_payload={
                "engine_native_reason_codes": ["EXPECTED_EDGE_PROXY_BLOCKED"]
            },
        ),
    )

    result = build_strategy_ladder_engine_native_preselection(
        run_dir=tmp_path,
        source_candidate_events=source_events,
        materialized_candidate_events=materialized_events,
        preselected_only=False,
        diagnostic_full_replay=True,
        b1_5_policy_mode=B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY,
    )

    assert result.status == "ENGINE_NATIVE_PRESELECTION_READY"
    assert result.preselection_hard_rejected_count == 1
    assert result.preselection_soft_flagged_count == 1
    assert result.preselection_passed_count == 1
    assert result.engine_native_preselected_count == 1
    assert result.b2_replay_candidate_count == 2
    assert result.preselection_rejection_count == 0

    summary_payload = json.loads(
        Path(result.preselection_summary_path).read_text(encoding="utf-8")
    )
    assert summary_payload["replay_input_mode_status"] == "DIAGNOSTIC_FULL_REPLAY"
    assert summary_payload["preselected_only"] is False
    assert summary_payload["diagnostic_full_replay"] is True
    assert summary_payload["b2_replay_candidate_count"] == 2
