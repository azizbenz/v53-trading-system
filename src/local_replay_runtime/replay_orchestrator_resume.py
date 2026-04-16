"""Resume helpers for governed LOCAL_REPLAY orchestration."""

from __future__ import annotations

from pathlib import Path

from local_replay_runtime.artifact_exporter import ReplayArtifactExportResult
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.performance_mode_guard import PerformanceModeGuardReport
from local_replay_runtime.replay_executor import ReplayExecutionResult
from local_replay_runtime.replay_metrics_collector import ReplayMetricsSummary
from local_replay_runtime.replay_orchestrator_chunking import _resolve_chunk_indices
from local_replay_runtime.replay_orchestrator_io import (
    _load_chunk_session_summary,
    _load_existing_resume_metadata,
    _load_json_sidecar_with_backup,
    _validate_resume_request_against_existing_export,
)
from local_replay_runtime.replay_orchestrator_models import (
    ReplayOrchestratorRequest,
    ReplayOrchestratorResult,
)
from local_replay_runtime.replay_state_store import (
    ReplaySessionStateStore,
    ReplaySessionStoreConfig,
)
from local_replay_runtime.run_consistency_guard import RunConsistencyGuardReport


def _existing_export_completed(
    output_dir: Path,
    *,
    state_store: ReplaySessionStateStore,
) -> ReplayOrchestratorResult | None:
    state = state_store.build_state()
    if state.lifecycle_state != "export_completed":
        return None

    session_config_path = output_dir / "replay_session_config.json"
    session_state_path = output_dir / "replay_session_state.json"
    performance_mode_guard_path = output_dir / "performance_mode_guard.json"
    run_consistency_guard_path = output_dir / "run_consistency_guard.json"
    replay_run_manifest_path = output_dir / "replay_run_manifest.json"
    review_export_path = output_dir / "review_export.md"
    feature_bridge_path = output_dir / "feature_bridge.json"
    parity_diagnostics_path = output_dir / "parity_diagnostics.json"
    replay_metrics_path = output_dir / "replay_metrics.json"
    replay_dtr_path = output_dir / "replay_dtr.jsonl"

    required = (
        session_config_path,
        session_state_path,
        performance_mode_guard_path,
        run_consistency_guard_path,
        replay_run_manifest_path,
        review_export_path,
        feature_bridge_path,
        parity_diagnostics_path,
        replay_metrics_path,
        replay_dtr_path,
    )
    if not all(path.exists() for path in required):
        return None

    metadata = _load_existing_resume_metadata(output_dir)
    if metadata is None:
        return None
    session_config, _ = metadata
    performance_mode_guard = _load_json_sidecar_with_backup(
        performance_mode_guard_path,
        label="resume sidecar",
        parser=PerformanceModeGuardReport.model_validate_json,
    )
    run_consistency_guard = _load_json_sidecar_with_backup(
        run_consistency_guard_path,
        label="resume sidecar",
        parser=RunConsistencyGuardReport.model_validate_json,
    )
    export_result = ReplayExecutionResult(
        export_result=ReplayArtifactExportResult(
            export_dir=output_dir,
            run_manifest_path=replay_run_manifest_path,
            review_export_path=review_export_path,
            feature_bridge_path=feature_bridge_path,
            parity_diagnostics_path=parity_diagnostics_path,
            replay_metrics_path=replay_metrics_path,
            replay_dtr_path=replay_dtr_path,
        ),
        metrics_summary=_load_json_sidecar_with_backup(
            replay_metrics_path,
            label="resume sidecar",
            parser=ReplayMetricsSummary.model_validate_json,
        ),
    )
    dataset_id = "resumed_dataset"
    for note in state.notes:
        if note.startswith("dataset_id="):
            dataset_id = note.split("=", 1)[1] or dataset_id
            break
    pair_scope = state.pair_scope or ("UNKNOWN",)
    resumed_records = tuple(
        {
            "opportunity_id": f"resumed:{index}",
            "timestamp_ms": 1_700_000_000_000 + index,
            "pair": pair_scope[(index - 1) % len(pair_scope)],
            "engine_id": "engine_a",
            "feature_values": {"resumed": True},
        }
        for index in range(1, max(state.processed_records, 1) + 1)
    )
    processed_dataset = HistoricalReplayDataset.from_records(
        dataset_id=dataset_id,
        source_path=state.input_path or "resumed://dataset",
        records=resumed_records,
        source="resumed_state",
    )
    return ReplayOrchestratorResult(
        session_config_path=session_config_path,
        session_state_path=session_state_path,
        performance_mode_guard_path=performance_mode_guard_path,
        run_consistency_guard_path=run_consistency_guard_path,
        export_result=export_result,
        session_config=session_config,
        performance_mode_guard=performance_mode_guard,
        run_consistency_guard=run_consistency_guard,
        processed_dataset=processed_dataset,
        chunk_output_dirs=(output_dir,),
        completed_chunk_indices=(session_config.chunk_index,),
        resumed_chunk_indices=(session_config.chunk_index,),
        resumed=True,
    )


