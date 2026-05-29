from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.backbone_contract_probe_audit import (
    BACKBONE_CONTRACT_PROBE_FINAL_FILENAME,
    BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME,
    write_backbone_contract_probe_audit,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_backbone_contract_probe_is_read_only_and_writes_surface_reports(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    docs_dir = tmp_path / "docs"

    written = write_backbone_contract_probe_audit(
        repo_root=Path.cwd(),
        output_dir=output_dir,
        docs_dir=docs_dir,
    )

    assert BACKBONE_CONTRACT_PROBE_FINAL_FILENAME in written
    assert BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME in written
    assert "backbone_contract_probe_execution.json" in written
    assert "BACKBONE_CONTRACT_PROBE_AUDIT.md" in written

    final = _read_json(output_dir / BACKBONE_CONTRACT_PROBE_FINAL_FILENAME)
    assert final["audit_mode"] == "READ_ONLY_PRE_WIRING"
    assert final["trading_logic_modified"] is False
    assert final["thresholds_modified"] is False
    assert final["surface_count"] >= 8


def test_probe_blocks_slippage_truth_until_depth20_contract_exists(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"

    write_backbone_contract_probe_audit(
        repo_root=Path.cwd(),
        output_dir=output_dir,
        docs_dir=tmp_path / "docs",
    )

    matrix = _read_json(output_dir / BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME)
    slippage = next(row for row in matrix["rows"] if row["surface"] == "slippage_measurement")

    assert slippage["safe_to_wire_b2"] is False
    assert "depth20_walk_ref" in slippage["missing_inputs"]
    assert "ADD_DEPTH20_MEASURED_SLIPPAGE_CONTRACT" in slippage["required_pre_patch"]


def test_probe_finds_canonical_break_even_entrypoint_but_keeps_dashboard_gap_explicit(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"

    write_backbone_contract_probe_audit(
        repo_root=Path.cwd(),
        output_dir=output_dir,
        docs_dir=tmp_path / "docs",
    )

    matrix = _read_json(output_dir / BACKBONE_CONTRACT_PROBE_MATRIX_FILENAME)
    break_even = next(row for row in matrix["rows"] if row["surface"] == "break_even")

    assert any(row["name"] == "evaluate_break_even_filter" for row in break_even["entrypoints_found"])
    assert "expected_break_even" in break_even["output_contract"]
    assert "dashboard_fields_missing" in break_even
    assert "required_pre_patch" in break_even
