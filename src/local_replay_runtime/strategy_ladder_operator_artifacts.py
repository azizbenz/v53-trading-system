"""Additive operator-grade artifacts for Strategy Ladder backtest runs.

This module only derives artifacts from existing canonical Strategy Ladder
outputs. It never invents executions, fills, PnL, or promotion proof.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from interface_contracts.refusal_records import RefusalCategory
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
    StrategyLadderSharedReplayPayload,
    deterministic_payload_hash,
)


class StrategyLadderCandidateReplayWindowManifest(BaseModel, frozen=True):
    """Operator-facing replay window index for one candidate."""

    schema_version: str = Field(default="v1", min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    timeframe: str = ""
    timestamp_ms: int = Field(default=0, ge=0)
    window_start_ms: int | None = Field(default=None, ge=0)
    window_end_ms: int | None = Field(default=None, ge=0)
    raw_window_status: str = "RAW_WINDOW_NOT_PROVEN"
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    source_coverage_status: str = "RAW_WINDOW_SOURCE_NOT_PROVEN"
    raw_trade_path: str = ""
    raw_book_path: str = ""
    raw_book_delta_path: str = ""
    raw_ohlcv_path: str = ""
    raw_metadata_path: str = ""
    replay_artifact_path: str = ""
    replay_bucket_result_refs: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderTradeDetailLedgerRow(BaseModel, frozen=True):
    """One operator-facing trade row derived from executed/reduced replay results."""

    schema_version: str = Field(default="v1", min_length=1)
    trade_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=1)
    timeframe: str = ""
    execution_state: str = ""
    entry_timestamp_ms: int | None = Field(default=None, ge=0)
    exit_timestamp_ms: int | None = Field(default=None, ge=0)
    side: str = ""
    entry_price: float | None = Field(default=None, ge=0.0)
    exit_price: float | None = Field(default=None, ge=0.0)
    qty: float | None = Field(default=None, ge=0.0)
    notional: float | None = Field(default=None, ge=0.0)
    gross_return_bps: float | None = None
    fee_bps: float | None = None
    spread_cost_bps: float | None = None
    slippage_bps: float | None = None
    impact_bps: float | None = None
    net_return_bps: float | None = None
    holding_time_seconds: float | None = None
    mfe_bps: float | None = None
    mae_bps: float | None = None
    fill_status: str = "NOT_PROVEN"
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    reason_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderRefusalLedgerRow(BaseModel, frozen=True):
    """Truthful non-execution evidence derived from replay results."""

    schema_version: str = Field(default="v1", min_length=1)
    refusal_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=1)
    timeframe: str = ""
    timestamp_ms: int = Field(default=0, ge=0)
    refusal_category: str = Field(..., min_length=1)
    gate: str = ""
    execution_state: str = ""
    fill_status: str = "NOT_PROVEN"
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    reason_codes: tuple[str, ...] = ()
    context: dict[str, object] = Field(default_factory=dict)
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderLossAnalysisLedgerRow(BaseModel, frozen=True):
    """Loss analysis rows for real losing executed/reduced replay results."""

    schema_version: str = Field(default="v1", min_length=1)
    trade_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=1)
    timeframe: str = ""
    loss_bps: float | None = None
    loss_classification: str = "LOSS_UNCLASSIFIED"
    primary_cause: str = ""
    secondary_causes: tuple[str, ...] = ()
    evidence: dict[str, object] = Field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderTimeframeMatrixRow(BaseModel, frozen=True):
    """Operator-facing timeframe matrix row."""

    schema_version: str = Field(default="v1", min_length=1)
    timeframe: str = Field(..., min_length=1)
    candidate_count: int = Field(default=0, ge=0)
    replay_record_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    reduced_count: int = Field(default=0, ge=0)
    no_fill_count: int = Field(default=0, ge=0)
    win_count: int = Field(default=0, ge=0)
    loss_count: int = Field(default=0, ge=0)
    win_rate: float | None = None
    avg_gain_bps: float | None = None
    avg_loss_bps: float | None = None
    net_pnl_bps: float | None = None
    max_drawdown_bps: float | None = None
    avg_realized_cost_fraction: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    artifact_hash: str | None = None
    created_at: datetime | None = None


def _finalize_model(model: BaseModel) -> BaseModel:
    payload = model.model_dump(mode="json")
    if payload.get("created_at") is None:
        payload["created_at"] = datetime.now(tz=UTC)
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return model.__class__.model_validate(payload)


def _candidate_map(
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
) -> dict[str, StrategyLadderCandidateEvent]:
    return {candidate.candidate_id: candidate for candidate in candidate_events}


def _window_map(
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
) -> dict[str, StrategyLadderRawWindowManifest]:
    return {manifest.candidate_id: manifest for manifest in raw_window_manifests}


def _classify_refusal_category(
    result: StrategyLadderBucketReplayResult,
) -> RefusalCategory:
    reason_codes = set(result.reason_codes)
    if "economically_absurd" in reason_codes:
        return RefusalCategory.PHANTOM
    if result.no_fill_flag:
        return RefusalCategory.NO_FILL
    if any(code.startswith("MIN_NOTIONAL_") for code in reason_codes):
        return RefusalCategory.HARD_BLOCK
    return RefusalCategory.NO_TRADE


def _classify_loss(result: StrategyLadderBucketReplayResult) -> tuple[str, str]:
    reason_codes = set(result.reason_codes)
    if "economically_absurd" in reason_codes:
        return "LOSS_COST_FAILURE", "economically_absurd"
    if "partial_fill" in reason_codes:
        return "LOSS_EXECUTION_FAILURE", "partial_fill"
    if "no_fill" in reason_codes:
        return "LOSS_EXECUTION_FAILURE", "no_fill"
    if result.impact_source_status == "IMPACT_SOURCE_DEPTH20_MODEL":
        return "LOSS_LIQUIDITY_FRAGILITY", "depth20_model_only"
    return "LOSS_UNCLASSIFIED", ""


def build_candidate_replay_window_manifests(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
    replay_artifact_refs: dict[str, str],
    replay_bucket_refs: dict[str, tuple[str, ...]],
) -> tuple[StrategyLadderCandidateReplayWindowManifest, ...]:
    windows = _window_map(raw_window_manifests)
    rows: list[StrategyLadderCandidateReplayWindowManifest] = []
    for candidate in candidate_events:
        manifest = windows.get(candidate.candidate_id)
        row = StrategyLadderCandidateReplayWindowManifest(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            strategy_id=candidate.strategy_id,
            timeframe=candidate.timeframe or "",
            timestamp_ms=candidate.resolved_timestamp_ms,
            window_start_ms=manifest.window_start_ms if manifest is not None else None,
            window_end_ms=manifest.window_end_ms if manifest is not None else None,
            raw_window_status=(
                manifest.window_extraction_status
                if manifest is not None
                else "RAW_WINDOW_NOT_PROVEN"
            ),
            book_depth_source_status=(
                manifest.book_depth_source_status
                if manifest is not None
                else "BOOK_DEPTH_NOT_PROVEN"
            ),
            source_coverage_status=(
                manifest.source_coverage_status
                if manifest is not None
                else "RAW_WINDOW_SOURCE_NOT_PROVEN"
            ),
            raw_trade_path=manifest.raw_trade_path or "" if manifest is not None else "",
            raw_book_path=manifest.raw_book_path or "" if manifest is not None else "",
            raw_book_delta_path=(
                manifest.raw_book_delta_path or "" if manifest is not None else ""
            ),
            raw_ohlcv_path=manifest.raw_ohlcv_path or "" if manifest is not None else "",
            raw_metadata_path=manifest.raw_metadata_path or "" if manifest is not None else "",
            replay_artifact_path=replay_artifact_refs.get(candidate.candidate_id, ""),
            replay_bucket_result_refs=replay_bucket_refs.get(candidate.candidate_id, ()),
        )
        rows.append(_finalize_model(row))
    return tuple(rows)


def build_trade_detail_ledger_rows(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> tuple[StrategyLadderTradeDetailLedgerRow, ...]:
    candidates = _candidate_map(candidate_events)
    rows: list[StrategyLadderTradeDetailLedgerRow] = []
    for result in bucket_results:
        if result.execution_state not in {"executed", "reduced"}:
            continue
        candidate = candidates.get(result.candidate_id)
        compatibility = candidate.compatibility_payload if candidate is not None else {}
        dtr_record = result.dtr_record if isinstance(result.dtr_record, dict) else {}
        parity = result.parity_payload if isinstance(result.parity_payload, dict) else {}
        row = StrategyLadderTradeDetailLedgerRow(
            trade_id=f"{result.candidate_id}-{result.capital_bucket}",
            candidate_id=result.candidate_id,
            pair=result.pair,
            engine_id=result.engine_id,
            strategy_id=result.strategy_id,
            capital_bucket=result.capital_bucket,
            timeframe=(candidate.timeframe or "") if candidate is not None else "",
            execution_state=result.execution_state or "",
            entry_timestamp_ms=result.timestamp_ms,
            exit_timestamp_ms=(
                int(result.exit_ref.get("timestamp_ms"))
                if isinstance(result.exit_ref, dict)
                and result.exit_ref.get("timestamp_ms") is not None
                else None
            ),
            side=str(compatibility.get("side") or ""),
            entry_price=(
                float(
                    compatibility.get("entry_price")
                    if compatibility.get("entry_price") is not None
                    else compatibility.get("close_price")
                )
                if (
                    compatibility.get("entry_price") is not None
                    or compatibility.get("close_price") is not None
                )
                else None
            ),
            exit_price=(
                float(result.exit_ref.get("price"))
                if isinstance(result.exit_ref, dict)
                and result.exit_ref.get("price") is not None
                else None
            ),
            qty=(
                float(dtr_record["final_size"])
                if dtr_record.get("final_size") is not None
                else None
            ),
            notional=result.executed_notional or result.reduced_notional,
            gross_return_bps=(
                float(compatibility["gross_return_bps"])
                if compatibility.get("gross_return_bps") is not None
                else None
            ),
            fee_bps=(
                float(parity["replay_fee_bps"])
                if parity.get("replay_fee_bps") is not None
                else None
            ),
            spread_cost_bps=(
                float(compatibility["spread_bps"])
                if compatibility.get("spread_bps") is not None
                else None
            ),
            slippage_bps=(
                float(parity["replay_slippage_bps"])
                if parity.get("replay_slippage_bps") is not None
                else (
                    float(compatibility["slippage_bps"])
                    if compatibility.get("slippage_bps") is not None
                    else None
                )
            ),
            impact_bps=(
                float(parity["replay_impact_bps"])
                if parity.get("replay_impact_bps") is not None
                else None
            ),
            net_return_bps=(
                round(result.executed_only_net_return * 10_000.0, 6)
                if result.executed_only_net_return is not None
                else None
            ),
            holding_time_seconds=(
                round(float(result.holding_time_ms) / 1000.0, 6)
                if result.holding_time_ms is not None
                else None
            ),
            mfe_bps=result.mfe_bps,
            mae_bps=result.mae_bps,
            fill_status=result.fill_realism_status,
            fee_source_status=result.fee_source_status,
            impact_source_status=result.impact_source_status,
            cost_parity_status=result.cost_parity_status,
            reason_codes=result.reason_codes,
        )
        rows.append(_finalize_model(row))
    return tuple(rows)


def build_refusal_ledger_rows(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> tuple[StrategyLadderRefusalLedgerRow, ...]:
    candidates = _candidate_map(candidate_events)
    rows: list[StrategyLadderRefusalLedgerRow] = []
    for result in bucket_results:
        if result.execution_state in {"executed", "reduced"}:
            continue
        candidate = candidates.get(result.candidate_id)
        category = _classify_refusal_category(result)
        compatibility = candidate.compatibility_payload if candidate is not None else {}
        row = StrategyLadderRefusalLedgerRow(
            refusal_id=f"{result.candidate_id}-{result.capital_bucket}",
            candidate_id=result.candidate_id,
            pair=result.pair,
            engine_id=result.engine_id,
            strategy_id=result.strategy_id,
            capital_bucket=result.capital_bucket,
            timeframe=(candidate.timeframe or "") if candidate is not None else "",
            timestamp_ms=result.timestamp_ms,
            refusal_category=category.value,
            gate=(
                "COST_REJECTED"
                if "economically_absurd" in result.reason_codes
                else "EXECUTION_REJECTED"
            ),
            execution_state=result.execution_state or "",
            fill_status=result.fill_realism_status,
            fee_source_status=result.fee_source_status,
            impact_source_status=result.impact_source_status,
            cost_parity_status=result.cost_parity_status,
            reason_codes=result.reason_codes,
            context={
                "spread_bps": compatibility.get("spread_bps"),
                "expected_edge_bps": compatibility.get("expected_edge_bps"),
                "planned_notional": result.planned_notional,
                "min_notional": result.min_notional,
                "min_notional_viable": result.min_notional_viable,
            },
        )
        rows.append(_finalize_model(row))
    return tuple(rows)


def build_loss_analysis_ledger_rows(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> tuple[StrategyLadderLossAnalysisLedgerRow, ...]:
    candidates = _candidate_map(candidate_events)
    rows: list[StrategyLadderLossAnalysisLedgerRow] = []
    for result in bucket_results:
        if result.execution_state not in {"executed", "reduced"}:
            continue
        if result.executed_only_net_return is None or result.executed_only_net_return > 0:
            continue
        candidate = candidates.get(result.candidate_id)
        loss_classification, primary_cause = _classify_loss(result)
        row = StrategyLadderLossAnalysisLedgerRow(
            trade_id=f"{result.candidate_id}-{result.capital_bucket}",
            candidate_id=result.candidate_id,
            pair=result.pair,
            engine_id=result.engine_id,
            strategy_id=result.strategy_id,
            capital_bucket=result.capital_bucket,
            timeframe=(candidate.timeframe or "") if candidate is not None else "",
            loss_bps=round(abs(result.executed_only_net_return) * 10_000.0, 6),
            loss_classification=loss_classification,
            primary_cause=primary_cause,
            secondary_causes=tuple(code for code in result.reason_codes if code != primary_cause),
            evidence={
                "execution_state": result.execution_state,
                "fee_source_status": result.fee_source_status,
                "impact_source_status": result.impact_source_status,
                "fill_realism_status": result.fill_realism_status,
                "cost_parity_status": result.cost_parity_status,
            },
            reason_codes=result.reason_codes,
        )
        rows.append(_finalize_model(row))
    return tuple(rows)


def _aggregate_status(values: list[str], priority: tuple[str, ...], default: str) -> str:
    if not values:
        return default
    ordered = {value: index for index, value in enumerate(priority)}
    return min(values, key=lambda value: ordered.get(value, len(priority)))


def _max_drawdown_bps(net_returns_bps: list[float]) -> float | None:
    if not net_returns_bps:
        return None
    running = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in net_returns_bps:
        running += value
        peak = max(peak, running)
        max_dd = max(max_dd, peak - running)
    return round(max_dd, 6)


def build_timeframe_matrix_rows(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> tuple[StrategyLadderTimeframeMatrixRow, ...]:
    candidate_timeframes: dict[str, str] = {
        candidate.candidate_id: candidate.timeframe or "unknown"
        for candidate in candidate_events
    }
    rows_by_timeframe: dict[str, dict[str, object]] = {}
    for candidate in candidate_events:
        timeframe = candidate.timeframe or "unknown"
        bucket = rows_by_timeframe.setdefault(
            timeframe,
            {
                "candidate_ids": set(),
                "results": [],
            },
        )
        bucket["candidate_ids"].add(candidate.candidate_id)
    for result in bucket_results:
        timeframe = candidate_timeframes.get(result.candidate_id, "unknown")
        bucket = rows_by_timeframe.setdefault(
            timeframe,
            {"candidate_ids": set(), "results": []},
        )
        bucket["results"].append(result)
    rows: list[StrategyLadderTimeframeMatrixRow] = []
    fee_priority = (
        "FEE_SOURCE_MISSING",
        "FEE_SOURCE_NOT_PROVEN",
        "FEE_SOURCE_ESTIMATED",
        "FEE_SOURCE_EXCHANGE_METADATA",
        "FEE_SOURCE_CONFIGURED",
        "FEE_SOURCE_PROVEN",
    )
    impact_priority = (
        "IMPACT_SOURCE_MISSING",
        "IMPACT_SOURCE_NOT_PROVEN",
        "IMPACT_SOURCE_SYNTHETIC",
        "IMPACT_SOURCE_ESTIMATED",
        "IMPACT_SOURCE_TOP_OF_BOOK_PROXY",
        "IMPACT_SOURCE_LIMITED_DEPTH_MODEL",
        "IMPACT_SOURCE_DEPTH20_MODEL",
        "IMPACT_SOURCE_PROVEN",
    )
    fill_priority = (
        "FILL_REALISM_MISSING",
        "FILL_REALISM_NOT_PROVEN",
        "FILL_REALISM_MODEL_ONLY",
        "FILL_REALISM_SYNTHETIC_ONLY",
        "FILL_REALISM_PARTIAL",
        "FILL_REALISM_SHADOW_MEASURED",
        "FILL_REALISM_PROVEN",
    )
    parity_priority = (
        "REPLAY_LIVE_COST_PARITY_MISSING",
        "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
        "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "REPLAY_SHADOW_COST_PARITY_PROVEN",
        "REPLAY_LIVE_COST_PARITY_PROVEN",
    )
    for timeframe, payload in sorted(rows_by_timeframe.items()):
        results = tuple(payload["results"])
        executed = tuple(
            result for result in results if result.execution_state in {"executed", "reduced"}
        )
        net_returns_bps = [
            round(result.executed_only_net_return * 10_000.0, 6)
            for result in executed
            if result.executed_only_net_return is not None
        ]
        gains = [value for value in net_returns_bps if value > 0]
        losses = [value for value in net_returns_bps if value <= 0]
        executed_count = sum(1 for result in results if result.execution_state == "executed")
        reduced_count = sum(1 for result in results if result.execution_state == "reduced")
        no_fill_count = sum(1 for result in results if result.execution_state == "phantom")
        row = StrategyLadderTimeframeMatrixRow(
            timeframe=timeframe,
            candidate_count=len(payload["candidate_ids"]),
            replay_record_count=len(results),
            executed_count=executed_count,
            reduced_count=reduced_count,
            no_fill_count=no_fill_count,
            win_count=len(gains),
            loss_count=len(losses),
            win_rate=(
                round(len(gains) / len(executed), 6) if executed else None
            ),
            avg_gain_bps=(round(sum(gains) / len(gains), 6) if gains else None),
            avg_loss_bps=(round(sum(losses) / len(losses), 6) if losses else None),
            net_pnl_bps=(
                round(sum(net_returns_bps), 6) if net_returns_bps else None
            ),
            max_drawdown_bps=_max_drawdown_bps(net_returns_bps),
            avg_realized_cost_fraction=(
                round(
                    sum(
                        float(result.dtr_record.get("realized_cost") or 0.0)
                        for result in executed
                    )
                    / len(executed),
                    6,
                )
                if executed
                else None
            ),
            executed_only_net_return_status=(
                "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS"
                if not executed
                else (
                    "EXECUTED_NET_RETURN_PROVEN"
                    if all(result.executed_only_net_return is not None for result in executed)
                    else "EXECUTED_NET_RETURN_NOT_PROVEN"
                )
            ),
            true_net_equity_drawdown_status=(
                "TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS"
                if not executed
                else (
                    "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
                    if _max_drawdown_bps(net_returns_bps) is not None
                    else "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
                )
            ),
            fee_source_status=_aggregate_status(
                [result.fee_source_status for result in results],
                fee_priority,
                "FEE_SOURCE_NOT_PROVEN",
            ),
            impact_source_status=_aggregate_status(
                [result.impact_source_status for result in results],
                impact_priority,
                "IMPACT_SOURCE_NOT_PROVEN",
            ),
            fill_realism_status=_aggregate_status(
                [result.fill_realism_status for result in results],
                fill_priority,
                "FILL_REALISM_NOT_PROVEN",
            ),
            cost_parity_status=_aggregate_status(
                [result.cost_parity_status for result in results],
                parity_priority,
                "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
            ),
        )
        rows.append(_finalize_model(row))
    return tuple(rows)


def _episode_close_reason(result: StrategyLadderBucketReplayResult) -> str:
    reason_codes = {str(code).lower() for code in result.reason_codes}
    if any("take_profit" in code for code in reason_codes):
        return "TAKE_PROFIT"
    if any("time_stop" in code or "holding" in code for code in reason_codes):
        return "TIME_STOP"
    if any("stop" in code for code in reason_codes):
        return "STOP_OUT"
    return "STRUCTURAL_EXIT"


def _build_closed_episode_refs(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> tuple[dict[str, object], ...]:
    candidates = _candidate_map(candidate_events)
    episode_refs: list[dict[str, object]] = []
    for result in bucket_results:
        if result.execution_state not in {"executed", "reduced"}:
            continue
        if result.engine_id not in {"engine_a", "engine_c"}:
            continue
        candidate = candidates.get(result.candidate_id)
        entry_ref = dict(result.entry_ref) if isinstance(result.entry_ref, dict) else {}
        exit_ref = dict(result.exit_ref) if isinstance(result.exit_ref, dict) else {}
        invalidation_ref = (
            dict(result.invalidation_ref) if isinstance(result.invalidation_ref, dict) else {}
        )
        opened_at_ms = entry_ref.get("timestamp_ms")
        closed_at_ms = exit_ref.get("timestamp_ms")
        if (
            opened_at_ms is None
            or closed_at_ms is None
            or entry_ref.get("price") is None
            or exit_ref.get("price") is None
        ):
            continue
        net_return = result.executed_only_net_return
        if net_return is None:
            outcome_status = "CLOSED_EPISODE_OUTCOME_NOT_PROVEN"
        elif net_return > 0.0:
            outcome_status = "CLOSED_EPISODE_NET_POSITIVE"
        elif net_return < 0.0:
            outcome_status = "CLOSED_EPISODE_NET_NEGATIVE"
        else:
            outcome_status = "CLOSED_EPISODE_NET_FLAT"
        episode_refs.append(
            {
                "episode_id": str(
                    uuid5(
                        NAMESPACE_URL,
                        f"{result.candidate_id}:{result.capital_bucket}:{closed_at_ms}",
                    )
                ),
                "candidate_id": result.candidate_id,
                "pair": result.pair,
                "timeframe": candidate.timeframe if candidate is not None else "",
                "engine_id": result.engine_id,
                "capital_bucket": result.capital_bucket,
                "opened_at_ms": int(opened_at_ms),
                "closed_at_ms": int(closed_at_ms),
                "open_ref": entry_ref,
                "close_ref": exit_ref,
                "outcome_status": outcome_status,
                "invalidation_reason": str(result.reason_codes[0]) if result.reason_codes else "",
                "invalidation_ref": invalidation_ref,
                "replay_artifact_ref": str(result.dtr_record.get("artifact_path") or ""),
                "close_reason": _episode_close_reason(result),
                "evidence_class": "SCRATCH_ONLY",
            }
        )
    return tuple(episode_refs)


def _write_closed_episode_journal_artifacts(
    *,
    run_dir: Path,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> dict[str, str]:
    episode_refs = _build_closed_episode_refs(
        candidate_events=candidate_events,
        bucket_results=bucket_results,
    )
    journal_path = run_dir / "closed_episodes.jsonl"
    header_row = {
        "schema_version": "v1",
        "artifact_header": True,
        "evidence_class": "SCRATCH_ONLY",
        "status": (
            "CLOSED_EPISODE_JOURNAL_READY"
            if episode_refs
            else "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES"
        ),
        "record_count": len(episode_refs),
    }
    jsonl_payload = "\n".join(
        [
            json.dumps(header_row, sort_keys=True, ensure_ascii=True),
            *(
                json.dumps(row, sort_keys=True, ensure_ascii=True)
                for row in episode_refs
            ),
        ]
    )
    if jsonl_payload:
        jsonl_payload = f"{jsonl_payload}\n"
    atomic_write_text(journal_path, jsonl_payload)
    manifest_payload: dict[str, object] = {
        "journal_path": str(journal_path.resolve()),
        "record_count": len(episode_refs),
    }
    manifest_payload.update(
        {
            "status": (
                "CLOSED_EPISODE_JOURNAL_READY"
                if episode_refs
                else "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES"
            ),
            "source_status": (
                "CLOSED_EPISODE_SOURCE_EXECUTED_TRADES"
                if episode_refs
                else "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE"
            ),
            "closed_episode_count": len(episode_refs),
            "evidence_class": "SCRATCH_ONLY",
        }
    )
    manifest_path = run_dir / "closed_episode_manifest.json"
    atomic_write_json(manifest_path, manifest_payload, indent=2)
    return {
        "closed_episode_journal": str(journal_path.resolve()),
        "closed_episode_manifest": str(manifest_path.resolve()),
    }


def _collect_execution_report_rows(
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    shared_payload_cache: dict[str, StrategyLadderSharedReplayPayload] = {}
    for result in bucket_results:
        parity = _hydrate_execution_parity_payload(
            result=result,
            shared_payload_cache=shared_payload_cache,
        )
        rows.append(
            {
                "candidate_id": result.candidate_id,
                "capital_bucket": result.capital_bucket,
                "engine_id": result.engine_id,
                "execution_state": result.execution_state,
                "spread": dict(parity.get("measured_spread_report") or {}),
                "slippage": dict(parity.get("measured_slippage_report") or {}),
                "adverse_selection": dict(parity.get("adverse_selection_report") or {}),
                "fill_realism": dict(parity.get("fill_realism_report") or {}),
                "replay_outcome": dict(parity.get("replay_outcome_report") or {}),
            }
        )
    return tuple(rows)


def _hydrate_execution_parity_payload(
    *,
    result: StrategyLadderBucketReplayResult,
    shared_payload_cache: dict[str, StrategyLadderSharedReplayPayload],
) -> dict[str, object]:
    parity = (
        dict(result.parity_payload)
        if isinstance(result.parity_payload, dict)
        else {}
    )
    shared_ref = str(result.shared_payload_ref or "").strip()
    if not shared_ref:
        return parity
    try:
        shared_path = Path(shared_ref)
    except OSError:
        return parity
    if not shared_path.is_file():
        return parity
    cache_key = str(shared_path.resolve())
    shared_payload = shared_payload_cache.get(cache_key)
    if shared_payload is None:
        shared_payload = StrategyLadderSharedReplayPayload.model_validate_json(
            shared_path.read_text(encoding="utf-8-sig")
        )
        shared_payload_cache[cache_key] = shared_payload
    merged = dict(shared_payload.shared_parity_payload)
    merged.update(parity)
    return merged


def _status_count(rows: tuple[dict[str, object], ...], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get(key) or "")
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _write_execution_realism_reports(
    *,
    run_dir: Path,
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> dict[str, str]:
    collected = _collect_execution_report_rows(bucket_results)
    spread_rows = tuple(
        {
            "candidate_id": row["candidate_id"],
            "capital_bucket": row["capital_bucket"],
            **row["spread"],
        }
        for row in collected
    )
    slippage_rows = tuple(
        {
            "candidate_id": row["candidate_id"],
            "capital_bucket": row["capital_bucket"],
            **row["slippage"],
        }
        for row in collected
    )
    adverse_rows = tuple(
        {
            "candidate_id": row["candidate_id"],
            "capital_bucket": row["capital_bucket"],
            **row["adverse_selection"],
        }
        for row in collected
    )
    fill_rows = tuple(
        {
            "candidate_id": row["candidate_id"],
            "capital_bucket": row["capital_bucket"],
            **row["fill_realism"],
        }
        for row in collected
    )
    summary_payload = {
        "schema_version": "v1",
        "row_count": len(collected),
        "spread_status_counts": _status_count(
            tuple({"status": row.get("status")} for row in spread_rows),
            "status",
        ),
        "slippage_status_counts": _status_count(
            tuple({"status": row.get("status")} for row in slippage_rows),
            "status",
        ),
        "adverse_selection_status_counts": _status_count(
            tuple({"status": row.get("status")} for row in adverse_rows),
            "status",
        ),
        "fill_realism_status_counts": _status_count(
            tuple({"status": row.get("status")} for row in fill_rows),
            "status",
        ),
        "replay_outcome_status_counts": _status_count(
            tuple(
                {"status": row["replay_outcome"].get("status")}
                for row in collected
            ),
            "status",
        ),
        "promotion_ready": False,
    }
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    spread_path = reports_dir / "measured_spread_report.json"
    slippage_path = reports_dir / "measured_slippage_report.json"
    adverse_path = reports_dir / "adverse_selection_report.json"
    fill_path = reports_dir / "fill_realism_report.json"
    summary_path = reports_dir / "execution_realism_summary.json"
    atomic_write_json(
        spread_path,
        {"schema_version": "v1", "row_count": len(spread_rows), "rows": list(spread_rows)},
        indent=2,
    )
    atomic_write_json(
        slippage_path,
        {"schema_version": "v1", "row_count": len(slippage_rows), "rows": list(slippage_rows)},
        indent=2,
    )
    atomic_write_json(
        adverse_path,
        {"schema_version": "v1", "row_count": len(adverse_rows), "rows": list(adverse_rows)},
        indent=2,
    )
    atomic_write_json(
        fill_path,
        {"schema_version": "v1", "row_count": len(fill_rows), "rows": list(fill_rows)},
        indent=2,
    )
    atomic_write_json(summary_path, summary_payload, indent=2)
    return {
        "measured_spread_report": str(spread_path.resolve()),
        "measured_slippage_report": str(slippage_path.resolve()),
        "adverse_selection_report": str(adverse_path.resolve()),
        "fill_realism_report": str(fill_path.resolve()),
        "execution_realism_summary": str(summary_path.resolve()),
    }


def _write_jsonl_rows(path: Path, rows: tuple[BaseModel, ...]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header_payload = json.dumps(
        {
            "schema_version": "v1",
            "artifact_header": True,
            "evidence_class": "SCRATCH_ONLY" if not rows else "AUDIT_ROWS_PRESENT",
            "status": "LEDGER_READY" if rows else "LEDGER_EMPTY_NO_ROWS",
            "record_count": len(rows),
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    lines = [header_payload, *(row.model_dump_json() for row in rows)]
    text = "\n".join(lines) + "\n"
    atomic_write_text(path, text)
    return path


def write_strategy_ladder_operator_artifacts(
    *,
    run_dir: Path,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
    replay_artifact_refs: dict[str, str],
    replay_bucket_refs: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    """Persist additive operator-grade artifacts derived from canonical outputs."""

    trade_rows = build_trade_detail_ledger_rows(
        candidate_events=candidate_events,
        bucket_results=bucket_results,
    )
    refusal_rows = build_refusal_ledger_rows(
        candidate_events=candidate_events,
        bucket_results=bucket_results,
    )
    loss_rows = build_loss_analysis_ledger_rows(
        candidate_events=candidate_events,
        bucket_results=bucket_results,
    )
    replay_windows = build_candidate_replay_window_manifests(
        candidate_events=candidate_events,
        raw_window_manifests=raw_window_manifests,
        replay_artifact_refs=replay_artifact_refs,
        replay_bucket_refs=replay_bucket_refs,
    )
    timeframe_rows = build_timeframe_matrix_rows(
        candidate_events=candidate_events,
        bucket_results=bucket_results,
    )
    refs: dict[str, str] = {}
    refs["trade_detail_ledger"] = str(
        _write_jsonl_rows(run_dir / "trade_detail_ledger.jsonl", trade_rows).resolve()
    )
    refs["refusal_ledger"] = str(
        _write_jsonl_rows(run_dir / "refusal_ledger.jsonl", refusal_rows).resolve()
    )
    refs["loss_analysis_ledger"] = str(
        _write_jsonl_rows(run_dir / "loss_analysis_ledger.jsonl", loss_rows).resolve()
    )
    timeframe_path = run_dir / "reports" / "timeframe_matrix.json"
    timeframe_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        timeframe_path,
        [row.model_dump(mode="json") for row in timeframe_rows],
    )
    refs["timeframe_matrix"] = str(timeframe_path.resolve())
    replay_window_root = run_dir / "candidate_replay_windows"
    replay_window_root.mkdir(parents=True, exist_ok=True)
    for row in replay_windows:
        atomic_write_json(
            replay_window_root / f"{row.candidate_id}.json",
            row.model_dump(mode="json"),
        )
    refs["candidate_replay_window_root"] = str(replay_window_root.resolve())
    refs.update(
        _write_closed_episode_journal_artifacts(
            run_dir=run_dir,
            candidate_events=candidate_events,
            bucket_results=bucket_results,
        )
    )
    refs.update(
        _write_execution_realism_reports(
            run_dir=run_dir,
            bucket_results=bucket_results,
        )
    )
    return refs


__all__ = [
    "StrategyLadderCandidateReplayWindowManifest",
    "StrategyLadderLossAnalysisLedgerRow",
    "StrategyLadderRefusalLedgerRow",
    "StrategyLadderTimeframeMatrixRow",
    "StrategyLadderTradeDetailLedgerRow",
    "build_candidate_replay_window_manifests",
    "build_loss_analysis_ledger_rows",
    "build_refusal_ledger_rows",
    "build_timeframe_matrix_rows",
    "build_trade_detail_ledger_rows",
    "write_strategy_ladder_operator_artifacts",
]
