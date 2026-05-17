"""First controlled Strategy Ladder run harness for Patch 6."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_data_factory import run_strategy_ladder_data_factory
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
    StrategyLadderFirstControlledRunArtifactInventory,
    StrategyLadderFirstControlledRunManifest,
    StrategyLadderFirstControlledRunRequest,
    StrategyLadderFirstControlledRunStageSummary,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_runner import (
    StrategyLadderRunResult,
    run_backtest_strategy_ladder,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderRequest


@dataclass(frozen=True)
class StrategyLadderFirstControlledRunResult:
    manifest: StrategyLadderFirstControlledRunManifest
    stage_summary: StrategyLadderFirstControlledRunStageSummary
    artifact_inventory: StrategyLadderFirstControlledRunArtifactInventory
    ladder_result: StrategyLadderRunResult | None


def _first_run_status_from_ladder_manifest(final_status: str, raw_window_status: str) -> str:
    if final_status == "STRATEGY_LADDER_MEASURED_ARTIFACTS_PRODUCED":
        return "FIRST_RUN_MEASURED_ARTIFACTS_PRODUCED"
    if raw_window_status == "RAW_WINDOW_NOT_PROVEN":
        return "FIRST_RUN_BLOCKED_BY_RAW_WINDOW_COVERAGE"
    if final_status in {
        "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE",
        "STRATEGY_LADDER_BLOCKED_BY_DEPTH_DATA",
        "STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA",
    }:
        return "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE"
    if final_status == "STRATEGY_LADDER_READY_TO_RUN":
        return "FIRST_RUN_READY_TO_EXECUTE"
    return "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE"


def _should_block_broad_run(request: StrategyLadderFirstControlledRunRequest) -> bool:
    """Legacy broad-run gate. Kept for backwards compatibility; prefer ``classify_date_guard``."""

    if request.allow_broad_run:
        return False
    if request.dry_run or request.fixture_mode or request.small_scope:
        return False
    if request.pairs or request.start or request.end:
        return False
    return True


def classify_date_guard(
    request: StrategyLadderFirstControlledRunRequest,
) -> tuple[str, ...]:
    """Return typed blocker codes for non-dry-run scope safety.

    The first controlled run can be promoted to a real backtest only when an
    explicit start/end window is supplied, OR when the operator explicitly
    accepts a broad scan via ``--allow-broad-run``. Dry-run / fixture-mode /
    small-scope flags continue to bypass these gates because they do not
    materialise gold artefacts.
    """

    if request.dry_run or request.fixture_mode or request.small_scope:
        return ()
    blockers: list[str] = []
    if not request.start or not request.end:
        if not request.allow_broad_run:
            blockers.append("DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN")
    if not request.pairs and not request.start and not request.end and not request.allow_broad_run:
        blockers.append("BROAD_RUN_REQUIRES_EXPLICIT_CONFIRMATION")
    if request.allow_broad_run and not (request.start and request.end) and not request.pairs:
        # ``allow_broad_run`` was set but no scope at all — preserve legacy guard.
        blockers.append("BROAD_RUN_REQUIRES_EXPLICIT_CONFIRMATION")
    # Dedupe while preserving order.
    deduped: list[str] = []
    for code in blockers:
        if code not in deduped:
            deduped.append(code)
    return tuple(deduped)


def _write_first_run_payloads(
    output_root: Path,
    *,
    manifest: StrategyLadderFirstControlledRunManifest,
    stage_summary: StrategyLadderFirstControlledRunStageSummary,
    blockers: tuple[str, ...],
    artifact_inventory: StrategyLadderFirstControlledRunArtifactInventory,
    request: StrategyLadderFirstControlledRunRequest | None = None,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_root / "first_run_manifest.json", manifest.model_dump(mode="json"))
    atomic_write_json(
        output_root / "first_run_blockers.json",
        {
            "schema_version": "v1",
            "run_id": manifest.run_id,
            "blockers": blockers,
            "created_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    atomic_write_json(
        output_root / "first_run_stage_summary.json",
        stage_summary.model_dump(mode="json"),
    )
    atomic_write_json(
        output_root / "first_run_artifact_inventory.json",
        artifact_inventory.model_dump(mode="json"),
    )
    # Patch 6 — refresh the typed backtest proof matrix after every first-run
    # payload write so the cockpit always reflects the latest evidence/gaps.
    from local_replay_runtime.backtest_proof_matrix import emit_backtest_proof_matrix

    emit_backtest_proof_matrix(
        output_root=output_root,
        run_id=manifest.run_id,
        pairs=request.pairs if request is not None else (),
        start=request.start if request is not None else "",
        end=request.end if request is not None else "",
        ml_mode=manifest.ml_mode_status,
    )
    from local_replay_runtime.run_class_component_coverage import (
        emit_run_class_component_coverage,
    )

    emit_run_class_component_coverage(
        output_root=output_root,
        run_id=manifest.run_id,
        ml_mode=manifest.ml_mode_status,
    )


def run_strategy_ladder_first_controlled_run(
    request: StrategyLadderFirstControlledRunRequest,
) -> StrategyLadderFirstControlledRunResult:
    """Run the bounded Patch 6 first controlled Strategy Ladder workflow."""

    if request.ml_mode == "ML_MODE_TRAINING_LAB_ONLY":
        raise ValueError("First controlled Strategy Ladder run forbids ML_MODE_TRAINING_LAB_ONLY")
    if request.ml_mode == "ML_MODE_OVERLAY_FROZEN" and (
        request.frozen_ml_artifact_path is None or not request.frozen_ml_artifact_hash
    ):
        raise ValueError("ML_MODE_OVERLAY_FROZEN requires artifact path and hash")

    output_root = request.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(tz=UTC)

    date_guard_blockers = classify_date_guard(request)
    if _should_block_broad_run(request) or date_guard_blockers:
        legacy_blockers = (
            ("BROAD_RUN_REQUIRES_ALLOW_BROAD_RUN", "NO_FULL_SCAN_DEFAULT")
            if _should_block_broad_run(request)
            else ()
        )
        blockers = tuple(dict.fromkeys((*legacy_blockers, *date_guard_blockers)))
        manifest = finalize_hashed_model(
            StrategyLadderFirstControlledRunManifest(
                run_id=request.run_id,
                first_run_status="FIRST_RUN_BLOCKED_BY_DATA_FACTORY",
                data_factory_status="DATA_FACTORY_NOT_PROVEN",
                feature_store_status="FEATURE_STORE_NOT_PROVEN",
                raw_window_status="RAW_WINDOW_NOT_PROVEN",
                orderbook_reconstruction_status="ORDERBOOK_RECONSTRUCTION_NOT_PROVEN",
                capital_profile_status="CAPITAL_PROFILE_NOT_PROVEN",
                ml_mode_status=request.ml_mode,
                blocker_codes=blockers,
                estimated_files_scanned=0,
                estimated_pairs_considered=len(request.pairs),
                allow_broad_run=request.allow_broad_run,
                dry_run=request.dry_run,
                created_at=created_at,
            )
        )
        stage_summary = finalize_hashed_model(
            StrategyLadderFirstControlledRunStageSummary(
                run_id=request.run_id,
                stage_statuses={
                    "data_factory_status": "DATA_FACTORY_NOT_PROVEN",
                    "first_run_status": manifest.first_run_status,
                },
                blockers=blockers,
                created_at=created_at,
            )
        )
        inventory = finalize_hashed_model(
            StrategyLadderFirstControlledRunArtifactInventory(
                run_id=request.run_id,
                artifact_refs={},
                created_at=created_at,
            )
        )
        _write_first_run_payloads(
            output_root,
            manifest=manifest,
            stage_summary=stage_summary,
            blockers=blockers,
            artifact_inventory=inventory,
            request=request,
        )
        return StrategyLadderFirstControlledRunResult(
            manifest=manifest,
            stage_summary=stage_summary,
            artifact_inventory=inventory,
            ladder_result=None,
        )

    data_factory_result = run_strategy_ladder_data_factory(
        StrategyLadderDataFactoryRequest(
            run_id=request.run_id,
            input_root=output_root,
            raw_roots=request.raw_roots,
            raw_source_manifest_path=request.raw_source_manifest_path,
            historical_metadata_root=request.historical_metadata_root,
            silver_root=request.silver_root,
            gold_root=request.gold_root,
            pairs=request.pairs,
            engines=request.engines,
            timeframes=request.timeframes,
            start=request.start,
            end=request.end,
            resume=False,
            dry_run=request.dry_run,
            small_scope=request.small_scope,
            max_gold_feature_rows=(
                request.engine_native_sample_size
                if request.small_scope and request.engine_native_sample_size > 0
                else 0
            ),
            # Audit 2026-05-07 (P0 CE/cost provenance) — propage l'opt-in
            # depuis FirstControlledRunRequest. Quand True, data_factory mesure
            # spread_bps reel depuis snapshots orderbook au lieu du hardcoded.
            use_measured_economic_provenance=(
                getattr(request, "use_measured_economic_provenance", False)
                or getattr(request, "engine_native_mode", False)
            ),
        )
    )
    available_pairs = data_factory_result.pair_universe_report.available_pairs
    selected_pairs = request.pairs or available_pairs
    blocker_codes = list(data_factory_result.manifest.blocker_codes)
    ladder_result: StrategyLadderRunResult | None = None

    if request.pairs and not available_pairs:
        blocker_codes.append("PAIR_UNIVERSE_EMPTY")
        first_run_status = "FIRST_RUN_BLOCKED_BY_DATA_FACTORY"
    elif request.dry_run:
        first_run_status = "FIRST_RUN_READY_TO_EXECUTE"
    elif data_factory_result.gold_feature_manifest.gold_feature_store_status not in {
        "FEATURE_STORE_READY",
        "GOLD_FEATURE_STORE_READY",
    }:
        blocker_codes.append("GOLD_FEATURE_STORE_NOT_READY")
        first_run_status = "FIRST_RUN_BLOCKED_BY_FEATURE_STORE"
    else:
        ladder_request = StrategyLadderRequest(
            run_id=request.run_id,
            input_root=output_root,
            feature_store_root=request.gold_root,
            raw_root=request.raw_roots[0] if request.raw_roots else (request.input_root / "raw"),
            raw_roots=request.raw_roots,
            raw_source_manifest_path=request.raw_source_manifest_path,
            silver_index_path=output_root / "silver_index.json",
            output_root=output_root,
            pairs=selected_pairs,
            engines=request.engines,
            capital_buckets=request.capital_buckets,
            timeframes=request.timeframes,
            start=request.start,
            end=request.end,
            dry_run=False,
            ml_mode=request.ml_mode,
            frozen_ml_artifact_path=request.frozen_ml_artifact_path,
            frozen_ml_artifact_hash=request.frozen_ml_artifact_hash,
            engine_native_mode=getattr(request, "engine_native_mode", False),
            engine_native_sample_size=getattr(
                request, "engine_native_sample_size", 10
            ),
        )
        run_dir = output_root / "backtest_strategy_ladder" / request.run_id

        def _progress_callback(progress_manifest) -> None:
            progress_blockers = tuple(
                dict.fromkeys(
                    (
                        *data_factory_result.manifest.blocker_codes,
                        *progress_manifest.blocker_codes,
                    )
                )
            )
            progress_stage_statuses = {
                "data_factory_status": data_factory_result.manifest.data_factory_status,
                "raw_source_status": data_factory_result.manifest.raw_source_status,
                "pair_universe_status": data_factory_result.manifest.pair_universe_status,
                "silver_index_status": data_factory_result.manifest.silver_index_status,
                "gold_feature_store_status": data_factory_result.manifest.gold_feature_store_status,
                "trade_schema_status": data_factory_result.manifest.trade_schema_status,
                "kline_schema_status": data_factory_result.manifest.kline_schema_status,
                "orderbook_reconstruction_status": data_factory_result.manifest.orderbook_schema_status,
                "ml_mode_status": request.ml_mode,
                "first_run_status": _first_run_status_from_ladder_manifest(
                    progress_manifest.final_status,
                    progress_manifest.raw_window_extraction_status,
                ),
                "feature_store_status": progress_manifest.feature_store_status,
                "candidate_export_status": progress_manifest.candidate_export_status,
                "raw_window_status": progress_manifest.raw_window_extraction_status,
                "detailed_replay_status": progress_manifest.detailed_replay_status,
                "capital_profile_status": progress_manifest.capital_profile_generation_status,
                "promotion_artifact_status": progress_manifest.promotion_artifact_status,
                "sample_size_survival_status": progress_manifest.sample_size_survival_status,
                "candidate_truth_status": progress_manifest.candidate_truth_status,
                "expected_edge_truth_status": progress_manifest.expected_edge_truth_status,
                "engine_native_status": progress_manifest.engine_native_status,
            }
            progress_manifest_root = finalize_hashed_model(
                StrategyLadderFirstControlledRunManifest(
                    run_id=request.run_id,
                    first_run_status=_first_run_status_from_ladder_manifest(
                        progress_manifest.final_status,
                        progress_manifest.raw_window_extraction_status,
                    ),
                    data_factory_status=data_factory_result.manifest.data_factory_status,
                    feature_store_status=progress_manifest.feature_store_status,
                    raw_window_status=progress_manifest.raw_window_extraction_status,
                    orderbook_reconstruction_status=data_factory_result.manifest.orderbook_schema_status,
                    capital_profile_status=progress_manifest.capital_profile_generation_status,
                    ml_mode_status=request.ml_mode,
                    blocker_codes=progress_blockers,
                    estimated_files_scanned=(
                        data_factory_result.manifest.files_processed
                        + data_factory_result.manifest.files_skipped
                    ),
                    estimated_pairs_considered=len(selected_pairs),
                    allow_broad_run=request.allow_broad_run,
                    dry_run=request.dry_run,
                    created_at=created_at,
                )
            )
            progress_stage_summary = finalize_hashed_model(
                StrategyLadderFirstControlledRunStageSummary(
                    run_id=request.run_id,
                    stage_statuses=progress_stage_statuses,
                    blockers=progress_blockers,
                    candidate_count=progress_manifest.candidate_count,
                    raw_window_count=progress_manifest.raw_window_count,
                    detailed_replay_count=progress_manifest.detailed_replay_count,
                    capital_profile_count=progress_manifest.capital_profile_count,
                    created_at=created_at,
                )
            )
            artifact_refs = {
                "data_factory_manifest": str((output_root / "data_factory_manifest.json").resolve()),
                "raw_source_report": str((output_root / "raw_source_report.json").resolve()),
                "pair_universe_report": str((output_root / "pair_universe_report.json").resolve()),
                "data_quality_report": str((output_root / "data_quality_report.json").resolve()),
                "silver_index": str((output_root / "silver_index.json").resolve()),
                "gold_feature_manifest": str((output_root / "gold_feature_manifest.json").resolve()),
                "compression_report": str((output_root / "compression_report.json").resolve()),
                "strategy_ladder_run_manifest": str((run_dir / "run_manifest.json").resolve()),
                "run_class_component_coverage": str((output_root / "run_class_component_coverage.json").resolve()),
            }
            summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
            if summary_path.is_file():
                artifact_refs["strategy_ladder_summary"] = str(summary_path.resolve())
            inventory = finalize_hashed_model(
                StrategyLadderFirstControlledRunArtifactInventory(
                    run_id=request.run_id,
                    artifact_refs=artifact_refs,
                    created_at=created_at,
                )
            )
            _write_first_run_payloads(
                output_root,
                manifest=progress_manifest_root,
                stage_summary=progress_stage_summary,
                blockers=progress_blockers,
                artifact_inventory=inventory,
                request=request,
            )

        ladder_result = run_backtest_strategy_ladder(
            ladder_request,
            progress_callback=_progress_callback,
        )
        blocker_codes.extend(ladder_result.run_manifest.blocker_codes)
        first_run_status = _first_run_status_from_ladder_manifest(
            ladder_result.run_manifest.final_status,
            ladder_result.run_manifest.raw_window_extraction_status,
        )

    stage_statuses = {
        "data_factory_status": data_factory_result.manifest.data_factory_status,
        "raw_source_status": data_factory_result.manifest.raw_source_status,
        "pair_universe_status": data_factory_result.manifest.pair_universe_status,
        "silver_index_status": data_factory_result.manifest.silver_index_status,
        "gold_feature_store_status": data_factory_result.manifest.gold_feature_store_status,
        "trade_schema_status": data_factory_result.manifest.trade_schema_status,
        "kline_schema_status": data_factory_result.manifest.kline_schema_status,
        "orderbook_reconstruction_status": data_factory_result.manifest.orderbook_schema_status,
        "ml_mode_status": request.ml_mode,
        "first_run_status": first_run_status,
    }
    if ladder_result is not None:
        stage_statuses.update(
            {
                "feature_store_status": ladder_result.run_manifest.feature_store_status,
                "candidate_export_status": ladder_result.run_manifest.candidate_export_status,
                "raw_window_status": ladder_result.run_manifest.raw_window_extraction_status,
                "detailed_replay_status": ladder_result.run_manifest.detailed_replay_status,
                "capital_profile_status": ladder_result.run_manifest.capital_profile_generation_status,
                "promotion_artifact_status": ladder_result.run_manifest.promotion_artifact_status,
                "sample_size_survival_status": ladder_result.run_manifest.sample_size_survival_status,
                "candidate_truth_status": getattr(
                    ladder_result.run_manifest,
                    "candidate_truth_status",
                    "CANDIDATE_TRUTH_NOT_PROVEN",
                ),
                "expected_edge_truth_status": getattr(
                    ladder_result.run_manifest,
                    "expected_edge_truth_status",
                    "EXPECTED_EDGE_TRUTH_NOT_PROVEN",
                ),
                "engine_native_status": getattr(
                    ladder_result.run_manifest,
                    "engine_native_status",
                    "ENGINE_NATIVE_NOT_REQUESTED",
                ),
            }
        )
    blockers = tuple(dict.fromkeys(str(item) for item in blocker_codes if item))
    manifest = finalize_hashed_model(
        StrategyLadderFirstControlledRunManifest(
            run_id=request.run_id,
            first_run_status=first_run_status,
            data_factory_status=data_factory_result.manifest.data_factory_status,
            feature_store_status=(
                ladder_result.run_manifest.feature_store_status
                if ladder_result is not None
                else data_factory_result.gold_feature_manifest.gold_feature_store_status
            ),
            raw_window_status=(
                ladder_result.run_manifest.raw_window_extraction_status
                if ladder_result is not None
                else "RAW_WINDOW_NOT_PROVEN"
            ),
            orderbook_reconstruction_status=data_factory_result.manifest.orderbook_schema_status,
            capital_profile_status=(
                ladder_result.run_manifest.capital_profile_generation_status
                if ladder_result is not None
                else "CAPITAL_PROFILE_NOT_PROVEN"
            ),
            ml_mode_status=request.ml_mode,
            blocker_codes=blockers,
            estimated_files_scanned=(
                data_factory_result.manifest.files_processed + data_factory_result.manifest.files_skipped
            ),
            estimated_pairs_considered=len(selected_pairs),
            allow_broad_run=request.allow_broad_run,
            dry_run=request.dry_run,
            created_at=created_at,
        )
    )
    stage_summary = finalize_hashed_model(
        StrategyLadderFirstControlledRunStageSummary(
            run_id=request.run_id,
            stage_statuses=stage_statuses,
            blockers=blockers,
            candidate_count=(ladder_result.run_manifest.candidate_count if ladder_result is not None else 0),
            raw_window_count=(
                getattr(ladder_result.run_manifest, "raw_window_count", 0)
                if ladder_result is not None
                else 0
            ),
            detailed_replay_count=(ladder_result.run_manifest.detailed_replay_count if ladder_result is not None else 0),
            capital_profile_count=(ladder_result.run_manifest.capital_profile_count if ladder_result is not None else 0),
            created_at=created_at,
        )
    )
    artifact_refs = {
        "data_factory_manifest": str((output_root / "data_factory_manifest.json").resolve()),
        "raw_source_report": str((output_root / "raw_source_report.json").resolve()),
        "pair_universe_report": str((output_root / "pair_universe_report.json").resolve()),
        "data_quality_report": str((output_root / "data_quality_report.json").resolve()),
        "silver_index": str((output_root / "silver_index.json").resolve()),
                "gold_feature_manifest": str((output_root / "gold_feature_manifest.json").resolve()),
                "compression_report": str((output_root / "compression_report.json").resolve()),
                "run_class_component_coverage": str((output_root / "run_class_component_coverage.json").resolve()),
            }
    if ladder_result is not None:
        run_dir = output_root / "backtest_strategy_ladder" / request.run_id
        artifact_refs.update(
            {
                "strategy_ladder_run_manifest": str((run_dir / "run_manifest.json").resolve()),
                "strategy_ladder_summary": str((run_dir / "reports" / "strategy_ladder_summary.json").resolve()),
                "engine_matrix": str((run_dir / "reports" / "engine_matrix.json").resolve()),
                "pair_matrix": str((run_dir / "reports" / "pair_matrix.json").resolve()),
                "timeframe_matrix": str((run_dir / "reports" / "timeframe_matrix.json").resolve()),
                "trade_detail_ledger": str((run_dir / "trade_detail_ledger.jsonl").resolve()),
                "refusal_ledger": str((run_dir / "refusal_ledger.jsonl").resolve()),
                "loss_analysis_ledger": str((run_dir / "loss_analysis_ledger.jsonl").resolve()),
                "candidate_replay_window_root": str((run_dir / "candidate_replay_windows").resolve()),
            }
        )
    artifact_inventory = finalize_hashed_model(
        StrategyLadderFirstControlledRunArtifactInventory(
            run_id=request.run_id,
            artifact_refs=artifact_refs,
            created_at=created_at,
        )
    )
    _write_first_run_payloads(
        output_root,
        manifest=manifest,
        stage_summary=stage_summary,
        blockers=blockers,
        artifact_inventory=artifact_inventory,
        request=request,
    )
    return StrategyLadderFirstControlledRunResult(
        manifest=manifest,
        stage_summary=stage_summary,
        artifact_inventory=artifact_inventory,
        ladder_result=ladder_result,
    )


__all__ = [
    "StrategyLadderFirstControlledRunResult",
    "run_strategy_ladder_first_controlled_run",
]
