"""P0-C-auto (2026-05-29) — test auto-detection of feature_names from A2 manifest.

Covers `scripts/run_strategy_ladder_ml_lab_handoff.py` helpers:
  - `_load_feature_names_from_a2_manifest`
  - `_resolve_feature_names`

Validates that:
  - When A2 manifest is reachable, 22 features are auto-loaded (no decorrelation footgun)
  - Explicit --feature-names always wins (back-compat)
  - Missing/empty manifest fails closed
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_strategy_ladder_ml_lab_handoff.py"


def _load_handoff_cli_module():
    """Import the handoff CLI script as a module (it lives in scripts/, not in a package)."""

    src_root = REPO_ROOT / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    spec = importlib.util.spec_from_file_location("run_strategy_ladder_ml_lab_handoff", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_manifest(a2_root: Path, feature_names: list[str]) -> None:
    a2_root.mkdir(parents=True, exist_ok=True)
    manifest_path = a2_root / "expected_edge_feature_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "dataset_id": "test_dataset",
                "status": "EXPECTED_EDGE_FEATURE_DATASET_READY",
                "feature_names": feature_names,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_load_feature_names_from_a2_manifest_returns_full_list(tmp_path: Path) -> None:
    module = _load_handoff_cli_module()
    expected = [
        "close_return", "high_low_range", "volume",
        "spread_bps", "slippage_bps", "book_depth_levels", "break_even_bps",
        "vpin", "cumulative_ofi", "queue_pressure",
        "kyle_lambda", "realized_vol_current",
    ]
    _write_manifest(tmp_path, expected)

    loaded = module._load_feature_names_from_a2_manifest(tmp_path)

    assert loaded == tuple(expected)
    assert len(loaded) == 12


def test_load_feature_names_from_a2_manifest_missing_file_fails_closed(tmp_path: Path) -> None:
    module = _load_handoff_cli_module()

    with pytest.raises(FileNotFoundError, match="A2 manifest not found"):
        module._load_feature_names_from_a2_manifest(tmp_path)


def test_load_feature_names_from_a2_manifest_empty_list_fails_closed(tmp_path: Path) -> None:
    module = _load_handoff_cli_module()
    _write_manifest(tmp_path, [])

    with pytest.raises(ValueError, match="empty feature_names"):
        module._load_feature_names_from_a2_manifest(tmp_path)


def test_resolve_feature_names_auto_detects_when_a2_root_and_feature_names_empty(tmp_path: Path) -> None:
    """P0-C-strict: --a2-output-root + empty --feature-names → auto-load."""
    module = _load_handoff_cli_module()
    extended = ["close_return", "high_low_range", "volume", "vpin", "cumulative_ofi"]
    _write_manifest(tmp_path, extended)

    resolved = module._resolve_feature_names(
        raw_feature_names="",
        a2_output_root_arg=str(tmp_path),
    )

    assert resolved == tuple(extended)
    assert len(resolved) == 5


def test_resolve_feature_names_explicit_overrides_auto_detection(tmp_path: Path) -> None:
    """P0-C-strict: explicit --feature-names always wins over auto-detect."""
    module = _load_handoff_cli_module()
    manifest_features = ["close_return", "high_low_range", "volume", "vpin", "kyle_lambda"]
    _write_manifest(tmp_path, manifest_features)

    explicit_csv = "close_return,high_low_range,volume,spread_bps"
    resolved = module._resolve_feature_names(
        raw_feature_names=explicit_csv,
        a2_output_root_arg=str(tmp_path),
    )

    assert resolved == ("close_return", "high_low_range", "volume", "spread_bps")


def test_resolve_feature_names_no_a2_root_uses_explicit(tmp_path: Path) -> None:
    module = _load_handoff_cli_module()

    resolved = module._resolve_feature_names(
        raw_feature_names="close_return,high_low_range,volume,spread_bps",
        a2_output_root_arg="",
    )

    assert resolved == ("close_return", "high_low_range", "volume", "spread_bps")


def test_resolve_feature_names_fail_closed_when_neither_source_provided() -> None:
    """P0-C-strict: NO silent 3-feature fallback. Empty + empty → SystemExit."""
    module = _load_handoff_cli_module()

    with pytest.raises(SystemExit, match="P0-C-strict: feature_names not provided"):
        module._resolve_feature_names(
            raw_feature_names="",
            a2_output_root_arg="",
        )
