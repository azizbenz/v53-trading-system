"""Run a governed Local IA Lab post-trade review from exported replay DTR records."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backtest_artifact_import.export_dir_bridge import discover_local_replay_export
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from interface_contracts.domain_types import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime.replay_dtr_exporter import load_replay_dtr_records
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from meta_learning import (
    TradeLearningInput,
    build_trade_loss_attribution_report,
    run_meta_learning_review,
)
from meta_learning.monitoring_projection import build_build9x_projection
from meta_minimal import build_meta_runtime_result_from_records
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


_ENGINE_TO_STRATEGY: dict[str, StrategyClassification] = {
    "engine_a": StrategyClassification.A_VARIANT,
    "engine_b": StrategyClassification.B_VARIANT,
    "engine_c": StrategyClassification.C_CANDIDATE,
    "engine_d": StrategyClassification.D_CANDIDATE,
}


class GovernedPostTradeInputSummary(BaseModel, frozen=True):
    """Future-facing audit summary of the Local IA Lab review input surface."""

    correlation_id: str = Field(..., min_length=1)
    source_kind: str = Field(..., min_length=1)
    replay_dtr_ref: str = Field(..., min_length=1)
    export_dir: str | None = None
    run_id: str | None = None
    artifact_hash: str | None = None
    dataset_manifest_id: str | None = None
    profile_scope: str | None = None
    source_runtime_mode: str = Field(..., min_length=1)
    strategy_id: str | None = None
    strategy_version: str | None = None
    lineage_version: str | None = None
    feature_set_version: str | None = None
    transform_set_version: str | None = None
    tested_pairs: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    review_export_ref: str | None = None
    feature_bridge_ref: str | None = None
    parity_diagnostics_ref: str | None = None
    replay_metrics_ref: str | None = None
    selected_pair: str | None = None
    selected_engine_id: str | None = None
    filtered_record_count: int = Field(..., ge=0)
    total_opportunities: int | None = Field(default=None, ge=0)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a governed Local IA Lab meta-learning review from replay DTR exports.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--replay-dtr",
        help="Path to governed replay_dtr.json or replay_dtr.jsonl",
    )
    source_group.add_argument(
        "--export-dir",
        help="Path to a governed LOCAL_REPLAY export directory containing replay sidecars",
    )
    parser.add_argument("--correlation-id", required=True, help="Governed review correlation id")
    parser.add_argument("--pair", help="Optional pair selector applied before review generation")
    parser.add_argument("--engine-id", help="Optional engine selector applied before review generation")
    parser.add_argument(
        "--strategy-classification",
        choices=tuple(item.value for item in StrategyClassification),
        help="Optional strategy classification; defaults from the final engine_id",
    )
    parser.add_argument(
        "--source-runtime-mode",
        choices=tuple(item.value for item in RuntimeMode),
        default=RuntimeMode.LOCAL_REPLAY.value,
        help="Source runtime mode carried by the governed review input",
    )
    parser.add_argument(
        "--source-version",
        default="local_lab_post_trade_review.v1",
        help="Governed source_version recorded on the review input",
    )
    parser.add_argument("--notes", default="", help="Optional governed notes")
    parser.add_argument("--output-dir", default="build/local_lab_post_trade_review", help="Directory for outputs")
    parser.add_argument("--state-dir", help="Optional append-only state dir for meta_learning persistence")
    parser.add_argument(
        "--near-miss-threshold",
        type=float,
        default=0.70,
        help="Near-miss threshold forwarded to meta_learning.review_orchestrator",
    )
    parser.add_argument(
        "--total-opportunities",
        type=int,
        help="Optional governed total opportunities for DTR coverage reconstruction",
    )
    return parser.parse_args(argv)


def _resolve_governed_review_source(
    args: argparse.Namespace,
) -> tuple[tuple[DTRRecord, ...], GovernedPostTradeInputSummary, ReplayRunManifest | None]:
    if args.export_dir is not None:
        discovery = discover_local_replay_export(Path(args.export_dir))
        records = load_replay_dtr_records(discovery.payload_bundle.replay_dtr_ref)
        total_opportunities = args.total_opportunities
        if total_opportunities is None and discovery.run_manifest.record_count > 0:
            total_opportunities = discovery.run_manifest.record_count
        return (
            records,
            GovernedPostTradeInputSummary(
                correlation_id=args.correlation_id,
                source_kind="export_dir",
                replay_dtr_ref=discovery.payload_bundle.replay_dtr_ref,
                export_dir=str(discovery.export_dir),
                run_id=discovery.run_manifest.run_id,
                artifact_hash=discovery.run_manifest.artifact_hash,
                dataset_manifest_id=discovery.run_manifest.dataset_manifest_id,
                profile_scope=discovery.run_manifest.profile_scope.value,
                source_runtime_mode=discovery.run_manifest.runtime_mode.value,
                strategy_id=discovery.run_manifest.strategy_id,
                strategy_version=discovery.run_manifest.strategy_version,
                lineage_version=discovery.run_manifest.lineage_version,
                feature_set_version=discovery.run_manifest.feature_set_version,
                transform_set_version=discovery.run_manifest.transform_set_version,
                tested_pairs=discovery.run_manifest.tested_pairs,
                engine_scope=discovery.run_manifest.engine_scope,
                review_export_ref=discovery.payload_bundle.review_export_ref,
                feature_bridge_ref=discovery.payload_bundle.feature_bridge_ref,
                parity_diagnostics_ref=discovery.payload_bundle.parity_diagnostics_ref,
                replay_metrics_ref=discovery.payload_bundle.replay_metrics_ref,
                selected_pair=args.pair,
                selected_engine_id=args.engine_id,
                filtered_record_count=len(records),
                total_opportunities=total_opportunities,
            ),
            discovery.run_manifest,
        )

    replay_dtr_ref = str(Path(args.replay_dtr).resolve())
    records = load_replay_dtr_records(replay_dtr_ref)
    return (
        records,
        GovernedPostTradeInputSummary(
            correlation_id=args.correlation_id,
            source_kind="replay_dtr",
            replay_dtr_ref=replay_dtr_ref,
            source_runtime_mode=RuntimeMode(args.source_runtime_mode).value,
            selected_pair=args.pair,
            selected_engine_id=args.engine_id,
            filtered_record_count=len(records),
            total_opportunities=args.total_opportunities,
        ),
        None,
    )


def _filter_records(
    records: tuple[DTRRecord, ...],
    *,
    pair: str | None,
    engine_id: str | None,
) -> tuple[DTRRecord, ...]:
    filtered = records
    if pair is not None:
        filtered = tuple(record for record in filtered if record.pair == pair)
        if not filtered:
            raise ValueError(f"No replay DTR records remain after pair filter {pair!r}")
    if engine_id is not None:
        filtered = tuple(record for record in filtered if record.engine_id == engine_id)
        if not filtered:
            raise ValueError(f"No replay DTR records remain after engine filter {engine_id!r}")
    return filtered


def _require_single_value(
    records: tuple[DTRRecord, ...],
    attribute: str,
) -> str:
    values = tuple(dict.fromkeys(getattr(record, attribute) for record in records))
    if len(values) != 1:
        raise ValueError(
            f"Post-trade review requires a single {attribute}; got {values}. "
            f"Use --pair and/or --engine-id to scope the replay DTR export first."
        )
    return str(values[0])


def _resolve_strategy_classification(
    engine_id: str,
    explicit: str | None,
) -> StrategyClassification:
    if explicit is not None:
        return StrategyClassification(explicit)
    if engine_id not in _ENGINE_TO_STRATEGY:
        raise ValueError(
            f"No default strategy classification is defined for engine_id {engine_id!r}; "
            "pass --strategy-classification explicitly."
        )
    return _ENGINE_TO_STRATEGY[engine_id]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    records, source_summary, run_manifest = _resolve_governed_review_source(args)
    scoped_records = _filter_records(records, pair=args.pair, engine_id=args.engine_id)
    if not scoped_records:
        raise ValueError("Governed post-trade review requires at least one replay DTR record")

    pair = _require_single_value(scoped_records, "pair")
    engine_id = _require_single_value(scoped_records, "engine_id")
    strategy_classification = _resolve_strategy_classification(engine_id, args.strategy_classification)
    total_opportunities = source_summary.total_opportunities
    if total_opportunities is None and run_manifest is not None and run_manifest.record_count > 0:
        total_opportunities = run_manifest.record_count

    meta_result = build_meta_runtime_result_from_records(
        scoped_records,
        total_opportunities=total_opportunities,
    )
    trade_input = TradeLearningInput(
        correlation_id=args.correlation_id,
        dtr_ids=tuple(record.dtr_id for record in scoped_records),
        pair=pair,
        engine_id=engine_id,
        profile=ProfileId.COMPLETE,
        source_runtime_mode=RuntimeMode(args.source_runtime_mode),
        strategy_classification=strategy_classification,
        source_version=args.source_version,
        notes=args.notes,
    )
    bundle = run_meta_learning_review(
        trade_input,
        dtr_records=scoped_records,
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
        near_miss_threshold=args.near_miss_threshold,
        state_dir=Path(args.state_dir) if args.state_dir else None,
    )
    projection = build_build9x_projection(bundle)
    loss_attribution = build_trade_loss_attribution_report(
        args.correlation_id,
        dtr_records=scoped_records,
        diagnostics=bundle.diagnostics,
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
    )

    output_dir = Path(args.output_dir)
    meta_runtime_path = output_dir / "meta_runtime_result.json"
    bundle_path = output_dir / "meta_learning_review.bundle.json"
    review_markdown_path = output_dir / "meta_learning_review.md"
    projection_path = output_dir / "meta_learning_projection.json"
    loss_attribution_path = output_dir / "trade_loss_attribution.json"
    input_summary_path = output_dir / "governed_input_summary.json"

    resolved_input_summary = source_summary.model_copy(
        update={
            "selected_pair": pair,
            "selected_engine_id": engine_id,
            "filtered_record_count": len(scoped_records),
            "total_opportunities": total_opportunities,
        }
    )

    atomic_write_json(meta_runtime_path, meta_result.model_dump(mode="json"), indent=2)
    atomic_write_json(bundle_path, bundle.model_dump(mode="json"), indent=2)
    atomic_write_text(review_markdown_path, bundle.review_export.markdown_body, encoding="utf-8")
    atomic_write_json(projection_path, projection.model_dump(mode="json"), indent=2)
    atomic_write_json(loss_attribution_path, loss_attribution.model_dump(mode="json"), indent=2)
    atomic_write_json(input_summary_path, resolved_input_summary.model_dump(mode="json"), indent=2)

    print(f"Meta runtime JSON: {meta_runtime_path}")
    print(f"Review bundle JSON: {bundle_path}")
    print(f"Review markdown: {review_markdown_path}")
    print(f"Monitoring projection JSON: {projection_path}")
    print(f"Trade loss attribution JSON: {loss_attribution_path}")
    print(f"Governed input summary JSON: {input_summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
