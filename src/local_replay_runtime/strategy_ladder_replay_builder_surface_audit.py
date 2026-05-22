from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from engines.engine_c.engine_c_runner import EngineCInput, run_engine_c
from engines.engine_d.engine_d_models import EngineDInput
from engines.engine_d.engine_d_runner import run_engine_d
from local_replay_runtime.strategy_ladder_candidate_discovery import (
    load_strategy_ladder_candidate_events,
)
from local_replay_runtime.strategy_ladder_complete_enabler_support import (
    apply_build14_shadow_context,
)
from local_replay_runtime.strategy_ladder_economic_provenance import EconomicProvenance
from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
    build_engine_c_input_from_window,
)
from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
    build_engine_d_input_from_window,
)
from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    build_engine_c_microstructure_inputs_from_window,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)
from local_replay_runtime.strategy_ladder_runner import (
    _extract_engine_d_first_episode_context,
)


@dataclass(frozen=True)
class ReplayBuilderSurfaceExample:
    candidate_id: str
    timeframe: str
    decision: str
    builder_status: str
    input_provenance: str
    no_trade_reasons: tuple[str, ...]
    reason_codes: tuple[str, ...]
    metrics: dict[str, object]


@dataclass(frozen=True)
class ReplayBuilderSurfaceSummary:
    engine_id: str
    total_windows: int
    emit_count: int
    no_trade_count: int
    builder_status_counts: dict[str, int]
    decision_counts: dict[str, int]
    no_trade_reason_counts: dict[str, int]
    sample_emit_cases: tuple[ReplayBuilderSurfaceExample, ...]
    sample_no_trade_cases: tuple[ReplayBuilderSurfaceExample, ...]


@dataclass(frozen=True)
class ReplayBuilderSurfaceAuditReport:
    schema_version: str
    generated_at: str
    workflow_root: str
    diagnostic_only: bool
    synthetic_expected_edge_bps: float
    synthetic_expected_cost_bps: float
    engine_summaries: tuple[ReplayBuilderSurfaceSummary, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "workflow_root": self.workflow_root,
            "diagnostic_only": self.diagnostic_only,
            "synthetic_expected_edge_bps": self.synthetic_expected_edge_bps,
            "synthetic_expected_cost_bps": self.synthetic_expected_cost_bps,
            "engine_summaries": [asdict(summary) for summary in self.engine_summaries],
        }


@dataclass(frozen=True)
class _EngineAuditCase:
    engine_id: str
    candidate_id: str
    timeframe: str
    decision: str
    builder_status: str
    input_provenance: str
    no_trade_reasons: tuple[str, ...]
    reason_codes: tuple[str, ...]
    metrics: dict[str, object]


def _b1_candidate_events_path(workflow_root: Path) -> Path:
    return (
        workflow_root
        / "phase_b1_candidate_discovery"
        / "backtest_strategy_ladder"
        / workflow_root.name
        / "fast_candidates"
        / "candidate_events.jsonl"
    )


def _b2_candidate_windows_dir(workflow_root: Path) -> Path:
    return (
        workflow_root
        / "phase_b2_detailed_replay"
        / "backtest_strategy_ladder"
        / workflow_root.name
        / "candidate_replay_windows"
    )


def _load_window_manifests(
    windows_dir: Path,
) -> dict[str, StrategyLadderRawWindowManifest]:
    manifests: dict[str, StrategyLadderRawWindowManifest] = {}
    for path in sorted(windows_dir.glob("*.json")):
        manifest = StrategyLadderRawWindowManifest.model_validate_json(
            path.read_text(encoding="utf-8-sig")
        )
        manifests[manifest.candidate_id] = manifest
    return manifests


def _synthetic_truth_provenance() -> EconomicProvenance:
    spread_bps = 1.0
    slippage_bps = 0.5
    latency_bps = 0.1
    return EconomicProvenance(
        expected_edge_bps=30.0,
        expected_edge_provenance="GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
        spread_bps=spread_bps,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=slippage_bps,
        slippage_provenance="MEASURED_FROM_KYLE_LAMBDA",
        latency_penalty_bps=latency_bps,
        latency_provenance="STATIC_CONSERVATIVE_VENUE_MODEL",
        fee_bps=10.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
        measurement_warnings=(),
        expected_edge_model_status="GOVERNED_EDGE_MODEL_READY",
        expected_edge_model_artifact_hash="SURFACE_AUDIT_DIAGNOSTIC",
        expected_edge_model_feature_hash="SURFACE_AUDIT_DIAGNOSTIC",
    )


