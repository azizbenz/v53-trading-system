from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType
from uuid import uuid4

from jsonschema import Draft202012Validator


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


def _load_shadow_gate_schema() -> dict[str, object]:
    return json.loads(Path("schemas/shadow_gate_report.schema.json").read_text(encoding="utf-8"))


def _assert_valid_shadow_gate_report(payload: dict[str, object]) -> None:
    Draft202012Validator(_load_shadow_gate_schema()).validate(payload)


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
                "refusal_analysis": {
                    "engine_a": {
                        "total_refusals": 4,
                        "hard_block_refusals": 1,
                        "portfolio_refusals": 1,
                    }
                },
                "capital_usage": {
                    "engine_a": {
                        "tier_cap_respected": True,
                        "max_capital_fraction_used": 0.42,
                        "capital_tier": "micro_live_tier_1",
                    }
                },
                "execution_stats": {
                    "engine_a": {
                        "fill_rate": 0.91,
                        "average_slippage_bps": 3.2,
                        "average_spread_paid_bps": 4.8,
                    }
                },
                "hard_vetos": {key: 0 for key in module.HARD_VETO_KEYS if key != "HV-9_sample_too_small"},
                "calibration_in_use": "calibration_v3",
            },
        )
        output_path = scratch / "shadow_gate_report.json"

        exit_code = module.main(
            [
                "--run-id",
                "g21-pass",
                "--window-days",
                "21",
                "--engine-id",
                "engine_a",
                "--shadow-session-dir",
                str(session_dir),
                "--input",
                str(evidence_path),
                "--output",
                str(output_path),
            ]
        )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert exit_code == 0
        assert payload["schema_version"] == "shadow_gate_report.v1"
        assert payload["overall_machine_recommendation"] == "PASS_RECOMMENDED"
        assert payload["sample"]["n_days_satisfied"] is True
        assert payload["sample"]["n_trades_satisfied"] is True
        assert payload["stat_tests"]["PSR"]["pass"] is True
        assert payload["stat_tests"]["profit_factor"]["pass"] is True
        assert payload["refusal_analysis"]["status"] == "ready"
        assert payload["refusal_analysis"]["total_refusals"] == 4
        assert payload["capital_usage"]["status"] == "ready"
        assert payload["capital_usage"]["tier_cap_respected"] is True
        assert payload["execution_stats"]["status"] == "ready"
        assert payload["execution_stats"]["fill_rate"] == 0.91
        assert payload["missing_inputs"] == []
        _assert_valid_shadow_gate_report(payload)
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
        assert exit_code == 1
        assert payload["schema_version"] == "shadow_gate_report.v1"
        assert payload["overall_machine_recommendation"] == "FAIL"
        assert "shadow_trade_returns" in payload["missing_inputs"]
        assert payload["stat_tests"]["PSR"]["status"] == "missing_input"
        assert payload["hard_vetos"]["HV-9_sample_too_small"]["pass"] is False
        assert payload["refusal_analysis"]["status"] == "not_provided"
        assert payload["capital_usage"]["status"] == "not_provided"
        assert payload["execution_stats"]["status"] == "not_provided"
        _assert_valid_shadow_gate_report(payload)
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
        assert payload["refusal_analysis"]["status"] == "not_provided"
        assert payload["capital_usage"]["status"] == "not_provided"
        assert payload["execution_stats"]["status"] == "not_provided"
        _assert_valid_shadow_gate_report(payload)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_shadow_gate_check_uses_run_id_for_default_output_path() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("run_id_default_output")
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
            },
        )

        exit_code = module.main(
            [
                "--run-id",
                "shadow-g21",
                "--window-days",
                "21",
                "--engine-id",
                "engine_a",
                "--shadow-session-dir",
                str(session_dir),
                "--input",
                str(evidence_path),
            ]
        )

        output_path = session_dir / "shadow_gate_report.shadow-g21.json"
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert exit_code == 0
        assert output_path.exists()
        assert payload["gate_id"] == "G2.1"
        _assert_valid_shadow_gate_report(payload)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_shadow_gate_check_marks_partial_optional_sections_as_missing_input() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("partial_optional_sections")
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
                "refusal_analysis": {"engine_a": {"hard_block_refusals": 1}},
                "capital_usage": {"engine_a": {"max_capital_fraction_used": 0.5}},
                "execution_stats": {"engine_a": {"average_slippage_bps": 2.4}},
                "hard_vetos": {key: 0 for key in module.HARD_VETO_KEYS if key != "HV-9_sample_too_small"},
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
        assert payload["refusal_analysis"]["status"] == "missing_input"
        assert payload["capital_usage"]["status"] == "missing_input"
        assert payload["execution_stats"]["status"] == "missing_input"
        _assert_valid_shadow_gate_report(payload)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
