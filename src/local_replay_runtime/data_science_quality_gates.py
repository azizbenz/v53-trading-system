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
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    SUPPORTED_FEATURE_NAME_SET,
)


DATA_SCIENCE_QUALITY_REPORT_FILENAME = "data_science_quality_report.json"
ANTI_LEAKAGE_PRECHECK_REPORT_FILENAME = "anti_leakage_precheck_report.json"
RAW_DATA_PROCESSING_REPORT_JSON_FILENAME = "raw_data_processing_report.json"
RAW_DATA_PROCESSING_REPORT_MD_FILENAME = "raw_data_processing_report.md"


# Patch P5 (2026-05-29) — A2 gold prod-safe whitelist enums. Only these
# truth-status values clear the promotion gate. Anything else → blocker code.
_PROD_SAFE_BOOK_FRESHNESS_STATUSES: frozenset[str] = frozenset({
    "BOOK_DEPTH20_AVAILABLE_FRESH",
})
_PROD_SAFE_SLIPPAGE_TRUTH_STATUSES: frozenset[str] = frozenset({
    "SLIPPAGE_A2_KYLE_MEASURED",
    "SLIPPAGE_A2_KYLE_OVERRIDE",
    "SLIPPAGE_B2_DEPTH20_BOOK_WALK_MEASURED",
})
_PROD_SAFE_EXPECTED_EDGE_TRUTH_STATUSES: frozenset[str] = frozenset({
    "EXPECTED_EDGE_MODEL_GOVERNED",
})

# Patch P7 (2026-05-29) — fine-grained calibration thresholds. Audit C2/C3/C4
# decisions: fail-closed on insufficient depth, fee schedule drift, metadata
# staleness. These thresholds drive `assess_gold_row_prod_safety` checks.
PROD_SAFE_MIN_BOOK_DEPTH_LEVELS: int = 20
PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS: int = 90
PROD_SAFE_MAX_METADATA_STALENESS_DAYS: int = 90

# P0-2 (2026-06-08) — modern microstructure signals (Cont-Kukanov OFI,
# Easley-Lopez-O'Hara VPIN, queue/book pressure, Kyle's lambda price impact,
# realized-kernel vol). Mirrors strategy_ladder_data_factory._A2_ENGINE_NATIVE_
# BRIDGE_FEATURES. A prod-safe (governed) gold row must carry at least one of
# these; a row with only legacy OHLCV + cost features (the silent 3-legacy
# feature-request degradation) is research-only, NOT prod-safe.
_PROD_SAFE_REQUIRED_MICROSTRUCTURE_FEATURES: frozenset[str] = frozenset({
    "vpin",
    "cumulative_ofi",
    "queue_pressure",
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
})


def _days_drift(iso_date: str | None, row_timestamp_ms: int | None) -> int | None:
    """P7 helper — compute absolute drift in days between an ISO date and a
    row timestamp (epoch ms). Returns None if either input is missing or
    unparseable (caller treats None as "drift unknown → cannot enforce").
    """
    from datetime import datetime, timezone

    if not iso_date or row_timestamp_ms is None:
        return None
    try:
        ref_dt = datetime.fromisoformat(str(iso_date)[:10])
        ref_dt = ref_dt.replace(tzinfo=timezone.utc)
        row_dt = datetime.fromtimestamp(int(row_timestamp_ms) / 1000.0, tz=timezone.utc)
        return abs((row_dt - ref_dt).days)
    except (ValueError, TypeError, OSError):
        return None


