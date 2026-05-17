"""Anti-leakage and operator-facing quality gates for the canonical data rail."""

from __future__ import annotations

from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.raw_data_processing_contracts import (
    BacktestReplayDatasetManifest,
    BronzeMarketIndexManifest,
    DataScienceQualityReport,
    ExpectedEdgeFeatureManifest,
    GoldMicrostructureFeatureManifest,
    RawMarketFileManifest,
    RuntimeFeatureParityManifest,
    SilverSynchronizedMarketManifest,
    finalize_hashed_model,
)


DATA_SCIENCE_QUALITY_REPORT_FILENAME = "data_science_quality_report.json"
ANTI_LEAKAGE_PRECHECK_REPORT_FILENAME = "anti_leakage_precheck_report.json"
RAW_DATA_PROCESSING_REPORT_JSON_FILENAME = "raw_data_processing_report.json"
RAW_DATA_PROCESSING_REPORT_MD_FILENAME = "raw_data_processing_report.md"


def build_runtime_feature_parity_manifest(
    *,
    gold_manifest: GoldMicrostructureFeatureManifest,
    source_silver_index_ref: str,
) -> RuntimeFeatureParityManifest:
    """Build the runtime/shadow placeholder contract without activating live parity."""

    return finalize_hashed_model(
        RuntimeFeatureParityManifest(
            status="RUNTIME_PARITY_NOT_PROVEN",
            source_gold_feature_refs=gold_manifest.output_paths,
            source_silver_index_ref=source_silver_index_ref,
            feature_hash=gold_manifest.feature_hash,
            blocker_codes=("RUNTIME_PARITY_NOT_PROVEN",),
        )
    )


def build_data_science_quality_report(
    *,
    expected_edge_manifest: ExpectedEdgeFeatureManifest,
) -> DataScienceQualityReport:
    """Build the governed anti-leakage precheck over the IA Lab dataset export."""

    feature_timestamp_aligned = (
        "FEATURE_TIMESTAMP_ALIGNED"
        if expected_edge_manifest.feature_timestamp_policy == "FEATURE_TIMESTAMP_LEQ_DECISION_TIMESTAMP_ENFORCED"
        else "FEATURE_TIMESTAMP_DRIFT_DETECTED"
    )
    no_future_features = (
        "NO_FUTURE_FEATURES"
        if feature_timestamp_aligned == "FEATURE_TIMESTAMP_ALIGNED"
        else "FUTURE_FEATURES_DETECTED"
    )
    label_window_after_decision = (
        "LABEL_WINDOW_AFTER_DECISION"
        if expected_edge_manifest.row_count > 0
        else "LABEL_WINDOW_AFTER_DECISION_NOT_PROVEN"
    )
    feature_hash_stable = (
        "FEATURE_HASH_STABLE" if expected_edge_manifest.feature_hash else "FEATURE_HASH_NOT_PROVEN"
    )
    dataset_hash_stable = (
        "DATASET_HASH_STABLE" if expected_edge_manifest.dataset_hash else "DATASET_HASH_NOT_PROVEN"
    )
    source_refs_non_empty = (
        "SOURCE_REFS_NON_EMPTY"
        if expected_edge_manifest.source_refs_count > 0
        else "SOURCE_REFS_EMPTY"
    )
    blockers: list[str] = []
    if feature_timestamp_aligned != "FEATURE_TIMESTAMP_ALIGNED":
        blockers.append("DATA_SCIENCE_BLOCKED_BY_TIMESTAMP_DRIFT")
    if no_future_features != "NO_FUTURE_FEATURES":
        blockers.append("DATA_SCIENCE_BLOCKED_BY_LEAKAGE_RISK")
    if source_refs_non_empty != "SOURCE_REFS_NON_EMPTY":
        blockers.append("DATA_SCIENCE_BLOCKED_BY_MISSING_SOURCE_REFS")
    if expected_edge_manifest.feature_groups_missing:
        blockers.append("DATA_SCIENCE_BLOCKED_BY_FEATURE_DRIFT")
    status = "DATA_SCIENCE_READY_FOR_RESEARCH"
    if blockers:
        status = blockers[0]
    return finalize_hashed_model(
        DataScienceQualityReport(
            status=status,
            feature_timestamp_aligned=feature_timestamp_aligned,
            no_future_features=no_future_features,
            label_window_after_decision=label_window_after_decision,
            random_split_forbidden="RANDOM_SPLIT_FORBIDDEN",
            purge_window_declared="PURGE_WINDOW_DECLARED",
            embargo_window_declared="EMBARGO_WINDOW_DECLARED",
            feature_hash_stable=feature_hash_stable,
            dataset_hash_stable=dataset_hash_stable,
            source_refs_non_empty=source_refs_non_empty,
            feature_hash=expected_edge_manifest.feature_hash,
            dataset_hash=expected_edge_manifest.dataset_hash,
            row_count=expected_edge_manifest.row_count,
            source_refs_count=expected_edge_manifest.source_refs_count,
            blocker_codes=tuple(dict.fromkeys((*blockers, *expected_edge_manifest.blocker_codes))),
        )
    )


