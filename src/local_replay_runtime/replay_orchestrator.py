"""Governed orchestration helpers for LOCAL_REPLAY exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, Field, ValidationError, model_validator

from interface_contracts import (
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_TRANSFORM_SET_VERSION,
    ProfileId,
    StrategyClassification,
)
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    build_feature_bridge_payload,
)
from local_replay_runtime.performance_mode_guard import (
    PerformanceModeGuardReport,
    build_performance_mode_guard_report,
)
from local_replay_runtime.replay_clock import build_replay_clock
from local_replay_runtime.artifact_exporter import ReplayArtifactExportResult
from local_replay_runtime.replay_executor import (
    ReplayExecutionInput,
    ReplayExecutionResult,
    execute_local_replay_export,
)
from local_replay_runtime.replay_metrics_collector import ReplayMetricsSummary
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_session_config import (
    ReplayInputKind,
    ReplaySessionConfig,
    build_replay_session_config,
)
from local_replay_runtime.replay_state_store import (
    ReplaySessionStateStore,
    ReplaySessionStoreConfig,
)
from local_replay_runtime.run_consistency_guard import (
    RunConsistencyGuardReport,
    compare_replay_runs,
)
from local_replay_runtime.shadow_execution_simulator import (
    build_parity_diagnostics_payload,
    simulate_shadow_compatible_dtrs,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord

_LoadedModelT = TypeVar("_LoadedModelT")


class ReplayOrchestratorRequest(BaseModel, frozen=True):
    """Inputs required to run the governed LOCAL_REPLAY orchestrator."""

    output_dir: Path
    run_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    strategy_classification: StrategyClassification
    lineage_version: str = Field(..., min_length=1)
    performance_mode: str = Field(..., min_length=1)
    input_kind: ReplayInputKind | None = None
    dataset: HistoricalReplayDataset | None = None
    profile_scope: ProfileId = ProfileId.COMPLETE
    chunk_count: int = Field(default=1, ge=1)
    chunk_index: int = Field(default=1, ge=1)
    selected_chunk_indices: tuple[int, ...] = ()
    window_start_ms: int | None = Field(default=None, ge=0)
    window_end_ms: int | None = Field(default=None, ge=0)
    rewind_requested: bool = False
    resume: bool = False
    run_all_chunks: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> "ReplayOrchestratorRequest":
        if self.chunk_index > self.chunk_count:
            raise ValueError("ReplayOrchestratorRequest chunk_index must stay <= chunk_count")
        if self.window_start_ms is not None and self.window_end_ms is not None:
            if self.window_end_ms < self.window_start_ms:
                raise ValueError(
                    "ReplayOrchestratorRequest window_end_ms must stay >= window_start_ms"
                )
        if any(index < 1 or index > self.chunk_count for index in self.selected_chunk_indices):
            raise ValueError(
                "ReplayOrchestratorRequest selected_chunk_indices must stay within chunk_count"
            )
        if len(self.selected_chunk_indices) != len(set(self.selected_chunk_indices)):
            raise ValueError(
                "ReplayOrchestratorRequest selected_chunk_indices must stay unique"
            )
        return self


class ReplayChunkArtifact(BaseModel, frozen=True):
    """Audit-ready summary of a chunk export produced in a governed replay session."""

    chunk_index: int = Field(..., ge=1)
    chunk_output_dir: Path
    record_count: int = Field(default=0, ge=0)
    produced_dtr_count: int = Field(default=0, ge=0)
    replay_run_manifest_path: Path
    review_export_path: Path
    replay_dtr_path: Path
    completed: bool = False
    resumed: bool = False


class ReplayChunkSessionSummary(BaseModel, frozen=True):
    """Session-level summary for a governed multi-chunk LOCAL_REPLAY export."""

    run_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    input_kind: ReplayInputKind
    performance_mode: str = Field(..., min_length=1)
    chunk_count: int = Field(..., ge=1)
    selected_chunk_indices: tuple[int, ...] = ()
    window_start_ms: int | None = Field(default=None, ge=0)
    window_end_ms: int | None = Field(default=None, ge=0)
    completed_chunk_indices: tuple[int, ...] = ()
    resumed_chunk_indices: tuple[int, ...] = ()
    aggregate_ready: bool = False
    aggregate_export_dir: Path
    chunk_artifacts: tuple[ReplayChunkArtifact, ...] = ()
    summary: str = Field(..., min_length=1)


class ReplayOrchestratorResult(BaseModel, frozen=True):
    """Stable output of the governed LOCAL_REPLAY orchestrator."""

    session_config_path: Path
    session_state_path: Path
    performance_mode_guard_path: Path
    run_consistency_guard_path: Path
    export_result: ReplayExecutionResult
    session_config: ReplaySessionConfig
    performance_mode_guard: PerformanceModeGuardReport
    run_consistency_guard: RunConsistencyGuardReport
    processed_dataset: HistoricalReplayDataset
    chunk_session_path: Path | None = None
    chunk_output_dirs: tuple[Path, ...] = ()
    completed_chunk_indices: tuple[int, ...] = ()
    resumed_chunk_indices: tuple[int, ...] = ()
    resumed: bool = False


def _slice_dataset_for_chunk(
    dataset: HistoricalReplayDataset,
    *,
    chunk_count: int,
    chunk_index: int,
) -> HistoricalReplayDataset:
    if chunk_index > chunk_count:
        raise ValueError("chunk_index must stay <= chunk_count")
    total = len(dataset.rows)
    start = total * (chunk_index - 1) // chunk_count
    end = total * chunk_index // chunk_count
    chunk_rows = dataset.rows[start:end]
    if not chunk_rows:
        raise ValueError("chunk replay produced an empty dataset slice")
    return HistoricalReplayDataset.from_records(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        records=chunk_rows,
        source=dataset.source,
    )


def _chunk_output_dir(output_dir: Path, chunk_index: int) -> Path:
    return output_dir / "chunks" / f"chunk_{chunk_index:04d}"


def _filter_dataset_by_window(
    dataset: HistoricalReplayDataset,
    *,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> HistoricalReplayDataset:
    if window_start_ms is None and window_end_ms is None:
        return dataset
    filtered_rows = tuple(
        row
        for row in dataset.rows
        if (window_start_ms is None or row.timestamp_ms >= window_start_ms)
        and (window_end_ms is None or row.timestamp_ms <= window_end_ms)
    )
    if not filtered_rows:
        raise ValueError("requested replay window produced an empty dataset slice")
    return HistoricalReplayDataset.from_records(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        records=filtered_rows,
        source=dataset.source,
    )


def _resolve_chunk_indices(request: ReplayOrchestratorRequest) -> tuple[int, ...]:
    if request.run_all_chunks:
        if request.selected_chunk_indices:
            return tuple(sorted(request.selected_chunk_indices))
        return tuple(range(1, request.chunk_count + 1))
    return (request.chunk_index,)


def _read_dtr_records(replay_dtr_path: Path) -> tuple[DTRRecord, ...]:
    records: list[DTRRecord] = []
    for line in replay_dtr_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(DTRRecord.model_validate(json.loads(stripped)))
    return tuple(records)


def _load_json_sidecar_with_backup(
    path: Path,
    *,
    label: str,
    parser: Callable[[str], _LoadedModelT],
) -> _LoadedModelT:
    try:
        return parser(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError, TypeError) as exc:
        backup = path.with_suffix(".corrupted")
        try:
            path.replace(backup)
        except OSError:
            pass
        raise ValueError(f"LOCAL_REPLAY {label} is corrupted: {path.name}") from exc


def _load_existing_resume_metadata(
    output_dir: Path,
) -> tuple[ReplaySessionConfig, ReplayRunManifest] | None:
    session_config_path = output_dir / "replay_session_config.json"
    replay_run_manifest_path = output_dir / "replay_run_manifest.json"
    if not session_config_path.exists() or not replay_run_manifest_path.exists():
        return None
    session_config = _load_json_sidecar_with_backup(
        session_config_path,
        label="resume metadata",
        parser=ReplaySessionConfig.model_validate_json,
    )
    replay_run_manifest = _load_json_sidecar_with_backup(
        replay_run_manifest_path,
        label="resume metadata",
        parser=ReplayRunManifest.model_validate_json,
    )
    return session_config, replay_run_manifest


def _validate_resume_request_against_existing_export(
    request: ReplayOrchestratorRequest,
    *,
    session_config: ReplaySessionConfig,
    replay_run_manifest: ReplayRunManifest,
) -> None:
    mismatches: list[str] = []
    expected_fields = (
        ("run_id", request.run_id, session_config.run_id),
        ("strategy_id", request.strategy_id, session_config.strategy_id),
        ("strategy_version", request.strategy_version, session_config.strategy_version),
        ("lineage_version", request.lineage_version, session_config.lineage_version),
        ("profile_scope", request.profile_scope.value, session_config.profile_scope.value),
        ("performance_mode", request.performance_mode, session_config.performance_mode),
        (
            "strategy_classification",
            request.strategy_classification.value,
            replay_run_manifest.strategy_classification.value,
        ),
        ("chunk_count", request.chunk_count, session_config.chunk_count),
    )
    for field_name, actual, expected in expected_fields:
        if actual != expected:
            mismatches.append(f"{field_name} expected {expected!r}, got {actual!r}")

    if not request.run_all_chunks and request.chunk_index != session_config.chunk_index:
        mismatches.append(
            f"chunk_index expected {session_config.chunk_index!r}, got {request.chunk_index!r}"
        )
    if request.input_kind is not None and request.input_kind != session_config.input_kind:
        mismatches.append(
            f"input_kind expected {session_config.input_kind!r}, got {request.input_kind!r}"
        )
    if mismatches:
        raise ValueError(
            "LOCAL_REPLAY resume request does not match the persisted export: "
            + "; ".join(mismatches)
        )


def _load_chunk_session_summary(output_dir: Path) -> ReplayChunkSessionSummary | None:
    chunk_session_path = output_dir / "replay_chunk_session.json"
    if not chunk_session_path.exists():
        return None
    return _load_json_sidecar_with_backup(
        chunk_session_path,
        label="chunk session metadata",
        parser=ReplayChunkSessionSummary.model_validate_json,
    )


def build_execution_input_from_dataset(
    *,
    run_id: str,
    strategy_id: str,
    strategy_version: str,
    strategy_classification: StrategyClassification,
    lineage_version: str,
    performance_mode: str,
    profile_scope: ProfileId,
    dataset: HistoricalReplayDataset,
) -> ReplayExecutionInput:
    """Build the governed replay execution payload directly from a normalized dataset."""

    clock = build_replay_clock(
        dataset,
        clock_id=f"clock-{run_id}",
        mode=performance_mode,
    )
    dtr_records = simulate_shadow_compatible_dtrs(dataset)
    feature_bridge_payload = build_feature_bridge_payload(dataset)
    parity_diagnostics_payload = build_parity_diagnostics_payload(dataset, dtr_records)
    return ReplayExecutionInput(
        run_manifest=ReplayRunManifest(
            run_id=run_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            strategy_classification=strategy_classification,
            lineage_version=lineage_version,
            profile_scope=profile_scope,
            engine_scope=dataset.engine_scope,
            tested_pairs=dataset.pair_scope,
            dataset_manifest_id=dataset.dataset_id,
            timeframe_scope=clock.timeframe_scope,
            feature_set_version=CANONICAL_FEATURE_SET_VERSION,
            transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
            formula_set_version="formula.v1",
            scoring_version="score.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode=performance_mode,  # type: ignore[arg-type]
            artifact_schema_version="1.0.0",
            artifact_hash=f"artifact-{run_id}",
            clock_id=clock.clock_ref.clock_id,
            start_timestamp_ms=clock.clock_ref.start_timestamp_ms,
            end_timestamp_ms=clock.clock_ref.end_timestamp_ms,
            tick_count=clock.clock_ref.tick_count,
            record_count=dataset.record_count,
        ),
        total_opportunities=dataset.record_count,
        dtr_records=dtr_records,
        feature_bridge_payload=feature_bridge_payload,
        parity_diagnostics_payload=parity_diagnostics_payload,
        review_notes=(
            f"strategy_version={strategy_version}",
            f"lineage_version={lineage_version}",
            f"performance_mode={performance_mode}",
            f"dataset_source={dataset.source_path}",
            f"record_count={dataset.record_count}",
        ),
    )


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


def _orchestrate_single_chunk_export(
    request: ReplayOrchestratorRequest,
    *,
    output_dir: Path,
) -> ReplayOrchestratorResult:
    state_store = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
            state_filename="replay_session_state.json",
        )
    )
    if request.resume:
        resumed = _existing_export_completed(output_dir, state_store=state_store)
        if resumed is not None:
            metadata = _load_existing_resume_metadata(output_dir)
            if metadata is None:
                raise ValueError("LOCAL_REPLAY resume metadata is missing for a completed export")
            session_config, replay_run_manifest = metadata
            _validate_resume_request_against_existing_export(
                request,
                session_config=session_config,
                replay_run_manifest=replay_run_manifest,
            )
            if request.dataset is not None:
                resumed_dataset = _slice_dataset_for_chunk(
                    request.dataset,
                    chunk_count=request.chunk_count,
                    chunk_index=request.chunk_index,
                )
                return resumed.model_copy(update={"processed_dataset": resumed_dataset})
            return resumed
    if request.dataset is None or request.input_kind is None:
        raise ValueError(
            "LOCAL_REPLAY orchestration requires dataset and input_kind unless a completed "
            "export is being resumed"
        )

    processed_dataset = _slice_dataset_for_chunk(
        request.dataset,
        chunk_count=request.chunk_count,
        chunk_index=request.chunk_index,
    )
    execution_input = build_execution_input_from_dataset(
        run_id=request.run_id,
        strategy_id=request.strategy_id,
        strategy_version=request.strategy_version,
        strategy_classification=request.strategy_classification,
        lineage_version=request.lineage_version,
        performance_mode=request.performance_mode,
        profile_scope=request.profile_scope,
        dataset=processed_dataset,
    )
    session_config = build_replay_session_config(
        execution_input.run_manifest,
        input_kind=request.input_kind,
        input_path=processed_dataset.source_path,
        input_record_count=processed_dataset.record_count,
        chunk_count=request.chunk_count,
        chunk_index=request.chunk_index,
        rewind_requested=request.rewind_requested,
    )
    session_config_path = output_dir / "replay_session_config.json"
    atomic_write_json(session_config_path, session_config.model_dump(mode="json"))
    state_store.initialize(session_config, output_dir=output_dir)
    state_store.mark_dataset_ready(processed_dataset)

    performance_mode_guard = build_performance_mode_guard_report(
        session_config,
        execution_input.run_manifest,
    )
    performance_mode_guard_path = output_dir / "performance_mode_guard.json"
    atomic_write_json(
        performance_mode_guard_path,
        performance_mode_guard.model_dump(mode="json"),
    )
    if not performance_mode_guard.guard_passed:
        raise ValueError("LOCAL_REPLAY performance_mode_guard failed")

    reference_dtr_records = simulate_shadow_compatible_dtrs(processed_dataset)
    run_consistency_guard = compare_replay_runs(
        reference_dtr_records,
        execution_input.dtr_records,
        reference_label="shadow_fidelity_mode",
        candidate_label=request.performance_mode,
    )
    run_consistency_guard_path = output_dir / "run_consistency_guard.json"
    atomic_write_json(
        run_consistency_guard_path,
        run_consistency_guard.model_dump(mode="json"),
    )
    if not run_consistency_guard.consistent:
        raise ValueError("LOCAL_REPLAY run_consistency_guard failed")

    execution_result = execute_local_replay_export(output_dir, execution_input)
    state_store.mark_export_completed(execution_result)

    return ReplayOrchestratorResult(
        session_config_path=session_config_path,
        session_state_path=output_dir / "replay_session_state.json",
        performance_mode_guard_path=performance_mode_guard_path,
        run_consistency_guard_path=run_consistency_guard_path,
        export_result=execution_result,
        session_config=session_config,
        performance_mode_guard=performance_mode_guard,
        run_consistency_guard=run_consistency_guard,
        processed_dataset=processed_dataset,
        chunk_output_dirs=(output_dir,),
        completed_chunk_indices=(request.chunk_index,),
        resumed_chunk_indices=(request.chunk_index,) if request.resume else (),
        resumed=False,
    )


def _aggregate_chunk_session(
    request: ReplayOrchestratorRequest,
    *,
    output_dir: Path,
    chunk_results: tuple[ReplayOrchestratorResult, ...],
) -> ReplayOrchestratorResult:
    if request.dataset is None or request.input_kind is None:
        raise ValueError("Chunk session aggregation requires a governed dataset and input_kind")

    aggregate_dataset = HistoricalReplayDataset.from_records(
        dataset_id=request.dataset.dataset_id,
        source_path=request.dataset.source_path,
        records=tuple(
            row
            for result in chunk_results
            for row in result.processed_dataset.rows
        ),
        source=request.dataset.source,
    )
    combined_dtr_records = tuple(
        record
        for result in chunk_results
        for record in _read_dtr_records(result.export_result.export_result.replay_dtr_path)
    )
    aggregate_seed = build_execution_input_from_dataset(
        run_id=request.run_id,
        strategy_id=request.strategy_id,
        strategy_version=request.strategy_version,
        strategy_classification=request.strategy_classification,
        lineage_version=request.lineage_version,
        performance_mode=request.performance_mode,
        profile_scope=request.profile_scope,
        dataset=aggregate_dataset,
    )
    aggregate_input = ReplayExecutionInput(
        run_manifest=aggregate_seed.run_manifest,
        total_opportunities=aggregate_dataset.record_count,
        dtr_records=combined_dtr_records,
        feature_bridge_payload=build_feature_bridge_payload(aggregate_dataset),
        parity_diagnostics_payload=build_parity_diagnostics_payload(
            aggregate_dataset,
            combined_dtr_records,
        ),
        review_notes=(
            f"session_scope=multi_chunk",
            f"chunk_count={request.chunk_count}",
            "completed_chunks="
            + ",".join(str(result.session_config.chunk_index) for result in chunk_results),
            *(
                f"chunk_{result.session_config.chunk_index}_dir={result.export_result.export_result.export_dir}"
                for result in chunk_results
            ),
        ),
    )
    aggregate_execution_result = execute_local_replay_export(output_dir, aggregate_input)
    session_config = build_replay_session_config(
        aggregate_input.run_manifest,
        input_kind=request.input_kind,
        input_path=aggregate_dataset.source_path,
        input_record_count=aggregate_dataset.record_count,
        chunk_count=request.chunk_count,
        chunk_index=1,
        rewind_requested=request.rewind_requested,
    )
    session_config_path = output_dir / "replay_session_config.json"
    atomic_write_json(session_config_path, session_config.model_dump(mode="json"))
    state_store = ReplaySessionStateStore(
        config=ReplaySessionStoreConfig(
            state_dir=output_dir,
            persist_state=True,
            state_filename="replay_session_state.json",
        )
    )
    state_store.initialize(session_config, output_dir=output_dir)
    state_store.mark_dataset_ready(aggregate_dataset)
    state_store.mark_export_completed(aggregate_execution_result)

    performance_mode_guard = build_performance_mode_guard_report(
        session_config,
        aggregate_input.run_manifest,
    )
    performance_mode_guard_path = output_dir / "performance_mode_guard.json"
    atomic_write_json(
        performance_mode_guard_path,
        performance_mode_guard.model_dump(mode="json"),
    )
    if not performance_mode_guard.guard_passed:
        raise ValueError("LOCAL_REPLAY aggregate performance_mode_guard failed")

    reference_dtr_records = simulate_shadow_compatible_dtrs(aggregate_dataset)
    run_consistency_guard = compare_replay_runs(
        reference_dtr_records,
        combined_dtr_records,
        reference_label="shadow_fidelity_mode",
        candidate_label=request.performance_mode,
    )
    run_consistency_guard_path = output_dir / "run_consistency_guard.json"
    atomic_write_json(
        run_consistency_guard_path,
        run_consistency_guard.model_dump(mode="json"),
    )
    if not run_consistency_guard.consistent:
        raise ValueError("LOCAL_REPLAY aggregate run_consistency_guard failed")

    chunk_artifacts = tuple(
        ReplayChunkArtifact(
            chunk_index=result.session_config.chunk_index,
            chunk_output_dir=result.export_result.export_result.export_dir,
            record_count=result.processed_dataset.record_count,
            produced_dtr_count=result.export_result.metrics_summary.total_records,
            replay_run_manifest_path=result.export_result.export_result.run_manifest_path,
            review_export_path=result.export_result.export_result.review_export_path,
            replay_dtr_path=result.export_result.export_result.replay_dtr_path,
            completed=True,
            resumed=result.resumed,
        )
        for result in chunk_results
    )
    completed_chunk_indices = tuple(
        artifact.chunk_index for artifact in chunk_artifacts if artifact.completed
    )
    resumed_chunk_indices = tuple(
        artifact.chunk_index for artifact in chunk_artifacts if artifact.resumed
    )
    chunk_session = ReplayChunkSessionSummary(
        run_id=request.run_id,
        strategy_id=request.strategy_id,
        strategy_version=request.strategy_version,
        lineage_version=request.lineage_version,
        input_kind=request.input_kind,
        performance_mode=request.performance_mode,
        chunk_count=request.chunk_count,
        selected_chunk_indices=_resolve_chunk_indices(request),
        window_start_ms=request.window_start_ms,
        window_end_ms=request.window_end_ms,
        completed_chunk_indices=completed_chunk_indices,
        resumed_chunk_indices=resumed_chunk_indices,
        aggregate_ready=True,
        aggregate_export_dir=output_dir,
        chunk_artifacts=chunk_artifacts,
        summary=(
            f"run_id={request.run_id} / chunk_count={request.chunk_count} / "
            f"completed={len(completed_chunk_indices)} / aggregate_ready=yes"
        ),
    )
    chunk_session_path = output_dir / "replay_chunk_session.json"
    atomic_write_json(chunk_session_path, chunk_session.model_dump(mode="json"))

    return ReplayOrchestratorResult(
        session_config_path=session_config_path,
        session_state_path=output_dir / "replay_session_state.json",
        performance_mode_guard_path=performance_mode_guard_path,
        run_consistency_guard_path=run_consistency_guard_path,
        export_result=aggregate_execution_result,
        session_config=session_config,
        performance_mode_guard=performance_mode_guard,
        run_consistency_guard=run_consistency_guard,
        processed_dataset=aggregate_dataset,
        chunk_session_path=chunk_session_path,
        chunk_output_dirs=tuple(artifact.chunk_output_dir for artifact in chunk_artifacts),
        completed_chunk_indices=completed_chunk_indices,
        resumed_chunk_indices=resumed_chunk_indices,
        resumed=bool(resumed_chunk_indices),
    )


def orchestrate_local_replay_export(
    request: ReplayOrchestratorRequest,
) -> ReplayOrchestratorResult:
    """Run the governed LOCAL_REPLAY export flow with chunking and clean resume."""

    if request.dataset is not None:
        request = request.model_copy(
            update={
                "dataset": _filter_dataset_by_window(
                    request.dataset,
                    window_start_ms=request.window_start_ms,
                    window_end_ms=request.window_end_ms,
                )
            }
        )
    output_dir = request.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if request.run_all_chunks:
        if request.dataset is None or request.input_kind is None:
            raise ValueError("LOCAL_REPLAY multi-chunk orchestration requires dataset and input_kind")
        if request.resume:
            resumed = _existing_multi_chunk_export_completed(
                output_dir,
                request=request,
            )
            if resumed is not None:
                return resumed
        chunk_results = tuple(
            _orchestrate_single_chunk_export(
                request.model_copy(
                    update={
                        "chunk_index": chunk_index,
                        "run_all_chunks": False,
                    }
                ),
                output_dir=_chunk_output_dir(output_dir, chunk_index),
            )
            for chunk_index in _resolve_chunk_indices(request)
        )
        return _aggregate_chunk_session(
            request,
            output_dir=output_dir,
            chunk_results=chunk_results,
        )
    return _orchestrate_single_chunk_export(request, output_dir=output_dir)


__all__ = [
    "ReplayChunkArtifact",
    "ReplayChunkSessionSummary",
    "ReplayOrchestratorRequest",
    "ReplayOrchestratorResult",
    "build_execution_input_from_dataset",
    "orchestrate_local_replay_export",
]
