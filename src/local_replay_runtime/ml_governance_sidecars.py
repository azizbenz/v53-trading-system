"""Typed ML governance sidecars for Local-Lab handoff and promotion audit."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    MlAntiLeakageProofArtifact,
    MlLiveDriftSnapshot,
    MlModelArtifact,
    MlModelWindow,
)
from interface_contracts.atomic_io import atomic_write_json
from meta_learning.model_risk_registry import MlModelDriftSnapshot as RuntimeDriftSnapshot


ML_ANTI_LEAKAGE_PROOF_FILENAME = "ml_anti_leakage_proof_artifact.json"
ML_LIVE_DRIFT_SNAPSHOT_FILENAME = "ml_live_drift_snapshot.json"
DEFAULT_ML_LIVE_DRIFT_TTL = timedelta(days=7)


class MlGovernanceSidecarRefs(BaseModel, frozen=True):
    """Resolved Local-Lab sidecar refs adjacent to a governed ML artifact."""

    anti_leakage_proof_ref: str = Field(..., min_length=1)
    live_drift_snapshot_ref: str = Field(..., min_length=1)

    @property
    def supplementary_refs(self) -> tuple[str, ...]:
        return (
            self.anti_leakage_proof_ref,
            self.live_drift_snapshot_ref,
        )


def _utc_datetime(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _artifact_training_metrics(artifact: MlModelArtifact) -> dict[str, object]:
    metrics = artifact.training_metrics
    return dict(metrics) if isinstance(metrics, dict) else {}


def _metric_str(metrics: dict[str, object], key: str) -> str | None:
    value = str(metrics.get(key) or "").strip()
    return value or None


def _metric_int(metrics: dict[str, object], key: str) -> int | None:
    raw_value = metrics.get(key)
    if isinstance(raw_value, bool):
        return None
    try:
        value = int(raw_value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _date_window(start_day: date, end_day: date) -> MlModelWindow:
    start_at = datetime.combine(start_day, time.min, tzinfo=UTC)
    end_at = datetime.combine(end_day, time.max, tzinfo=UTC)
    return MlModelWindow(start_at=start_at, end_at=end_at)


def _governance_stage(snapshot: RuntimeDriftSnapshot | None) -> str:
    if snapshot is None:
        return "SHADOW"
    return snapshot.stage.value.upper()


def _runtime_snapshot_hash(snapshot: RuntimeDriftSnapshot) -> str:
    return _hash_payload(snapshot.model_dump(mode="json"))


def build_ml_anti_leakage_proof_artifact(
    artifact: MlModelArtifact,
    *,
    test_start: date,
    test_end: date,
    created_at: datetime | None = None,
) -> MlAntiLeakageProofArtifact:
    """Project the training windows and declared horizon into a verifiable proof sidecar."""

    metrics = _artifact_training_metrics(artifact)
    label_policy = (
        _metric_str(metrics, "strategy_ladder_label_source")
        or _metric_str(metrics, "strategy_ladder_target_policy")
    )
    horizon_minutes = _metric_int(metrics, "strategy_ladder_target_horizon_minutes")
    purge_size = _metric_int(metrics, "strategy_ladder_purge_window_minutes")
    embargo_size = _metric_int(metrics, "strategy_ladder_embargo_window_minutes")
    split_declared = metrics.get("strategy_ladder_split_declared") is True
    walkforward_declared = (
        _metric_str(metrics, "strategy_ladder_walkforward_status")
        == "EXPECTED_EDGE_WALKFORWARD_DECLARED"
    )
    horizon_delta = None if horizon_minutes is None else timedelta(minutes=horizon_minutes)
    validation_window = artifact.validation_window
    test_window = _date_window(test_start, test_end)

    sequential_windows = (
        artifact.train_window.start_at <= artifact.train_window.end_at
        and artifact.train_window.end_at < validation_window.start_at
        and validation_window.start_at <= validation_window.end_at
        and validation_window.end_at < test_window.start_at
    )
    train_validation_gap_ok = (
        horizon_delta is not None
        and (_utc_datetime(validation_window.start_at) - _utc_datetime(artifact.train_window.end_at))
        >= horizon_delta
    )
    validation_test_gap_ok = (
        horizon_delta is not None
        and (_utc_datetime(test_window.start_at) - _utc_datetime(validation_window.end_at))
        >= horizon_delta
    )
    feature_timestamp_alignment_status = (
        "FEATURE_TIMESTAMP_ALIGNED"
        if sequential_windows and horizon_delta is not None
        else "FEATURE_TIMESTAMP_ALIGNMENT_NOT_PROVEN"
    )
    no_future_data_leak_status = (
        "NO_FUTURE_DATA_LEAK_PROVEN"
        if (
            split_declared
            and walkforward_declared
            and horizon_delta is not None
            and sequential_windows
            and train_validation_gap_ok
            and validation_test_gap_ok
        )
        else "NO_FUTURE_DATA_LEAK_NOT_PROVEN"
    )

    proof_created_at = _utc_datetime(created_at or datetime.now(tz=UTC))
    max_feature_timestamp = _utc_datetime(validation_window.end_at)
    min_label_timestamp = (
        None if horizon_delta is None else max_feature_timestamp + horizon_delta
    )
    return MlAntiLeakageProofArtifact.create(
        artifact_id=f"{artifact.artifact_hash[:12]}:anti-leakage-proof",
        target_artifact_hash=artifact.artifact_hash,
        dataset_hash=artifact.dataset_hash,
        feature_hash=artifact.feature_hash,
        label_policy=label_policy,
        train_window=artifact.train_window,
        validation_window=validation_window,
        test_window=test_window,
        purge_size=purge_size,
        embargo_size=embargo_size,
        label_horizon=None if horizon_minutes is None else f"{horizon_minutes}m",
        max_feature_timestamp=max_feature_timestamp,
        min_label_timestamp=min_label_timestamp,
        random_split_forbidden=True,
        feature_timestamp_alignment_status=feature_timestamp_alignment_status,
        no_future_data_leak_status=no_future_data_leak_status,
        reviewer_signature="LOCAL_LAB_AUTOGEN",
        method_version_hash="local_replay.ml_governance_sidecars.anti_leakage.v1",
        created_at=proof_created_at,
    )


def build_ml_live_drift_snapshot(
    artifact: MlModelArtifact,
    *,
    runtime_snapshot: RuntimeDriftSnapshot | None = None,
    created_at: datetime | None = None,
    expires_after: timedelta = DEFAULT_ML_LIVE_DRIFT_TTL,
    input_data_hash: str | None = None,
) -> MlLiveDriftSnapshot:
    """Emit a governed drift snapshot when runtime evidence exists, else an honest placeholder."""

    snapshot_created_at = _utc_datetime(created_at or datetime.now(tz=UTC))
    snapshot_payload_hash = (
        None
        if runtime_snapshot is None
        else (input_data_hash or _runtime_snapshot_hash(runtime_snapshot))
    )
    snapshot_stage = _governance_stage(runtime_snapshot)
    source_status = (
        "LIVE_DRIFT_SOURCE_GOVERNED"
        if runtime_snapshot is not None and snapshot_stage in {"SHADOW", "LIVE"}
        else "LIVE_DRIFT_SOURCE_NOT_PROVEN"
    )
    return MlLiveDriftSnapshot.create(
        artifact_id=f"{artifact.artifact_hash[:12]}:live-drift",
        target_artifact_hash=artifact.artifact_hash,
        feature_hash=artifact.feature_hash,
        stage=snapshot_stage,
        feature_ks_pvalue=(
            artifact.ks_test_features_pvalue
            if runtime_snapshot is None
            else runtime_snapshot.feature_ks_pvalue
        ),
        shadow_diff_pct=(
            artifact.shadow_diff_pct if runtime_snapshot is None else runtime_snapshot.shadow_diff_pct
        ),
        live_diff_pct=None if runtime_snapshot is None else runtime_snapshot.live_diff_pct,
        win_rate_delta=None if runtime_snapshot is None else runtime_snapshot.win_rate_delta,
        ce_delta=None if runtime_snapshot is None else runtime_snapshot.ce_delta,
        source_status=source_status,
        input_data_hash=snapshot_payload_hash,
        method_version_hash="local_replay.ml_governance_sidecars.live_drift.v1",
        created_at=snapshot_created_at,
        expires_at=snapshot_created_at + expires_after,
    )


def write_ml_governance_sidecars(
    artifact_dir: Path,
    *,
    anti_leakage_proof: MlAntiLeakageProofArtifact,
    live_drift_snapshot: MlLiveDriftSnapshot,
) -> MlGovernanceSidecarRefs:
    """Persist proof sidecars next to the source artifact so transport can discover them."""

    resolved_dir = artifact_dir.resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    anti_leakage_path = (resolved_dir / ML_ANTI_LEAKAGE_PROOF_FILENAME).resolve()
    live_drift_path = (resolved_dir / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).resolve()
    atomic_write_json(anti_leakage_path, anti_leakage_proof.model_dump(mode="json"), indent=2)
    atomic_write_json(live_drift_path, live_drift_snapshot.model_dump(mode="json"), indent=2)
    return MlGovernanceSidecarRefs(
        anti_leakage_proof_ref=str(anti_leakage_path),
        live_drift_snapshot_ref=str(live_drift_path),
    )


def discover_ml_governance_sidecar_refs(source_artifact_ref: str | Path) -> tuple[str, ...]:
    """Return existing ML governance sidecars adjacent to the source artifact."""

    artifact_dir = Path(source_artifact_ref).resolve().parent
    refs: list[str] = []
    for filename in (
        ML_ANTI_LEAKAGE_PROOF_FILENAME,
        ML_LIVE_DRIFT_SNAPSHOT_FILENAME,
    ):
        path = (artifact_dir / filename).resolve()
        if path.is_file():
            refs.append(str(path))
    return tuple(refs)


def load_ml_anti_leakage_proof(path_ref: str | Path) -> MlAntiLeakageProofArtifact:
    path = Path(path_ref).resolve()
    return MlAntiLeakageProofArtifact.model_validate_json(path.read_text(encoding="utf-8-sig"))


def load_ml_live_drift_snapshot(path_ref: str | Path) -> MlLiveDriftSnapshot:
    path = Path(path_ref).resolve()
    return MlLiveDriftSnapshot.model_validate_json(path.read_text(encoding="utf-8-sig"))


def resolve_ml_governance_sidecar_refs(artifact_ref: str | Path) -> MlGovernanceSidecarRefs | None:
    """Resolve both sidecars next to an artifact when the pair is complete."""

    artifact_dir = Path(artifact_ref).resolve().parent
    anti_leakage_path = (artifact_dir / ML_ANTI_LEAKAGE_PROOF_FILENAME).resolve()
    live_drift_path = (artifact_dir / ML_LIVE_DRIFT_SNAPSHOT_FILENAME).resolve()
    if not anti_leakage_path.is_file() or not live_drift_path.is_file():
        return None
    return MlGovernanceSidecarRefs(
        anti_leakage_proof_ref=str(anti_leakage_path),
        live_drift_snapshot_ref=str(live_drift_path),
    )


__all__ = [
    "DEFAULT_ML_LIVE_DRIFT_TTL",
    "ML_ANTI_LEAKAGE_PROOF_FILENAME",
    "ML_LIVE_DRIFT_SNAPSHOT_FILENAME",
    "MlGovernanceSidecarRefs",
    "build_ml_anti_leakage_proof_artifact",
    "build_ml_live_drift_snapshot",
    "discover_ml_governance_sidecar_refs",
    "load_ml_anti_leakage_proof",
    "load_ml_live_drift_snapshot",
    "resolve_ml_governance_sidecar_refs",
    "write_ml_governance_sidecars",
]
