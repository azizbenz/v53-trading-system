from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import shutil
from uuid import uuid4

import yaml


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "build9_core_smoke_script_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _write_execution_runtime_projection(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "correlation_id": "corr-exec-runtime",
                "export_dir": "build/local_lab",
                "run_id": "local-lab-run-1",
                "projection_status": "ready",
                "projection_ready": True,
                "execution_review_status": "ready",
                "execution_review_ready": True,
                "consumer_count": 3,
                "ready_consumer_count": 3,
                "partial_consumer_count": 0,
                "blocked_consumer_count": 0,
                "blocking_reasons": [],
                "caution_flags": [],
                "consumers": [
                    {
                        "consumer_id": "rate_limiter",
                        "consumer_interface": "quota_ratio_ceiling",
                        "threshold_id": "THR-X03",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "little_law_burst_margin_capped",
                        "unit": "quota_ratio",
                        "projection_value": 0.8,
                        "projection_value_semantics": "max_observed_quota_ratio_before_throttle",
                        "hard_cap_human": 0.8,
                        "hard_cap_binding": False,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                    {
                        "consumer_id": "spread_guard",
                        "consumer_interface": "spread_bps_ceiling",
                        "threshold_id": "THR-X04",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "lognormal_mu_plus_2sigma_capped",
                        "unit": "bps",
                        "projection_value": 24.0,
                        "projection_value_semantics": "max_observed_spread_bps_before_no_trade",
                        "hard_cap_human": 50.0,
                        "hard_cap_binding": False,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                    {
                        "consumer_id": "slippage_model",
                        "consumer_interface": "sqrt_size_slippage_predictor",
                        "threshold_id": "THR-X05",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "sqrt_size_huber_linear_v1",
                        "unit": "bps",
                        "projection_value": 18.0,
                        "projection_value_semantics": "reference_slippage_bps_at_q95_size",
                        "reference_size": 4.0,
                        "size_proxy": "final_size",
                        "intercept_bps": 2.0,
                        "sqrt_size_coefficient": 8.0,
                        "r_squared": 0.55,
                        "mean_absolute_error_bps": 1.5,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_reconciliation_scheduler_artifact(root: Path, *, interval_s: int | float = 1800) -> None:
    from calibration_loader import CalibrationArtifact

    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_id": "thr-i04-artifact",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-12T12:00:00Z",
        "thresholds": (
            {
                "threshold_id": "THR-I04",
                "value": interval_s,
                "source_module": "src/execution_backbone/reconciliation_layer/scheduler.py",
                "calibration_artifact": "config/calibration/v1/infra.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-12T12:05:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    (version_dir / "infra.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _load_script_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_build9_core_smoke.py"
    sys.path.insert(0, str(repo_root / "src"))
    spec = importlib.util.spec_from_file_location("run_build9_core_smoke", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_execution_bootstrap_smoke_check_passes():
    script_module = _load_script_module()

    result = script_module._run_execution_bootstrap_smoke()

    assert result.passed is True
    assert result.name == "execution_bootstrap"
    assert "boot reconciliation" in result.message


def test_engine_chain_smoke_check_passes_via_canonical_engine_facades():
    script_module = _load_script_module()

    result, engine_a_output, engine_b_output = script_module._run_engine_chain()

    assert result.passed is True
    assert result.name == "engine_chain"
    assert engine_a_output.engine_id == "engine_a"
    assert engine_b_output.engine_id == "engine_b"


def test_execution_bootstrap_smoke_check_accepts_execution_runtime_projection():
    script_module = _load_script_module()
    output_dir = _scratch_dir("projection")
    projection_path = output_dir / "local_lab_execution_runtime_projection.json"

    try:
        _write_execution_runtime_projection(projection_path)

        result = script_module._run_execution_bootstrap_smoke_with_projection(
            projection_path
        )

        assert result.passed is True
        assert result.name == "execution_bootstrap"
        assert "THR-X03/X04/X05" in result.message
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_execution_bootstrap_smoke_check_accepts_reconciliation_calibration_root():
    script_module = _load_script_module()
    output_dir = _scratch_dir("reconciliation")

    try:
        _write_reconciliation_scheduler_artifact(output_dir, interval_s=1800)

        result = script_module._run_execution_bootstrap_smoke_with_projection(
            reconciliation_calibration_root=output_dir
        )

        assert result.passed is True
        assert result.name == "execution_bootstrap"
        assert "THR-I04" in result.message
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_execution_bootstrap_smoke_check_accepts_gatekeeper_audit_path():
    script_module = _load_script_module()
    output_dir = _scratch_dir("gatekeeper_audit")
    audit_path = output_dir / "artifacts" / "gatekeeper" / "audit.jsonl"

    try:
        result = script_module._run_execution_bootstrap_smoke_with_projection(
            gatekeeper_audit_path=audit_path
        )

        assert result.passed is True
        assert result.name == "execution_bootstrap"
        assert "gatekeeper audit store" in result.message
        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["decision"] == "submitted"
        assert payload["pair"] == "BTCUSDT"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
