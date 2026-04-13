"""Shared Local IA Lab calibration-method primitives."""

from calibration_methods.bootstrap import (
    StationaryBootstrapConfig,
    StationaryBootstrapError,
    StationaryBootstrapInterval,
    infer_stationary_block_length,
    stationary_bootstrap_confidence_interval,
)
from calibration_methods.execution import (
    ExecutionCalibrationError,
    ExecutionSlippageModelEstimate,
    ExecutionThresholdEstimate,
    HampelFilterResult,
    apply_hampel_filter,
    calibrate_rate_limit_throttle_ratio,
    calibrate_slippage_model_bps,
    calibrate_spread_guard_threshold_bps,
    calibrate_time_sync_threshold_ms,
    calibrate_websocket_gap_threshold_s,
    empirical_quantile,
)
from calibration_methods.dsr import (
    DeflatedSharpeRatioError,
    DeflatedSharpeRatioResult,
    compute_deflated_sharpe_ratio,
)
from calibration_methods.hard_cap_floor import (
    HumanHardCapPolicyError,
    HumanHardCapPolicyResult,
    apply_human_maximum_cap,
    apply_human_minimum_floor,
)
from calibration_methods.multiple_testing import (
    HolmBonferroniAdjustedHypothesis,
    HolmBonferroniResult,
    MultipleTestingError,
    apply_holm_bonferroni,
)
from calibration_methods.pot_gpd import (
    PotGpdConfig,
    PotGpdError,
    PotGpdResult,
    fit_pot_gpd_tail_risk,
)
from calibration_methods.stationarity import (
    AugmentedDickeyFullerResult,
    DualStationarityResult,
    KpssLevelStationarityResult,
    StationarityTestError,
    compute_adf_level_stationarity,
    compute_kpss_level_stationarity,
    evaluate_dual_stationarity,
)
from calibration_methods.walkforward import (
    PurgedWalkForwardConfig,
    PurgedWalkForwardError,
    PurgedWalkForwardFold,
    PurgedWalkForwardPlan,
    build_purged_walk_forward_plan,
)

__all__ = [
    "DeflatedSharpeRatioError",
    "DeflatedSharpeRatioResult",
    "HumanHardCapPolicyError",
    "HumanHardCapPolicyResult",
    "HolmBonferroniAdjustedHypothesis",
    "HolmBonferroniResult",
    "MultipleTestingError",
    "PotGpdConfig",
    "PotGpdError",
    "PotGpdResult",
    "AugmentedDickeyFullerResult",
    "DualStationarityResult",
    "KpssLevelStationarityResult",
    "PurgedWalkForwardConfig",
    "PurgedWalkForwardError",
    "PurgedWalkForwardFold",
    "PurgedWalkForwardPlan",
    "StationaryBootstrapConfig",
    "StationaryBootstrapError",
    "StationaryBootstrapInterval",
    "StationarityTestError",
    "ExecutionCalibrationError",
    "ExecutionSlippageModelEstimate",
    "ExecutionThresholdEstimate",
    "HampelFilterResult",
    "build_purged_walk_forward_plan",
    "apply_hampel_filter",
    "calibrate_rate_limit_throttle_ratio",
    "calibrate_slippage_model_bps",
    "compute_deflated_sharpe_ratio",
    "compute_adf_level_stationarity",
    "compute_kpss_level_stationarity",
    "calibrate_spread_guard_threshold_bps",
    "calibrate_time_sync_threshold_ms",
    "calibrate_websocket_gap_threshold_s",
    "empirical_quantile",
    "evaluate_dual_stationarity",
    "apply_human_maximum_cap",
    "apply_human_minimum_floor",
    "apply_holm_bonferroni",
    "fit_pot_gpd_tail_risk",
    "infer_stationary_block_length",
    "stationary_bootstrap_confidence_interval",
]
