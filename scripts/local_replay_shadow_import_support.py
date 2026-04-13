#!/usr/bin/env python3
"""Governed import-context helpers for the LOCAL_REPLAY -> SHADOW runner."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from backtest_artifact_import import (
    ArtifactPayloadRefBundle,
    ArtifactUploadContext,
    build_artifact_upload_decision,
    build_import_context_from_export_dir,
    build_import_context_from_replay_plan,
    build_upload_context_from_replay_import_context,
    discover_local_replay_export,
    summarize_import_request,
    validate_import_request,
)
from interface_contracts import (
    ArtifactActivationStage,
    ArtifactClass,
    ArtifactLifecyclePolicy,
    ArtifactLogicFormat,
    ProfileId,
    RuntimeMode,
    StrategyClassification,
)
from local_replay_runtime import (
    LocalReplayEvidenceRecorder,
    LocalReplayEvidenceRecorderConfig,
    LocalReplayOrchestrator,
    LocalReplayRequest,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayRunManifest,
)
from local_replay_shadow_models import (
    LocalReplayShadowImportBundle,
    LocalReplayShadowImportContextBundle,
    _shadow_upload_proof_summary,
    _shadow_upload_signature_envelope,
)
from local_replay_shadow_payloads import (
    _build_replay_projection,
    _demo_payload_refs,
    _load_json_payload_from_ref,
)
from protocols import ShadowDailyOrchestrator

_SHADOW_IMPORT_LIFECYCLE_POLICY = ArtifactLifecyclePolicy(
    ttl_max_days=30,
    rule_half_life_days=7,
)
_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD = 0.85

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


def _build_local_replay_shadow_import_context_bundle(
    output_dir: Path,
    *,
    export_dir: Path | None,
    session_date: str | None,
) -> LocalReplayShadowImportContextBundle:
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
    payload_refs = (
        export_discovery.payload_bundle
        if export_discovery is not None
        else _demo_payload_refs(
            run_manifest.run_id if run_manifest is not None else "corr-local-replay-shadow-demo"
        )
    )
    replay_metrics_payload = _load_json_payload_from_ref(payload_refs.replay_metrics_ref)
    run_manifest_json_path: Path | None = None
    if run_manifest is not None and export_dir is not None:
        run_manifest_json_path = output_dir / "local_replay_shadow.run_manifest.json"
        run_manifest_json_path.write_text(
            run_manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
    import_governance_reference_date = _resolve_import_governance_reference_date(
        governed_session_date=(governed_slot.session_date if governed_slot is not None else None),
        run_manifest=run_manifest,
        fallback_timestamp_ms=(
            run_manifest.end_timestamp_ms if run_manifest is not None else 1_700_000_060_000
        ),
    )
    import_context = _build_local_replay_shadow_import_context(
        payload_refs=payload_refs,
        export_dir=export_dir,
        run_manifest=run_manifest,
        import_governance_reference_date=import_governance_reference_date,
    )
    return LocalReplayShadowImportContextBundle(
        export_dir=export_dir,
        governed_session_date=(governed_slot.session_date if governed_slot is not None else None),
        import_governance_reference_date=import_governance_reference_date,
        payload_refs=payload_refs,
        replay_metrics_payload=replay_metrics_payload,
        run_manifest=run_manifest,
        run_manifest_json_path=run_manifest_json_path,
        import_context=import_context,
    )


def _build_local_replay_shadow_import_context(
    *,
    payload_refs: ArtifactPayloadRefBundle,
    export_dir: Path | None,
    run_manifest: ReplayRunManifest | None,
    import_governance_reference_date: date,
) -> LocalReplayImportBuildContext:
    if export_dir is not None:
        return build_import_context_from_export_dir(
            export_dir,
            lifecycle_policy=_SHADOW_IMPORT_LIFECYCLE_POLICY,
            training_end=import_governance_reference_date,
            governance_reference_date=import_governance_reference_date,
            drift_score_threshold=_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD,
        )
    correlation_id = (
        run_manifest.run_id
        if run_manifest is not None
        else "corr-local-replay-shadow-demo"
    )
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
        dataset_ref=ReplayDatasetRef(
            dataset_id="dataset-local-replay-shadow-demo",
            pair_scope=("BTCUSDT", "ETHUSDT"),
            record_count=2,
        ),
        clock_ref=ReplayClockRef(
            clock_id="clock-local-replay-shadow-demo",
            mode="historical",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_060_000,
            tick_count=60,
        ),
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
                        update={"activation_stage": ArtifactActivationStage.SHADOW_READY}
                    )
                }
            )
        }
    )
    return build_import_context_from_replay_plan(
        replay_plan,
        payload_bundle=payload_refs,
        lifecycle_policy=_SHADOW_IMPORT_LIFECYCLE_POLICY,
        training_end=import_governance_reference_date,
        governance_reference_date=import_governance_reference_date,
        drift_score_threshold=_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD,
    )


def _materialize_local_replay_shadow_import_bundle(
    output_dir: Path,
    *,
    import_context_bundle: LocalReplayShadowImportContextBundle,
) -> LocalReplayShadowImportBundle:
    replay_plan = import_context_bundle.import_context.replay_plan
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
    local_replay_evidence_json_path = (
        output_dir / "local_replay_shadow.local_replay_evidence.json"
    )
    local_replay_evidence_json_path.write_text(
        local_replay_evidence.model_dump_json(indent=2),
        encoding="utf-8",
    )
    upload_context = build_upload_context_from_replay_import_context(
        import_context_bundle.import_context,
        local_replay_evidence=local_replay_evidence,
        signature_envelope=_shadow_upload_signature_envelope(),
        uploaded_by="local_replay_shadow_runner",
        upload_context=ArtifactUploadContext.LOCAL_LAB,
        governance_reference_date=import_context_bundle.import_governance_reference_date,
        artifact_class=ArtifactClass.DAMAGE_REDUCER,
        artifact_scope=(
            "shadow_runner:export_dir"
            if import_context_bundle.run_manifest is not None
            else "shadow_runner:demo"
        ),
        lifecycle_policy=_SHADOW_IMPORT_LIFECYCLE_POLICY,
        drift_score_threshold=_SHADOW_IMPORT_DRIFT_SCORE_THRESHOLD,
        proof_summary=_shadow_upload_proof_summary(),
        distilled_logic_format=ArtifactLogicFormat.THRESHOLD_JSON,
        covariance_shrinkage_matrix_ref="matrix_ref:local_replay_shadow",
    )
    import_summary = summarize_import_request(
        upload_context.import_request,
        validate_import_request(upload_context.import_request),
    )
    upload_request_json_path = output_dir / "local_replay_shadow.upload_request.json"
    upload_decision_json_path = output_dir / "local_replay_shadow.upload_decision.json"
    import_summary_json_path = output_dir / "local_replay_shadow.import_summary.json"
    upload_request_json_path.write_text(
        upload_context.upload_request.model_dump_json(indent=2),
        encoding="utf-8",
    )
    upload_decision_json_path.write_text(
        build_artifact_upload_decision(
            upload_context.upload_request,
            validate_import_request(upload_context.import_request),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    import_summary_json_path.write_text(
        import_summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return LocalReplayShadowImportBundle(
        replay_plan=replay_plan,
        replay_plan_json_path=replay_plan_json_path,
        import_summary=import_summary,
        import_summary_json_path=import_summary_json_path,
        local_replay_evidence=local_replay_evidence,
        local_replay_evidence_json_path=local_replay_evidence_json_path,
        replay_projection=_build_replay_projection(import_summary),
        upload_request_json_path=upload_request_json_path,
        upload_decision_json_path=upload_decision_json_path,
    )
