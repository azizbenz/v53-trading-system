"""Execution pipeline for governed LOCAL_REPLAY orchestration."""

from __future__ import annotations

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
from local_replay_runtime.replay_execution_contracts import (
    ReplayExecutionEvaluationRequest,
    ReplayExecutionEvaluationResult,
)
from local_replay_runtime.replay_execution_runtime import (
    build_replay_parity_diagnostics,
    evaluate_replay_execution,
)
from local_replay_runtime.replay_executor import (
    ReplayExecutionInput,
    ReplayExecutionResult,
    execute_local_replay_export,
)
from local_replay_runtime.replay_metrics_collector import ReplayMetricsSummary
from local_replay_runtime.replay_orchestrator_chunking import (
    _chunk_output_dir,
    _filter_dataset_by_window,
    _resolve_chunk_indices,
    _slice_dataset_for_chunk,
)
from local_replay_runtime.replay_orchestrator_io import (
    _load_existing_resume_metadata,
    _read_dtr_records,
    _validate_resume_request_against_existing_export,
)
from local_replay_runtime.replay_orchestrator_models import (
    ReplayChunkArtifact,
    ReplayChunkSessionSummary,
    ReplayOrchestratorRequest,
    ReplayOrchestratorResult,
)
from local_replay_runtime.replay_orchestrator_resume import (
    _existing_export_completed,
    _existing_multi_chunk_export_completed,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_scope_identity import build_replay_scope_identity
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
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


def _evaluate_dataset_execution(
    dataset: HistoricalReplayDataset,
    *,
    execution_label: str,
    execution_runtime_projection_path: str | None = None,
) -> ReplayExecutionEvaluationResult:
    return evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=dataset,
            execution_label=execution_label,
            execution_runtime_projection_path=execution_runtime_projection_path,
        )
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
    execution_runtime_projection_path: str | None = None,
) -> ReplayExecutionInput:
    """Build the governed replay execution payload directly from a normalized dataset."""

    clock = build_replay_clock(
        dataset,
        clock_id=f"clock-{run_id}",
        mode=performance_mode,
    )
    execution_evaluation = _evaluate_dataset_execution(
        dataset,
        execution_label=performance_mode,
        execution_runtime_projection_path=execution_runtime_projection_path,
    )
    dtr_records = execution_evaluation.dtr_records
    auto_materialize_feature_locks = dataset.source == "historical_snapshot_router"
    feature_bridge_payload = build_feature_bridge_payload(
        dataset,
        auto_materialize_feature_locks=auto_materialize_feature_locks,
    )
    parity_diagnostics_payload = execution_evaluation.parity_diagnostics_payload
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
            "execution_provider="
            f"{execution_evaluation.request.provider.provider_kind.value}:"
            f"{execution_evaluation.request.provider.provider_version}",
            (
                "execution_runtime_projection="
                f"{execution_runtime_projection_path}"
            )
            if execution_runtime_projection_path is not None
            else "execution_runtime_projection=none",
            f"dataset_source={dataset.source_path}",
            f"record_count={dataset.record_count}",
        ),
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
        execution_runtime_projection_path=(
            None
            if request.execution_runtime_projection_path is None
            else str(request.execution_runtime_projection_path)
        ),
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

    reference_dtr_records = _evaluate_dataset_execution(
        processed_dataset,
        execution_label="shadow_fidelity_mode",
        execution_runtime_projection_path=(
            None
            if request.execution_runtime_projection_path is None
            else str(request.execution_runtime_projection_path)
        ),
    ).dtr_records
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

    aggregate_dataset, combined_dtr_records, aggregate_input = _build_aggregate_execution_input(
        request,
        chunk_results=chunk_results,
    )
    aggregate_execution_result = execute_local_replay_export(output_dir, aggregate_input)
    (
        session_config_path,
        performance_mode_guard_path,
        run_consistency_guard_path,
        session_config,
        performance_mode_guard,
        run_consistency_guard,
    ) = _persist_aggregate_session_state(
        request,
        output_dir=output_dir,
        aggregate_dataset=aggregate_dataset,
        aggregate_input=aggregate_input,
        aggregate_execution_result=aggregate_execution_result,
        combined_dtr_records=combined_dtr_records,
    )
    (
        chunk_session_path,
        chunk_artifacts,
        completed_chunk_indices,
        resumed_chunk_indices,
    ) = _build_chunk_session_summary(
        request,
        output_dir=output_dir,
        chunk_results=chunk_results,
    )

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