def _extract_engine_c_metrics(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: payload.get(key)
        for key in (
            "breakout_strength",
            "range_quality",
            "compression_quality",
            "volume_confirmation",
            "followthrough_room",
            "extension_pct",
            "retrace_risk",
            "cumulative_ofi",
            "queue_pressure",
            "vpin",
            "kyle_lambda",
            "entry_price",
            "breakout_level",
            "range_low",
            "range_high",
        )
    }


def _extract_engine_d_metrics(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: payload.get(key)
        for key in (
            "prior_trade_quality",
            "reformation_quality",
            "pullback_quality",
            "continuation_room",
            "concentration_headroom",
            "marginal_edge",
            "reentry_lateness",
            "anti_revenge_state",
            "last_fresh_a_detection_at_ns",
            "marginal_portfolio_gain",
            "covered_share_by_engine_a",
            "duplication_overlap_with_engine_a",
            "entry_price",
            "reentry_anchor_price",
        )
    }


def _run_engine_c_case(
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest,
    synthetic_truth: EconomicProvenance,
) -> _EngineAuditCase:
    bridge = build_engine_c_microstructure_inputs_from_window(
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        window_start_ms=window.window_start_ms,
        window_end_ms=window.window_end_ms,
        raw_trade_path=window.raw_trade_path,
        raw_book_path=window.raw_book_path,
        raw_book_delta_path=window.raw_book_delta_path,
    )
    builder = build_engine_c_input_from_window(
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        window_start_ms=window.window_start_ms,
        window_end_ms=window.window_end_ms,
        raw_trade_path=window.raw_trade_path,
        raw_ohlcv_path=window.raw_ohlcv_path,
        microstructure_partial_payload=bridge.engine_c_partial_input_payload,
        expected_gain=synthetic_truth.expected_edge_bps / 10_000.0,
        expected_cost=(
            synthetic_truth.spread_bps
            + synthetic_truth.slippage_bps * 1.15
            + synthetic_truth.latency_penalty_bps
        )
        / 10_000.0,
        candidate_size=float(
            (candidate.compatibility_payload or {}).get("planned_notional") or 1000.0
        ),
    )
    adjusted_payload = apply_build14_shadow_context(
        engine_id="engine_c",
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        candidate_payload=dict(candidate.compatibility_payload or {}),
        engine_input_payload=builder.engine_c_input_payload,
    ).adjusted_engine_input_payload
    output = run_engine_c(EngineCInput.model_validate(adjusted_payload))
    return _EngineAuditCase(
        engine_id="engine_c",
        candidate_id=candidate.candidate_id,
        timeframe=str(candidate.timeframe or ""),
        decision=str(output.decision),
        builder_status=builder.builder_status,
        input_provenance=builder.engine_c_input_provenance,
        no_trade_reasons=tuple(str(item) for item in output.no_trade_reasons),
        reason_codes=tuple(str(item) for item in output.reason_codes),
        metrics=_extract_engine_c_metrics(adjusted_payload),
    )


def _run_engine_d_case(
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest,
    synthetic_truth: EconomicProvenance,
) -> _EngineAuditCase:
    candidate_payload = dict(candidate.compatibility_payload or {})
    builder = build_engine_d_input_from_window(
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        window_start_ms=window.window_start_ms,
        window_end_ms=window.window_end_ms,
        raw_trade_path=window.raw_trade_path,
        raw_ohlcv_path=window.raw_ohlcv_path,
        first_episode_context=_extract_engine_d_first_episode_context(candidate_payload),
        expected_gain=synthetic_truth.expected_edge_bps / 10_000.0,
        expected_cost=(
            synthetic_truth.spread_bps
            + synthetic_truth.slippage_bps * 1.15
            + synthetic_truth.latency_penalty_bps
        )
        / 10_000.0,
        candidate_size=float(candidate_payload.get("planned_notional") or 800.0),
    )
    adjusted_payload = apply_build14_shadow_context(
        engine_id="engine_d",
        candidate_id=candidate.candidate_id,
        pair=candidate.pair,
        candidate_payload=candidate_payload,
        engine_input_payload=builder.engine_d_input_payload,
    ).adjusted_engine_input_payload
    output = run_engine_d(EngineDInput.model_validate(adjusted_payload))
    return _EngineAuditCase(
        engine_id="engine_d",
        candidate_id=candidate.candidate_id,
        timeframe=str(candidate.timeframe or ""),
        decision=str(output.decision),
        builder_status=builder.builder_status,
        input_provenance=builder.engine_d_input_provenance,
        no_trade_reasons=tuple(str(item) for item in output.no_trade_reasons),
        reason_codes=tuple(str(item) for item in output.reason_codes),
        metrics=_extract_engine_d_metrics(adjusted_payload),
    )


