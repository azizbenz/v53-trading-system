"""P0-C-strict (2026-05-29) — test new RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES blocker.

Validates that `build_runtime_feature_parity_manifest` flags the silent
undertrained footgun: gold A2 contains governed expected-edge features
(vpin, kyle_lambda, etc.) that the ML training set ignored.

The blocker fires ONLY for features in SUPPORTED_FEATURE_NAME_SET — gold
internal fields (spread_bps used for cost, etc.) don't trigger it.
"""

from __future__ import annotations

from local_replay_runtime.data_science_quality_gates import (
    build_runtime_feature_parity_manifest,
)
from local_replay_runtime.raw_data_processing_contracts import (
    ExpectedEdgeFeatureManifest,
    GoldMicrostructureFeatureManifest,
)


def _gold(feature_names: tuple[str, ...]) -> GoldMicrostructureFeatureManifest:
    return GoldMicrostructureFeatureManifest(
        symbol_scope=("BTCUSDT",),
        timeframe_scope=("15m",),
        feature_row_count=100,
        feature_status="GOLD_FEATURE_STORE_READY",
        output_paths=("K:/gold/BTCUSDT/15m.jsonl.gz",),
        feature_names=feature_names,
        feature_hash="gold_hash_xyz",
    )


def _expected_edge(feature_names: tuple[str, ...]) -> ExpectedEdgeFeatureManifest:
    return ExpectedEdgeFeatureManifest(
        dataset_id="btcusdt.expected_edge.v1",
        status="EXPECTED_EDGE_FEATURE_DATASET_READY",
        row_count=100,
        pair_scope=("BTCUSDT",),
        timeframe_scope=("15m",),
        feature_names=feature_names,
        feature_hash="edge_hash_abc",
    )


def test_parity_blocked_by_undertrained_when_gold_has_supported_feature_training_ignored() -> None:
    """Gold has vpin (supported expected-edge feature), training only used 3 OHLCV → BLOCKER."""
    gold = _gold(("close_return", "high_low_range", "volume", "vpin"))
    edge = _expected_edge(("close_return", "high_low_range", "volume"))

    manifest = build_runtime_feature_parity_manifest(
        gold_manifest=gold,
        expected_edge_manifest=edge,
        source_silver_index_ref="silver_index.json",
    )

    assert manifest.status == "RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES"
    assert "RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES" in manifest.blocker_codes
    assert "vpin" in manifest.extra_runtime_feature_names


def test_parity_ready_when_gold_extras_are_non_training_internal_fields_only() -> None:
    """Gold has internal cost field (not in SUPPORTED_FEATURE_NAME_SET) → READY, no blocker."""
    gold = _gold(("close_return", "high_low_range", "volume", "internal_cost_field"))
    edge = _expected_edge(("close_return", "high_low_range", "volume"))

    manifest = build_runtime_feature_parity_manifest(
        gold_manifest=gold,
        expected_edge_manifest=edge,
        source_silver_index_ref="silver_index.json",
    )

    assert manifest.status == "RUNTIME_PARITY_SCHEMA_MATCH_READY"
    assert manifest.blocker_codes == ()


def test_parity_ready_when_train_equals_runtime() -> None:
    """Identity case: train features == runtime features → READY."""
    features = ("close_return", "high_low_range", "volume", "vpin", "kyle_lambda")
    gold = _gold(features)
    edge = _expected_edge(features)

    manifest = build_runtime_feature_parity_manifest(
        gold_manifest=gold,
        expected_edge_manifest=edge,
        source_silver_index_ref="silver_index.json",
    )

    assert manifest.status == "RUNTIME_PARITY_SCHEMA_MATCH_READY"
    assert manifest.blocker_codes == ()


def test_parity_blocked_by_missing_runtime_takes_precedence_over_undertrained() -> None:
    """Missing runtime is a harder failure than undertrained — checked first."""
    gold = _gold(("close_return", "high_low_range", "volume"))
    edge = _expected_edge(("close_return", "high_low_range", "volume", "kyle_lambda"))

    manifest = build_runtime_feature_parity_manifest(
        gold_manifest=gold,
        expected_edge_manifest=edge,
        source_silver_index_ref="silver_index.json",
    )

    assert manifest.status == "RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES"


def test_parity_blocked_by_empty_training_takes_precedence_over_all() -> None:
    """Empty training set is the hardest failure — checked first."""
    gold = _gold(("close_return", "high_low_range", "volume", "vpin"))
    edge = _expected_edge(())

    manifest = build_runtime_feature_parity_manifest(
        gold_manifest=gold,
        expected_edge_manifest=edge,
        source_silver_index_ref="silver_index.json",
    )

    assert manifest.status == "RUNTIME_PARITY_BLOCKED_BY_EMPTY_TRAINING_FEATURE_SET"
