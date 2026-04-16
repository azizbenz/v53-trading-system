"""Shared Local IA Lab calibration-method primitives."""

from __future__ import annotations

from calibration_methods.energy_distance import (
    EnergyDistanceError,
    EnergyDistanceResult,
    compute_energy_distance_test,
)
from calibration_methods.ks_test import (
    KolmogorovSmirnovError,
    KolmogorovSmirnovResult,
    compute_ks_2sample,
)
from calibration_methods.mann_kendall import (
    MannKendallError,
    MannKendallResult,
    compute_mann_kendall_test,
)
from calibration_methods.psr import (
    ProbabilisticSharpeRatioError,
    ProbabilisticSharpeRatioResult,
    compute_probabilistic_sharpe_ratio,
)
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
from calibration_methods.hansen_spa import (
    HansenSpaError,
    HansenSpaResult,
    compute_hansen_spa_test,
)
from calibration_methods.multiple_testing import (
    HolmBonferroniAdjustedHypothesis,
    HolmBonferroniResult,
    MultipleTestingError,
    apply_holm_bonferroni,
)
from calibration_methods.multiple_testing_guard import (
    CURRENT_REPO_PAIR_UNIVERSE_COUNT,
    V53_CANONICAL_SHADOW_PAIR_FLOOR,
    HarveyLiuZhuDeflatedSharpeResult,
    HarveyLiuZhuPairCountMode,
    HarveyLiuZhuTestCount,
    MultipleTestingGuardError,
    compose_hlz_test_count,
    compute_harvey_liu_zhu_deflated_sharpe,
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
    "EnergyDistanceError",
    "EnergyDistanceResult",
    "KolmogorovSmirnovError",
    "KolmogorovSmirnovResult",
    "MannKendallError",
    "MannKendallResult",
    "ProbabilisticSharpeRatioError",
    "ProbabilisticSharpeRatioResult",
    "DeflatedSharpeRatioError",
    "DeflatedSharpeRatioResult",
    "HumanHardCapPolicyError",
    "HumanHardCapPolicyResult",
    "HansenSpaError",
    "HansenSpaResult",
    "HolmBonferroniAdjustedHypothesis",
    "HolmBonferroniResult",
    "HarveyLiuZhuDeflatedSharpeResult",
    "HarveyLiuZhuPairCountMode",
    "HarveyLiuZhuTestCount",
    "MultipleTestingError",
    "MultipleTestingGuardError",
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
    "compute_hansen_spa_test",
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
    "compose_hlz_test_count",
    "fit_pot_gpd_tail_risk",
    "infer_stationary_block_length",
    "stationary_bootstrap_confidence_interval",
    "compute_harvey_liu_zhu_deflated_sharpe",
    "compute_energy_distance_test",
    "compute_ks_2sample",
    "compute_mann_kendall_test",
    "compute_probabilistic_sharpe_ratio",
    "CURRENT_REPO_PAIR_UNIVERSE_COUNT",
    "V53_CANONICAL_SHADOW_PAIR_FLOOR",
]