def _summarize_engine_cases(
    engine_id: str,
    cases: list[_EngineAuditCase],
) -> ReplayBuilderSurfaceSummary:
    builder_status_counts = Counter(case.builder_status for case in cases)
    decision_counts = Counter(case.decision for case in cases)
    no_trade_reason_counts = Counter(
        reason for case in cases for reason in case.no_trade_reasons
    )
    emit_cases = [
        ReplayBuilderSurfaceExample(
            candidate_id=case.candidate_id,
            timeframe=case.timeframe,
            decision=case.decision,
            builder_status=case.builder_status,
            input_provenance=case.input_provenance,
            no_trade_reasons=case.no_trade_reasons,
            reason_codes=case.reason_codes,
            metrics=case.metrics,
        )
        for case in cases
        if case.decision == "emit"
    ][:5]
    no_trade_cases = [
        ReplayBuilderSurfaceExample(
            candidate_id=case.candidate_id,
            timeframe=case.timeframe,
            decision=case.decision,
            builder_status=case.builder_status,
            input_provenance=case.input_provenance,
            no_trade_reasons=case.no_trade_reasons,
            reason_codes=case.reason_codes,
            metrics=case.metrics,
        )
        for case in cases
        if case.decision != "emit"
    ][:5]
    return ReplayBuilderSurfaceSummary(
        engine_id=engine_id,
        total_windows=len(cases),
        emit_count=decision_counts.get("emit", 0),
        no_trade_count=len(cases) - decision_counts.get("emit", 0),
        builder_status_counts=dict(builder_status_counts),
        decision_counts=dict(decision_counts),
        no_trade_reason_counts=dict(no_trade_reason_counts),
        sample_emit_cases=tuple(emit_cases),
        sample_no_trade_cases=tuple(no_trade_cases),
    )


def run_replay_builder_surface_audit(
    workflow_root: Path | str,
    *,
    engine_ids: tuple[str, ...] = ("engine_c", "engine_d"),
) -> ReplayBuilderSurfaceAuditReport:
    workflow_path = Path(workflow_root).resolve()
    candidates = load_strategy_ladder_candidate_events(_b1_candidate_events_path(workflow_path))
    windows = _load_window_manifests(_b2_candidate_windows_dir(workflow_path))
    candidate_by_id = {
        candidate.candidate_id: candidate
        for candidate in candidates
        if candidate.candidate_id in windows
        and str(candidate.engine_id or "").strip().lower() in set(engine_ids)
    }
    synthetic_truth = _synthetic_truth_provenance()
    engine_case_map: dict[str, list[_EngineAuditCase]] = {engine_id: [] for engine_id in engine_ids}
    for candidate_id, candidate in candidate_by_id.items():
        engine_id = str(candidate.engine_id or "").strip().lower()
        window = windows[candidate_id]
        if engine_id == "engine_c":
            engine_case_map[engine_id].append(
                _run_engine_c_case(candidate, window, synthetic_truth)
            )
        elif engine_id == "engine_d":
            engine_case_map[engine_id].append(
                _run_engine_d_case(candidate, window, synthetic_truth)
            )

    summaries = tuple(
        _summarize_engine_cases(engine_id, engine_case_map[engine_id])
        for engine_id in engine_ids
    )
    return ReplayBuilderSurfaceAuditReport(
        schema_version="strategy_ladder.replay_builder_surface_audit.v1",
        generated_at=datetime.now(tz=UTC).isoformat(),
        workflow_root=str(workflow_path),
        diagnostic_only=True,
        synthetic_expected_edge_bps=synthetic_truth.expected_edge_bps,
        synthetic_expected_cost_bps=(
            synthetic_truth.spread_bps
            + synthetic_truth.slippage_bps * 1.15
            + synthetic_truth.latency_penalty_bps
        ),
        engine_summaries=summaries,
    )


def render_replay_builder_surface_audit(
    report: ReplayBuilderSurfaceAuditReport,
) -> str:
    return json.dumps(report.to_dict(), indent=2)


__all__ = [
    "ReplayBuilderSurfaceAuditReport",
    "ReplayBuilderSurfaceSummary",
    "ReplayBuilderSurfaceExample",
    "render_replay_builder_surface_audit",
    "run_replay_builder_surface_audit",
]
