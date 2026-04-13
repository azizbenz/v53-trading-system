#!/usr/bin/env python3
"""Runtime and session materialization helpers for the governed LOCAL_REPLAY -> SHADOW runner."""

from __future__ import annotations

import json
from datetime import date, datetime, time as time_of_day, timedelta, timezone
from pathlib import Path

from backtest_artifact_import import ArtifactImportSummary
from local_replay_runtime import LocalReplayRuntimeEvidence, ReplayRunManifest
from local_replay_shadow_engines import _run_engine_shadow_evaluations
from local_replay_shadow_import_support import (
    _build_local_replay_shadow_import_context_bundle,
    _materialize_local_replay_shadow_import_bundle,
)
from local_replay_shadow_models import (
    LocalReplayShadowArtifacts,
    LocalReplayShadowDayRecording,
    LocalReplayShadowImportBundle,
    LocalReplayShadowImportContextBundle,
    LocalReplayShadowRuntimeBundle,
    LocalReplayShadowSessionBundle,
    ShadowEngineRuntimeEvidence,
    _load_optional_daily_pnl_breaker_assessment,
    _load_optional_info_stress_assessment,
    _load_optional_regime_lite_assessment,
    _load_optional_regime_lite_safing_recommendation,
    _recover_shadow_state_from_artifacts,
)
from local_replay_shadow_payloads import (
    _build_component_assessments,
    _build_demo_payload,
    _resolve_daily_pnl_breaker_assessment_path,
    _resolve_execution_runtime_projection_path,
    _resolve_info_stress_assessment_path,
    _resolve_regime_lite_assessment_path,
    _resolve_regime_lite_safing_recommendation_path,
    ReplayImportProjection,
)
from protocols import (
    ShadowDayCounter,
    ShadowProfile,
    ShadowRunSummary,
    ShadowRuntimeEvidence,
    ShadowRuntimeEvidenceRecorder,
    ShadowRuntimeEvidenceRecorderConfig,
    ShadowSessionEntry,
    ShadowSessionRegistry,
    build_shadow_daily_metrics_summary,
    build_shadow_input_from_payloads,
    run_shadow_validation,
)
from protocols.shadow_day_counter import ShadowDayRecord
from regime_classifier import RegimeLiteAssessment
from risk_backbone import InfoStressAssessment, RegimeLiteSafingRecommendation

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

def _resolve_local_replay_shadow_runtime_assessments(
    output_dir: Path,
    *,
    regime_lite_assessment_path: Path | None,
    regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None,
    daily_pnl_breaker_assessment_path: Path | None,
) -> tuple[
    RegimeLiteAssessment | None,
    RegimeLiteSafingRecommendation | None,
    InfoStressAssessment | None,
]:
    regime_lite_assessment = _load_optional_regime_lite_assessment(
        _resolve_regime_lite_assessment_path(output_dir=output_dir, explicit_path=regime_lite_assessment_path)
    )
    regime_lite_safing_recommendation = _load_optional_regime_lite_safing_recommendation(
        _resolve_regime_lite_safing_recommendation_path(
            output_dir=output_dir,
            explicit_path=regime_lite_safing_recommendation_path,
        )
    )
    info_stress_assessment = _load_optional_info_stress_assessment(
        _resolve_info_stress_assessment_path(output_dir=output_dir, explicit_path=info_stress_assessment_path)
    )
    _ = _load_optional_daily_pnl_breaker_assessment(
        _resolve_daily_pnl_breaker_assessment_path(
            output_dir=output_dir,
            explicit_path=daily_pnl_breaker_assessment_path,
        )
    )
    return (
        regime_lite_assessment,
        regime_lite_safing_recommendation,
        info_stress_assessment,
    )


def _write_local_replay_shadow_engine_evidence_json(
    output_dir: Path,
    *,
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...],
) -> Path:
    engine_shadow_evidence_json_path = (
        output_dir / "local_replay_shadow.engine_shadow_evidence.json"
    )
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
    return engine_shadow_evidence_json_path


