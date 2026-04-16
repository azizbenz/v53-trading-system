from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType
from uuid import uuid4


def _load_script_module() -> ModuleType:
    script_path = Path("scripts/shadow_gate_check.py")
    spec = importlib.util.spec_from_file_location("shadow_gate_check", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    path = Path(".codex_tmp_shadow_gate_tests") / f"{label}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _session_dates(count: int) -> list[str]:
    return [f"2026-04-{day:02d}" for day in range(1, count + 1)]


def _build_shadow_session(session_dir: Path, *, days: int, active_engines: tuple[str, ...]) -> None:
    _write_json(
        session_dir / "local_replay_shadow.shadow_report.json",
        {
            "consecutive_days": days,
            "shadow_report_ready": days >= 20,
        },
    )
    _write_json(
        session_dir / "local_replay_shadow.shadow_session_summary.json",
        {
            "base_session_date": "2026-04-01",
            "session_dates": _session_dates(days),
            "consecutive_days": days,
            "remaining_days": max(0, 60 - days),
            "shadow_report_ready": days >= 20,
            "promotion_gate_passed": False,
        },
    )
    _write_json(
        session_dir / "local_replay_shadow.shadow_summary.json",
        {
            "decision": {
                "accepted": False,
                "verdict": "blocked",
                "blocking_reasons": [],
                "manual_review_required": True,
            },
            "active_engines": list(active_engines),
            "build14_status": "nominal",
        },
    )


def _passing_trade_returns(count: int) -> list[float]:
    pattern = [0.012, 0.006, 0.010, -0.002, 0.008]
    return [pattern[index % len(pattern)] for index in range(count)]


def _passing_daily_returns(count: int) -> list[float]:
    pattern = [0.004, 0.003, -0.001, 0.005, 0.002, 0.004, -0.001]
    return [pattern[index % len(pattern)] for index in range(count)]


def test_shadow_gate_check_passes_g21_with_complete_evidence() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("g21_pass")
    try:
        session_dir = scratch / "shadow_session"
        _build_shadow_session(session_dir, days=21, active_engines=("engine_a",))
        evidence_path = scratch / "evidence.json"
        trade_returns = _passing_trade_returns(60)
        _write_json(
            evidence_path,
            {
                "shadow_trade_returns": {"engine_a": trade_returns},
                "backtest_trade_returns": {"engine_a": trade_returns},
                "shadow_daily_returns": {"engine_a": _passing_daily_returns(21)},
                "drawdown_calibration": {"engine_a": -0.04},
                "hard_vetos": {key: 0 for key in module.HARD_VETO_KEYS if key != "HV-9_sample_too_small"},
                "calibration_in_use": "calibration_v3",
            },
        )
        output_path = scratch / "shadow_gate_report.json"

        exit_code = module.main(
            [
                "--gate-id",
                "G2.1",
                "--engine-id",
                "engine_a",
                "--shadow-session-dir",
                str(session_dir),
                "--inputs-json",
                str(evidence_path),
                "--output",
                str(output_path),
            ]
        )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert exit_code == 0
        assert payload["overall_machine_recommendation"] == "PASS_RECOMMENDED"
        assert payload["sample"]["n_days_satisfied"] is True
        assert payload["sample"]["n_trades_satisfied"] is True
        assert payload["stat_tests"]["PSR"]["pass"] is True
        assert payload["stat_tests"]["profit_factor"]["pass"] is True
        assert payload["missing_inputs"] == []
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_shadow_gate_check_fails_when_required_evidence_is_missing() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("missing_evidence")
    try:
        session_dir = scratch / "shadow_session"
        _build_shadow_session(
            session_dir,
            days=1,
            active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        )
        output_path = scratch / "shadow_gate_report.json"

        exit_code = module.main(
            [
                "--gate-id",
                "G2.1",
                "--engine-id",
                "engine_a",
                "--shadow-session-dir",
                str(session_dir),
                "--output",
                str(output_path),
            ]
        )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert exit_code == 2
        assert payload["overall_machine_recommendation"] == "FAIL"
        assert "shadow_trade_returns" in payload["missing_inputs"]
        assert payload["stat_tests"]["PSR"]["status"] == "missing_input"
        assert payload["hard_vetos"]["HV-9_sample_too_small"]["pass"] is False
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_shadow_gate_check_g22_requires_hansen_spa_for_multi_engine_scope() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("g22_missing_hansen")
    try:
        session_dir = scratch / "shadow_session"
        _build_shadow_session(session_dir, days=45, active_engines=("engine_a", "engine_b"))
        evidence_path = scratch / "evidence.json"
        trade_returns = _passing_trade_returns(180)
        _write_json(
            evidence_path,
            {
                "shadow_trade_returns": {"engine_a": trade_returns},
                "backtest_trade_returns": {"engine_a": trade_returns},
                "shadow_daily_returns": {"engine_a": _passing_daily_returns(45)},
                "drawdown_calibration": {"engine_a": -0.05},
                "hard_vetos": {key: 0 for key in module.HARD_VETO_KEYS if key != "HV-9_sample_too_small"},
            },
        )
        output_path = scratch / "shadow_gate_report.json"

        exit_code = module.main(
            [
                "--gate-id",
                "G2.2",
                "--engine-id",
                "engine_a",
                "--shadow-session-dir",
                str(session_dir),
                "--inputs-json",
                str(evidence_path),
                "--output",
                str(output_path),
            ]
        )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert exit_code == 2
        assert payload["overall_machine_recommendation"] == "FAIL"
        assert payload["stat_tests"]["hansen_spa_pvalue"]["status"] == "missing_input"
        assert "loss_differentials_by_candidate" in payload["missing_inputs"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
