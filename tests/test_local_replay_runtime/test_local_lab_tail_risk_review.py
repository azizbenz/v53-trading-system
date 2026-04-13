from __future__ import annotations

from calibration_methods import PotGpdConfig
from local_replay_runtime import LocalLabTailRiskStatus, build_local_lab_tail_risk_review
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _records_from_daily_net_returns(net_returns: tuple[float, ...]):
    base_timestamp = 1_700_000_000.0
    return tuple(
        build_dtr(
            dtr_id=f"dtr-tail-risk-{index}",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0002,
            realized_cost=0.0001,
            gross_return=net_return + 0.0001,
            ce_expected=0.0015,
            regime="trend" if index % 2 == 0 else "range",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=1.0,
            timestamp=base_timestamp + (index * 86_400.0),
        )
        for index, net_return in enumerate(net_returns)
    )


def test_local_lab_tail_risk_review_is_partial_when_no_positive_loss_periods_exist():
    review = build_local_lab_tail_risk_review(
        correlation_id="corr-tail-risk",
        export_dir="E:/lab/export",
        run_id="run-tail-risk",
        records=_records_from_daily_net_returns((0.0020, 0.0018, 0.0022, 0.0019)),
        config=PotGpdConfig(min_exceedances=3, bootstrap_samples=20),
    )

    assert review.review_status == LocalLabTailRiskStatus.PARTIAL
    assert review.review_ready is False
    assert review.ready_breaker_count == 0
    assert review.partial_breaker_count == 3
    assert review.blocked_breaker_count == 0
    assert all(breaker.review_status == LocalLabTailRiskStatus.PARTIAL for breaker in review.breakers)
    assert all(
        f"{breaker.threshold_id}_NO_POSITIVE_LOSS_PERIODS" in breaker.caution_flags
        for breaker in review.breakers
    )


def test_local_lab_tail_risk_review_is_partial_when_exceedances_are_insufficient():
    net_returns = tuple(
        -0.0020 - ((index % 17) * 0.00015) - ((index // 30) * 0.00002)
        for index in range(150)
    )

    review = build_local_lab_tail_risk_review(
        correlation_id="corr-tail-risk",
        export_dir="E:/lab/export",
        run_id="run-tail-risk",
        records=_records_from_daily_net_returns(net_returns),
        config=PotGpdConfig(
            threshold_quantile=0.90,
            min_exceedances=3,
            bootstrap_samples=20,
        ),
    )

    assert review.review_status == LocalLabTailRiskStatus.PARTIAL
    assert review.review_ready is False
    assert review.ready_breaker_count == 2
    assert review.partial_breaker_count == 1
    assert review.blocked_breaker_count == 0
    assert review.breakers[0].review_status == LocalLabTailRiskStatus.READY
    assert review.breakers[1].review_status == LocalLabTailRiskStatus.READY
    assert review.breakers[2].review_status == LocalLabTailRiskStatus.PARTIAL
    assert "THR-R03_INSUFFICIENT_EXCEEDANCES" in review.breakers[2].caution_flags


def test_local_lab_tail_risk_review_is_ready_for_stable_multi_month_loss_history():
    net_returns = tuple(
        -0.0010 - ((index % 7) * 0.00005) - ((index // 30) * 0.000005)
        for index in range(365)
    )

    review = build_local_lab_tail_risk_review(
        correlation_id="corr-tail-risk",
        export_dir="E:/lab/export",
        run_id="run-tail-risk",
        records=_records_from_daily_net_returns(net_returns),
        config=PotGpdConfig(
            threshold_quantile=0.10,
            min_exceedances=3,
            bootstrap_samples=30,
        ),
    )

    assert review.review_status == LocalLabTailRiskStatus.READY
    assert review.review_ready is True
    assert review.ready_breaker_count == 3
    assert review.partial_breaker_count == 0
    assert review.blocked_breaker_count == 0
    assert review.blocking_reasons == ()
    assert all(breaker.review_status == LocalLabTailRiskStatus.READY for breaker in review.breakers)
    assert all(breaker.fit_ready is True for breaker in review.breakers)
    assert all(breaker.fit_result is not None for breaker in review.breakers)
    assert all(breaker.hard_cap_satisfied is True for breaker in review.breakers)
    assert all(breaker.hard_cap_binding is False for breaker in review.breakers)