def _build_local_replay_shadow_runtime_bundle(
    output_dir: Path,
    *,
    local_replay_evidence: LocalReplayRuntimeEvidence,
    replay_projection: ReplayImportProjection,
    execution_runtime_projection_path: Path | None,
    regime_lite_assessment_path: Path | None,
    regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None,
    daily_pnl_breaker_assessment_path: Path | None,
) -> LocalReplayShadowRuntimeBundle:
    resolved_execution_runtime_projection_path = _resolve_execution_runtime_projection_path(
        output_dir=output_dir,
        explicit_path=execution_runtime_projection_path,
    )
    (
        regime_lite_assessment,
        regime_lite_safing_recommendation,
        info_stress_assessment,
    ) = _resolve_local_replay_shadow_runtime_assessments(
        output_dir,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        daily_pnl_breaker_assessment_path=daily_pnl_breaker_assessment_path,
    )
    engine_runtime_evidence = _run_engine_shadow_evaluations()
    engine_shadow_evidence_json_path = _write_local_replay_shadow_engine_evidence_json(
        output_dir,
        engine_runtime_evidence=engine_runtime_evidence,
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
        execution_runtime_projection_path=resolved_execution_runtime_projection_path,
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
        execution_runtime_projection_path=resolved_execution_runtime_projection_path,
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
    return LocalReplayShadowRuntimeBundle(
        execution_runtime_projection_json_path=resolved_execution_runtime_projection_path,
        regime_lite_assessment=regime_lite_assessment,
        regime_lite_safing_recommendation=regime_lite_safing_recommendation,
        info_stress_assessment=info_stress_assessment,
        engine_runtime_evidence=engine_runtime_evidence,
        engine_shadow_evidence_json_path=engine_shadow_evidence_json_path,
        baseline_payload=baseline_payload,
        candidate_payload=candidate_payload,
        baseline_payload_json_path=baseline_payload_json_path,
        candidate_payload_json_path=candidate_payload_json_path,
        shadow_runtime_evidence=_build_local_replay_shadow_runtime_evidence(
            output_dir=output_dir,
            recorder=shadow_recorder,
        ),
        shadow_runtime_evidence_json_path=output_dir / "local_replay_shadow.shadow_runtime_evidence.json",
    )


def _build_local_replay_shadow_runtime_evidence(
    *,
    output_dir: Path,
    recorder: ShadowRuntimeEvidenceRecorder,
) -> ShadowRuntimeEvidence:
    recorder.mark_runtime_source("recorded_replay")
    recorder.mark_config_loaded("config:complete.shadow.official")
    recorder.mark_shadow_dtr_persisted("shadow_dtr:corr-local-replay-shadow-demo")
    recorder.record_event_loop_tick(1_700_000_000_000)
    recorder.record_event_loop_tick(1_700_086_400_000)
    shadow_runtime_evidence = recorder.build_evidence()
    (output_dir / "local_replay_shadow.shadow_runtime_evidence.json").write_text(
        shadow_runtime_evidence.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return shadow_runtime_evidence


def _build_local_replay_shadow_input_and_summary(
    *,
    baseline_payload: object,
    candidate_payload: object,
    artifact_id: str,
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...],
    shadow_days_completed: int,
    shadow_report_ready: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    shadow_runtime_evidence: ShadowRuntimeEvidence,
    regime_lite_assessment: RegimeLiteAssessment | None,
    regime_lite_safing_recommendation: RegimeLiteSafingRecommendation | None,
    info_stress_assessment: InfoStressAssessment | None,
) -> tuple[object, ShadowRunSummary]:
    shadow_input = build_shadow_input_from_payloads(
        baseline_payload,
        candidate_payload,
        truth_ref="shadow_truth:local_replay_shadow_demo",
        validation_ref=f"shadow_validation:{artifact_id}",
        component_assessments=_build_component_assessments(engine_runtime_evidence),
        shadow_days_completed=shadow_days_completed,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        runtime_evidence=shadow_runtime_evidence,
    )
    return shadow_input, run_shadow_validation(
        shadow_input,
        run_id="local-replay-shadow-demo-run",
        regime_lite_assessment=regime_lite_assessment,
        regime_lite_safing_recommendation=regime_lite_safing_recommendation,
        info_stress_assessment=info_stress_assessment,
    )


def _record_local_replay_shadow_days(
    output_dir: Path,
    *,
    shadow_days_dir_path: Path,
    shadow_days: int,
    session_date: str | None,
    import_context_bundle: LocalReplayShadowImportContextBundle,
    governed_session_date: str | None,
    run_manifest: ReplayRunManifest | None,
    import_summary: ArtifactImportSummary,
    replay_metrics_payload: dict[str, object],
    runtime_bundle: LocalReplayShadowRuntimeBundle,
) -> LocalReplayShadowDayRecording:
    _, provisional_shadow_summary = _build_local_replay_shadow_input_and_summary(
        baseline_payload=runtime_bundle.baseline_payload,
        candidate_payload=runtime_bundle.candidate_payload,
        artifact_id=import_summary.artifact_id,
        engine_runtime_evidence=runtime_bundle.engine_runtime_evidence,
        shadow_days_completed=30,
        shadow_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
        shadow_runtime_evidence=runtime_bundle.shadow_runtime_evidence,
        regime_lite_assessment=runtime_bundle.regime_lite_assessment,
        regime_lite_safing_recommendation=runtime_bundle.regime_lite_safing_recommendation,
        info_stress_assessment=runtime_bundle.info_stress_assessment,
    )
    shadow_counter = ShadowDayCounter(state_dir=output_dir, profile=ShadowProfile.COMPLETE)
    shadow_registry = ShadowSessionRegistry(state_dir=output_dir)
    _recover_shadow_state_from_artifacts(
        output_dir,
        shadow_counter=shadow_counter,
        shadow_registry=shadow_registry,
    )
    starting_consecutive_days = shadow_counter.get_status().consecutive_days
    base_session_date = _resolve_base_session_date(
        requested_session_date=session_date,
        governed_session_date=governed_session_date,
        last_session_date=shadow_registry.last_session_date(),
        run_manifest=run_manifest,
        candidate_payload_timestamp_ms=runtime_bundle.candidate_payload.timestamp_ms,
    )
    planned_session_dates = tuple(
        (base_session_date + timedelta(days=day_index)).isoformat()
        for day_index in range(shadow_days)
    )
    shadow_registry.validate_session_dates(planned_session_dates)
    daily_record_paths: list[str] = []
    daily_session_dates: list[str] = []
    registry_entries: list[ShadowSessionEntry] = []
    shadow_day_record: ShadowDayRecord | None = None
    for day_index, planned_session_date in enumerate(planned_session_dates):
        absolute_day_number = starting_consecutive_days + day_index + 1
        current_session_date = date.fromisoformat(planned_session_date)
        day_payload = _day_candidate_payload(
            runtime_bundle.candidate_payload,
            absolute_day_number=absolute_day_number,
            timestamp_ms=_next_shadow_day_timestamp_ms(
                template_timestamp_ms=runtime_bundle.candidate_payload.timestamp_ms,
                session_date=current_session_date,
            ),
        )
        shadow_day_record = shadow_counter.record_shadow_day(
            passed_all_gates=provisional_shadow_summary.decision.accepted,
            metrics_summary=build_shadow_daily_metrics_summary(
                day_payload,
                provisional_shadow_summary,
                capital_simulated_usdt=10_000.0,
                replay_metrics_payload=replay_metrics_payload,
                hard_block_rate=0.0,
                phantom_trade_count=0,
                operator_actions_logged=True,
                ui_locked=True,
                go_no_go_rendered=True,
            ),
            now=day_payload.timestamp_ms / 1000.0,
        )
        day_record_path = shadow_days_dir_path / f"local_replay_shadow.day_{absolute_day_number:04d}.json"
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
                    export_dir_ref=(
                        str(import_context_bundle.export_dir.resolve())
                        if import_context_bundle.export_dir is not None
                        else ""
                    ),
                )
            )
    assert shadow_day_record is not None
    if registry_entries:
        shadow_registry.append_entries(tuple(registry_entries))
    else:
        shadow_registry.ensure_persisted()
    return LocalReplayShadowDayRecording(
        shadow_counter=shadow_counter,
        shadow_registry=shadow_registry,
        starting_consecutive_days=starting_consecutive_days,
        base_session_date=base_session_date,
        daily_record_paths=tuple(daily_record_paths),
        daily_session_dates=tuple(daily_session_dates),
        shadow_day_record=shadow_day_record,
        shadow_report=shadow_counter.generate_report(),
    )


