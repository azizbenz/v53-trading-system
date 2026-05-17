"""Backtest/replay compatibility manifest over the governed Strategy Ladder data rail."""

from __future__ import annotations

from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.raw_data_processing_contracts import (
    BacktestReplayDatasetManifest,
    GoldMicrostructureFeatureManifest,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)


BACKTEST_REPLAY_DATASET_MANIFEST_FILENAME = "backtest_replay_dataset_manifest.json"
RUNTIME_FEATURE_PARITY_MANIFEST_FILENAME = "runtime_feature_parity_manifest.json"


def build_backtest_replay_dataset_manifest(
    *,
    pair_scope: tuple[str, ...],
    timeframe_scope: tuple[str, ...],
    silver_index: tuple[StrategyLadderSilverIndexEntry, ...],
    gold_manifest: GoldMicrostructureFeatureManifest,
    raw_window_refs: tuple[str, ...] = (),
) -> BacktestReplayDatasetManifest:
    """Build one backtest/replay compatibility surface over shared refs."""

    metadata_refs = tuple(
        sorted(
            {
                entry.path
                for entry in silver_index
                if entry.data_type == "metadata" and entry.path
            }
        )
    )
    gold_refs = gold_manifest.output_paths
    status = "BACKTEST_REPLAY_DATASET_NOT_READY"
    blockers: list[str] = []
    if not gold_refs:
        blockers.append("BACKTEST_GOLD_FEATURE_REFS_EMPTY")
    if not silver_index:
        blockers.append("BACKTEST_SILVER_INDEX_EMPTY")
    if gold_refs and silver_index:
        status = "BACKTEST_REPLAY_DATASET_READY"
    return finalize_hashed_model(
        BacktestReplayDatasetManifest(
            status=status,
            pair_scope=pair_scope,
            timeframe_scope=timeframe_scope,
            candidate_feature_snapshot_refs=gold_refs,
            raw_window_refs=raw_window_refs,
            silver_index_ref="silver_index.json",
            gold_feature_refs=gold_refs,
            venue_metadata_refs=metadata_refs,
            feature_hash=gold_manifest.feature_hash,
            replay_compatibility_status="FEATURE_PARITY_NOT_PROVEN",
            blocker_codes=tuple(dict.fromkeys(blockers)),
        )
    )


def write_backtest_replay_dataset_manifest(
    output_dir: Path,
    manifest: BacktestReplayDatasetManifest,
) -> str:
    """Write the backtest/replay consumer manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / BACKTEST_REPLAY_DATASET_MANIFEST_FILENAME
    atomic_write_json(path, manifest.model_dump(mode="json"), indent=2)
    return str(path.resolve())


__all__ = [
    "BACKTEST_REPLAY_DATASET_MANIFEST_FILENAME",
    "RUNTIME_FEATURE_PARITY_MANIFEST_FILENAME",
    "build_backtest_replay_dataset_manifest",
    "write_backtest_replay_dataset_manifest",
]
