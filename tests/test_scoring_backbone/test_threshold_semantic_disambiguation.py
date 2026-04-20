from __future__ import annotations

from pathlib import Path

from engines.engine_d.marginal_value_estimator_d import (
    ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID,
)
from risk_backbone.risk_runtime_drawdown_calibration import (
    RiskDrawdownCalibrationConfig,
)
from scoring_backbone import ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_repo_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_thr_w01_stays_reserved_for_risk_runtime_semantics() -> None:
    risk_code = _read_repo_text(
        "src/risk_backbone/risk_runtime_drawdown_calibration.py"
    )

    assert RiskDrawdownCalibrationConfig().warning_threshold_id == "THR-W01"
    assert 'warning_threshold_id: str = "THR-W01"' in risk_code
    assert ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID == "THR-E05"


def test_docs_use_thr_e05_for_economics_and_not_old_thr_w01_aliases() -> None:
    economics_docs = (
        "docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md",
        "docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md",
        "docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md",
        "docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md",
    )

    for relative_path in economics_docs:
        text = _read_repo_text(relative_path)
        assert "THR-E05" in text
        assert "THR-W01_floor" not in text
        assert "inherits THR-W01" not in text

    catalog_text = _read_repo_text(
        "docs/production_deployment_plan/11_DYNAMIC_THRESHOLDS_CATALOG.md"
    )
    assert "threshold_id: THR-E05" in catalog_text
    assert "THR-W01 reste strictement r" in catalog_text


def test_engine_d_model_a_threshold_remains_local_setup_quality() -> None:
    estimator_code = _read_repo_text(
        "src/engines/engine_d/marginal_value_estimator_d.py"
    )

    assert ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID == (
        "THR-D_MARGINAL_VALUE_SCORE_MIN"
    )
    assert "THR-W01" not in estimator_code
    assert "local setup-quality governance" in estimator_code