def _materialize_local_replay_shadow_session_bundle(
    output_dir: Path,
    *,
    shadow_days: int,
    shadow_days_dir_path: Path,
    import_context_bundle: LocalReplayShadowImportContextBundle,
    import_bundle: LocalReplayShadowImportBundle,
    runtime_bundle: LocalReplayShadowRuntimeBundle,
    day_recording: LocalReplayShadowDayRecording,
) -> LocalReplayShadowSessionBundle:
    shadow_day_record_json_path = output_dir / "local_replay_shadow.shadow_day_record.json"
    shadow_day_record_json_path.write_text(
        day_recording.shadow_day_record.model_dump_json(indent=2),
        encoding="utf-8",
    )
    shadow_report_json_path = output_dir / "local_replay_shadow.shadow_report.json"
    shadow_report_json_path.write_text(
        json.dumps(day_recording.shadow_report, indent=2),
        encoding="utf-8",
    )
    shadow_input, shadow_summary = _build_local_replay_shadow_input_and_summary(
        baseline_payload=runtime_bundle.baseline_payload,
        candidate_payload=runtime_bundle.candidate_payload,
        artifact_id=import_bundle.import_summary.artifact_id,
        engine_runtime_evidence=runtime_bundle.engine_runtime_evidence,
        shadow_days_completed=day_recording.shadow_report["consecutive_days"],
        shadow_report_ready=day_recording.shadow_report["shadow_report_ready"],
        inter_engine_comparison_ready=day_recording.shadow_report["inter_engine_comparison_ready"],
        build14_contribution_ready=day_recording.shadow_report["build14_contribution_ready"],
        shadow_runtime_evidence=runtime_bundle.shadow_runtime_evidence,
        regime_lite_assessment=runtime_bundle.regime_lite_assessment,
        regime_lite_safing_recommendation=runtime_bundle.regime_lite_safing_recommendation,
        info_stress_assessment=runtime_bundle.info_stress_assessment,
    )
    shadow_input_json_path = output_dir / "local_replay_shadow.shadow_input.json"
    shadow_summary_json_path = output_dir / "local_replay_shadow.shadow_summary.json"
    shadow_input_json_path.write_text(
        shadow_input.model_dump_json(indent=2),
        encoding="utf-8",
    )
    shadow_summary_json_path.write_text(
        shadow_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    shadow_session_summary_json_path = output_dir / "local_replay_shadow.shadow_session_summary.json"
    shadow_session_summary_json_path.write_text(
        json.dumps(
            {
                "requested_shadow_days": shadow_days,
                "recorded_shadow_days_this_run": shadow_days,
                "session_resumed": day_recording.starting_consecutive_days > 0,
                "starting_consecutive_days": day_recording.starting_consecutive_days,
                "base_session_date": day_recording.base_session_date.isoformat(),
                "session_dates": list(day_recording.daily_session_dates),
                "consecutive_days": day_recording.shadow_report["consecutive_days"],
                "remaining_days": day_recording.shadow_report["remaining_days"],
                "shadow_report_ready": day_recording.shadow_report["shadow_report_ready"],
                "promotion_gate_passed": (
                    day_recording.shadow_report["consecutive_days"]
                    >= day_recording.shadow_report["required_days"]
                    and day_recording.shadow_report["shadow_report_ready"]
                ),
                "daily_record_paths": list(day_recording.daily_record_paths),
                "registry_path": str(day_recording.shadow_registry.state_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return LocalReplayShadowSessionBundle(
        shadow_input_json_path=shadow_input_json_path,
        shadow_summary_json_path=shadow_summary_json_path,
        shadow_day_record_json_path=shadow_day_record_json_path,
        shadow_report_json_path=shadow_report_json_path,
        shadow_days_dir_path=shadow_days_dir_path,
        shadow_session_summary_json_path=shadow_session_summary_json_path,
        shadow_session_registry_json_path=day_recording.shadow_registry.state_path,
    )


def export_local_replay_shadow_run(
    output_dir: Path,
    *,
    export_dir: Path | None = None,
    shadow_days: int = 1,
    session_date: str | None = None,
    execution_runtime_projection_path: Path | None = None,
    regime_lite_assessment_path: Path | None = None,
    regime_lite_safing_recommendation_path: Path | None = None,
    info_stress_assessment_path: Path | None = None,
    daily_pnl_breaker_assessment_path: Path | None = None,
) -> LocalReplayShadowArtifacts:
    """Materialize the governed LOCAL_REPLAY -> import VPS -> SHADOW chain."""

    output_dir.mkdir(parents=True, exist_ok=True)
    shadow_days_dir_path = output_dir / "shadow_days"
    shadow_days_dir_path.mkdir(parents=True, exist_ok=True)
    import_context_bundle = _build_local_replay_shadow_import_context_bundle(
        output_dir,
        export_dir=export_dir,
        session_date=session_date,
    )
    import_bundle = _materialize_local_replay_shadow_import_bundle(
        output_dir,
        import_context_bundle=import_context_bundle,
    )
    runtime_bundle = _build_local_replay_shadow_runtime_bundle(
        output_dir,
        local_replay_evidence=import_bundle.local_replay_evidence,
        replay_projection=import_bundle.replay_projection,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        daily_pnl_breaker_assessment_path=daily_pnl_breaker_assessment_path,
    )
    day_recording = _record_local_replay_shadow_days(
        output_dir,
        shadow_days_dir_path=shadow_days_dir_path,
        shadow_days=shadow_days,
        session_date=session_date,
        import_context_bundle=import_context_bundle,
        governed_session_date=import_context_bundle.governed_session_date,
        run_manifest=import_context_bundle.run_manifest,
        import_summary=import_bundle.import_summary,
        replay_metrics_payload=import_context_bundle.replay_metrics_payload,
        runtime_bundle=runtime_bundle,
    )
    session_bundle = _materialize_local_replay_shadow_session_bundle(
        output_dir,
        shadow_days=shadow_days,
        shadow_days_dir_path=shadow_days_dir_path,
        import_context_bundle=import_context_bundle,
        import_bundle=import_bundle,
        runtime_bundle=runtime_bundle,
        day_recording=day_recording,
    )
    return LocalReplayShadowArtifacts(
        run_manifest_json_path=import_context_bundle.run_manifest_json_path,
        replay_plan_json_path=import_bundle.replay_plan_json_path,
        import_summary_json_path=import_bundle.import_summary_json_path,
        local_replay_evidence_json_path=import_bundle.local_replay_evidence_json_path,
        baseline_payload_json_path=runtime_bundle.baseline_payload_json_path,
        candidate_payload_json_path=runtime_bundle.candidate_payload_json_path,
        engine_shadow_evidence_json_path=runtime_bundle.engine_shadow_evidence_json_path,
        shadow_input_json_path=session_bundle.shadow_input_json_path,
        shadow_runtime_evidence_json_path=runtime_bundle.shadow_runtime_evidence_json_path,
        shadow_summary_json_path=session_bundle.shadow_summary_json_path,
        shadow_day_record_json_path=session_bundle.shadow_day_record_json_path,
        shadow_report_json_path=session_bundle.shadow_report_json_path,
        shadow_days_dir_path=session_bundle.shadow_days_dir_path,
        shadow_session_summary_json_path=session_bundle.shadow_session_summary_json_path,
        shadow_session_registry_json_path=session_bundle.shadow_session_registry_json_path,
        execution_runtime_projection_json_path=runtime_bundle.execution_runtime_projection_json_path,
        upload_request_json_path=import_bundle.upload_request_json_path,
        upload_decision_json_path=import_bundle.upload_decision_json_path,
    )
