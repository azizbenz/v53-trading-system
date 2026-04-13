#!/usr/bin/env python3
"""Support models and recovery helpers for the governed LOCAL_REPLAY -> SHADOW runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from backtest_artifact_import import (
    ArtifactImportSummary,
    ArtifactPayloadRefBundle,
    LocalReplayImportBuildContext,
    build_lab_fixture_signature_envelope,
)
from interface_contracts import ArtifactProofSummary, ArtifactSignatureEnvelope
from local_replay_runtime import LocalReplayRuntimeEvidence, ReplayExecutionPlan, ReplayRunManifest
from monitoring import ReplayImportProjection
from protocols import (
    ShadowComponentVerdict,
    ShadowDayCounter,
    ShadowProfile,
    ShadowSessionEntry,
    ShadowSessionRegistry,
    ShadowRuntimeEvidence,
)
from protocols.shadow_day_counter import ShadowDayRecord
from regime_classifier import RegimeLiteAssessment
from risk_backbone import InfoStressAssessment, RegimeLiteSafingRecommendation
from risk_backbone.loss_budgeter import DailyPnlBreakerAssessment

_RECOVERED_SHADOW_RUN_ID = "recovered:shadow_session_registry"

def _load_optional_regime_lite_assessment(
    path: Path | None,
) -> RegimeLiteAssessment | None:
    if path is None:
        return None
    return RegimeLiteAssessment.model_validate_json(path.read_text(encoding="utf-8"))


def _load_optional_regime_lite_safing_recommendation(
    path: Path | None,
) -> RegimeLiteSafingRecommendation | None:
    if path is None:
        return None
    return RegimeLiteSafingRecommendation.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def _load_optional_info_stress_assessment(
    path: Path | None,
) -> InfoStressAssessment | None:
    if path is None:
        return None
    return InfoStressAssessment.model_validate_json(path.read_text(encoding="utf-8"))


def _load_optional_daily_pnl_breaker_assessment(
    path: Path | None,
) -> DailyPnlBreakerAssessment | None:
    if path is None:
        return None
    return DailyPnlBreakerAssessment.model_validate_json(
        path.read_text(encoding="utf-8")
    )
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
    execution_runtime_projection_json_path: Path | None = None
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


@dataclass(frozen=True)
class LocalReplayShadowImportContextBundle:
    export_dir: Path | None
    governed_session_date: str | None
    import_governance_reference_date: date
    payload_refs: ArtifactPayloadRefBundle
    replay_metrics_payload: dict[str, object]
    run_manifest: ReplayRunManifest | None
    run_manifest_json_path: Path | None
    import_context: LocalReplayImportBuildContext


@dataclass(frozen=True)
class LocalReplayShadowImportBundle:
    replay_plan: ReplayExecutionPlan
    replay_plan_json_path: Path
    import_summary: ArtifactImportSummary
    import_summary_json_path: Path
    local_replay_evidence: LocalReplayRuntimeEvidence
    local_replay_evidence_json_path: Path
    replay_projection: ReplayImportProjection
    upload_request_json_path: Path
    upload_decision_json_path: Path


@dataclass(frozen=True)
class LocalReplayShadowRuntimeBundle:
    execution_runtime_projection_json_path: Path | None
    regime_lite_assessment: RegimeLiteAssessment | None
    regime_lite_safing_recommendation: RegimeLiteSafingRecommendation | None
    info_stress_assessment: InfoStressAssessment | None
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...]
    engine_shadow_evidence_json_path: Path
    baseline_payload: object
    candidate_payload: object
    baseline_payload_json_path: Path
    candidate_payload_json_path: Path
    shadow_runtime_evidence: ShadowRuntimeEvidence
    shadow_runtime_evidence_json_path: Path


@dataclass(frozen=True)
class LocalReplayShadowDayRecording:
    shadow_counter: ShadowDayCounter
    shadow_registry: ShadowSessionRegistry
    starting_consecutive_days: int
    base_session_date: date
    daily_record_paths: tuple[str, ...]
    daily_session_dates: tuple[str, ...]
    shadow_day_record: ShadowDayRecord
    shadow_report: dict[str, object]


@dataclass(frozen=True)
class LocalReplayShadowSessionBundle:
    shadow_input_json_path: Path
    shadow_summary_json_path: Path
    shadow_day_record_json_path: Path
    shadow_report_json_path: Path
    shadow_days_dir_path: Path
    shadow_session_summary_json_path: Path
    shadow_session_registry_json_path: Path
