"""Runtime tests for risk_backbone Build-4."""

import pytest

from risk_backbone import (
    PortfolioRiskSnapshot,
    RiskCandidate,
    RiskLimits,
    RiskMicroFrictionPrecheckHook,
    RiskMicroFrictionPrecheckOutcome,
    RiskRuntime,
    RiskRuntimeAction,
)
from risk_backbone.btc_factor_guard.pair_beta_registry import PairBetaRegistry
from risk_backbone.correlation_cluster_guard.cluster_registry import ClusterRegistry
from risk_backbone.exposure_budgeter.gross_exposure_calculator import Position


pytestmark = pytest.mark.build4


def _limits() -> RiskLimits:
    return RiskLimits(
        gross_cap=500.0,
        position_cap=250.0,
        loss_cap=100.0,
        beta_cap=1.0,
        cluster_cap=200.0,
        drawdown_warning_threshold_pct=0.02,
        drawdown_observe_threshold_pct=0.04,
    )


def _runtime(
    snapshot: PortfolioRiskSnapshot | None = None,
    *,
    micro_friction_precheck_hook: RiskMicroFrictionPrecheckHook | None = None,
) -> RiskRuntime:
    beta_registry = PairBetaRegistry()
    beta_registry.set_beta("BTCUSDT", 1.0, as_of_ts=0.0)
    beta_registry.set_beta("ETHUSDT", 0.6, as_of_ts=0.0)
    beta_registry.set_beta("LINKUSDT", 0.55, as_of_ts=0.0)
    beta_registry.set_beta("SOLUSDT", 0.7, as_of_ts=0.0)
    return RiskRuntime(
        _limits(),
        pair_beta_registry=beta_registry,
        cluster_registry=ClusterRegistry(),
        snapshot=snapshot,
        micro_friction_precheck_hook=micro_friction_precheck_hook,
    )


