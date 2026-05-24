"""Tests Patch P2b (2026-05-22) — multi-pair C1 manifest writer for handoff.

Verifies that the writer produces a manifest validated by the P1 provider
(`StrategyLadderMultiPairC1Manifest`), with deterministic encoding and
fail-closed on invalid inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_edge_model_provider_multi_pair import (
    MULTI_PAIR_C1_ARTIFACT_KIND,
    StrategyLadderMultiPairC1Manifest,
)
from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    PAIR_ID_FEATURE_KEY,
)
from local_replay_runtime.strategy_ladder_multi_pair_handoff_writer import (
    MULTI_PAIR_C1_HANDOFF_MANIFEST_FILENAME,
    build_multi_pair_c1_handoff_manifest,
    maybe_emit_multi_pair_c1_handoff_manifest,
    write_multi_pair_c1_handoff_manifest,
)


def _required_features(*extra: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*extra, PAIR_ID_FEATURE_KEY)))


def test_build_manifest_has_expected_kind_and_encoding() -> None:
    manifest = build_multi_pair_c1_handoff_manifest(
        artifact_id="multipair_v1_15m",
        calibration_version="v1",
        timeframe="15m",
        selected_pairs=("BTCUSDT", "ETHUSDT"),
        feature_names=_required_features("close_return", "high_low_range"),
        model_path_ref="expected_edge_multipair_15m.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    assert manifest["artifact_kind"] == MULTI_PAIR_C1_ARTIFACT_KIND
    # Deterministic encoding (sorted alphabetical)
    assert manifest["pair_id_encoding"] == {"BTCUSDT": 0, "ETHUSDT": 1}
    # Feature names include pair_id
    assert PAIR_ID_FEATURE_KEY in manifest["feature_names"]
    # 64-char sha256 hex hashes
    assert len(manifest["artifact_hash"]) == 64
    assert len(manifest["feature_hash"]) == 64


def test_build_manifest_round_trips_through_p1_pydantic_validator() -> None:
    """Manifest produced by writer MUST pass StrategyLadderMultiPairC1Manifest validation."""
    manifest = build_multi_pair_c1_handoff_manifest(
        artifact_id="multipair_v2_1m",
        calibration_version="v2",
        timeframe="1m",
        selected_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        feature_names=_required_features("close_return", "high_low_range", "volume"),
        model_path_ref="expected_edge_multipair_1m.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    # Round-trip through P1 pydantic validator
    raw = json.dumps(manifest)
    validated = StrategyLadderMultiPairC1Manifest.model_validate_json(raw)
    assert validated.artifact_kind == MULTI_PAIR_C1_ARTIFACT_KIND
    assert validated.pair_id_encoding == {"BTCUSDT": 0, "ETHUSDT": 1, "SOLUSDT": 2}
    assert PAIR_ID_FEATURE_KEY in validated.feature_names


def test_build_manifest_normalizes_pair_case_and_whitespace() -> None:
    manifest = build_multi_pair_c1_handoff_manifest(
        artifact_id="x",
        calibration_version="v1",
        timeframe="15m",
        selected_pairs=("  btcusdt  ", "ETHUSDT"),
        feature_names=_required_features("close_return"),
        model_path_ref="x.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    assert manifest["pair_id_encoding"] == {"BTCUSDT": 0, "ETHUSDT": 1}


def test_build_manifest_fails_close_on_empty_pairs() -> None:
    with pytest.raises(ValueError, match="EMPTY_PAIRS"):
        build_multi_pair_c1_handoff_manifest(
            artifact_id="x",
            calibration_version="v1",
            timeframe="15m",
            selected_pairs=(),
            feature_names=_required_features("close_return"),
            model_path_ref="x.lgb",
            train_start="2025-01-01",
            train_end="2025-06-30",
        )


def test_build_manifest_fails_close_when_pair_id_missing_from_features() -> None:
    with pytest.raises(ValueError, match="MISSING_PAIR_ID"):
        build_multi_pair_c1_handoff_manifest(
            artifact_id="x",
            calibration_version="v1",
            timeframe="15m",
            selected_pairs=("BTCUSDT",),
            feature_names=("close_return", "volume"),  # pair_id absent
            model_path_ref="x.lgb",
            train_start="2025-01-01",
            train_end="2025-06-30",
        )


def test_write_manifest_persists_json_file(tmp_path: Path) -> None:
    manifest = build_multi_pair_c1_handoff_manifest(
        artifact_id="x",
        calibration_version="v1",
        timeframe="15m",
        selected_pairs=("BTCUSDT", "ETHUSDT"),
        feature_names=_required_features("close_return"),
        model_path_ref="x.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
    )
    output_path = write_multi_pair_c1_handoff_manifest(
        export_dir=tmp_path,
        manifest=manifest,
    )
    assert output_path == tmp_path / MULTI_PAIR_C1_HANDOFF_MANIFEST_FILENAME
    assert output_path.is_file()
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded["artifact_kind"] == MULTI_PAIR_C1_ARTIFACT_KIND


def test_maybe_emit_returns_none_when_selected_pairs_under_2() -> None:
    """Mono-pair (0 or 1 selected pair) → no manifest emission."""
    assert maybe_emit_multi_pair_c1_handoff_manifest(
        selected_pairs=(),
        artifact_id="x",
        calibration_version="v1",
        timeframe="15m",
        feature_names=("close_return",),
        model_path_ref="x.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
        export_dir=Path("/tmp"),
    ) is None
    assert maybe_emit_multi_pair_c1_handoff_manifest(
        selected_pairs=("BTCUSDT",),
        artifact_id="x",
        calibration_version="v1",
        timeframe="15m",
        feature_names=("close_return",),
        model_path_ref="x.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
        export_dir=Path("/tmp"),
    ) is None


def test_maybe_emit_writes_manifest_when_multi_pair(tmp_path: Path) -> None:
    """≥ 2 selected pairs → manifest written and path returned."""
    path = maybe_emit_multi_pair_c1_handoff_manifest(
        selected_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        artifact_id="multipair_v1_15m",
        calibration_version="v1",
        timeframe="15m",
        feature_names=("close_return", "high_low_range", "volume"),
        model_path_ref="expected_edge_multipair_15m.lgb",
        train_start="2025-01-01",
        train_end="2025-06-30",
        export_dir=tmp_path,
    )
    assert path is not None
    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["pair_id_encoding"] == {"BTCUSDT": 0, "ETHUSDT": 1, "SOLUSDT": 2}
    # pair_id auto-injected into feature_names by maybe_emit_*
    assert PAIR_ID_FEATURE_KEY in loaded["feature_names"]