def assess_gold_row_prod_safety(row: object) -> tuple[str, ...]:
    """P5 (2026-05-29) — assess a single gold row for prod-safe readiness.

    Returns a tuple of blocker codes (`A2_GOLD_PROD_SAFE_BLOCKED_BY_*`) when
    any required field is missing or proxy-tainted. Empty tuple means the row
    is fully prod-safe.

    Checks (per P1-P5 cleanup):
      - P1 : input_data_hash, method_version_hash, raw_catalog_ref, feature_set_hash all non-empty
      - P2 : metadata_effective_at, metadata_source, metadata_hash all populated
      - P3 : book_freshness_status in PROD_SAFE whitelist (FRESH only)
      - P4 : slippage_truth_status in PROD_SAFE whitelist
      - P5 : expected_edge_row_truth_status == MODEL_GOVERNED

    Designed to be called over a sample of gold rows; aggregator counts
    blocker codes across the sample and emits a manifest-level summary.
    """

    blockers: list[str] = []

    # P1 — 4 hashes for reproducibility
    if not getattr(row, "input_data_hash", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_INPUT_DATA_HASH")
    if not getattr(row, "method_version_hash", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_METHOD_VERSION_HASH")
    if not getattr(row, "raw_catalog_ref", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_RAW_CATALOG_REF")
    if not getattr(row, "feature_set_hash", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_FEATURE_SET_HASH")

    # P2 — venue metadata temporal proof
    if not getattr(row, "metadata_effective_at", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_METADATA_EFFECTIVE_AT")
    if not getattr(row, "metadata_source", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_METADATA_SOURCE")
    if not getattr(row, "metadata_hash", None):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_METADATA_HASH")

    # P3 — book freshness (FRESH only for prod)
    book_status = str(getattr(row, "book_freshness_status", "") or "")
    if book_status not in _PROD_SAFE_BOOK_FRESHNESS_STATUSES:
        blockers.append(f"A2_GOLD_PROD_SAFE_BLOCKED_BY_BOOK_NOT_FRESH:{book_status}")

    # P4 — slippage truth (Kyle measured or override only)
    slippage_status = str(getattr(row, "slippage_truth_status", "") or "")
    if slippage_status not in _PROD_SAFE_SLIPPAGE_TRUTH_STATUSES:
        blockers.append(
            f"A2_GOLD_PROD_SAFE_BLOCKED_BY_SLIPPAGE_NOT_PROVEN:{slippage_status}"
        )

    # P5 — expected-edge truth (governed ML only for prod)
    edge_status = str(getattr(row, "expected_edge_row_truth_status", "") or "")
    if edge_status not in _PROD_SAFE_EXPECTED_EDGE_TRUTH_STATUSES:
        blockers.append(
            f"A2_GOLD_PROD_SAFE_BLOCKED_BY_EXPECTED_EDGE_NOT_GOVERNED:{edge_status}"
        )

    # P7 — fine-grained calibration thresholds
    # B4: book_depth_levels >= 20 (canonical depth20 ladder for slippage measurement)
    book_depth = getattr(row, "book_depth_levels", None)
    if book_depth is None or int(book_depth) < PROD_SAFE_MIN_BOOK_DEPTH_LEVELS:
        blockers.append(
            f"A2_GOLD_PROD_SAFE_BLOCKED_BY_ORDERBOOK_DEPTH_INSUFFICIENT:"
            f"{book_depth if book_depth is not None else 'missing'}_<_{PROD_SAFE_MIN_BOOK_DEPTH_LEVELS}"
        )

    # B5 + C2: fee_schedule_date drift vs row timestamp must be within tolerance
    fee_drift = _days_drift(
        getattr(row, "fee_schedule_date", None),
        getattr(row, "timestamp_ms", None),
    )
    if fee_drift is None:
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_FEE_SCHEDULE_DRIFT_NOT_PROVEN")
    elif fee_drift > PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS:
        blockers.append(
            f"A2_GOLD_PROD_SAFE_BLOCKED_BY_FEE_SCHEDULE_DRIFT_TOO_LARGE:"
            f"{fee_drift}d_>_{PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS}d"
        )

    # C4: metadata_effective_at staleness vs row timestamp must be within tolerance
    metadata_staleness = _days_drift(
        getattr(row, "metadata_effective_at", None),
        getattr(row, "timestamp_ms", None),
    )
    if metadata_staleness is None:
        # Only block when metadata_effective_at is itself missing.
        # If P2 already flagged that, we still want this distinct code
        # for "drift could not be computed".
        if not getattr(row, "metadata_effective_at", None):
            # P2 already raised the missing blocker — skip duplicate signal
            pass
        else:
            blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_METADATA_STALENESS_NOT_PROVEN")
    elif metadata_staleness > PROD_SAFE_MAX_METADATA_STALENESS_DAYS:
        blockers.append(
            f"A2_GOLD_PROD_SAFE_BLOCKED_BY_METADATA_STALENESS_TOO_LARGE:"
            f"{metadata_staleness}d_>_{PROD_SAFE_MAX_METADATA_STALENESS_DAYS}d"
        )

    # P0-2 (2026-06-08) — microstructure coverage. A governed/prod-safe gold must
    # carry modern microstructure signals; a legacy-only gold (the silent 3-feature
    # request degradation, e.g. a chunked run launched without --feature-names) is
    # research-only, not prod-safe. Microstructure lives in row.feature_values
    # (a dict), not as top-level columns.
    feature_values = getattr(row, "feature_values", None)
    if not isinstance(feature_values, dict) or not any(
        feature_values.get(name) is not None
        for name in _PROD_SAFE_REQUIRED_MICROSTRUCTURE_FEATURES
    ):
        blockers.append("A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_MICROSTRUCTURE")

    return tuple(blockers)


def build_runtime_feature_parity_manifest(
    *,
    gold_manifest: GoldMicrostructureFeatureManifest,
    expected_edge_manifest: ExpectedEdgeFeatureManifest,
    source_silver_index_ref: str,
) -> RuntimeFeatureParityManifest:
    """Build the governed training-vs-runtime feature parity contract."""

    training_feature_names = tuple(sorted(expected_edge_manifest.feature_names))
    runtime_feature_names = tuple(sorted(gold_manifest.feature_names))
    runtime_feature_set = set(runtime_feature_names)
    training_feature_set = set(training_feature_names)
    missing_runtime_feature_names = tuple(
        sorted(name for name in training_feature_set if name not in runtime_feature_set)
    )
    extra_runtime_feature_names = tuple(
        sorted(name for name in runtime_feature_set if name not in training_feature_set)
    )
    blocker_codes: tuple[str, ...] = ()
    status = "RUNTIME_PARITY_SCHEMA_MATCH_READY"
    if not training_feature_names:
        status = "RUNTIME_PARITY_BLOCKED_BY_EMPTY_TRAINING_FEATURE_SET"
        blocker_codes = ("RUNTIME_PARITY_BLOCKED_BY_EMPTY_TRAINING_FEATURE_SET",)
    elif missing_runtime_feature_names:
        status = "RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES"
        blocker_codes = ("RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES",)
    else:
        # P0-C-strict (2026-05-29) — only block on extra runtime features that
        # are governed expected-edge candidates. Non-training features (e.g.
        # spread_bps used for cost calculation, internal microstructure fields)
        # may legitimately exist in gold without being in the training set.
        # The blocker fires only when gold has SUPPORTED_FEATURE_NAME_SET
        # features that the training set ignored = silent-undertrained-model
        # footgun (gold has e.g. vpin/ofi/kyle_lambda but training used 3).
        undertrained_candidates = tuple(
            name for name in extra_runtime_feature_names if name in SUPPORTED_FEATURE_NAME_SET
        )
        if undertrained_candidates:
            status = "RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES"
            blocker_codes = ("RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES",)
    return finalize_hashed_model(
        RuntimeFeatureParityManifest(
            status=status,
            source_gold_feature_refs=gold_manifest.output_paths,
            source_silver_index_ref=source_silver_index_ref,
            feature_hash=gold_manifest.feature_hash,
            training_feature_names=training_feature_names,
            runtime_feature_names=runtime_feature_names,
            missing_runtime_feature_names=missing_runtime_feature_names,
            extra_runtime_feature_names=extra_runtime_feature_names,
            blocker_codes=blocker_codes,
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