def _build_aggregate_execution_input(
    request: ReplayOrchestratorRequest,
    *,
    chunk_results: tuple[ReplayOrchestratorResult, ...],
) -> tuple[HistoricalReplayDataset, tuple[DTRRecord, ...], ReplayExecutionInput]:
    if request.dataset is None:
        raise ValueError("Chunk session aggregation requires a governed dataset")
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
        execution_runtime_projection_path=(
            None
            if request.execution_runtime_projection_path is None
            else str(request.execution_runtime_projection_path)
        ),
    )
    aggregate_input = ReplayExecutionInput(
        run_manifest=aggregate_seed.run_manifest,
        total_opportunities=aggregate_dataset.record_count,
        dtr_records=combined_dtr_records,
        feature_bridge_payload=build_feature_bridge_payload(
            aggregate_dataset,
            auto_materialize_feature_locks=(
                aggregate_dataset.source == "historical_snapshot_router"
            ),
        ),
        parity_diagnostics_payload=build_replay_parity_diagnostics(
            aggregate_dataset,
            combined_dtr_records,
        ).model_dump(mode="json"),
        review_notes=(
            "session_scope=multi_chunk",
            f"chunk_count={request.chunk_count}",
            "completed_chunks="
            + ",".join(str(result.session_config.chunk_index) for result in chunk_results),
            *(
                f"chunk_{result.session_config.chunk_index}_dir={result.export_result.export_result.export_dir}"
                for result in chunk_results
            ),
        ),
    )
    return aggregate_dataset, combined_dtr_records, aggregate_input


def _persist_aggregate_session_state(
    request: ReplayOrchestratorRequest,
    *,
    output_dir: Path,
    aggregate_dataset: HistoricalReplayDataset,
    aggregate_input: ReplayExecutionInput,
    aggregate_execution_result: ReplayExecutionResult,
    combined_dtr_records: tuple[DTRRecord, ...],
) -> tuple[
    Path,
    Path,
    Path,
    ReplaySessionConfig,
    PerformanceModeGuardReport,
    RunConsistencyGuardReport,
]:
    if request.input_kind is None:
        raise ValueError("Chunk session aggregation requires a governed input_kind")
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

    reference_dtr_records = _evaluate_dataset_execution(
        aggregate_dataset,
        execution_label="shadow_fidelity_mode",
        execution_runtime_projection_path=(
            None
            if request.execution_runtime_projection_path is None
            else str(request.execution_runtime_projection_path)
        ),
    ).dtr_records
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

    return (
        session_config_path,
        performance_mode_guard_path,
        run_consistency_guard_path,
        session_config,
        performance_mode_guard,
        run_consistency_guard,
    )


def _build_chunk_session_summary(
    request: ReplayOrchestratorRequest,
    *,
    output_dir: Path,
    chunk_results: tuple[ReplayOrchestratorResult, ...],
) -> tuple[Path, tuple[ReplayChunkArtifact, ...], tuple[int, ...], tuple[int, ...]]:
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
    replay_scope_identity = build_replay_scope_identity(
        datasets=tuple(result.processed_dataset for result in chunk_results),
        input_kind=request.input_kind,
        performance_mode=request.performance_mode,
        chunk_count=request.chunk_count,
        selected_chunk_indices=_resolve_chunk_indices(request),
        requested_window_start_ms=request.window_start_ms,
        requested_window_end_ms=request.window_end_ms,
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
        replay_scope_identity=replay_scope_identity,
        chunk_artifacts=chunk_artifacts,
        summary=(
            f"run_id={request.run_id} / chunk_count={request.chunk_count} / "
            f"completed={len(completed_chunk_indices)} / aggregate_ready=yes"
        ),
    )
    chunk_session_path = output_dir / "replay_chunk_session.json"
    atomic_write_json(chunk_session_path, chunk_session.model_dump(mode="json"))
    return (
        chunk_session_path,
        chunk_artifacts,
        completed_chunk_indices,
        resumed_chunk_indices,
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
    "build_execution_input_from_dataset",
    "orchestrate_local_replay_export",
]
