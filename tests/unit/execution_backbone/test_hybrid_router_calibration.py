from __future__ import annotations

from dataclasses import replace

import pytest

from execution_backbone.order_decider.hybrid_router import HybridRouter
from execution_backbone.order_decider.hybrid_router_calibration import (
    CALIBRATION_SCHEMA_VERSION,
    CalibrationArtifactNotFoundError,
    HybridRouterCalibration,
    HybridRouterCalibrationConfig,
    resolve_hybrid_router_calibration,
)
from execution_backbone.order_decider.hybrid_router_metrics import HybridRouterMetricsSink
from execution_backbone.order_decider.hybrid_router_types import build_compact_routing_trace_payload
from tests.support_hybrid_router_v2 import build_calibration, build_snapshot


def test_validate_rejects_negative_timeout() -> None:
    calibration = build_calibration(maker_timeout_s=-1.0)

    with pytest.raises(ValueError, match="maker_timeout_s"):
        calibration.validate()


def test_validate_rejects_p_out_of_01() -> None:
    calibration = build_calibration(maker_fill_probability_min=1.5)

    with pytest.raises(ValueError, match="maker_fill_probability_min"):
        calibration.validate()


def test_validate_rejects_non_finite_weight() -> None:
    calibration = build_calibration(w_obi=float("inf"))

    with pytest.raises(ValueError, match="w_obi"):
        calibration.validate()


def test_validate_rejects_w_sum_far_from_one() -> None:
    calibration = build_calibration(w_obi=0.8, w_micro=0.3, w_aggr=0.2)

    with pytest.raises(ValueError, match="w_obi \\+ w_micro \\+ w_aggr"):
        calibration.validate()


def test_validate_rejects_wrong_schema_version() -> None:
    calibration = replace(build_calibration(), schema_version="hybrid_router_v0")

    with pytest.raises(ValueError, match=CALIBRATION_SCHEMA_VERSION):
        calibration.validate()


def test_default_shadow_has_live_mode_false() -> None:
    assert HybridRouterCalibration.default_shadow().live_mode_enabled is False


def test_default_shadow_validates() -> None:
    HybridRouterCalibration.default_shadow().validate()


def test_loader_uses_default_when_key_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingLoader:
        def __init__(self, root: object) -> None:
            self.root = root

        def load(self, *, version: str) -> object:
            _ = version
            raise CalibrationArtifactNotFoundError("missing")

    monkeypatch.setattr(
        "execution_backbone.order_decider.hybrid_router_calibration.CalibrationLoader",
        MissingLoader,
    )

    calibration = resolve_hybrid_router_calibration(HybridRouterCalibrationConfig())

    assert calibration.profile_name == "default_shadow"


