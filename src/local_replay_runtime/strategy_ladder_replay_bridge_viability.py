from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_candidate_discovery import (
    load_strategy_ladder_candidate_events,
)
from local_replay_runtime.strategy_ladder_economic_provenance import EconomicProvenance
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)
from local_replay_runtime.strategy_ladder_runner import _run_native_engine_candidate


@dataclass(frozen=True)
class ReplayBridgeCaseResult:
    engine_id: str
    candidate_id: str
    timeframe: str
    synthetic_expected_edge_bps: float
    synthetic_expected_cost_bps: float
    builder_status: str
    input_provenance: str
    runner_status: str
    native_decision: str
    production_decision_state: str
    hard_block_reasons: tuple[str, ...]
    native_reason_codes: tuple[str, ...]
    native_no_trade_reasons: tuple[str, ...]
    records_built: int
    raw_window_status: str
    book_depth_source_status: str


@dataclass(frozen=True)
class ReplayBridgeViabilityReport:
    schema_version: str
    generated_at: str
    workflow_root: str
    diagnostic_only: bool
    cases: tuple[ReplayBridgeCaseResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "workflow_root": self.workflow_root,
            "diagnostic_only": self.diagnostic_only,
            "cases": [asdict(case) for case in self.cases],
        }


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


def _load_window_manifests(windows_dir: Path) -> dict[str, StrategyLadderRawWindowManifest]:
    manifests: dict[str, StrategyLadderRawWindowManifest] = {}
    for path in sorted(windows_dir.glob("*.json")):
        manifest = StrategyLadderRawWindowManifest.model_validate_json(
            path.read_text(encoding="utf-8-sig")
        )
        manifests[manifest.candidate_id] = manifest
    return manifests


def _select_one_candidate_per_engine(
    candidates: tuple[StrategyLadderCandidateEvent, ...],
    manifests: dict[str, StrategyLadderRawWindowManifest],
) -> tuple[StrategyLadderCandidateEvent, ...]:
    selected: list[StrategyLadderCandidateEvent] = []
    seen_engines: set[str] = set()
    for candidate in candidates:
        engine_id = str(candidate.engine_id or "").strip().lower()
        if engine_id in seen_engines:
            continue
        if candidate.candidate_id not in manifests:
            continue
        selected.append(candidate)
        seen_engines.add(engine_id)
        if len(seen_engines) == 4:
            break
    return tuple(selected)


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
        expected_edge_model_artifact_hash="SYNTHETIC_DIAGNOSTIC",
        expected_edge_model_feature_hash="SYNTHETIC_DIAGNOSTIC",
    )


def run_replay_bridge_viability_report(
    workflow_root: Path | str,
) -> ReplayBridgeViabilityReport:
    workflow_path = Path(workflow_root).resolve()
    candidates = load_strategy_ladder_candidate_events(_b1_candidate_events_path(workflow_path))
    window_manifests = _load_window_manifests(_b2_candidate_windows_dir(workflow_path))
    selected_candidates = _select_one_candidate_per_engine(candidates, window_manifests)
    synthetic_truth = _synthetic_truth_provenance()

    cases: list[ReplayBridgeCaseResult] = []
    for candidate in selected_candidates:
        window = window_manifests[candidate.candidate_id]
        synthetic_event, records_built, _invoked = _run_native_engine_candidate(
            candidate=candidate,
            window=window,
            economic_provenance=synthetic_truth,
        )
        payload = dict(synthetic_event.compatibility_payload or {})
        cases.append(
            ReplayBridgeCaseResult(
                engine_id=str(candidate.engine_id),
                candidate_id=candidate.candidate_id,
                timeframe=str(candidate.timeframe or ""),
                synthetic_expected_edge_bps=synthetic_truth.expected_edge_bps,
                synthetic_expected_cost_bps=(
                    synthetic_truth.spread_bps
                    + synthetic_truth.slippage_bps * 1.15
                    + synthetic_truth.latency_penalty_bps
                ),
                builder_status=str(payload.get("engine_native_builder_status") or ""),
                input_provenance=str(payload.get("engine_native_input_provenance") or ""),
                runner_status=str(payload.get("engine_native_status") or ""),
                native_decision=str(payload.get("engine_native_decision") or ""),
                production_decision_state=str(payload.get("production_decision_state") or ""),
                hard_block_reasons=tuple(
                    str(item) for item in tuple(payload.get("hard_block_reasons") or ())
                ),
                native_reason_codes=tuple(
                    str(item)
                    for item in tuple(payload.get("engine_native_reason_codes") or ())
                ),
                native_no_trade_reasons=tuple(
                    str(item)
                    for item in tuple(payload.get("engine_native_no_trade_reasons") or ())
                ),
                records_built=records_built,
                raw_window_status=str(window.window_extraction_status),
                book_depth_source_status=str(window.book_depth_source_status),
            )
        )

    return ReplayBridgeViabilityReport(
        schema_version="strategy_ladder.replay_bridge_viability.v1",
        generated_at=datetime.now(tz=UTC).isoformat(),
        workflow_root=str(workflow_path),
        diagnostic_only=True,
        cases=tuple(cases),
    )


def render_replay_bridge_viability_report(report: ReplayBridgeViabilityReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


__all__ = [
    "ReplayBridgeCaseResult",
    "ReplayBridgeViabilityReport",
    "run_replay_bridge_viability_report",
    "render_replay_bridge_viability_report",
]
