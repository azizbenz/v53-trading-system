from __future__ import annotations

from meta_learning import (
    StrategyDriftSnapshot,
    StrategyDriftState,
    evaluate_strategy_drift,
)


def test_strategy_drift_monitor_blocks_on_forecast_distribution_shift() -> None:
    signal = evaluate_strategy_drift(
        StrategyDriftSnapshot(
            sample_count=64,
            forecast_distribution_ks_pvalue=0.03,
            win_rate_delta=0.0,
            ce_delta=0.0,
        )
    )

    assert signal.state == StrategyDriftState.BLOCK
    assert signal.promotion_block is True


def test_strategy_drift_monitor_pauses_on_wr_or_ce_drift() -> None:
    signal = evaluate_strategy_drift(
        StrategyDriftSnapshot(
            sample_count=64,
            forecast_distribution_ks_pvalue=0.4,
            win_rate_delta=-0.12,
            ce_delta=-0.01,
        )
    )

    assert signal.state == StrategyDriftState.PAUSE
    assert signal.pause_signal is True


def test_strategy_drift_monitor_green_path_does_not_overfire() -> None:
    signal = evaluate_strategy_drift(
        StrategyDriftSnapshot(
            sample_count=64,
            forecast_distribution_ks_pvalue=0.4,
            win_rate_delta=-0.01,
            ce_delta=-0.01,
        )
    )

    assert signal.state == StrategyDriftState.GREEN
