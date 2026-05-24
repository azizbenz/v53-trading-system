from __future__ import annotations

from pathlib import Path

from local_replay_runtime.expected_edge_feature_promotion_registry import (
    ExpectedEdgeFeatureVerdict,
    FeaturePromotionEntry,
    FeaturePromotionRegistry,
    load_feature_promotion_registry,
    save_feature_promotion_registry,
)


def _entry(
    *,
    pair: str = "BTCUSDT",
    timeframe: str = "1m",
    feature_name: str = "close_return",
    verdict: ExpectedEdgeFeatureVerdict = ExpectedEdgeFeatureVerdict.PROMOTED,
) -> FeaturePromotionEntry:
    return FeaturePromotionEntry(
        pair=pair,
        timeframe=timeframe,
        feature_name=feature_name,
        verdict=verdict,
        shap_rank=1,
        ablation_delta_psr=0.07,
        ablation_delta_sharpe=0.03,
        ablation_delta_break_even_bps=1.2,
        talab_quadruple_pass=True,
        min_btl_required=252,
        min_btl_satisfied=True,
        evidence_artifact_ref="E:/artifact.json",
    )


def test_empty_registry_default() -> None:
    registry = FeaturePromotionRegistry()
    assert registry.entries == ()


def test_registry_lookup_by_pair_tf_feature() -> None:
    entry = _entry()
    registry = FeaturePromotionRegistry(entries=(entry,))
    assert registry.lookup(pair="BTCUSDT", timeframe="1m", feature_name="close_return") == entry
    assert registry.lookup(pair="ETHUSDT", timeframe="1m", feature_name="close_return") is None


def test_registry_entries_for_pair_tf_filter() -> None:
    first = _entry()
    second = _entry(feature_name="volume")
    third = _entry(pair="ETHUSDT")
    registry = FeaturePromotionRegistry(entries=(first, second, third))
    assert registry.entries_for_pair_tf("BTCUSDT", "1m") == (first, second)


def test_load_missing_file_returns_empty_registry(tmp_path: Path) -> None:
    registry = load_feature_promotion_registry(tmp_path / "missing.json")
    assert registry.entries == ()


def test_load_invalid_json_returns_empty_registry(tmp_path: Path) -> None:
    target = tmp_path / "invalid.json"
    target.write_text("{not-json", encoding="utf-8")
    registry = load_feature_promotion_registry(target)
    assert registry.entries == ()


def test_save_load_roundtrip_deterministic(tmp_path: Path) -> None:
    target = tmp_path / "registry.json"
    registry = FeaturePromotionRegistry(entries=(_entry(), _entry(feature_name="volume")))
    save_feature_promotion_registry(target, registry)
    loaded = load_feature_promotion_registry(target)
    assert loaded == registry


def test_verdict_enum_4_values() -> None:
    assert tuple(ExpectedEdgeFeatureVerdict) == (
        ExpectedEdgeFeatureVerdict.PROMOTED,
        ExpectedEdgeFeatureVerdict.NEUTRAL,
        ExpectedEdgeFeatureVerdict.DEMOTED,
        ExpectedEdgeFeatureVerdict.INSUFFICIENT_EVIDENCE,
    )


def test_entry_schema_v1() -> None:
    assert _entry().schema_version == "expected_edge.feature_promotion_entry.v1"


def test_registry_schema_v1() -> None:
    assert FeaturePromotionRegistry().schema_version == "expected_edge.feature_promotion_registry.v1"


def test_atomic_write_no_partial_file(tmp_path: Path) -> None:
    target = tmp_path / "registry.json"
    registry = FeaturePromotionRegistry(entries=(_entry(),))
    save_feature_promotion_registry(target, registry)
    sibling_names = {path.name for path in tmp_path.iterdir()}
    assert "registry.json" in sibling_names
    assert not any(name.startswith("registry.json.") for name in sibling_names)