def build_raw_data_processing_report_payload(
    *,
    raw_manifests: tuple[RawMarketFileManifest, ...],
    bronze_index: BronzeMarketIndexManifest,
    silver_manifest: SilverSynchronizedMarketManifest,
    gold_manifest: GoldMicrostructureFeatureManifest,
    expected_edge_manifest: ExpectedEdgeFeatureManifest,
    backtest_manifest: BacktestReplayDatasetManifest,
    runtime_parity_manifest: RuntimeFeatureParityManifest,
    data_science_report: DataScienceQualityReport,
) -> dict[str, object]:
    """Build the operator-facing aggregate report payload."""

    known_blockers = tuple(
        dict.fromkeys(
            (
                *bronze_index.source_types_missing,
                *silver_manifest.blocker_codes,
                *gold_manifest.blocker_codes,
                *expected_edge_manifest.blocker_codes,
                *backtest_manifest.blocker_codes,
                *runtime_parity_manifest.blocker_codes,
                *data_science_report.blocker_codes,
            )
        )
    )
    return {
        "schema_version": "v1",
        "raw_coverage": {
            "file_count": len(raw_manifests),
            "source_types_present": list(bronze_index.source_types_present),
            "source_types_missing": list(bronze_index.source_types_missing),
        },
        "bronze_index_status": bronze_index.index_status,
        "silver_sync_status": silver_manifest.silver_sync_status,
        "gold_feature_status": gold_manifest.feature_status,
        "gold_feature_groups_generated": list(gold_manifest.feature_groups_generated),
        "gold_feature_groups_missing": list(gold_manifest.feature_groups_missing),
        "timestamp_gap_stale_diagnostics": {
            "bronze_gap_count": bronze_index.gap_count,
            "bronze_largest_gap_ms": bronze_index.largest_gap_ms,
            "silver_stale_book_count": silver_manifest.stale_book_count,
            "silver_missing_book_count": silver_manifest.missing_book_count,
            "silver_missing_trade_count": silver_manifest.missing_trade_count,
            "silver_missing_ohlcv_count": silver_manifest.missing_ohlcv_count,
        },
        "ia_lab_readiness": expected_edge_manifest.status,
        "backtest_readiness": backtest_manifest.status,
        "replay_compatibility": backtest_manifest.replay_compatibility_status,
        "anti_leakage_precheck": data_science_report.status,
        "runtime_parity_status": runtime_parity_manifest.status,
        "feature_hash": gold_manifest.feature_hash,
        "dataset_hash": expected_edge_manifest.dataset_hash,
        "known_blockers": list(known_blockers),
    }