def _existing_multi_chunk_export_completed(
    output_dir: Path,
    *,
    request: ReplayOrchestratorRequest,
) -> ReplayOrchestratorResult | None:
    chunk_session = _load_chunk_session_summary(output_dir)
    if chunk_session is None or not chunk_session.aggregate_ready:
        return None
    if chunk_session.chunk_count != request.chunk_count:
        return None
    expected_chunks = _resolve_chunk_indices(request)
    if chunk_session.completed_chunk_indices != expected_chunks:
        return None
    if chunk_session.run_id != request.run_id:
        return None
    if chunk_session.strategy_id != request.strategy_id:
        return None
    if chunk_session.strategy_version != request.strategy_version:
        return None
    if chunk_session.lineage_version != request.lineage_version:
        return None
    if chunk_session.performance_mode != request.performance_mode:
        return None
    if request.input_kind is not None and chunk_session.input_kind != request.input_kind:
        return None
    if chunk_session.selected_chunk_indices != expected_chunks:
        return None
    if chunk_session.window_start_ms != request.window_start_ms:
        return None
    if chunk_session.window_end_ms != request.window_end_ms:
        return None
    metadata = _load_existing_resume_metadata(output_dir)
    if metadata is None:
        return None
    session_config, replay_run_manifest = metadata
    try:
        _validate_resume_request_against_existing_export(
            request,
            session_config=session_config,
            replay_run_manifest=replay_run_manifest,
        )
    except ValueError:
        return None
    if not all(
        artifact.chunk_output_dir.exists()
        and artifact.replay_run_manifest_path.exists()
        and artifact.review_export_path.exists()
        and artifact.replay_dtr_path.exists()
        for artifact in chunk_session.chunk_artifacts
    ):
        return None

    state_store = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
            state_filename="replay_session_state.json",
        )
    )
    existing = _existing_export_completed(output_dir, state_store=state_store)
    if existing is None:
        return None

    resumed_chunk_indices = expected_chunks
    updated_chunk_session = chunk_session.model_copy(
        update={
            "resumed_chunk_indices": resumed_chunk_indices,
            "chunk_artifacts": tuple(
                artifact.model_copy(update={"resumed": True})
                for artifact in chunk_session.chunk_artifacts
            ),
            "summary": (
                f"run_id={chunk_session.run_id} / chunk_count={chunk_session.chunk_count} / "
                f"completed={len(chunk_session.completed_chunk_indices)} / aggregate_ready=yes / "
                f"resume=full"
            ),
        }
    )
    chunk_session_path = output_dir / "replay_chunk_session.json"
    from interface_contracts.atomic_io import atomic_write_json

    atomic_write_json(chunk_session_path, updated_chunk_session.model_dump(mode="json"))
    return existing.model_copy(
        update={
            "chunk_session_path": chunk_session_path,
            "chunk_output_dirs": tuple(
                artifact.chunk_output_dir for artifact in updated_chunk_session.chunk_artifacts
            ),
            "completed_chunk_indices": updated_chunk_session.completed_chunk_indices,
            "resumed_chunk_indices": updated_chunk_session.resumed_chunk_indices,
            "resumed": True,
        }
    )


__all__ = [
    "_existing_export_completed",
    "_existing_multi_chunk_export_completed",
]
