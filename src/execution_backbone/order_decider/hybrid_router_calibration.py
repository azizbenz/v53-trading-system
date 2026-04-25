"""Governed calibration for the Build-3 hybrid router."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from calibration_loader.loader import (
    CalibrationArtifactNotFoundError,
    CalibrationArtifactValidationError,
    CalibrationLoader,
    CalibrationLoaderError,
)


@dataclass(frozen=True)
class HybridRouterCalibration:
    # Mode
    live_mode_enabled: bool

    # Decision thresholds
    maker_timeout_s: float
    route_edge_floor_bps: float
    maker_advantage_min_bps: float
    maker_fill_probability_min: float
    maker_min_fill_progress_ratio: float
    max_signal_age_for_fallback_s: float
    inv003_max_participation_ratio: float

    # Logistic p_fill proxy
    beta_0: float
    beta_dir: float
    beta_toxic: float
    beta_transition: float
    beta_vol: float
    beta_participation: float
    w_obi: float
    w_micro: float
    w_aggr: float

    # Costs
    tau_alpha_s: float
    adverse_selection_scale_bps: float
    lambda_impact_bps: float
    capital_opportunity_rate_bps_per_s: float
    latency_staleness_scale_bps: float

    # Sanity
    eps_notional_eur: float
    vol_z_clip: float
    vol_zscore_window_s: float

    def validate(self) -> None:
        positive_fields = {
            "maker_timeout_s": self.maker_timeout_s,
            "tau_alpha_s": self.tau_alpha_s,
            "eps_notional_eur": self.eps_notional_eur,
            "vol_z_clip": self.vol_z_clip,
            "vol_zscore_window_s": self.vol_zscore_window_s,
        }
        non_negative_fields = {
            "route_edge_floor_bps": self.route_edge_floor_bps,
            "maker_advantage_min_bps": self.maker_advantage_min_bps,
            "maker_min_fill_progress_ratio": self.maker_min_fill_progress_ratio,
            "max_signal_age_for_fallback_s": self.max_signal_age_for_fallback_s,
            "adverse_selection_scale_bps": self.adverse_selection_scale_bps,
            "lambda_impact_bps": self.lambda_impact_bps,
            "capital_opportunity_rate_bps_per_s": self.capital_opportunity_rate_bps_per_s,
            "latency_staleness_scale_bps": self.latency_staleness_scale_bps,
        }
        for name, value in positive_fields.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        for name, value in non_negative_fields.items():
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and >= 0")
        probability_fields = {
            "maker_fill_probability_min": self.maker_fill_probability_min,
            "maker_min_fill_progress_ratio": self.maker_min_fill_progress_ratio,
        }
        for name, value in probability_fields.items():
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if not math.isfinite(self.inv003_max_participation_ratio) or not 0.0 < self.inv003_max_participation_ratio <= 1.0:
            raise ValueError("inv003_max_participation_ratio must be in (0, 1]")
        for name in (
            "beta_0",
            "beta_dir",
            "beta_toxic",
            "beta_transition",
            "beta_vol",
            "beta_participation",
            "w_obi",
            "w_micro",
            "w_aggr",
        ):
            value = getattr(self, name)
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")

    @classmethod
    def default(cls) -> "HybridRouterCalibration":
        """Return the conservative shadow-only starting point for Build-3 hybrid routing."""

        calibration = cls(
            live_mode_enabled=False,
            maker_timeout_s=2.0,
            route_edge_floor_bps=2.0,
            maker_advantage_min_bps=0.5,
            maker_fill_probability_min=0.55,
            maker_min_fill_progress_ratio=0.25,
            max_signal_age_for_fallback_s=1.5,
            inv003_max_participation_ratio=0.25,
            beta_0=0.0,
            beta_dir=1.2,
            beta_toxic=1.5,
            beta_transition=1.5,
            beta_vol=0.8,
            beta_participation=2.0,
            w_obi=0.5,
            w_micro=0.3,
            w_aggr=0.2,
            tau_alpha_s=30.0,
            adverse_selection_scale_bps=2.0,
            lambda_impact_bps=1.5,
            capital_opportunity_rate_bps_per_s=0.0002,
            latency_staleness_scale_bps=0.3,
            eps_notional_eur=1.0,
            vol_z_clip=5.0,
            vol_zscore_window_s=300.0,
        )
        calibration.validate()
        return calibration


@dataclass(frozen=True)
class HybridRouterCalibrationConfig:
    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"


_THRESHOLD_IDS: dict[str, str] = {
    "live_mode_enabled": "HYBRID_ROUTER_V1_LIVE_MODE_ENABLED",
    "maker_timeout_s": "HYBRID_ROUTER_V1_MAKER_TIMEOUT_S",
    "route_edge_floor_bps": "HYBRID_ROUTER_V1_ROUTE_EDGE_FLOOR_BPS",
    "maker_advantage_min_bps": "HYBRID_ROUTER_V1_MAKER_ADVANTAGE_MIN_BPS",
    "maker_fill_probability_min": "HYBRID_ROUTER_V1_MAKER_FILL_PROBABILITY_MIN",
    "maker_min_fill_progress_ratio": "HYBRID_ROUTER_V1_MAKER_MIN_FILL_PROGRESS_RATIO",
    "max_signal_age_for_fallback_s": "HYBRID_ROUTER_V1_MAX_SIGNAL_AGE_FOR_FALLBACK_S",
    "inv003_max_participation_ratio": "HYBRID_ROUTER_V1_INV003_MAX_PARTICIPATION_RATIO",
    "beta_0": "HYBRID_ROUTER_V1_BETA_0",
    "beta_dir": "HYBRID_ROUTER_V1_BETA_DIR",
    "beta_toxic": "HYBRID_ROUTER_V1_BETA_TOXIC",
    "beta_transition": "HYBRID_ROUTER_V1_BETA_TRANSITION",
    "beta_vol": "HYBRID_ROUTER_V1_BETA_VOL",
    "beta_participation": "HYBRID_ROUTER_V1_BETA_PARTICIPATION",
    "w_obi": "HYBRID_ROUTER_V1_W_OBI",
    "w_micro": "HYBRID_ROUTER_V1_W_MICRO",
    "w_aggr": "HYBRID_ROUTER_V1_W_AGGR",
    "tau_alpha_s": "HYBRID_ROUTER_V1_TAU_ALPHA_S",
    "adverse_selection_scale_bps": "HYBRID_ROUTER_V1_ADVERSE_SELECTION_SCALE_BPS",
    "lambda_impact_bps": "HYBRID_ROUTER_V1_LAMBDA_IMPACT_BPS",
    "capital_opportunity_rate_bps_per_s": "HYBRID_ROUTER_V1_CAPITAL_OPPORTUNITY_RATE_BPS_PER_S",
    "latency_staleness_scale_bps": "HYBRID_ROUTER_V1_LATENCY_STALENESS_SCALE_BPS",
    "eps_notional_eur": "HYBRID_ROUTER_V1_EPS_NOTIONAL_EUR",
    "vol_z_clip": "HYBRID_ROUTER_V1_VOL_Z_CLIP",
    "vol_zscore_window_s": "HYBRID_ROUTER_V1_VOL_ZSCORE_WINDOW_S",
}


def resolve_hybrid_router_calibration(
    config: HybridRouterCalibrationConfig | None = None,
) -> HybridRouterCalibration:
    calibration_config = config or HybridRouterCalibrationConfig()
    loader = CalibrationLoader(calibration_config.calibration_root)
    try:
        collection = loader.load(version=calibration_config.calibration_version)
    except (CalibrationLoaderError, OSError):
        return HybridRouterCalibration.default()
    try:
        raw_values = {
            field_name: loader.get_value(collection, threshold_id)
            for field_name, threshold_id in _THRESHOLD_IDS.items()
        }
    except (CalibrationArtifactNotFoundError, CalibrationArtifactValidationError, CalibrationLoaderError):
        return HybridRouterCalibration.default()
    calibration = HybridRouterCalibration(
        live_mode_enabled=_coerce_bool(raw_values["live_mode_enabled"]),
        maker_timeout_s=float(raw_values["maker_timeout_s"]),
        route_edge_floor_bps=float(raw_values["route_edge_floor_bps"]),
        maker_advantage_min_bps=float(raw_values["maker_advantage_min_bps"]),
        maker_fill_probability_min=float(raw_values["maker_fill_probability_min"]),
        maker_min_fill_progress_ratio=float(raw_values["maker_min_fill_progress_ratio"]),
        max_signal_age_for_fallback_s=float(raw_values["max_signal_age_for_fallback_s"]),
        inv003_max_participation_ratio=float(raw_values["inv003_max_participation_ratio"]),
        beta_0=float(raw_values["beta_0"]),
        beta_dir=float(raw_values["beta_dir"]),
        beta_toxic=float(raw_values["beta_toxic"]),
        beta_transition=float(raw_values["beta_transition"]),
        beta_vol=float(raw_values["beta_vol"]),
        beta_participation=float(raw_values["beta_participation"]),
        w_obi=float(raw_values["w_obi"]),
        w_micro=float(raw_values["w_micro"]),
        w_aggr=float(raw_values["w_aggr"]),
        tau_alpha_s=float(raw_values["tau_alpha_s"]),
        adverse_selection_scale_bps=float(raw_values["adverse_selection_scale_bps"]),
        lambda_impact_bps=float(raw_values["lambda_impact_bps"]),
        capital_opportunity_rate_bps_per_s=float(raw_values["capital_opportunity_rate_bps_per_s"]),
        latency_staleness_scale_bps=float(raw_values["latency_staleness_scale_bps"]),
        eps_notional_eur=float(raw_values["eps_notional_eur"]),
        vol_z_clip=float(raw_values["vol_z_clip"]),
        vol_zscore_window_s=float(raw_values["vol_zscore_window_s"]),
    )
    calibration.validate()
    return calibration


def _coerce_bool(value: bool | int | float | str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Unsupported boolean calibration value: {value!r}")


__all__ = [
    "HybridRouterCalibration",
    "HybridRouterCalibrationConfig",
    "resolve_hybrid_router_calibration",
]