class TestRiskRuntime:
    def test_runtime_accepts_candidate_and_updates_stateful_reporters(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                positions=(Position(pair="BTCUSDT", engine_id="eng-a", size=100.0),),
                current_loss_budget=20.0,
                current_equity=995.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=100.0,
                planned_loss=20.0,
            ),
            now=10.0,
        )
        assert evaluation.action == RiskRuntimeAction.ACCEPT
        assert evaluation.accepted is True
        assert evaluation.reason_details == ()
        assert evaluation.dominant_reason_code == ""
        assert evaluation.explain_summary == "risk=accept / no blocker triggered"
        assert evaluation.explainability.blocked_guard_count == 0
        assert evaluation.explainability.drawdown_state_code == "accepted"
        assert evaluation.explainability.decision_severity == "nominal"
        assert evaluation.explainability.physics_pressure_state == "nominal"
        assert evaluation.explainability.execution_survivability_score == pytest.approx(1.0)
        assert evaluation.gross_result.projected_gross == pytest.approx(200.0)
        assert evaluation.beta_projection.projected_beta == pytest.approx(0.8)
        assert runtime.get_snapshot().current_loss_budget == pytest.approx(40.0)
        assert runtime.get_exposure_stats().current_gross == pytest.approx(200.0)
        assert runtime.get_loss_stats().current_budget == pytest.approx(40.0)
        assert runtime.get_beta_stats().current_portfolio_beta == pytest.approx(0.8)
        assert runtime.get_cluster_stats().cluster_exposures["eth_ecosystem"] == pytest.approx(100.0)

    def test_runtime_requires_explicit_now(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )

        with pytest.raises(ValueError, match="requires explicit now"):
            runtime.evaluate_candidate(
                RiskCandidate(
                    pair="ETHUSDT",
                    engine_id="eng-a",
                    size=50.0,
                    planned_loss=5.0,
                )
            )

    def test_runtime_rejects_missing_loss_estimate(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=50.0,
                planned_loss=None,
            ),
            now=20.0,
        )
        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "RISK_NO_LOSS_ESTIMATE"
        assert evaluation.reason_details[0].category == "loss_cap"
        assert evaluation.explain_summary.startswith("risk=reject / dominant=RISK_NO_LOSS_ESTIMATE")
        assert evaluation.explainability.blocked_guard_codes == ("RISK_NO_LOSS_ESTIMATE",)
        assert evaluation.explainability.blocked_guard_categories == ("loss_cap",)
        assert evaluation.explainability.decision_severity == "critical"
        assert evaluation.loss_result.verdict.value == "rejected_no_loss_estimate"
        assert runtime.get_loss_stats().total_refused == 1

    def test_runtime_blocks_multiple_small_correlated_trades(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        first = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=120.0,
                planned_loss=15.0,
            ),
            now=30.0,
        )
        second = runtime.evaluate_candidate(
            RiskCandidate(
                pair="LINKUSDT",
                engine_id="eng-b",
                size=100.0,
                planned_loss=15.0,
            ),
            now=31.0,
        )
        assert first.action == RiskRuntimeAction.ACCEPT
        assert second.action == RiskRuntimeAction.REJECT
        assert second.accepted is False
        assert second.dominant_reason_code == "RISK_CLUSTER_CAP"
        assert any(detail.code == "RISK_CLUSTER_CAP" for detail in second.reason_details)
        assert "cluster_cap" in second.explainability.blocked_guard_categories
        assert any(result.verdict.value == "rejected" for result in second.cluster_results)
        assert "eth_ecosystem" in second.reasons[0]

    def test_runtime_drawdown_observe_only_blocks_even_if_other_guards_pass(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=950.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=50.0,
                planned_loss=10.0,
            ),
            now=40.0,
        )
        assert evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "RISK_DRAWDOWN_OBSERVE"
        assert evaluation.reason_details[0].category == "drawdown_state"
        assert evaluation.explainability.drawdown_state_code == "observe_only"
        assert evaluation.explainability.decision_severity == "critical"
        assert "drawdown" in evaluation.reasons[0]

    def test_runtime_fail_closed_when_pair_has_no_cluster(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="DOGEUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
                pair_beta=0.9,
            ),
            now=50.0,
        )
        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.dominant_reason_code == "RISK_CLUSTER_MAPPING_MISSING"
        assert evaluation.explainability.blocked_guard_codes == ("RISK_CLUSTER_MAPPING_MISSING",)
        assert evaluation.cluster_results[0].verdict.value == "rejected_no_cluster"

    def test_runtime_rejects_candidate_without_explicit_beta_mapping(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="XRPUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
            ),
            now=55.0,
        )

        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "RISK_BETA_MAPPING_MISSING"
        assert evaluation.reason_details[0].category == "beta_cap"
        assert evaluation.reason_details[0].message == "missing explicit beta mapping for pair XRPUSDT"

    def test_runtime_accepts_candidate_beta_override_when_registry_mapping_is_missing(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="XRPUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
                pair_beta=0.9,
            ),
            now=56.0,
        )

        assert evaluation.action == RiskRuntimeAction.ACCEPT
        assert evaluation.accepted is True
        assert evaluation.dominant_reason_code == ""

    def test_runtime_rejects_when_current_snapshot_contains_position_without_explicit_beta_mapping(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                positions=(Position(pair="XRPUSDT", engine_id="eng-a", size=30.0),),
                current_loss_budget=5.0,
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-b",
                size=40.0,
                planned_loss=5.0,
            ),
            now=57.0,
        )

        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "RISK_BETA_MAPPING_MISSING"
        assert evaluation.reason_details[0].message == "missing explicit beta mapping for pair XRPUSDT"

    def test_runtime_rejects_stale_beta_mapping(self):
        beta_registry = PairBetaRegistry()
        beta_registry.set_beta("BTCUSDT", 1.0, as_of_ts=0.0)
        beta_registry.set_beta("ETHUSDT", 0.6, as_of_ts=0.0)
        runtime = RiskRuntime(
            RiskLimits(
                gross_cap=500.0,
                position_cap=250.0,
                loss_cap=100.0,
                beta_cap=1.0,
                cluster_cap=200.0,
                beta_mapping_max_age_s=10.0,
                drawdown_warning_threshold_pct=0.02,
                drawdown_observe_threshold_pct=0.04,
            ),
            pair_beta_registry=beta_registry,
            cluster_registry=ClusterRegistry(),
            snapshot=PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
            ),
            now=20.0,
        )

        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "RISK_BETA_MAPPING_STALE"
        assert evaluation.reason_details[0].message == "stale beta mapping for pair ETHUSDT"

    def test_runtime_marks_elevated_execution_pressure_without_rejecting(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
                execution_fragility=0.8,
                market_toxicity=0.8,
                spread_regime_penalty=0.6,
            ),
            now=60.0,
        )
        assert evaluation.action == RiskRuntimeAction.ACCEPT
        assert evaluation.accepted is True
        assert evaluation.explainability.physics_pressure_state == "elevated"
        assert evaluation.explainability.decision_severity == "warning"
        assert evaluation.explain_summary.startswith("risk=accept / physics=elevated")
        assert evaluation.explainability.execution_survivability_score < 1.0
        assert evaluation.explainability.micro_friction_score > 0.0

    def test_runtime_rejects_when_micro_friction_precheck_hook_blocks(self):
        def _block_micro_friction(_hook_input):
            return RiskMicroFrictionPrecheckOutcome(
                accepted=False,
                reason_codes=("ARTIFACT_RISK_MICRO_FRICTION_BLOCK",),
                detail="artifact veto on risk micro-friction precheck",
            )

        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
            micro_friction_precheck_hook=_block_micro_friction,
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
                execution_fragility=0.8,
                market_toxicity=0.8,
                spread_regime_penalty=0.6,
            ),
            now=60.5,
        )

        assert evaluation.action == RiskRuntimeAction.REJECT
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "ARTIFACT_RISK_MICRO_FRICTION_BLOCK"
        assert evaluation.reason_details[-1].category == "micro_friction_hook"
        assert evaluation.reason_details[-1].message == "artifact veto on risk micro-friction precheck"
        assert evaluation.explainability.physics_pressure_state == "elevated"
        assert evaluation.explainability.blocked_guard_codes[-1] == "ARTIFACT_RISK_MICRO_FRICTION_BLOCK"
        assert evaluation.reasons == ("artifact veto on risk micro-friction precheck",)

    def test_runtime_reduces_exposure_on_severe_execution_pressure(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
                execution_fragility=1.0,
                market_toxicity=1.0,
                spread_regime_penalty=1.0,
                participation_penalty=1.0,
            ),
            now=61.0,
        )
        assert evaluation.action == RiskRuntimeAction.REDUCE_EXPOSURE
        assert evaluation.accepted is False
        assert evaluation.dominant_reason_code == "RISK_EXECUTION_PRESSURE"
        assert evaluation.reason_details[-1].category == "execution_pressure"
        assert evaluation.explainability.physics_pressure_state == "severe"
        assert evaluation.explainability.execution_survivability_score < 0.2
        assert evaluation.explainability.micro_friction_score >= 0.8

    def test_runtime_can_release_accepted_position_and_budget(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )
        accepted = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=80.0,
                planned_loss=12.0,
            ),
            now=70.0,
        )

        assert accepted.action == RiskRuntimeAction.ACCEPT
        runtime.register_position_closed(
            pair="ETHUSDT",
            engine_id="eng-a",
            released_size=80.0,
            released_planned_loss=12.0,
        )

        snapshot = runtime.get_snapshot()
        assert snapshot.positions == ()
        assert snapshot.current_loss_budget == pytest.approx(0.0)
        assert runtime.get_exposure_stats().current_gross == pytest.approx(0.0)
        assert runtime.get_loss_stats().current_budget == pytest.approx(0.0)
        assert runtime.get_beta_stats().current_portfolio_beta == pytest.approx(0.0)
        assert runtime.get_cluster_stats().cluster_exposures == {}

    def test_runtime_rejects_releasing_more_size_than_tracked(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                positions=(Position(pair="ETHUSDT", engine_id="eng-a", size=25.0),),
                current_loss_budget=5.0,
                current_equity=1000.0,
                session_peak_equity=1000.0,
            ),
        )

        with pytest.raises(ValueError, match="cannot release more size"):
            runtime.register_position_closed(
                pair="ETHUSDT",
                engine_id="eng-a",
                released_size=30.0,
                released_planned_loss=5.0,
            )

    def test_runtime_replace_snapshot_resynchronizes_reporters(self):
        runtime = _runtime()
        runtime.replace_snapshot(
            PortfolioRiskSnapshot(
                positions=(
                    Position(pair="BTCUSDT", engine_id="eng-a", size=100.0),
                    Position(pair="ETHUSDT", engine_id="eng-b", size=50.0),
                ),
                current_loss_budget=15.0,
                current_equity=980.0,
                session_peak_equity=1000.0,
            )
        )

        assert runtime.get_exposure_stats().current_gross == pytest.approx(150.0)
        assert runtime.get_loss_stats().current_budget == pytest.approx(15.0)
        assert runtime.get_beta_stats().current_portfolio_beta == pytest.approx(0.8666666667)
        assert runtime.get_cluster_stats().cluster_exposures["btc_majors"] == pytest.approx(100.0)
        assert runtime.get_cluster_stats().cluster_exposures["eth_ecosystem"] == pytest.approx(50.0)

    def test_runtime_normalizes_missing_session_peak_to_current_equity(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1000.0,
                session_peak_equity=0.0,
            ),
        )

        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
            ),
            now=80.0,
        )

        assert evaluation.action == RiskRuntimeAction.ACCEPT
        assert runtime.get_snapshot().session_peak_equity == pytest.approx(1000.0)
        assert evaluation.drawdown_result.drawdown_pct == pytest.approx(0.0)

    def test_runtime_normalizes_stale_session_peak_below_current_equity(self):
        runtime = _runtime(
            PortfolioRiskSnapshot(
                current_equity=1020.0,
                session_peak_equity=1000.0,
            ),
        )

        evaluation = runtime.evaluate_candidate(
            RiskCandidate(
                pair="ETHUSDT",
                engine_id="eng-a",
                size=40.0,
                planned_loss=5.0,
            ),
            now=81.0,
        )

        assert evaluation.action == RiskRuntimeAction.ACCEPT
        assert runtime.get_snapshot().session_peak_equity == pytest.approx(1020.0)
        assert evaluation.drawdown_result.drawdown_pct == pytest.approx(0.0)

    def test_runtime_rejects_uninitialized_equity_state_on_evaluate(self):
        runtime = _runtime()

        with pytest.raises(ValueError, match="RiskRuntime.evaluate_candidate requires current_equity > 0"):
            runtime.evaluate_candidate(
                RiskCandidate(
                    pair="ETHUSDT",
                    engine_id="eng-a",
                    size=40.0,
                    planned_loss=5.0,
                ),
                now=82.0,
            )

    def test_runtime_set_equity_rejects_negative_current_equity(self):
        runtime = _runtime()

        with pytest.raises(ValueError, match="RiskRuntime.set_equity requires current_equity >= 0"):
            runtime.set_equity(current_equity=-1.0, session_peak_equity=1000.0)

    def test_runtime_replace_snapshot_rejects_zero_current_equity(self):
        runtime = _runtime()

        with pytest.raises(ValueError, match="RiskRuntime.replace_snapshot requires current_equity > 0"):
            runtime.replace_snapshot(
                PortfolioRiskSnapshot(
                    current_equity=0.0,
                    session_peak_equity=1000.0,
                )
            )
