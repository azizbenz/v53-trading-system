"""Cockpit visibility for the silver→gold timeframe propagation diff.

Patch 2026-05-15 (timeframe propagation audit) added 5 new fields to
``StrategyLadderGoldFeatureManifest`` so that operators can see exactly which
silver timeframes were materialized in gold and which were pruned, with the
explicit reason code. These tests pin the cockpit reader to that contract: a
gold manifest carrying the new fields must surface them on
``StrategyLadderBacktestSummary``; a legacy manifest without them must keep
rendering with empty defaults (no regression).
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from cockpit.action_support import (
    CockpitBacktestJobKind,
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
)
from cockpit.runtime_support import _read_strategy_ladder_summary
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A2,
    ensure_workflow_manifest,
    upsert_workflow_phase,
    workflow_manifest_path,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed_workflow(scratch: Path, *, label: str) -> tuple[Path, Path]:
    """Create a minimal workflow_root + phase_a2_root + manifest registration.

    Returns ``(workflow_root, phase_a2_root)``.
    """

    workflow_root = scratch / "workflows" / f"strategy_ladder_workflow-{label}"
    phase_a2_root = workflow_root / "phase_a2_data_factory"
    phase_a2_root.mkdir(parents=True, exist_ok=True)
    ensure_workflow_manifest(
        workflow_root=workflow_root,
        workflow_run_id=f"strategy_ladder_workflow-{label}",
        request_hash="workflow-hash",
        phase_id=PHASE_A2,
        pairs=("BTCUSDT",),
        start="2025-09-01",
        end="2025-09-02",
        ml_mode="ML_MODE_OFF",
        candidate_discovery_mode="BROAD_DIAGNOSTIC",
        engine_native_sample_size=10,
        engine_count=4,
        allow_broad_run=True,
        small_scope_enabled=False,
        full_scan_enabled=True,
        no_full_scan_enabled=False,
        silver_storage_mode_requested="jsonl",
        silver_storage_mode_effective="jsonl",
    )
    upsert_workflow_phase(
        workflow_root=workflow_root,
        workflow_run_id=f"strategy_ladder_workflow-{label}",
        phase_id=PHASE_A2,
        phase_run_id=f"phase-a2-{label}",
        phase_output_root=phase_a2_root,
        parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
        phase_status="PHASE_A2_DATA_FACTORY_READY",
        produced_artifact_refs={
            "phase_a2_data_factory_manifest": str(
                (phase_a2_root / "data_factory_manifest.json").resolve()
            )
        },
    )
    _write_json(
        phase_a2_root / "data_factory_manifest.json",
        {
            "data_factory_status": "DATA_FACTORY_READY",
            "raw_source_status": "RAW_SOURCE_READY",
            "pair_universe_status": "PAIR_UNIVERSE_READY",
            "silver_index_status": "SILVER_INDEX_READY",
            "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
        },
    )
    return workflow_root, phase_a2_root


def _build_job_record(
    scratch: Path, *, workflow_root: Path, phase_a2_root: Path, label: str
) -> CockpitBacktestJobRecord:
    return CockpitBacktestJobRecord(
        job_id=f"runner-{label}",
        correlation_id=f"corr-{label}",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
        status=CockpitBacktestJobStatus.JOB_COMPLETED,
        requested_at_iso="2026-05-15T10:00:00+00:00",
        started_at_iso="2026-05-15T10:00:01+00:00",
        finished_at_iso="2026-05-15T10:00:02+00:00",
        output_root=str(phase_a2_root),
        record_path=str(scratch / f"job_{label}.json"),
        stdout_log_path=str(scratch / f"runner_{label}.log"),
        command=("python", "stub.py"),
        phase_id=PHASE_A2,
        workflow_run_id=f"strategy_ladder_workflow-{label}",
        phase_run_id=f"phase-a2-{label}",
        parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
        request_hash="workflow-hash",
    )


def test_cockpit_surfaces_timeframe_propagation_fields_when_manifest_has_them() -> None:
    """Gold manifest with the new fields must populate the cockpit summary."""

    scratch = _scratch_dir("cockpit_timeframe_propagation_present")
    try:
        workflow_root, phase_a2_root = _seed_workflow(scratch, label="present")
        _write_json(
            phase_a2_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 580,
                "feature_groups_declared": ["ofi_features"],
                "feature_groups_generated": ["ofi_features"],
                "feature_groups_ready": ["ofi_features"],
                "silver_timeframes_detected": ["1m", "5m", "10m", "15m"],
                "gold_timeframes_generated": ["1m", "5m"],
                "timeframes_pruned": ["10m", "15m"],
                "pruning_reason_by_timeframe": {
                    "10m": "TIMEFRAME_PRUNED_NOT_REQUESTED",
                    "15m": "TIMEFRAME_PRUNED_NOT_REQUESTED",
                },
                "timeframe_feature_row_count": {"1m": 400, "5m": 180},
                "blocker_codes": ["TIMEFRAME_PRUNED_NOT_REQUESTED"],
            },
        )

        summary = _read_strategy_ladder_summary(
            (_build_job_record(scratch, workflow_root=workflow_root, phase_a2_root=phase_a2_root, label="present"),)
        )

        assert summary.silver_timeframes_detected == ("1m", "5m", "10m", "15m")
        assert summary.gold_timeframes_generated == ("1m", "5m")
        assert summary.timeframes_pruned == ("10m", "15m")
        assert summary.pruning_reason_by_timeframe == {
            "10m": "TIMEFRAME_PRUNED_NOT_REQUESTED",
            "15m": "TIMEFRAME_PRUNED_NOT_REQUESTED",
        }
        assert summary.timeframe_feature_row_count == {"1m": 400, "5m": 180}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_cockpit_handles_legacy_gold_manifest_without_timeframe_fields() -> None:
    """Legacy manifest (pre-patch) must surface empty defaults — no regression."""

    scratch = _scratch_dir("cockpit_timeframe_propagation_legacy")
    try:
        workflow_root, phase_a2_root = _seed_workflow(scratch, label="legacy")
        _write_json(
            phase_a2_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 580,
                "feature_groups_declared": ["ofi_features"],
                "feature_groups_generated": ["ofi_features"],
                "feature_groups_ready": ["ofi_features"],
                # No silver_timeframes_detected / gold_timeframes_generated /
                # timeframes_pruned / pruning_reason_by_timeframe /
                # timeframe_feature_row_count: this manifest was written by
                # the pre-patch builder.
            },
        )

        summary = _read_strategy_ladder_summary(
            (_build_job_record(scratch, workflow_root=workflow_root, phase_a2_root=phase_a2_root, label="legacy"),)
        )

        assert summary.silver_timeframes_detected == ()
        assert summary.gold_timeframes_generated == ()
        assert summary.timeframes_pruned == ()
        assert summary.pruning_reason_by_timeframe == {}
        assert summary.timeframe_feature_row_count == {}
        # Pre-existing feature_groups fields still flow correctly.
        assert summary.feature_groups_declared == ("ofi_features",)
        assert summary.feature_groups_generated == ("ofi_features",)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
