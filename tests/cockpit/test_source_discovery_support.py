from __future__ import annotations

import json
from pathlib import Path
import sys

from cockpit.source_discovery_support import (
    build_duplication_audit,
    discover_pages,
    run_discovery,
    summarize_artifacts,
    write_discovery_outputs,
)

from ._operational_helpers import cleanup_scratch, scratch_dir


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_cockpit_source_discovery


def _seed_minimal_repo(repo_root: Path) -> None:
    (repo_root / "src" / "cockpit" / "templates" / "pages").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "cockpit" / "templates" / "partials").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "cockpit").mkdir(parents=True, exist_ok=True)
    (repo_root / "scripts").mkdir(parents=True, exist_ok=True)
    (repo_root / "build" / "service").mkdir(parents=True, exist_ok=True)
    (repo_root / "config").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "cockpit" / "templates" / "index.html").write_text(
        '{% include "partials/_system_flow.html" %}\n{{ vm.feature_bridge.bridge_status }}\n',
        encoding="utf-8",
    )
    (repo_root / "src" / "cockpit" / "templates" / "pages" / "trading.html").write_text(
        '{% include "partials/_feature_bridge.html" %}\n{{ vm.replay.ce_net }}\n',
        encoding="utf-8",
    )
    for name in ("shadow", "vps", "lab", "backtest", "logs", "observability"):
        (repo_root / "src" / "cockpit" / "templates" / "pages" / f"{name}.html").write_text(
            "{{ vm.current_page }}\n",
            encoding="utf-8",
        )
    (repo_root / "src" / "cockpit" / "templates" / "partials" / "_system_flow.html").write_text(
        "{{ vm.operational_proof.system_flow.operability_score.overall_verdict }}\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "cockpit" / "templates" / "partials" / "_feature_bridge.html").write_text(
        "{{ vm.feature_bridge.lineage_lock_status }}\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "cockpit" / "state.py").write_text(
        "from dataclasses import dataclass\n"
        "from pydantic import BaseModel\n"
        "@dataclass(frozen=True)\n"
        "class DashboardViewModel:\n"
        "    feature_bridge: str\n"
        "    replay: str\n"
        "    operational_proof: 'OperationalProofSnapshot'\n"
        "    current_page: str\n"
        "class OperationalProofSnapshot(BaseModel):\n"
        "    system_flow: str\n"
        "    queue_trace: str\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "cockpit" / "state_feature_bridge.py").write_text(
        '"""Read feature bridge."""\n'
        "def read_feature_bridge(auto_exports_root, max_age_seconds=300):\n"
        "    recognition_rate = len(recognized_feature_keys) / max(len(feature_keys), 1)\n"
        "    lineage_lock_status = 'missing'\n"
        "    return recognition_rate, lineage_lock_status\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "cockpit" / "runtime_support.py").write_text(
        '"""Runtime surfaces."""\n'
        "def read_runtime_surfaces(service_dir):\n"
        "    return {'service_state': service_dir / 'shadow_vps_service.state.json'}\n",
        encoding="utf-8",
    )
    (repo_root / "scripts" / "run_shadow.ps1").write_text(
        "$OutputDir = 'build/run'\n"
        "$GrafanaPort = 3000\n",
        encoding="utf-8",
    )
    (repo_root / "build" / "service" / "shadow_vps_service.state.json").write_text(
        json.dumps({"service_status": "running"}),
        encoding="utf-8",
    )
    (repo_root / "config" / "thresholds.yml").write_text(
        "thresholds:\n  - threshold_id: THR-X01\n    value: 0.95\n",
        encoding="utf-8",
    )


def test_discover_pages_matches_real_cockpit_surface_count() -> None:
    pages = discover_pages(REPO_ROOT)
    # Patch A (2026-05-31) — /backtest/replay sub-page added (backtest_replay.html)
    # per 2026-05-30_A_BACKTEST_REPLAY_SUBPAGE_SPLIT_SPEC.md → 8 → 9 surfaces.
    assert len(pages) == 9
    page_ids = {page.page_id for page in pages}
    assert page_ids == {
        "overview",
        "trading",
        "shadow",
        "vps",
        "lab",
        "backtest",
        "backtest_replay",
        "logs",
        "observability",
    }


def test_runner_generates_expected_outputs_for_minimal_repo() -> None:
    scratch = scratch_dir("source_discovery_minimal")
    try:
        repo_root = scratch / "repo"
        _seed_minimal_repo(repo_root)
        output_dir = repo_root / "docs" / "cockpit"
        artifacts = run_discovery(repo_root=repo_root, runtime_root=repo_root / "build")
        summary = summarize_artifacts(artifacts)
        assert "pages=8" in summary
        assert any(entry.file_path.endswith("state_feature_bridge.py") for entry in artifacts.file_ledger)
        assert any(row.metric_name.startswith("recognition_rate") for row in artifacts.formulas)
        paths = write_discovery_outputs(
            artifacts=artifacts,
            output_dir=output_dir,
            emit_json=True,
        )
        assert paths["page_source"].is_file()
        assert paths["file_ledger"].is_file()
        json_payload = json.loads((output_dir / "discovery_artifacts" / "file_source_ledger.json").read_text(encoding="utf-8"))
        assert any(item["file_path"].endswith("state_feature_bridge.py") for item in json_payload)
        duplication_rows = build_duplication_audit(artifacts.pages)
        assert isinstance(duplication_rows, tuple)
    finally:
        cleanup_scratch(scratch)


def test_cli_stdout_only_returns_summary() -> None:
    exit_code = run_cockpit_source_discovery.main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--runtime-root",
            str(REPO_ROOT / "build"),
            "--stdout-only",
        ]
    )
    assert exit_code == 0