def test_loader_refuses_to_start_on_schema_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "schema_version": "wrong-version",
        "profile_name": "bad",
        "live_mode_enabled": False,
        "maker_timeout_s": 2.0,
        "route_edge_floor_bps": 2.0,
        "maker_advantage_min_bps": 0.5,
        "maker_fill_probability_min": 0.55,
        "maker_min_fill_progress_ratio": 0.25,
        "max_signal_age_for_fallback_s": 1.5,
        "beta_0": 0.0,
        "beta_dir": 1.2,
        "beta_toxic": 1.5,
        "beta_transition": 1.5,
        "beta_vol": 0.8,
        "beta_participation": 2.0,
        "w_obi": 0.5,
        "w_micro": 0.3,
        "w_aggr": 0.2,
        "tau_alpha_s": 30.0,
        "adverse_selection_scale_bps": 2.0,
        "lambda_impact_bps": 1.5,
        "capital_opportunity_rate_bps_per_s": 0.0002,
        "latency_staleness_scale_bps": 0.3,
        "eps_notional_eur": 1.0,
        "vol_z_clip": 5.0,
        "vol_zscore_window_s": 300.0,
        "min_coverage_ratio": 0.8,
        "max_snapshot_age_s": 0.5,
    }

    class FakeLoader:
        def __init__(self, root: object) -> None:
            self.root = root

        def load(self, *, version: str) -> object:
            _ = version
            return object()

        @staticmethod
        def get_value(collection: object, threshold_id: str) -> object:
            _ = collection
            return values[
                {
                    "HYBRID_ROUTER_V1_SCHEMA_VERSION": "schema_version",
                    "HYBRID_ROUTER_V1_PROFILE_NAME": "profile_name",
                    "HYBRID_ROUTER_V1_LIVE_MODE_ENABLED": "live_mode_enabled",
                    "HYBRID_ROUTER_V1_MAKER_TIMEOUT_S": "maker_timeout_s",
                    "HYBRID_ROUTER_V1_ROUTE_EDGE_FLOOR_BPS": "route_edge_floor_bps",
                    "HYBRID_ROUTER_V1_MAKER_ADVANTAGE_MIN_BPS": "maker_advantage_min_bps",
                    "HYBRID_ROUTER_V1_MAKER_FILL_PROBABILITY_MIN": "maker_fill_probability_min",
                    "HYBRID_ROUTER_V1_MAKER_MIN_FILL_PROGRESS_RATIO": "maker_min_fill_progress_ratio",
                    "HYBRID_ROUTER_V1_MAX_SIGNAL_AGE_FOR_FALLBACK_S": "max_signal_age_for_fallback_s",
                    "HYBRID_ROUTER_V1_BETA_0": "beta_0",
                    "HYBRID_ROUTER_V1_BETA_DIR": "beta_dir",
                    "HYBRID_ROUTER_V1_BETA_TOXIC": "beta_toxic",
                    "HYBRID_ROUTER_V1_BETA_TRANSITION": "beta_transition",
                    "HYBRID_ROUTER_V1_BETA_VOL": "beta_vol",
                    "HYBRID_ROUTER_V1_BETA_PARTICIPATION": "beta_participation",
                    "HYBRID_ROUTER_V1_W_OBI": "w_obi",
                    "HYBRID_ROUTER_V1_W_MICRO": "w_micro",
                    "HYBRID_ROUTER_V1_W_AGGR": "w_aggr",
                    "HYBRID_ROUTER_V1_TAU_ALPHA_S": "tau_alpha_s",
                    "HYBRID_ROUTER_V1_ADVERSE_SELECTION_SCALE_BPS": "adverse_selection_scale_bps",
                    "HYBRID_ROUTER_V1_LAMBDA_IMPACT_BPS": "lambda_impact_bps",
                    "HYBRID_ROUTER_V1_CAPITAL_OPPORTUNITY_RATE_BPS_PER_S": "capital_opportunity_rate_bps_per_s",
                    "HYBRID_ROUTER_V1_LATENCY_STALENESS_SCALE_BPS": "latency_staleness_scale_bps",
                    "HYBRID_ROUTER_V1_EPS_NOTIONAL_EUR": "eps_notional_eur",
                    "HYBRID_ROUTER_V1_VOL_Z_CLIP": "vol_z_clip",
                    "HYBRID_ROUTER_V1_VOL_ZSCORE_WINDOW_S": "vol_zscore_window_s",
                    "HYBRID_ROUTER_V1_MIN_COVERAGE_RATIO": "min_coverage_ratio",
                    "HYBRID_ROUTER_V1_MAX_SNAPSHOT_AGE_S": "max_snapshot_age_s",
                }[threshold_id]
            ]

    monkeypatch.setattr(
        "execution_backbone.order_decider.hybrid_router_calibration.CalibrationLoader",
        FakeLoader,
    )

    with pytest.raises(ValueError, match=CALIBRATION_SCHEMA_VERSION):
        resolve_hybrid_router_calibration(HybridRouterCalibrationConfig())


def test_calibration_version_propagates_to_plan_and_trace() -> None:
    calibration = build_calibration(profile_name="post_wave0_v1")
    router = HybridRouter(calibration, HybridRouterMetricsSink())
    decision = router.decide(build_snapshot())
    plan = router.build_plan(decision)
    trace = build_compact_routing_trace_payload(
        decision,
        calibration_version=plan.calibration_version,
        shadow_only=plan.shadow_only,
    )

    assert plan.calibration_version == f"{CALIBRATION_SCHEMA_VERSION}:post_wave0_v1"
    assert trace["calibration_version"] == plan.calibration_version
