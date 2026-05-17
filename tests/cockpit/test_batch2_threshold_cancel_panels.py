"""Patch 6 batch 2 — feature/threshold manifest + cancel job + dashboard panels.

Covers:
- ``feature_threshold_manifest.json`` is built with typed feature groups,
  threshold registry, and provenance (no fake calibration claims).
- ``request_job_cancel`` writes ``cancel_request.json`` with the correct
  PID and refuses to act on terminal jobs or jobs without a PID.
- ``CockpitBacktestJobStatus`` exposes the new states (JOB_CANCELLING /
  JOB_KILLED / JOB_CANCEL_FAILED / JOB_NOT_RUNNING).
- ``CockpitBacktestJobRecord`` rounds-trips the new ``pid`` /
  ``cancel_requested_at`` / ``cancel_reason`` / ``termination_method`` fields.

We do NOT spawn real subprocesses in tests — the Popen migration is
exercised by the existing cockpit suite (which already runs
``launch_backtest_job`` end-to-end via ``_fake_launch_backtest_job``
monkeypatches).
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from cockpit.action_support import (
    CANCEL_REQUEST_FILENAME,
    CockpitBacktestJobKind,
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
    JOB_ID_NOT_FOUND,
    PID_NOT_FOUND,
    request_job_cancel,
)
from local_replay_runtime.feature_threshold_manifest import (
    FeatureThresholdManifest,
    build_feature_threshold_manifest,
    emit_feature_threshold_manifest,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / ".test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{label}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


# ---------------------------------------------------------------------------
# Part G — feature_threshold_manifest builder
# ---------------------------------------------------------------------------


def _write_gold_manifest(output_root: Path, feature_groups: list[str]) -> None:
    payload = {
        "schema_version": "v1",
        "gold_feature_store_status": "FEATURE_STORE_READY",
        "feature_paths": ["/tmp/dummy_feature.jsonl"],
        "feature_row_count": 100,
        "feature_groups": feature_groups,
    }
    (output_root / "gold_feature_manifest.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_feature_threshold_manifest_builds_with_real_feature_groups() -> None:
    scratch = _scratch_dir("ftm_build")
    try:
        _write_gold_manifest(
            scratch,
            [
                "kline_return_features",
                "depth_features",
                "ofi_features",
                "vpin_features",
            ],
        )
        manifest = build_feature_threshold_manifest(
            output_root=scratch,
            run_id="ftm-test",
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-30",
            timeframes=("1m",),
        )
        # Available groups carry through.
        groups = {row.feature_group for row in manifest.feature_groups_available}
        assert "kline_return_features" in groups
        assert "depth_features" in groups
        # Each available group has used_by_engines populated.
        for row in manifest.feature_groups_available:
            assert row.used_by_engines, row.feature_group
            assert row.feature_readiness_flag in {"FEATURE_GROUP_READY", "FEATURE_GROUP_PARTIAL", "FEATURE_GROUP_NOT_PROVEN"}
        # Missing groups are reported.
        assert "spread_features" in manifest.feature_groups_missing
        assert "trade_flow_features" in manifest.feature_groups_missing
        # Threshold registry is non-empty and all thresholds default to
        # THRESHOLD_DEFAULT (no calibration artefacts supplied).
        assert manifest.thresholds_used
        for entry in manifest.thresholds_used:
            assert entry.threshold_status in {"THRESHOLD_DEFAULT", "THRESHOLD_NOT_PROVEN"}
            assert entry.calibration_status == "CALIBRATION_NOT_PROVEN"
            assert entry.calibration_artefact_path == ""
            assert entry.applies_to_engines, entry.threshold_name
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_feature_threshold_manifest_calibration_only_with_real_artefact() -> None:
    """No calibration claim without an actual artefact path that exists on disk."""

    scratch = _scratch_dir("ftm_calibration")
    try:
        _write_gold_manifest(scratch, ["kline_return_features"])
        # Real artefact for one threshold; fake (missing) for another.
        real_calib = scratch / "ev_net_floor_bps.calibrated.json"
        real_calib.write_text("{}", encoding="utf-8")
        fake_calib = scratch / "missing_artefact.json"
        manifest = build_feature_threshold_manifest(
            output_root=scratch,
            run_id="ftm-cal",
            calibration_artefact_paths={
                "ev_net_floor_bps": real_calib,
                "spread_guard_max_spread_bps": fake_calib,  # does not exist
            },
        )
        by_name = {entry.threshold_name: entry for entry in manifest.thresholds_used}
        assert by_name["ev_net_floor_bps"].threshold_status == "THRESHOLD_CALIBRATED"
        assert by_name["ev_net_floor_bps"].calibration_status == "CALIBRATION_READY"
        assert by_name["ev_net_floor_bps"].calibration_artefact_path == str(real_calib.resolve())
        # Fake/missing calibration must NOT promote.
        assert by_name["spread_guard_max_spread_bps"].threshold_status == "THRESHOLD_DEFAULT"
        assert by_name["spread_guard_max_spread_bps"].calibration_status == "CALIBRATION_NOT_PROVEN"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_feature_threshold_manifest_emits_json_and_md() -> None:
    scratch = _scratch_dir("ftm_emit")
    try:
        _write_gold_manifest(scratch, ["kline_return_features"])
        manifest, json_path = emit_feature_threshold_manifest(
            output_root=scratch,
            run_id="ftm-emit",
            pairs=("BTCUSDT",),
        )
        assert json_path.is_file()
        assert json_path.name == "feature_threshold_manifest.json"
        md_path = scratch / "feature_threshold_manifest.md"
        assert md_path.is_file()
        # Markdown contains the threshold table header.
        md_text = md_path.read_text(encoding="utf-8")
        assert "## Thresholds" in md_text
        assert "Calibration" in md_text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Part J — Cancel infrastructure
# ---------------------------------------------------------------------------


def _build_record(
    *,
    job_dir: Path,
    status: CockpitBacktestJobStatus,
    pid: int = 0,
) -> CockpitBacktestJobRecord:
    """Build a synthetic job record on disk for cancel-flow tests."""

    job_dir.mkdir(parents=True, exist_ok=True)
    record = CockpitBacktestJobRecord(
        job_id=job_dir.name,
        correlation_id="cockpit-backtest-test",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
        status=status,
        requested_at_iso="2025-04-29T00:00:00+00:00",
        record_path=str((job_dir / "job.json").resolve()),
        stdout_log_path=str((job_dir / "stdout.log").resolve()),
        output_root=str((job_dir / "output").resolve()),
        command=("python", "-c", "pass"),
        command_preview="python -c pass",
        job_request_path=str((job_dir / "job_request.json").resolve()),
        job_status_path=str((job_dir / "job_status.json").resolve()),
        pid=pid,
    )
    (job_dir / "job.json").write_text(record.model_dump_json(), encoding="utf-8")
    return record


def test_request_job_cancel_writes_cancel_request_json_for_running_job() -> None:
    scratch = _scratch_dir("cancel_running")
    try:
        jobs_root = scratch / "jobs"
        job_dir = jobs_root / "data-factory-test-job"
        record = _build_record(
            job_dir=job_dir, status=CockpitBacktestJobStatus.JOB_RUNNING, pid=12345
        )
        status_code, blocker = request_job_cancel(
            jobs_root=jobs_root,
            job_id=record.job_id,
            operator_reason="user_smashed_button",
        )
        assert status_code == "JOB_CANCELLING"
        assert blocker == ""
        cancel_path = job_dir / CANCEL_REQUEST_FILENAME
        assert cancel_path.is_file()
        payload = json.loads(cancel_path.read_text(encoding="utf-8"))
        assert payload["job_id"] == record.job_id
        assert payload["pid"] == 12345
        assert payload["reason"] == "user_smashed_button"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_request_job_cancel_returns_not_running_for_terminal_states() -> None:
    scratch = _scratch_dir("cancel_terminal")
    try:
        jobs_root = scratch / "jobs"
        job_dir = jobs_root / "completed-job"
        _build_record(
            job_dir=job_dir,
            status=CockpitBacktestJobStatus.JOB_COMPLETED,
            pid=99999,
        )
        status_code, blocker = request_job_cancel(
            jobs_root=jobs_root, job_id="completed-job"
        )
        assert status_code == "JOB_NOT_RUNNING"
        assert blocker == ""
        # No cancel_request.json should be written for terminal jobs.
        assert not (job_dir / CANCEL_REQUEST_FILENAME).is_file()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_request_job_cancel_fails_when_pid_missing() -> None:
    scratch = _scratch_dir("cancel_no_pid")
    try:
        jobs_root = scratch / "jobs"
        job_dir = jobs_root / "no-pid-job"
        _build_record(
            job_dir=job_dir,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            pid=0,  # PID never written
        )
        status_code, blocker = request_job_cancel(
            jobs_root=jobs_root, job_id="no-pid-job"
        )
        assert status_code == "JOB_CANCEL_FAILED"
        assert blocker == PID_NOT_FOUND
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_request_job_cancel_fails_when_job_id_missing() -> None:
    scratch = _scratch_dir("cancel_no_job")
    try:
        jobs_root = scratch / "jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        status_code, blocker = request_job_cancel(
            jobs_root=jobs_root, job_id="does-not-exist"
        )
        assert status_code == "JOB_CANCEL_FAILED"
        assert blocker == JOB_ID_NOT_FOUND
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_request_job_cancel_only_targets_specified_job_id() -> None:
    """A cancel request must NEVER affect another job's directory."""

    scratch = _scratch_dir("cancel_isolated")
    try:
        jobs_root = scratch / "jobs"
        job_dir_a = jobs_root / "job-a"
        job_dir_b = jobs_root / "job-b"
        _build_record(
            job_dir=job_dir_a,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            pid=11111,
        )
        _build_record(
            job_dir=job_dir_b,
            status=CockpitBacktestJobStatus.JOB_RUNNING,
            pid=22222,
        )
        status_code, _ = request_job_cancel(jobs_root=jobs_root, job_id="job-a")
        assert status_code == "JOB_CANCELLING"
        # Only job-a got a cancel sidecar; job-b is untouched.
        assert (job_dir_a / CANCEL_REQUEST_FILENAME).is_file()
        assert not (job_dir_b / CANCEL_REQUEST_FILENAME).is_file()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Status enum + record fields surface
