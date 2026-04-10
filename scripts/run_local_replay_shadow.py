#!/usr/bin/env python3
"""Materialize a governed LOCAL_REPLAY -> VPS import -> SHADOW demo run."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time as time_of_day, timedelta, timezone
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backtest_artifact_import import (  # noqa: E402
    ArtifactPayloadRefBundle,
    ArtifactUploadContext,
    build_lab_fixture_signature_envelope,
    build_artifact_upload_decision,
    build_import_context_from_replay_plan,
    build_import_context_from_export_dir,
    build_replay_import_projection,
    build_upload_context_from_replay_import_context,
    discover_local_replay_export,
    summarize_import_request,
    validate_import_request,
)
from complete_enablers import evaluate_build14_shadow_activation  # noqa: E402
from engines.engine_a import EngineAInput, EngineARuntime, EngineARuntimeInput, EngineARuntimeStatus  # noqa: E402
from engines.engine_b import EngineBInput, EngineBRuntime, EngineBRuntimeInput, EngineBRuntimeStatus  # noqa: E402
from engines.engine_c import EngineCInput, EngineCRuntime, EngineCRuntimeInput, EngineCRuntimeStatus  # noqa: E402
from engines.engine_d import EngineDInput, EngineDRuntime, EngineDRuntimeInput, EngineDRuntimeStatus  # noqa: E402
from interface_contracts import (  # noqa: E402
    ArtifactActivationStage,
    ArtifactClass,
    ArtifactLifecyclePolicy,
    ArtifactLogicFormat,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    PairHealthLevel,
    ProfileId,
    RuntimeMode,
    StrategyClassification,
)
from local_replay_runtime import (  # noqa: E402
    LocalReplayEvidenceRecorder,
    LocalReplayEvidenceRecorderConfig,
    LocalReplayOrchestrator,
    LocalReplayRequest,
    ReplayRunManifest,
    ReplayClockRef,
    ReplayDatasetRef,
)
from manifest_registry.profile_registry import get_modules_for_profile  # noqa: E402
from meta import build_break_even_report, build_cra_report, build_dtr_summary, build_edge_report  # noqa: E402
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView  # noqa: E402
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel  # noqa: E402
from meta_minimal.cra_monitor.sterilization_classifier import (  # noqa: E402
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState  # noqa: E402
from meta_minimal.dtr_core.dtr_record_builder import build_dtr  # noqa: E402
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (  # noqa: E402
    EdgeClassification,
    EdgeStatus,
)
from monitoring import (  # noqa: E402
    Build14ReaderProjection,
    Build14Projection,
    Build9XProjection,
    ReplayImportProjection,
    build_technical_dashboard_payload,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
    derive_build14_observation_from_snapshot,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker  # noqa: E402
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime  # noqa: E402
from protocols import (  # noqa: E402
    ShadowComponentAssessment,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowDailyOrchestrator,
    ShadowDayCounter,
    ShadowProfile,
    ShadowSessionEntry,
    ShadowSessionRegistry,
    ShadowRuntimeEvidenceRecorder,
    ShadowRuntimeEvidenceRecorderConfig,
    build_shadow_daily_metrics_summary,
    build_runtime_hook_bridge_projections,
    build_shadow_input_from_payloads,
    run_shadow_validation,
)
from protocols.shadow_day_counter import ShadowDayRecord  # noqa: E402
from scoring_backbone.penalty_aggregator.penalty_registry import (  # noqa: E402
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState  # noqa: E402
from scoring_backbone.scoring_runtime import ScoringRuntime  # noqa: E402


_SHADOW_IMPORT_LIFECYCLE_POLICY = ArtifactLifecyclePolicy(
    ttl_max_days=30,
    rule_half_life_days=7,
)
_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD = 0.85
_RECOVERED_SHADOW_RUN_ID = "recovered:shadow_session_registry"
_RECOVERED_SHADOW_ARTIFACT_ID = "recovered:artifact"
_RECOVERED_SHADOW_LINEAGE_VERSION = "recovered:lineage"


def _shadow_upload_signature_envelope() -> ArtifactSignatureEnvelope:
    return build_lab_fixture_signature_envelope()


def _shadow_upload_proof_summary() -> ArtifactProofSummary:
    return ArtifactProofSummary(
        anti_cowardice_pass=True,
        friction_regret_pass=True,
        walk_forward_pass=True,
        regime_segmentation_pass=True,
        operational_burden_pass=True,
        capital_efficiency_pass=True,
        ablation_delta_net_pnl=0.12,
        ablation_delta_ce=0.03,
        friction_regret_value=0.01,
        block_rate_delta=0.02,
    )


def _load_successful_shadow_day_records(
    output_dir: Path,
    *,
    profile: ShadowProfile,
) -> tuple[tuple[Path, ShadowDayRecord], ...]:
    shadow_days_dir = output_dir / "shadow_days"
    if not shadow_days_dir.is_dir():
        return ()

    loaded_records: list[tuple[Path, ShadowDayRecord]] = []
    for path in sorted(shadow_days_dir.glob("local_replay_shadow.day_*.json")):
        try:
            record = ShadowDayRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if record.profile != profile or not record.passed_all_gates:
            continue
        loaded_records.append((path, record))
    loaded_records.sort(key=lambda item: item[1].day_number)
    return tuple(loaded_records)


def _build_recovered_shadow_registry_entries(
    records: tuple[tuple[Path, ShadowDayRecord], ...],
) -> tuple[ShadowSessionEntry, ...]:
    recovered_entries: list[ShadowSessionEntry] = []
    for path, record in records:
        recovered_entries.append(
            ShadowSessionEntry(
                session_date=record.date,
                counter_day_number=record.day_number,
                correlation_id=f"recovered:corr:{record.date}:{record.day_number:04d}",
                run_id=_RECOVERED_SHADOW_RUN_ID,
                artifact_id=_RECOVERED_SHADOW_ARTIFACT_ID,
                lineage_version=_RECOVERED_SHADOW_LINEAGE_VERSION,
                day_record_ref=str(path.resolve()),
                export_dir_ref="",
            )
        )
    return tuple(recovered_entries)


def _recover_shadow_state_from_artifacts(
    output_dir: Path,
    *,
    shadow_counter: ShadowDayCounter,
    shadow_registry: ShadowSessionRegistry,
) -> None:
    recovered_records = _load_successful_shadow_day_records(
        output_dir,
        profile=ShadowProfile.COMPLETE,
    )
    if not recovered_records:
        return

    successful_records = tuple(record for _, record in recovered_records)
    counter_state = shadow_counter.get_status()
    registry_error = shadow_registry._state.last_error

    if counter_state.last_error:
        shadow_counter.recover_from_records(successful_records)
        counter_state = shadow_counter.get_status()

    if registry_error:
        shadow_registry.recover_from_entries(
            _build_recovered_shadow_registry_entries(recovered_records)
        )
    elif not shadow_registry.get_entries() and counter_state.consecutive_days > 0:
        shadow_registry.recover_from_entries(
            _build_recovered_shadow_registry_entries(recovered_records)
        )


@dataclass(frozen=True)
class LocalReplayShadowArtifacts:
    """Files generated by the governed LOCAL_REPLAY -> SHADOW runner."""

    run_manifest_json_path: Path | None
    replay_plan_json_path: Path
    import_summary_json_path: Path
    local_replay_evidence_json_path: Path
    baseline_payload_json_path: Path
    candidate_payload_json_path: Path
    engine_shadow_evidence_json_path: Path
    shadow_input_json_path: Path
    shadow_runtime_evidence_json_path: Path
    shadow_summary_json_path: Path
    shadow_day_record_json_path: Path
    shadow_report_json_path: Path
    shadow_days_dir_path: Path
    shadow_session_summary_json_path: Path
    shadow_session_registry_json_path: Path
    upload_request_json_path: Path | None = None
    upload_decision_json_path: Path | None = None


@dataclass(frozen=True)
class ShadowEngineRuntimeEvidence:
    component_id: str
    pair: str
    runtime_status: str
    emitted_signal: bool
    verdict: ShadowComponentVerdict
    evidence_summary: str
    expected_cost_bps: float
    expected_edge_bps: float
    ce_expected: float
    scoring_summary: str
    risk_summary: str
    scoring_reason_codes: tuple[str, ...]
    risk_reason_codes: tuple[str, ...]
    details: dict[str, object]


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _shadow_penalty_registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(
        PenaltyDefinition(
            penalty_id="shadow_context_soft",
            name="Shadow context soft",
            penalty_type=PenaltyType.SCORE,
        )
    )
    registry.register(
        PenaltyDefinition(
            penalty_id="breakout_warning",
            name="Breakout warning",
            penalty_type=PenaltyType.SCORE,
        )
    )
    return registry


def _shadow_scoring_runtime() -> ScoringRuntime:
    return ScoringRuntime(_shadow_penalty_registry())


def _shadow_risk_runtime() -> RiskRuntime:
    return RiskRuntime(
        RiskLimits(
            gross_cap=10_000.0,
            position_cap=4_000.0,
            loss_cap=1_000.0,
            beta_cap=10_000.0,
            cluster_cap=10_000.0,
        )
    )


def _shadow_portfolio_state() -> PortfolioState:
    return PortfolioState(
        remaining_gross_capacity=10_000.0,
        remaining_loss_capacity=1_000.0,
        remaining_beta_capacity=10_000.0,
        remaining_cluster_capacity={
            "btc_majors": 10_000.0,
            "eth_majors": 10_000.0,
        },
    )


def _expected_edge_bps(*, expected_cost: float, ce_expected: float, holding_hours: float) -> float:
    return round((expected_cost + ce_expected * holding_hours) * 10_000, 3)


def _scoring_reason_codes(engine_result: object) -> tuple[str, ...]:
    scoring_audit = getattr(engine_result, "scoring_audit", None)
    if scoring_audit is None:
        return ()
    explainability = getattr(scoring_audit, "explainability", None)
    if explainability is None:
        return ()
    codes = list(getattr(explainability, "hard_block_codes", ()))
    codes.extend(
        f"PEN_{penalty_id.upper()}"
        for penalty_id in getattr(explainability, "dominant_score_penalty_ids", ())
    )
    codes.extend(
        f"SIZE_{penalty_id.upper()}"
        for penalty_id in getattr(explainability, "dominant_size_penalty_ids", ())
    )
    portfolio_verdict = getattr(explainability, "portfolio_verdict_code", "")
    if portfolio_verdict:
        codes.append(f"PORTFOLIO_{portfolio_verdict.upper()}")
    selection_outcome = getattr(explainability, "selection_outcome_code", "")
    if selection_outcome:
        codes.append(f"SELECTION_{selection_outcome.upper()}")
    return tuple(dict.fromkeys(codes))


def _risk_reason_codes(engine_result: object) -> tuple[str, ...]:
    risk_evaluation = getattr(engine_result, "risk_evaluation", None)
    if risk_evaluation is None:
        return ()
    reason_details = getattr(risk_evaluation, "reason_details", ())
    return tuple(dict.fromkeys(detail.code for detail in reason_details))


def _scoring_summary(engine_result: object) -> str:
    scoring_audit = getattr(engine_result, "scoring_audit", None)
    if scoring_audit is None:
        return ""
    explainability = getattr(scoring_audit, "explainability", None)
    if explainability is None:
        return ""
    return getattr(explainability, "summary", "")


def _risk_summary(engine_result: object) -> str:
    risk_evaluation = getattr(engine_result, "risk_evaluation", None)
    if risk_evaluation is None:
        return ""
    return getattr(risk_evaluation, "explain_summary", "")


def _shadow_circuit_breaker(engine_id: str) -> EmergencyCircuitBreaker:
    state_dir = REPO_ROOT / "build" / "local_replay_shadow_breakers" / engine_id
    state_dir.mkdir(parents=True, exist_ok=True)
    return EmergencyCircuitBreaker(state_dir=state_dir)


def _run_engine_shadow_evaluations() -> tuple[ShadowEngineRuntimeEvidence, ...]:
    engine_a_runtime = EngineARuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_a"),
    )
    engine_a_result = engine_a_runtime.evaluate(
        EngineARuntimeInput(
            engine_inputs=EngineAInput(
                pair="BTCUSDT",
                direction_score=0.8,
                continuation_score=0.9,
                structure_quality=0.85,
                zone_proximity=0.7,
                trend_stability=0.8,
                regime="trending_up",
                regime_favorability=0.9,
                regime_confidence=0.8,
                pair_health=0.9,
                data_freshness=0.95,
                flow_coherence=0.8,
                flow_score=0.4,
                cost_preference_score=0.5,
                expected_gain=0.005,
                expected_cost=0.001,
                candidate_size=1_000.0,
                holding_period=4.0,
                entry_price=50_000.0,
                atr=500.0,
                scoring_version="engine_a.shadow.v1",
            ),
            timestamp_ms=1_700_000_000_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=1_000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.8,
            cluster_id="btc_majors",
        ),
        now=5.0,
    )
    engine_b_runtime = EngineBRuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_b"),
    )
    engine_b_result = engine_b_runtime.evaluate(
        EngineBRuntimeInput(
            engine_inputs=EngineBInput(
                pair="ETHUSDT",
                current_price=97.0,
                local_mean=100.0,
                local_std=1.5,
                structure_is_range=0.7,
                recent_expansion=0.1,
                regime="range",
                regime_trend_strength=0.1,
                volume_anomaly=0.1,
                structural_break=0.0,
                continuation_momentum=0.1,
                microstructure_breakout_confirmation=0.0,
                regime_favorability=0.7,
                pair_health=0.8,
                data_freshness=0.9,
                flow_coherence=0.8,
                expected_gain=0.003,
                expected_cost=0.001,
                candidate_size=100.0,
                holding_period=2.0,
                scoring_version="engine_b.shadow.v1",
            ),
            timestamp_ms=1_700_000_030_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=1_000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.7,
            cluster_id="eth_majors",
        ),
        now=10.0,
    )
    engine_c_runtime = EngineCRuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_c"),
    )
    engine_c_result = engine_c_runtime.evaluate(
        EngineCRuntimeInput(
            engine_inputs=EngineCInput(
                pair="BTCUSDT",
                breakout_strength=0.88,
                range_quality=0.79,
                compression_quality=0.76,
                volume_confirmation=0.82,
                followthrough_room=0.78,
                extension_pct=0.23,
                retrace_risk=0.16,
                rejection_wick_ratio=0.11,
                regime="breakout",
                regime_favorability=0.81,
                pair_health=0.93,
                data_freshness=0.96,
                flow_coherence=0.84,
                expected_gain=0.0115,
                expected_cost=0.0023,
                candidate_size=1_000.0,
                holding_period=3.0,
                entry_price=105.0,
                breakout_level=101.0,
                range_low=97.5,
                range_high=101.0,
                atr=2.0,
                engine_a_overlap_ratio=0.28,
                marginal_portfolio_gain=9.2,
                covered_share_by_engine_a=0.22,
                keff_contribution=0.31,
                scoring_version="engine_c.v1",
            ),
            timestamp_ms=1_700_000_000_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=1_000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.8,
            cluster_id="btc_majors",
        ),
        now=10.0,
    )
    engine_d_runtime = EngineDRuntime(
        scoring_runtime=_shadow_scoring_runtime(),
        risk_runtime=_shadow_risk_runtime(),
        circuit_breaker=_shadow_circuit_breaker("engine_d"),
    )
    engine_d_result = engine_d_runtime.evaluate(
        EngineDRuntimeInput(
            engine_inputs=EngineDInput(
                pair="ETHUSDT",
                origin_context_id="ctx-eth-breakout-01",
                origin_trade_id="trade-eth-01",
                link_type="prior_trade",
                prior_trade_quality=0.86,
                reformation_quality=0.79,
                pullback_quality=0.75,
                continuation_room=0.71,
                concentration_headroom=0.81,
                marginal_edge=0.74,
                reentry_lateness=0.17,
                structure_reformed_detected=True,
                regime="trending_up",
                regime_favorability=0.79,
                pair_health=0.91,
                data_freshness=0.95,
                flow_coherence=0.82,
                expected_gain=0.0095,
                expected_cost=0.0020,
                candidate_size=800.0,
                holding_period=2.0,
                entry_price=104.0,
                reentry_anchor_price=101.5,
                atr=1.8,
                duplication_overlap_with_engine_a=0.24,
                marginal_portfolio_gain=6.0,
                covered_share_by_engine_a=0.18,
                scoring_version="engine_d.v1",
            ),
            timestamp_ms=1_700_000_060_000,
            portfolio=_shadow_portfolio_state(),
            projected_size=800.0,
            projected_loss=40.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.7,
            cluster_id="eth_majors",
        ),
        now=20.0,
    )
    engine_a_evidence = ShadowEngineRuntimeEvidence(
        component_id="engine_a",
        pair=engine_a_result.engine_output.pair,
        runtime_status=engine_a_result.status.value,
        emitted_signal=engine_a_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_a_result.status == EngineARuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_a_result.status.value} / pair={engine_a_result.engine_output.pair} / "
            f"structure={engine_a_result.engine_output.structure_verdict.value} / "
            f"context={engine_a_result.engine_output.context_verdict.value} / "
            f"conviction={engine_a_result.engine_output.conviction.value}"
        ),
        expected_cost_bps=round(engine_a_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_a_result.engine_output.expected_cost,
            ce_expected=engine_a_result.engine_output.ce_expected,
            holding_hours=engine_a_result.engine_output.holding_hours,
        ),
        ce_expected=engine_a_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_a_result),
        risk_summary=_risk_summary(engine_a_result),
        scoring_reason_codes=_scoring_reason_codes(engine_a_result),
        risk_reason_codes=_risk_reason_codes(engine_a_result),
        details=engine_a_result.model_dump(mode="json"),
    )
    engine_b_evidence = ShadowEngineRuntimeEvidence(
        component_id="engine_b",
        pair=engine_b_result.engine_output.pair,
        runtime_status=engine_b_result.status.value,
        emitted_signal=engine_b_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_b_result.status == EngineBRuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_b_result.status.value} / pair={engine_b_result.engine_output.pair} / "
            f"z_score={engine_b_result.engine_output.z_score:.3f} / "
            f"breakout={engine_b_result.engine_output.breakout_verdict.value} / "
            f"conviction={engine_b_result.engine_output.conviction.value}"
        ),
        expected_cost_bps=round(engine_b_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_b_result.engine_output.expected_cost,
            ce_expected=engine_b_result.engine_output.ce_expected,
            holding_hours=engine_b_result.engine_output.expected_holding_hours,
        ),
        ce_expected=engine_b_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_b_result),
        risk_summary=_risk_summary(engine_b_result),
        scoring_reason_codes=_scoring_reason_codes(engine_b_result),
        risk_reason_codes=_risk_reason_codes(engine_b_result),
        details=engine_b_result.model_dump(mode="json"),
    )
    engine_c_evidence = ShadowEngineRuntimeEvidence(
        component_id="engine_c",
        pair=engine_c_result.engine_output.pair,
        runtime_status=engine_c_result.status.value,
        emitted_signal=engine_c_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_c_result.status == EngineCRuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_c_result.status.value} / pair={engine_c_result.engine_output.pair} / "
            f"breakout_type={engine_c_result.engine_output.breakout_type} / "
            f"duplication_with_a={engine_c_result.engine_output.duplication_overlap_with_engine_a:.2f} / "
            f"keff={engine_c_result.engine_output.keff_contribution:.2f}"
        ),
        expected_cost_bps=round(engine_c_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_c_result.engine_output.expected_cost,
            ce_expected=engine_c_result.engine_output.ce_expected,
            holding_hours=engine_c_result.engine_output.holding_hours,
        ),
        ce_expected=engine_c_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_c_result),
        risk_summary=_risk_summary(engine_c_result),
        scoring_reason_codes=_scoring_reason_codes(engine_c_result),
        risk_reason_codes=_risk_reason_codes(engine_c_result),
        details=engine_c_result.model_dump(mode="json"),
    )
    engine_d_evidence = ShadowEngineRuntimeEvidence(
        component_id="engine_d",
        pair=engine_d_result.engine_output.pair,
        runtime_status=engine_d_result.status.value,
        emitted_signal=engine_d_result.signal_candidate is not None,
        verdict=(
            ShadowComponentVerdict.SHADOW_VALIDATED
            if engine_d_result.status == EngineDRuntimeStatus.ACCEPTED
            else ShadowComponentVerdict.DORMANT
        ),
        evidence_summary=(
            f"runtime_status={engine_d_result.status.value} / pair={engine_d_result.engine_output.pair} / "
            f"origin={engine_d_result.engine_output.origin_trade_id or engine_d_result.engine_output.origin_context_id} / "
            f"link_type={engine_d_result.engine_output.link_type} / "
            f"duplication_with_a={engine_d_result.engine_output.duplication_overlap_with_engine_a:.2f}"
        ),
        expected_cost_bps=round(engine_d_result.engine_output.expected_cost * 10_000, 3),
        expected_edge_bps=_expected_edge_bps(
            expected_cost=engine_d_result.engine_output.expected_cost,
            ce_expected=engine_d_result.engine_output.ce_expected,
            holding_hours=engine_d_result.engine_output.holding_hours,
        ),
        ce_expected=engine_d_result.engine_output.ce_expected,
        scoring_summary=_scoring_summary(engine_d_result),
        risk_summary=_risk_summary(engine_d_result),
        scoring_reason_codes=_scoring_reason_codes(engine_d_result),
        risk_reason_codes=_risk_reason_codes(engine_d_result),
        details=engine_d_result.model_dump(mode="json"),
    )
    return (engine_a_evidence, engine_b_evidence, engine_c_evidence, engine_d_evidence)


def _meta_metrics():
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-local-replay-shadow-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1_700_000_000.0,
            ),
            build_dtr(
                dtr_id="dtr-local-replay-shadow-2",
                pair="ETHUSDT",
                engine_id="engine_b",
                decision_state=DecisionState.REJECTED_RANKING,
                timestamp=1_700_000_060.0,
            ),
        ),
        total_opportunities=4,
    )
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.HEALTHY,
                multiplier=1.0,
                phantom_risk_score=0.10,
            ),
            SterilizationResult(
                pair="ETHUSDT",
                engine_id="engine_b",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.55,
                phantom_risk_score=0.78,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_b",
                sterilization_rate=0.50,
                total_trades=2,
                sterilized_count=1,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=12,
                mean_realized_cost=0.0015,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0005,
                profitable_rate=0.41,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.0021,
                standard_error=0.0003,
                sample_size=18,
                sharpe_per_trade=0.31,
                mean_cost_p90=0.0010,
                ce_observed=0.0005,
                cluster_utilization=0.22,
            ),
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.0008,
                standard_error=0.0005,
                sample_size=16,
                sharpe_per_trade=-0.07,
                mean_cost_p90=0.0021,
                ce_observed=-0.0001,
                cluster_utilization=0.35,
            ),
        )
    )
    return collect_meta_metrics(
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
        future_learning_diagnostics=0,
        future_learning_hypotheses=0,
    )


def _build14_reader_projections(report) -> tuple[Build14ReaderProjection, ...]:
    return tuple(
        Build14ReaderProjection(
            reader_name=snapshot.reader_name,
            signal_family=snapshot.signal_family.value,
            observed_value=snapshot.observed_value,
            status=snapshot.status.value,
            detail=snapshot.detail,
            evidence_refs=snapshot.evidence_refs,
            structured_log_key=snapshot.structured_log_key,
        )
        for snapshot in report.snapshots
    )


def _build14_projection(snapshot) -> Build14Projection:
    report = evaluate_build14_shadow_activation(
        derive_build14_observation_from_snapshot(snapshot)
    )
    snapshots_by_reader = {entry.reader_name: entry for entry in report.snapshots}
    market_toxicity = snapshots_by_reader.get("market_toxicity_snapshot")
    execution_fragility = snapshots_by_reader.get("execution_fragility_score")
    status = (
        "critical"
        if report.signal.severity.value == "critical"
        else "warning"
        if report.signal.severity.value == "elevated"
        else "healthy"
    )
    return Build14Projection(
        status=status,
        hard_state=report.hard_state.value,
        live_promotion_eligible=report.live_promotion_eligible,
        influence_mode=report.signal.influence_mode.value,
        action=report.signal.action.value,
        severity=report.signal.severity.value,
        summary=report.signal.summary,
        market_toxicity_value=market_toxicity.observed_value if market_toxicity is not None else 0.0,
        market_toxicity_status=market_toxicity.status.value if market_toxicity is not None else "nominal",
        execution_fragility_value=(
            execution_fragility.observed_value if execution_fragility is not None else 0.0
        ),
        execution_fragility_status=(
            execution_fragility.status.value if execution_fragility is not None else "nominal"
        ),
        confidence_penalty_weight=0.0,
        recommended_budget_factor=1.0,
        requires_manual_review=report.signal.requires_manual_review,
        candidate_effect=report.signal.candidate_effect,
        reason_codes=report.signal.reason_codes,
        reader_projections=_build14_reader_projections(report),
    )


def _build_component_assessments(
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...],
) -> tuple[ShadowComponentAssessment, ...]:
    engine_ids = ("engine_a", "engine_b", "engine_c", "engine_d")
    build14_ids = (
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    )
    runtime_evidence_by_component = {
        evidence.component_id: evidence for evidence in engine_runtime_evidence
    }
    assessments: list[ShadowComponentAssessment] = []
    for component_id in engine_ids:
        evidence = runtime_evidence_by_component.get(component_id)
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.ENGINE,
                verdict=(
                    evidence.verdict
                    if evidence is not None
                    else ShadowComponentVerdict.SHADOW_VALIDATED
                ),
                evidence_summary=(
                    evidence.evidence_summary
                    if evidence is not None
                    else f"{component_id} stayed reproducible in the governed demo run."
                ),
            )
        )
    for component_id in build14_ids:
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.BUILD14_ENABLER,
                verdict=ShadowComponentVerdict.SHADOW_VALIDATED,
                evidence_summary=f"{component_id} remained available for governed Shadow review.",
            )
        )
    return tuple(assessments)


def _demo_payload_refs(correlation_id: str) -> ArtifactPayloadRefBundle:
    review_export_ref = "exports/local_replay_shadow_review.md"
    feature_bridge_ref = f"feature_bridge:{correlation_id}"
    parity_diagnostics_ref = f"parity_diagnostics:{correlation_id}"
    replay_metrics_ref = f"replay_metrics:{correlation_id}"
    replay_dtr_ref = f"replay_dtr:{correlation_id}"
    return ArtifactPayloadRefBundle(
        review_export_ref=review_export_ref,
        feature_bridge_ref=feature_bridge_ref,
        parity_diagnostics_ref=parity_diagnostics_ref,
        replay_metrics_ref=replay_metrics_ref,
        replay_dtr_ref=replay_dtr_ref,
    )


def _load_json_payload_from_ref(ref: str) -> dict | None:
    candidate = Path(ref)
    if not candidate.is_file():
        return None
    if candidate.suffix.lower() not in {".json", ".jsonl"}:
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _build_replay_projection(import_summary) -> ReplayImportProjection:
    return build_replay_import_projection(import_summary)


def _build_demo_payload(
    *,
    correlation_id: str,
    ce_net: float,
    dtr_coverage: float,
    cra_sterilization_rate: float,
    active_alert_count: int,
    queue_backlog: int,
    output_dir: Path,
    replay_projection: ReplayImportProjection,
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...] = (),
) -> object:
    runtime_evidence_by_component = {
        evidence.component_id: evidence for evidence in engine_runtime_evidence
    }
    engine_a_metrics = runtime_evidence_by_component.get("engine_a")
    engine_b_metrics = runtime_evidence_by_component.get("engine_b")
    engine_c_metrics = runtime_evidence_by_component.get("engine_c")
    engine_d_metrics = runtime_evidence_by_component.get("engine_d")
    snapshot = collect_monitoring_snapshot(
        correlation_id=correlation_id,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=35.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.30,
            capital_deployed_usdt=1200.0,
            ce_net=ce_net,
        ),
        infra=collect_infra_metrics(
            queue_backlog=queue_backlog,
            stale_pairs=("ETHUSDT",) if active_alert_count else (),
            stale_spike_count=1 if active_alert_count else 0,
        ),
        meta=_meta_metrics().model_copy(
            update={
                "dtr_coverage": dtr_coverage,
                "cra_sterilization_rate": cra_sterilization_rate,
            }
        ),
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=1 if engine_a_metrics is not None and engine_a_metrics.emitted_signal else 3,
                net_edge_bps=engine_a_metrics.expected_edge_bps if engine_a_metrics is not None else 8.0,
                expected_cost_bps=engine_a_metrics.expected_cost_bps if engine_a_metrics is not None else 2.0,
                ce_expected=engine_a_metrics.ce_expected if engine_a_metrics is not None else 0.0006,
                scoring_summary=engine_a_metrics.scoring_summary if engine_a_metrics is not None else "",
                risk_summary=engine_a_metrics.risk_summary if engine_a_metrics is not None else "",
                scoring_reason_codes=engine_a_metrics.scoring_reason_codes if engine_a_metrics is not None else (),
                risk_reason_codes=engine_a_metrics.risk_reason_codes if engine_a_metrics is not None else (),
            ),
            collect_engine_metrics(
                engine_id="engine_b",
                emitted_signals=1 if engine_b_metrics is not None and engine_b_metrics.emitted_signal else 2,
                net_edge_bps=engine_b_metrics.expected_edge_bps if engine_b_metrics is not None else 4.0,
                expected_cost_bps=engine_b_metrics.expected_cost_bps if engine_b_metrics is not None else 2.4,
                ce_expected=engine_b_metrics.ce_expected if engine_b_metrics is not None else 0.0002,
                scoring_summary=engine_b_metrics.scoring_summary if engine_b_metrics is not None else "",
                risk_summary=engine_b_metrics.risk_summary if engine_b_metrics is not None else "",
                scoring_reason_codes=engine_b_metrics.scoring_reason_codes if engine_b_metrics is not None else (),
                risk_reason_codes=engine_b_metrics.risk_reason_codes if engine_b_metrics is not None else (),
            ),
            collect_engine_metrics(
                engine_id="engine_c",
                emitted_signals=1 if engine_c_metrics is not None and engine_c_metrics.emitted_signal else 0,
                net_edge_bps=engine_c_metrics.expected_edge_bps if engine_c_metrics is not None else 6.5,
                expected_cost_bps=engine_c_metrics.expected_cost_bps if engine_c_metrics is not None else 2.3,
                ce_expected=engine_c_metrics.ce_expected if engine_c_metrics is not None else 0.00035,
                scoring_summary=engine_c_metrics.scoring_summary if engine_c_metrics is not None else "",
                risk_summary=engine_c_metrics.risk_summary if engine_c_metrics is not None else "",
                scoring_reason_codes=engine_c_metrics.scoring_reason_codes if engine_c_metrics is not None else (),
                risk_reason_codes=engine_c_metrics.risk_reason_codes if engine_c_metrics is not None else (),
            ),
            collect_engine_metrics(
                engine_id="engine_d",
                emitted_signals=1 if engine_d_metrics is not None and engine_d_metrics.emitted_signal else 0,
                net_edge_bps=engine_d_metrics.expected_edge_bps if engine_d_metrics is not None else 5.2,
                expected_cost_bps=engine_d_metrics.expected_cost_bps if engine_d_metrics is not None else 2.1,
                ce_expected=engine_d_metrics.ce_expected if engine_d_metrics is not None else 0.00028,
                scoring_summary=engine_d_metrics.scoring_summary if engine_d_metrics is not None else "",
                risk_summary=engine_d_metrics.risk_summary if engine_d_metrics is not None else "",
                scoring_reason_codes=engine_d_metrics.scoring_reason_codes if engine_d_metrics is not None else (),
                risk_reason_codes=engine_d_metrics.risk_reason_codes if engine_d_metrics is not None else (),
            ),
        ),
        pairs=(
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.HEALTHY,
                freshness_ms=900,
                backlog_depth=queue_backlog,
            ),
            collect_pair_metrics(
                pair="ETHUSDT",
                health=PairHealthLevel.STALE if active_alert_count else PairHealthLevel.HEALTHY,
                freshness_ms=9_000 if active_alert_count else 1_100,
                backlog_depth=queue_backlog,
            ),
        ),
    )
    active_modules = tuple(
        module.module_name for module in get_modules_for_profile(ProfileId.COMPLETE)
    )
    build14_projection = _build14_projection(snapshot)
    return build_technical_dashboard_payload(
        snapshot,
        active_modules=active_modules,
        active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        build9x_projection=Build9XProjection(
            status="info",
            diagnostics_count=0,
            diagnostics_summary="No diagnostic report",
            open_hypotheses=0,
            total_hypotheses=0,
            near_miss_count=0,
            replay_candidate_count=0,
            memory_record_count=1,
            latest_memory_summary="Governed replay candidate prepared for Shadow.",
            review_export_ready=True,
            review_export_ref="exports/local_replay_shadow_review.md",
        ),
        runtime_hook_bridge_projections=build_runtime_hook_bridge_projections(
            compiled_registry_state_dir=output_dir
        ),
        replay_projection=replay_projection,
        build14_projection=build14_projection,
    )


def _day_candidate_payload(
    payload: object,
    *,
    absolute_day_number: int,
    timestamp_ms: int,
) -> object:
    return payload.model_copy(
        update={
            "correlation_id": f"{payload.correlation_id}:day-{absolute_day_number}",
            "timestamp_ms": timestamp_ms,
        }
    )


def _next_shadow_day_timestamp_ms(
    *,
    template_timestamp_ms: int,
    session_date: date,
) -> int:
    template_dt = datetime.fromtimestamp(template_timestamp_ms / 1000.0, tz=timezone.utc)
    resolved = datetime.combine(
        session_date,
        time_of_day(
            hour=template_dt.hour,
            minute=template_dt.minute,
            second=template_dt.second,
            microsecond=template_dt.microsecond,
            tzinfo=timezone.utc,
        ),
    )
    return int(resolved.timestamp() * 1000)


def _resolve_base_session_date(
    *,
    requested_session_date: str | None,
    governed_session_date: str | None,
    last_session_date: date | None,
    run_manifest: ReplayRunManifest | None,
    candidate_payload_timestamp_ms: int,
) -> date:
    if requested_session_date:
        return date.fromisoformat(requested_session_date)
    if governed_session_date:
        return date.fromisoformat(governed_session_date)
    if last_session_date is not None:
        return last_session_date + timedelta(days=1)
    if run_manifest is not None:
        return datetime.fromtimestamp(
            run_manifest.start_timestamp_ms / 1000.0, tz=timezone.utc
        ).date()
    return datetime.fromtimestamp(
        candidate_payload_timestamp_ms / 1000.0, tz=timezone.utc
    ).date()


def _resolve_import_governance_reference_date(
    *,
    governed_session_date: str | None,
    run_manifest: ReplayRunManifest | None,
    fallback_timestamp_ms: int,
) -> date:
    if governed_session_date:
        return date.fromisoformat(governed_session_date)
    if run_manifest is not None:
        return datetime.fromtimestamp(
            run_manifest.end_timestamp_ms / 1000.0,
            tz=timezone.utc,
        ).date()
    return datetime.fromtimestamp(
        fallback_timestamp_ms / 1000.0,
        tz=timezone.utc,
    ).date()


def export_local_replay_shadow_run(
    output_dir: Path,
    *,
    export_dir: Path | None = None,
    shadow_days: int = 1,
    session_date: str | None = None,
) -> LocalReplayShadowArtifacts:
    """Materialize the governed LOCAL_REPLAY -> import VPS -> SHADOW chain."""

    output_dir.mkdir(parents=True, exist_ok=True)
    shadow_days_dir_path = output_dir / "shadow_days"
    shadow_days_dir_path.mkdir(parents=True, exist_ok=True)
    governed_slot = (
        ShadowDailyOrchestrator(output_dir).build_slot_from_export_dir(export_dir)
        if export_dir is not None
        else None
    )
    if (
        export_dir is not None
        and session_date is not None
        and governed_slot is not None
        and governed_slot.session_date != session_date
    ):
        raise ValueError(
            "Explicit session_date does not match governed export metadata: "
            f"{session_date} != {governed_slot.session_date}"
        )
    export_discovery = (
        discover_local_replay_export(export_dir)
        if export_dir is not None
        else None
    )
    run_manifest = export_discovery.run_manifest if export_discovery is not None else None
    run_manifest_json_path: Path | None = None
    correlation_id = (
        run_manifest.run_id
        if run_manifest is not None
        else "corr-local-replay-shadow-demo"
    )
    payload_refs = (
        export_discovery.payload_bundle
        if export_discovery is not None
        else _demo_payload_refs(correlation_id)
    )
    replay_metrics_payload = _load_json_payload_from_ref(payload_refs.replay_metrics_ref)
    if run_manifest is not None and export_dir is not None:
        run_manifest_json_path = output_dir / "local_replay_shadow.run_manifest.json"
        run_manifest_json_path.write_text(
            run_manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

    if run_manifest is not None:
        dataset_ref = None
        clock_ref = None
    else:
        dataset_ref = ReplayDatasetRef(
            dataset_id="dataset-local-replay-shadow-demo",
            pair_scope=("BTCUSDT", "ETHUSDT"),
            record_count=2,
        )
        clock_ref = ReplayClockRef(
            clock_id="clock-local-replay-shadow-demo",
            mode="historical",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_060_000,
            tick_count=60,
        )
    import_governance_reference_date = _resolve_import_governance_reference_date(
        governed_session_date=(
            governed_slot.session_date if governed_slot is not None else None
        ),
        run_manifest=run_manifest,
        fallback_timestamp_ms=(
            run_manifest.end_timestamp_ms
            if run_manifest is not None
            else clock_ref.end_timestamp_ms
        ),
    )
    if export_dir is not None:
        import_context = build_import_context_from_export_dir(
            export_dir,
            lifecycle_policy=_SHADOW_IMPORT_LIFECYCLE_POLICY,
            training_end=import_governance_reference_date,
            governance_reference_date=import_governance_reference_date,
            drift_score_threshold=_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD,
        )
        replay_plan = import_context.replay_plan
        import_request = import_context.import_request
    else:
        replay_request = LocalReplayRequest(
            correlation_id=correlation_id,
            profile=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v1.0.r1",
            replay_reason="Governed local replay candidate prepared for Shadow validation.",
        )
        replay_plan = LocalReplayOrchestrator.prepare_bundle(
            replay_request,
            artifact_id="artifact-local-replay-shadow-demo",
            strategy_version="a.v1.0",
            payload_refs=payload_refs.payload_refs,
            dataset_ref=dataset_ref,
            clock_ref=clock_ref,
            candidate_ids=("candidate:corr-local-replay-shadow-demo",),
            review_export_ref=payload_refs.review_export_ref,
            feature_bridge_ref=payload_refs.feature_bridge_ref,
            parity_diagnostics_ref=payload_refs.parity_diagnostics_ref,
            replay_metrics_ref=payload_refs.replay_metrics_ref,
            replay_dtr_ref=payload_refs.replay_dtr_ref,
            notes="Governed local replay export path for LOCAL_REPLAY -> VPS import -> SHADOW. demo metadata",
        )
        replay_plan = replay_plan.model_copy(
            update={
                "bundle": replay_plan.bundle.model_copy(
                    update={
                        "manifest": replay_plan.bundle.manifest.model_copy(
                            update={
                                "activation_stage": ArtifactActivationStage.SHADOW_READY,
                            }
                        )
                    }
                )
            }
        )
        import_context = build_import_context_from_replay_plan(
            replay_plan,
            payload_bundle=payload_refs,
            lifecycle_policy=_SHADOW_IMPORT_LIFECYCLE_POLICY,
            training_end=import_governance_reference_date,
            governance_reference_date=import_governance_reference_date,
            drift_score_threshold=_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD,
        )
        import_request = import_context.import_request
    replay_plan_json_path = output_dir / "local_replay_shadow.replay_plan.json"
    replay_plan_json_path.write_text(
        replay_plan.model_dump_json(indent=2),
        encoding="utf-8",
    )

    local_replay_recorder = LocalReplayEvidenceRecorder(
        config=LocalReplayEvidenceRecorderConfig(
            state_dir=output_dir,
            persist_state=True,
            state_filename="local_replay_shadow.local_replay_evidence.state.json",
        )
    )
    local_replay_recorder.load_execution_plan(replay_plan)
    local_replay_recorder.mark_payloads_generated(replay_plan.bundle.payload_refs)
    local_replay_evidence = local_replay_recorder.build_evidence()
    local_replay_evidence_json_path = output_dir / "local_replay_shadow.local_replay_evidence.json"
    local_replay_evidence_json_path.write_text(
        local_replay_evidence.model_dump_json(indent=2),
        encoding="utf-8",
    )

    upload_context = build_upload_context_from_replay_import_context(
        import_context,
        local_replay_evidence=local_replay_evidence,
        signature_envelope=_shadow_upload_signature_envelope(),
        uploaded_by="local_replay_shadow_runner",
        upload_context=ArtifactUploadContext.LOCAL_LAB,
        governance_reference_date=import_governance_reference_date,
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope=(
            "shadow_runner:export_dir"
            if export_dir is not None
            else "shadow_runner:demo"
        ),
        lifecycle_policy=_SHADOW_IMPORT_LIFECYCLE_POLICY,
        drift_score_threshold=_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD,
        proof_summary=_shadow_upload_proof_summary(),
        distilled_logic_format=ArtifactLogicFormat.THRESHOLD_JSON,
        covariance_shrinkage_matrix_ref="matrix_ref:local_replay_shadow",
    )
    upload_request = upload_context.upload_request
    import_request = upload_context.import_request
    import_decision = validate_import_request(import_request)
    upload_decision = build_artifact_upload_decision(upload_request, import_decision)
    upload_request_json_path = output_dir / "local_replay_shadow.upload_request.json"
    upload_decision_json_path = output_dir / "local_replay_shadow.upload_decision.json"
    upload_request_json_path.write_text(
        upload_request.model_dump_json(indent=2),
        encoding="utf-8",
    )
    upload_decision_json_path.write_text(
        upload_decision.model_dump_json(indent=2),
        encoding="utf-8",
    )
    import_summary = summarize_import_request(
        import_request,
        import_decision,
    )
    import_summary_json_path = output_dir / "local_replay_shadow.import_summary.json"
    import_summary_json_path.write_text(
        import_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )

    replay_projection = _build_replay_projection(import_summary)
    engine_runtime_evidence = _run_engine_shadow_evaluations()
    engine_shadow_evidence_json_path = output_dir / "local_replay_shadow.engine_shadow_evidence.json"
    engine_shadow_evidence_json_path.write_text(
        json.dumps(
            [
                {
                    "component_id": evidence.component_id,
                    "pair": evidence.pair,
                    "runtime_status": evidence.runtime_status,
                    "emitted_signal": evidence.emitted_signal,
                    "verdict": evidence.verdict.value,
                    "evidence_summary": evidence.evidence_summary,
                    "expected_cost_bps": evidence.expected_cost_bps,
                    "expected_edge_bps": evidence.expected_edge_bps,
                    "ce_expected": evidence.ce_expected,
                    "scoring_summary": evidence.scoring_summary,
                    "risk_summary": evidence.risk_summary,
                    "scoring_reason_codes": evidence.scoring_reason_codes,
                    "risk_reason_codes": evidence.risk_reason_codes,
                    "details": evidence.details,
                }
                for evidence in engine_runtime_evidence
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    baseline_payload = _build_demo_payload(
        correlation_id="corr-local-replay-shadow-demo:baseline",
        ce_net=0.0012,
        dtr_coverage=0.87,
        cra_sterilization_rate=0.08,
        active_alert_count=0,
        queue_backlog=8,
        output_dir=output_dir,
        replay_projection=replay_projection,
    )
    candidate_payload = _build_demo_payload(
        correlation_id="corr-local-replay-shadow-demo:candidate",
        ce_net=0.0010,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        active_alert_count=1,
        queue_backlog=10,
        output_dir=output_dir,
        replay_projection=replay_projection,
        engine_runtime_evidence=engine_runtime_evidence,
    )
    baseline_payload_json_path = output_dir / "local_replay_shadow.baseline_payload.json"
    candidate_payload_json_path = output_dir / "local_replay_shadow.candidate_payload.json"
    baseline_payload_json_path.write_text(
        baseline_payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    candidate_payload_json_path.write_text(
        candidate_payload.model_dump_json(indent=2),
        encoding="utf-8",
    )

    shadow_recorder = ShadowRuntimeEvidenceRecorder(
        local_replay_evidence=local_replay_evidence,
        config=ShadowRuntimeEvidenceRecorderConfig(
            state_dir=output_dir,
            persist_state=True,
            state_filename="local_replay_shadow.shadow_runtime_evidence.state.json",
        ),
    )
    shadow_recorder.mark_runtime_source("recorded_replay")
    shadow_recorder.mark_config_loaded("config:complete.shadow.official")
    shadow_recorder.mark_shadow_dtr_persisted("shadow_dtr:corr-local-replay-shadow-demo")
    shadow_recorder.record_event_loop_tick(1_700_000_000_000)
    shadow_recorder.record_event_loop_tick(1_700_086_400_000)
    shadow_runtime_evidence = shadow_recorder.build_evidence()
    shadow_runtime_evidence_json_path = output_dir / "local_replay_shadow.shadow_runtime_evidence.json"
    shadow_runtime_evidence_json_path.write_text(
        shadow_runtime_evidence.model_dump_json(indent=2),
        encoding="utf-8",
    )

    provisional_shadow_input = build_shadow_input_from_payloads(
        baseline_payload,
        candidate_payload,
        truth_ref="shadow_truth:local_replay_shadow_demo",
        validation_ref=f"shadow_validation:{import_summary.artifact_id}",
        component_assessments=_build_component_assessments(engine_runtime_evidence),
        shadow_days_completed=30,
        shadow_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
        runtime_evidence=shadow_runtime_evidence,
    )
    provisional_shadow_summary = run_shadow_validation(
        provisional_shadow_input,
        run_id="local-replay-shadow-demo-run",
    )
    shadow_counter = ShadowDayCounter(state_dir=output_dir, profile=ShadowProfile.COMPLETE)
    shadow_registry = ShadowSessionRegistry(state_dir=output_dir)
    _recover_shadow_state_from_artifacts(
        output_dir,
        shadow_counter=shadow_counter,
        shadow_registry=shadow_registry,
    )
    status_before_run = shadow_counter.get_status()
    starting_consecutive_days = status_before_run.consecutive_days
    base_session_date = _resolve_base_session_date(
        requested_session_date=session_date,
        governed_session_date=(
            governed_slot.session_date if governed_slot is not None else None
        ),
        last_session_date=shadow_registry.last_session_date(),
        run_manifest=run_manifest,
        candidate_payload_timestamp_ms=candidate_payload.timestamp_ms,
    )
    planned_session_dates = tuple(
        (base_session_date + timedelta(days=day_index)).isoformat()
        for day_index in range(shadow_days)
    )
    shadow_registry.validate_session_dates(planned_session_dates)
    daily_record_paths: list[str] = []
    daily_session_dates: list[str] = []
    registry_entries: list[ShadowSessionEntry] = []
    shadow_day_record = None
    for day_index in range(shadow_days):
        absolute_day_number = starting_consecutive_days + day_index + 1
        current_session_date = date.fromisoformat(planned_session_dates[day_index])
        day_timestamp_ms = _next_shadow_day_timestamp_ms(
            template_timestamp_ms=candidate_payload.timestamp_ms,
            session_date=current_session_date,
        )
        day_payload = _day_candidate_payload(
            candidate_payload,
            absolute_day_number=absolute_day_number,
            timestamp_ms=day_timestamp_ms,
        )
        shadow_day_metrics = build_shadow_daily_metrics_summary(
            day_payload,
            provisional_shadow_summary,
            capital_simulated_usdt=10_000.0,
            replay_metrics_payload=replay_metrics_payload,
            hard_block_rate=0.0,
            phantom_trade_count=0,
            operator_actions_logged=True,
            ui_locked=True,
            go_no_go_rendered=True,
        )
        shadow_day_record = shadow_counter.record_shadow_day(
            passed_all_gates=provisional_shadow_summary.decision.accepted,
            metrics_summary=shadow_day_metrics,
            now=day_payload.timestamp_ms / 1000.0,
        )
        day_record_path = (
            shadow_days_dir_path / f"local_replay_shadow.day_{absolute_day_number:04d}.json"
        )
        day_record_path.write_text(
            shadow_day_record.model_dump_json(indent=2),
            encoding="utf-8",
        )
        daily_record_paths.append(str(day_record_path))
        daily_session_dates.append(current_session_date.isoformat())
        if shadow_day_record.passed_all_gates:
            registry_entries.append(
                ShadowSessionEntry(
                    session_date=current_session_date.isoformat(),
                    counter_day_number=shadow_day_record.day_number,
                    correlation_id=day_payload.correlation_id,
                    run_id=provisional_shadow_summary.run_id,
                    artifact_id=import_summary.artifact_id,
                    lineage_version=import_summary.lineage_version,
                    day_record_ref=str(day_record_path),
                    export_dir_ref=str(export_dir.resolve()) if export_dir is not None else "",
                )
            )
    assert shadow_day_record is not None
    if registry_entries:
        shadow_registry.append_entries(tuple(registry_entries))
    else:
        shadow_registry.ensure_persisted()
    shadow_day_record_json_path = output_dir / "local_replay_shadow.shadow_day_record.json"
    shadow_day_record_json_path.write_text(
        shadow_day_record.model_dump_json(indent=2),
        encoding="utf-8",
    )
    shadow_report = shadow_counter.generate_report()
    shadow_report_json_path = output_dir / "local_replay_shadow.shadow_report.json"
    shadow_report_json_path.write_text(
        json.dumps(shadow_report, indent=2),
        encoding="utf-8",
    )
    shadow_input = build_shadow_input_from_payloads(
        baseline_payload,
        candidate_payload,
        truth_ref="shadow_truth:local_replay_shadow_demo",
        validation_ref=f"shadow_validation:{import_summary.artifact_id}",
        component_assessments=_build_component_assessments(engine_runtime_evidence),
        shadow_days_completed=shadow_report["consecutive_days"],
        shadow_report_ready=shadow_report["shadow_report_ready"],
        inter_engine_comparison_ready=shadow_report["inter_engine_comparison_ready"],
        build14_contribution_ready=shadow_report["build14_contribution_ready"],
        runtime_evidence=shadow_runtime_evidence,
    )
    shadow_summary = run_shadow_validation(
        shadow_input,
        run_id="local-replay-shadow-demo-run",
    )
    shadow_input_json_path = output_dir / "local_replay_shadow.shadow_input.json"
    shadow_input_json_path.write_text(
        shadow_input.model_dump_json(indent=2),
        encoding="utf-8",
    )
    shadow_summary_json_path = output_dir / "local_replay_shadow.shadow_summary.json"
    shadow_summary_json_path.write_text(
        shadow_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    shadow_session_summary_json_path = (
        output_dir / "local_replay_shadow.shadow_session_summary.json"
    )
    shadow_session_summary_json_path.write_text(
        json.dumps(
            {
                "requested_shadow_days": shadow_days,
                "recorded_shadow_days_this_run": shadow_days,
                "session_resumed": starting_consecutive_days > 0,
                "starting_consecutive_days": starting_consecutive_days,
                "base_session_date": base_session_date.isoformat(),
                "session_dates": daily_session_dates,
                "consecutive_days": shadow_report["consecutive_days"],
                "remaining_days": shadow_report["remaining_days"],
                "shadow_report_ready": shadow_report["shadow_report_ready"],
                "promotion_gate_passed": (
                    shadow_report["consecutive_days"] >= shadow_report["required_days"]
                    and shadow_report["shadow_report_ready"]
                ),
                "daily_record_paths": daily_record_paths,
                "registry_path": str(shadow_registry.state_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return LocalReplayShadowArtifacts(
        run_manifest_json_path=run_manifest_json_path,
        replay_plan_json_path=replay_plan_json_path,
        import_summary_json_path=import_summary_json_path,
        local_replay_evidence_json_path=local_replay_evidence_json_path,
        baseline_payload_json_path=baseline_payload_json_path,
        candidate_payload_json_path=candidate_payload_json_path,
        engine_shadow_evidence_json_path=engine_shadow_evidence_json_path,
        shadow_input_json_path=shadow_input_json_path,
        shadow_runtime_evidence_json_path=shadow_runtime_evidence_json_path,
        shadow_summary_json_path=shadow_summary_json_path,
        shadow_day_record_json_path=shadow_day_record_json_path,
        shadow_report_json_path=shadow_report_json_path,
        shadow_days_dir_path=shadow_days_dir_path,
        shadow_session_summary_json_path=shadow_session_summary_json_path,
        shadow_session_registry_json_path=shadow_registry.state_path,
        upload_request_json_path=upload_request_json_path,
        upload_decision_json_path=upload_decision_json_path,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the governed LOCAL_REPLAY -> SHADOW demo runner."""

    _configure_stdio()
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a governed demo run for the LOCAL_REPLAY -> VPS import -> SHADOW chain."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "local_replay_shadow",
        help="Directory where the governed run artifacts will be written.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help=(
            "Optional directory containing real local export files "
            "(review_export, feature_bridge, parity_diagnostics, replay_metrics, replay_dtr)."
        ),
    )
    parser.add_argument(
        "--shadow-days",
        type=int,
        default=1,
        help=(
            "Number of governed Shadow day records to materialize in this run. "
            "Each recorded day stays within the 24h no-reset rule."
        ),
    )
    parser.add_argument(
        "--session-date",
        type=str,
        default=None,
        help=(
            "Optional ISO date (YYYY-MM-DD) used as the first governed Shadow day "
            "for this invocation. If omitted, the runner resumes from the next day."
        ),
    )
    args = parser.parse_args(argv)

    artifacts = export_local_replay_shadow_run(
        args.output_dir,
        export_dir=args.export_dir,
        shadow_days=max(1, args.shadow_days),
        session_date=args.session_date,
    )
    if artifacts.run_manifest_json_path is not None:
        print(f"Run manifest JSON: {artifacts.run_manifest_json_path}")
    print(f"Replay plan JSON: {artifacts.replay_plan_json_path}")
    print(f"Import summary JSON: {artifacts.import_summary_json_path}")
    print(f"Local replay evidence JSON: {artifacts.local_replay_evidence_json_path}")
    print(f"Baseline payload JSON: {artifacts.baseline_payload_json_path}")
    print(f"Candidate payload JSON: {artifacts.candidate_payload_json_path}")
    print(f"Shadow input JSON: {artifacts.shadow_input_json_path}")
    print(f"Shadow runtime evidence JSON: {artifacts.shadow_runtime_evidence_json_path}")
    print(f"Shadow summary JSON: {artifacts.shadow_summary_json_path}")
    print(f"Shadow day record JSON: {artifacts.shadow_day_record_json_path}")
    print(f"Shadow report JSON: {artifacts.shadow_report_json_path}")
    print(f"Shadow days dir: {artifacts.shadow_days_dir_path}")
    print(f"Shadow session summary JSON: {artifacts.shadow_session_summary_json_path}")
    print(f"Shadow session registry JSON: {artifacts.shadow_session_registry_json_path}")
    print(
        "Inspect the JSON sidecars to review the governed LOCAL_REPLAY -> VPS import -> SHADOW chain."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
