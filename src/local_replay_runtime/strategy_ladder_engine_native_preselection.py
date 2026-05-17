"""Governed B1.5 native preselection for Strategy Ladder discovery candidates.

This stage keeps B1 broad discovery intact while cutting only policy-approved
hard failures before expensive detailed replay. Soft advisory findings remain
auditable and can either pass to B2 or fail-closed depending on the selected
policy mode.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    deterministic_payload_hash,
)


PRESELECTION_CANDIDATES_FILENAME = "preselection_candidates.jsonl"
PRESELECTION_SUMMARY_FILENAME = "preselection_summary.json"
PRESELECTION_REJECTION_LEDGER_FILENAME = "preselection_rejection_ledger.jsonl"
PHASE_B1_5_ENGINE_NATIVE_PRESELECTION = "PHASE_B1_5_ENGINE_NATIVE_PRESELECTION"

B1_5_POLICY_CONSERVATIVE_HARD_ONLY = "conservative_hard_only"
B1_5_POLICY_STRICT_FAIL_CLOSED = "strict_fail_closed"
B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY = "diagnostic_full_replay"
_VALID_POLICY_MODES = {
    B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
    B1_5_POLICY_STRICT_FAIL_CLOSED,
    B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY,
}

_GENERIC_NATIVE_REASON_CODES = {
    "ENGINE_NATIVE_NO_TRADE",
}
_HARD_DIRECTION_SUBSTRINGS = (
    "direction.non_long",
    "non_long_direction",
    "non_long_breakout",
)
_HARD_VALIDATION_REASON_CODES = (
    "INVALID_CANDIDATE_ID",
    "INVALID_PAIR",
    "INVALID_SOURCE",
    "INVALID_TIMESTAMP",
    "MISSING_REQUIRED_TIMEFRAME",
    "MISSING_REQUIRED_ENGINE_ID",
    "MISSING_REQUIRED_STRATEGY_ID",
    "MIN_NOTIONAL_PROVEN_INFEASIBLE",
)
_READY_BUILDER_TOKENS = ("ready",)


class StrategyLadderEngineNativePreselectionBuildResult(BaseModel, frozen=True):
    status: str = Field(..., min_length=1)
    phase_id: str = PHASE_B1_5_ENGINE_NATIVE_PRESELECTION
    b1_5_policy_mode: str = Field(
        default=B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
        min_length=1,
    )
    preselection_candidates_path: str = Field(..., min_length=1)
    preselection_summary_path: str = Field(..., min_length=1)
    preselection_rejection_ledger_path: str = Field(..., min_length=1)
    discovery_pre_candidate_count: int = Field(default=0, ge=0)
    engine_native_preselected_count: int = Field(default=0, ge=0)
    preselection_hard_rejected_count: int = Field(default=0, ge=0)
    preselection_soft_flagged_count: int = Field(default=0, ge=0)
    preselection_passed_count: int = Field(default=0, ge=0)
    b2_replay_candidate_count: int = Field(default=0, ge=0)
    preselection_rejection_count: int = Field(default=0, ge=0)
    replay_savings_estimate_count: int = Field(default=0, ge=0)


def _normalized_reason_codes(
    event: StrategyLadderCandidateEvent,
) -> tuple[str, ...]:
    payload = dict(event.compatibility_payload or {})
    merged: list[str] = []
    for raw_item in (
        *tuple(str(item) for item in (payload.get("engine_native_reason_codes") or ())),
        *tuple(
            str(item)
            for item in (payload.get("engine_native_no_trade_reasons") or ())
        ),
        *tuple(str(item) for item in (payload.get("hard_block_reasons") or ())),
    ):
        value = str(raw_item or "").strip()
        if value and value not in merged:
            merged.append(value)
    return tuple(merged)


def _candidate_generation_reason(
    source_event: StrategyLadderCandidateEvent | None,
) -> str:
    if source_event is None:
        return ""
    for code in source_event.preliminary_reason_codes:
        value = str(code or "").strip()
        if value and value not in {"NOT_LIVE_ENGINE_PARITY", "HARD_BLOCK_REASONS_PRESENT"}:
            return value
    return str(source_event.candidate_source or "")


def _as_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hard_validation_reasons(
    event: StrategyLadderCandidateEvent,
) -> tuple[str, ...]:
    payload = dict(event.compatibility_payload or {})
    reasons: list[str] = []
    if not str(event.candidate_id or "").strip():
        reasons.append("INVALID_CANDIDATE_ID")
    if not str(event.pair or "").strip():
        reasons.append("INVALID_PAIR")
    if not str(event.candidate_source or "").strip():
        reasons.append("INVALID_SOURCE")
    if event.resolved_timestamp_ms <= 0:
        reasons.append("INVALID_TIMESTAMP")
    if not str(event.timeframe or "").strip():
        reasons.append("MISSING_REQUIRED_TIMEFRAME")
    if not str(event.engine_id or "").strip():
        reasons.append("MISSING_REQUIRED_ENGINE_ID")
    if not str(event.strategy_id or "").strip():
        reasons.append("MISSING_REQUIRED_STRATEGY_ID")
    planned_notional = _as_float(payload.get("planned_notional"))
    min_notional = _as_float(payload.get("min_notional"))
    if (
        planned_notional is not None
        and min_notional is not None
        and planned_notional < min_notional
    ):
        reasons.append("MIN_NOTIONAL_PROVEN_INFEASIBLE")
    return tuple(dict.fromkeys(reasons))


def _hard_direction_reasons(
    reason_codes: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    for code in reason_codes:
        lowered = code.lower()
        if any(token in lowered for token in _HARD_DIRECTION_SUBSTRINGS):
            reasons.append(code)
    return tuple(dict.fromkeys(reasons))


def _soft_builder_status(
    event: StrategyLadderCandidateEvent,
    *,
    hard_reason_set: set[str],
) -> tuple[str, ...]:
    builder_status = str(
        dict(event.compatibility_payload or {}).get("engine_native_builder_status") or ""
    ).strip()
    lowered = builder_status.lower()
    if (
        not builder_status
        or builder_status in hard_reason_set
        or any(token in lowered for token in _READY_BUILDER_TOKENS)
    ):
        return ()
    return (builder_status,)


def _soft_advisory_reasons(
    event: StrategyLadderCandidateEvent,
    *,
    hard_reason_codes: tuple[str, ...],
) -> tuple[str, ...]:
    hard_reason_set = set(hard_reason_codes)
    advisories: list[str] = list(
        _soft_builder_status(event, hard_reason_set=hard_reason_set)
    )
    for code in _normalized_reason_codes(event):
        if code in hard_reason_set or code in _GENERIC_NATIVE_REASON_CODES:
            continue
        advisories.append(code)
    return tuple(dict.fromkeys(advisories))


def _classify_reason_sets(
    event: StrategyLadderCandidateEvent,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    hard_reasons = tuple(
        dict.fromkeys(
            (
                *_hard_validation_reasons(event),
                *_hard_direction_reasons(_normalized_reason_codes(event)),
            )
        )
    )
    soft_reasons = _soft_advisory_reasons(
        event,
        hard_reason_codes=hard_reasons,
    )
    return hard_reasons, soft_reasons


def _annotated_event(
    event: StrategyLadderCandidateEvent,
    *,
    b1_5_policy_mode: str,
    hard_rejection_reason_codes: tuple[str, ...],
    soft_advisory_reason_codes: tuple[str, ...],
    preselection_decision: str,
    preselection_status: str,
) -> StrategyLadderCandidateEvent:
    payload = dict(event.compatibility_payload or {})
    payload.update(
        {
            "b1_5_policy_mode": b1_5_policy_mode,
            "hard_rejection_reason_codes": list(hard_rejection_reason_codes),
            "soft_advisory_reason_codes": list(soft_advisory_reason_codes),
            "preselection_decision": preselection_decision,
            "preselection_status": preselection_status,
        }
    )
    return event.model_copy(update={"compatibility_payload": payload})


def _rejection_row(
    *,
    source_event: StrategyLadderCandidateEvent | None,
    materialized_event: StrategyLadderCandidateEvent,
    b1_5_policy_mode: str,
    hard_rejection_reason_codes: tuple[str, ...],
    soft_advisory_reason_codes: tuple[str, ...],
    preselection_decision: str,
) -> dict[str, object]:
    payload = dict(materialized_event.compatibility_payload or {})
    primary_reason = (
        hard_rejection_reason_codes[0]
        if hard_rejection_reason_codes
        else soft_advisory_reason_codes[0]
        if soft_advisory_reason_codes
        else ""
    )
    return {
        "phase_id": PHASE_B1_5_ENGINE_NATIVE_PRESELECTION,
        "candidate_id": materialized_event.candidate_id,
        "engine_id": materialized_event.engine_id,
        "pair": materialized_event.pair,
        "timeframe": materialized_event.timeframe,
        "candidate_intent": "DISCOVERY_PRE_CANDIDATE",
        "candidate_generation_reason": _candidate_generation_reason(source_event),
        "source_candidate_source": (
            source_event.candidate_source if source_event is not None else ""
        ),
        "materialized_candidate_source": materialized_event.candidate_source,
        "engine_native_decision": str(payload.get("engine_native_decision") or ""),
        "engine_native_builder_status": str(
            payload.get("engine_native_builder_status") or ""
        ),
        "b1_5_policy_mode": b1_5_policy_mode,
        "preselection_decision": preselection_decision,
        "preselection_reason_primary": primary_reason,
        "hard_rejection_reason_codes": hard_rejection_reason_codes,
        "soft_advisory_reason_codes": soft_advisory_reason_codes,
        "preselection_reason_codes": (
            hard_rejection_reason_codes or soft_advisory_reason_codes
        ),
        "preselection_status": "HARD_BLOCKED_CANDIDATE",
    }


def _count_reasons(rows: tuple[str, ...], counter: dict[str, int]) -> None:
    for reason in rows:
        counter[reason] = counter.get(reason, 0) + 1


def _sorted_reason_rows(counter: dict[str, int]) -> list[dict[str, object]]:
    return [
        {"reason_code": reason, "count": count}
        for reason, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )[:12]
    ]


def build_strategy_ladder_engine_native_preselection(
    *,
    run_dir: Path,
    source_candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    materialized_candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    diagnostic_full_replay: bool = False,
    preselected_only: bool = True,
    b1_5_policy_mode: str = B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
) -> StrategyLadderEngineNativePreselectionBuildResult:
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    preselection_candidates_path = run_dir / PRESELECTION_CANDIDATES_FILENAME
    preselection_summary_path = reports_dir / PRESELECTION_SUMMARY_FILENAME
    preselection_rejection_ledger_path = (
        run_dir / PRESELECTION_REJECTION_LEDGER_FILENAME
    )

    resolved_policy_mode = str(b1_5_policy_mode or "").strip().lower()
    if resolved_policy_mode not in _VALID_POLICY_MODES:
        resolved_policy_mode = (
            B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
            if diagnostic_full_replay
            else B1_5_POLICY_CONSERVATIVE_HARD_ONLY
        )

    source_by_candidate = {
        event.candidate_id: event for event in source_candidate_events
    }
    preselected_events: list[StrategyLadderCandidateEvent] = []
    rejection_rows: list[dict[str, object]] = []
    hard_reason_counts: dict[str, int] = {}
    soft_reason_counts: dict[str, int] = {}
    hard_rejected_count = 0
    soft_flagged_count = 0

    for materialized_event in materialized_candidate_events:
        hard_reasons, soft_reasons = _classify_reason_sets(materialized_event)
        source_event = source_by_candidate.get(materialized_event.candidate_id)
        has_hard_rejection = bool(hard_reasons)
        has_soft_advisory = bool(soft_reasons)
        reject_for_soft = (
            resolved_policy_mode == B1_5_POLICY_STRICT_FAIL_CLOSED
            and not has_hard_rejection
            and has_soft_advisory
        )

        if has_hard_rejection:
            hard_rejected_count += 1
            _count_reasons(hard_reasons, hard_reason_counts)
            rejection_rows.append(
                _rejection_row(
                    source_event=source_event,
                    materialized_event=materialized_event,
                    b1_5_policy_mode=resolved_policy_mode,
                    hard_rejection_reason_codes=hard_reasons,
                    soft_advisory_reason_codes=soft_reasons,
                    preselection_decision=(
                        "REJECTED_HARD_DIAGNOSTIC"
                        if resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
                        else "REJECTED_HARD"
                    ),
                )
            )
            if resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY:
                continue
            continue

        if has_soft_advisory:
            soft_flagged_count += 1
            _count_reasons(soft_reasons, soft_reason_counts)
            if reject_for_soft:
                rejection_rows.append(
                    _rejection_row(
                        source_event=source_event,
                        materialized_event=materialized_event,
                        b1_5_policy_mode=resolved_policy_mode,
                        hard_rejection_reason_codes=(),
                        soft_advisory_reason_codes=soft_reasons,
                        preselection_decision="REJECTED_SOFT_FAIL_CLOSED",
                    )
                )
                continue

        preselection_decision = (
            "PASSED_WITH_SOFT_ADVISORY"
            if has_soft_advisory
            else "PASSED_CLEAN"
        )
        preselection_status = (
            "ENGINE_NATIVE_PRESELECTED_SOFT_ADVISORY"
            if has_soft_advisory
            else "ENGINE_NATIVE_PRESELECTED"
        )
        preselected_events.append(
            _annotated_event(
                materialized_event,
                b1_5_policy_mode=resolved_policy_mode,
                hard_rejection_reason_codes=(),
                soft_advisory_reason_codes=soft_reasons,
                preselection_decision=preselection_decision,
                preselection_status=preselection_status,
            )
        )

    preselection_lines = [
        event.model_dump_json(exclude_none=False) for event in preselected_events
    ]
    atomic_write_text(
        preselection_candidates_path,
        "\n".join(preselection_lines) + ("\n" if preselection_lines else ""),
    )
    rejection_lines = [
        json.dumps(row, ensure_ascii=True, separators=(",", ":"))
        for row in rejection_rows
    ]
    atomic_write_text(
        preselection_rejection_ledger_path,
        "\n".join(rejection_lines) + ("\n" if rejection_lines else ""),
    )

    discovery_count = len(source_candidate_events or materialized_candidate_events)
    preselected_count = len(preselected_events)
    replay_candidate_count = (
        len(materialized_candidate_events)
        if resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
        else preselected_count
        if preselected_only or resolved_policy_mode in {
            B1_5_POLICY_CONSERVATIVE_HARD_ONLY,
            B1_5_POLICY_STRICT_FAIL_CLOSED,
        }
        else len(materialized_candidate_events)
    )
    preselection_rejection_count = (
        0
        if resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
        else len(rejection_rows)
    )
    status = (
        "ENGINE_NATIVE_PRESELECTION_BLOCKED"
        if not materialized_candidate_events
        else "ENGINE_NATIVE_PRESELECTION_READY"
        if resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
        else "ENGINE_NATIVE_PRESELECTION_EMPTY"
        if preselected_count == 0
        else "ENGINE_NATIVE_PRESELECTION_READY"
    )
    replay_mode = (
        "DIAGNOSTIC_FULL_REPLAY"
        if resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
        else "PRESELECTED_ONLY"
    )
    replay_savings_estimate_count = max(
        len(materialized_candidate_events) - replay_candidate_count,
        0,
    )
    replay_savings_estimate_pct = (
        round(replay_savings_estimate_count / len(materialized_candidate_events), 6)
        if materialized_candidate_events
        else 0.0
    )
    summary_payload = {
        "schema_version": "v1",
        "phase_id": PHASE_B1_5_ENGINE_NATIVE_PRESELECTION,
        "status": status,
        "b1_pre_candidates_status": (
            "B1_PRE_CANDIDATES_READY" if discovery_count > 0 else "B1_PRE_CANDIDATES_EMPTY"
        ),
        "replay_input_mode_status": replay_mode,
        "preselected_only": bool(
            resolved_policy_mode != B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
        ),
        "diagnostic_full_replay": bool(
            resolved_policy_mode == B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY
        ),
        "b1_5_policy_mode": resolved_policy_mode,
        "discovery_pre_candidate_count": discovery_count,
        "engine_native_preselected_count": preselected_count,
        "preselection_hard_rejected_count": hard_rejected_count,
        "preselection_soft_flagged_count": soft_flagged_count,
        "preselection_passed_count": preselected_count,
        "b2_replay_candidate_count": replay_candidate_count,
        "preselection_rejection_count": preselection_rejection_count,
        "replay_savings_estimate_count": replay_savings_estimate_count,
        "replay_savings_estimate_pct": replay_savings_estimate_pct,
        "top_rejection_reasons": _sorted_reason_rows(hard_reason_counts),
        "top_hard_rejection_reasons": _sorted_reason_rows(hard_reason_counts),
        "top_soft_advisory_reasons": _sorted_reason_rows(soft_reason_counts),
        "preselection_candidates_path": str(preselection_candidates_path.resolve()),
        "preselection_rejection_ledger_path": str(
            preselection_rejection_ledger_path.resolve()
        ),
    }
    summary_payload["artifact_hash"] = deterministic_payload_hash(summary_payload)
    atomic_write_json(preselection_summary_path, summary_payload, indent=2)

    return StrategyLadderEngineNativePreselectionBuildResult(
        status=status,
        b1_5_policy_mode=resolved_policy_mode,
        preselection_candidates_path=str(preselection_candidates_path.resolve()),
        preselection_summary_path=str(preselection_summary_path.resolve()),
        preselection_rejection_ledger_path=str(
            preselection_rejection_ledger_path.resolve()
        ),
        discovery_pre_candidate_count=discovery_count,
        engine_native_preselected_count=preselected_count,
        preselection_hard_rejected_count=hard_rejected_count,
        preselection_soft_flagged_count=soft_flagged_count,
        preselection_passed_count=preselected_count,
        b2_replay_candidate_count=replay_candidate_count,
        preselection_rejection_count=preselection_rejection_count,
        replay_savings_estimate_count=replay_savings_estimate_count,
    )


__all__ = [
    "B1_5_POLICY_CONSERVATIVE_HARD_ONLY",
    "B1_5_POLICY_DIAGNOSTIC_FULL_REPLAY",
    "B1_5_POLICY_STRICT_FAIL_CLOSED",
    "PHASE_B1_5_ENGINE_NATIVE_PRESELECTION",
    "PRESELECTION_CANDIDATES_FILENAME",
    "PRESELECTION_REJECTION_LEDGER_FILENAME",
    "PRESELECTION_SUMMARY_FILENAME",
    "StrategyLadderEngineNativePreselectionBuildResult",
    "build_strategy_ladder_engine_native_preselection",
]