# ---------------------------------------------------------------------------


def test_cockpit_job_status_enum_carries_new_cancel_states() -> None:
    """Spec parts: JOB_CANCELLING / JOB_KILLED / JOB_CANCEL_FAILED / JOB_NOT_RUNNING."""

    expected = {
        "JOB_CANCELLING",
        "JOB_KILLED",
        "JOB_CANCEL_FAILED",
        "JOB_NOT_RUNNING",
    }
    actual = {member.value for member in CockpitBacktestJobStatus}
    assert expected.issubset(actual)


def test_cockpit_job_record_carries_pid_and_cancel_telemetry() -> None:
    record = CockpitBacktestJobRecord(
        job_id="rec-1",
        correlation_id="cor-1",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
        status=CockpitBacktestJobStatus.JOB_CANCELLING,
        requested_at_iso="2025-04-29T00:00:00+00:00",
        pid=42,
        cancel_requested_at="2025-04-29T00:01:00+00:00",
        cancel_reason="operator_cancel",
        termination_method="SIGTERM",
    )
    serialized = json.loads(record.model_dump_json())
    assert serialized["pid"] == 42
    assert serialized["cancel_reason"] == "operator_cancel"
    assert serialized["termination_method"] == "SIGTERM"
    assert serialized["status"] == "JOB_CANCELLING"