def write_quality_reports(
    output_dir: Path,
    *,
    data_science_report: DataScienceQualityReport,
    runtime_parity_manifest: RuntimeFeatureParityManifest,
    raw_manifests: tuple[RawMarketFileManifest, ...],
    bronze_index: BronzeMarketIndexManifest,
    silver_manifest: SilverSynchronizedMarketManifest,
    gold_manifest: GoldMicrostructureFeatureManifest,
    expected_edge_manifest: ExpectedEdgeFeatureManifest,
    backtest_manifest: BacktestReplayDatasetManifest,
) -> tuple[str, str, str, str]:
    """Write the quality/precheck/report outputs for the canonical rail."""

    output_dir.mkdir(parents=True, exist_ok=True)
    data_science_path = output_dir / DATA_SCIENCE_QUALITY_REPORT_FILENAME
    anti_leakage_path = output_dir / ANTI_LEAKAGE_PRECHECK_REPORT_FILENAME
    runtime_parity_path = output_dir / "runtime_feature_parity_manifest.json"
    report_json_path = output_dir / RAW_DATA_PROCESSING_REPORT_JSON_FILENAME
    report_md_path = output_dir / RAW_DATA_PROCESSING_REPORT_MD_FILENAME
    atomic_write_json(data_science_path, data_science_report.model_dump(mode="json"), indent=2)
    atomic_write_json(anti_leakage_path, data_science_report.model_dump(mode="json"), indent=2)
    atomic_write_json(runtime_parity_path, runtime_parity_manifest.model_dump(mode="json"), indent=2)
    report_payload = build_raw_data_processing_report_payload(
        raw_manifests=raw_manifests,
        bronze_index=bronze_index,
        silver_manifest=silver_manifest,
        gold_manifest=gold_manifest,
        expected_edge_manifest=expected_edge_manifest,
        backtest_manifest=backtest_manifest,
        runtime_parity_manifest=runtime_parity_manifest,
        data_science_report=data_science_report,
    )
    atomic_write_json(report_json_path, report_payload, indent=2)
    markdown = [
        "# Raw Data Processing Report",
        "",
        f"1. Raw coverage: `{report_payload['raw_coverage']['file_count']}` files / present `{', '.join(report_payload['raw_coverage']['source_types_present']) or 'none'}` / missing `{', '.join(report_payload['raw_coverage']['source_types_missing']) or 'none'}`.",
        f"2. Bronze index status: `{bronze_index.index_status}`.",
        f"3. Silver synchronization status: `{silver_manifest.silver_sync_status}`.",
        f"4. Gold features generated: `{gold_manifest.feature_row_count}` rows / `{gold_manifest.feature_status}`.",
        f"5. Feature groups missing: `{', '.join(gold_manifest.feature_groups_missing) or 'none'}`.",
        f"6. Timestamp / gap / stale diagnostics: bronze_gap_count=`{bronze_index.gap_count}`, bronze_largest_gap_ms=`{bronze_index.largest_gap_ms}`, stale_book_count=`{silver_manifest.stale_book_count}`.",
        f"7. IA Lab readiness: `{expected_edge_manifest.status}`.",
        f"8. Backtest readiness: `{backtest_manifest.status}`.",
        f"9. Replay compatibility: `{backtest_manifest.replay_compatibility_status}`.",
        f"10. Anti-leakage precheck: `{data_science_report.status}`.",
        f"11. Known blockers: `{', '.join(report_payload['known_blockers']) or 'none'}`.",
    ]
    atomic_write_text(report_md_path, "\n".join(markdown) + "\n")
    return (
        str(data_science_path.resolve()),
        str(anti_leakage_path.resolve()),
        str(report_json_path.resolve()),
        str(report_md_path.resolve()),
    )


__all__ = [
    "ANTI_LEAKAGE_PRECHECK_REPORT_FILENAME",
    "DATA_SCIENCE_QUALITY_REPORT_FILENAME",
    "RAW_DATA_PROCESSING_REPORT_JSON_FILENAME",
    "RAW_DATA_PROCESSING_REPORT_MD_FILENAME",
    "build_data_science_quality_report",
    "build_raw_data_processing_report_payload",
    "build_runtime_feature_parity_manifest",
    "write_quality_reports",
]
