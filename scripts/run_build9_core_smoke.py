#!/usr/bin/env python3
"""Standalone launcher for the Build-1..9 core smoke suite."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import sys
from pathlib import Path


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    passed: bool
    message: str


CORE_MODULES: tuple[str, ...] = (
    "data_backbone",
    "execution_backbone",
    "risk_backbone",
    "scoring_backbone",
    "engine_a",
    "engine_b",
    "portfolio",
    "meta",
)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _bootstrap_module(module_name: str) -> SmokeCheck:
    try:
        if module_name in sys.modules:
            module = importlib.reload(sys.modules[module_name])
        else:
            module = importlib.import_module(module_name)

        declared = getattr(module, "__all__", None)
        if declared is not None:
            missing = [name for name in declared if not hasattr(module, name)]
            if missing:
                return SmokeCheck(
                    module_name,
                    False,
                    f"__all__ exports missing: {', '.join(missing)}",
                )
            return SmokeCheck(
                module_name,
                True,
                f"import + API OK ({len(declared)} exports)",
            )

        return SmokeCheck(module_name, True, "import OK")
    except Exception as exc:
        return SmokeCheck(module_name, False, f"{type(exc).__name__}: {exc}")


def _run_engine_chain() -> tuple[SmokeCheck, object, object]:
    from engine_a import EngineADecision, EngineAInput, run_engine_a
    from engine_b import EngineBDecision, EngineBInput, run_engine_b

    engine_a_output = run_engine_a(
        EngineAInput(
            pair="BTCUSDT",
            direction_score=0.8,
            continuation_score=0.9,
            structure_quality=0.85,
            zone_proximity=0.7,
            trend_stability=0.8,
            regime="trending_up",
            regime_favorability=0.9,
            regime_confidence=0.8,
            pair_health=0.9,
            data_freshness=0.95,
            flow_coherence=0.8,
            expected_gain=0.005,
            expected_cost=0.001,
            candidate_size=1000.0,
            holding_period=4.0,
            entry_price=50000.0,
            atr=500.0,
            scoring_version="build9_core_smoke_a",
        )
    )
    if engine_a_output.decision != EngineADecision.EMIT:
        return (
            SmokeCheck("engine_chain", False, "Engine A did not emit on canonical favorable inputs"),
            engine_a_output,
            None,
        )

    engine_b_output = run_engine_b(
        EngineBInput(
            pair="ETHUSDT",
            current_price=97.0,
            local_mean=100.0,
            local_std=1.5,
            structure_is_range=0.7,
            recent_expansion=0.1,
            regime="range",
            regime_trend_strength=0.1,
            volume_anomaly=0.1,
            structural_break=0.0,
            continuation_momentum=0.1,
            regime_favorability=0.7,
            pair_health=0.8,
            data_freshness=0.9,
            expected_gain=0.003,
            expected_cost=0.001,
            candidate_size=100.0,
            holding_period=2.0,
            scoring_version="build9_core_smoke_b",
        )
    )
    if engine_b_output.decision != EngineBDecision.EMIT:
        return (
            SmokeCheck("engine_chain", False, "Engine B did not emit on canonical favorable inputs"),
            engine_a_output,
            engine_b_output,
        )

    return (
        SmokeCheck(
            "engine_chain",
            True,
            "Engine A and Engine B emit on canonical favorable inputs",
        ),
        engine_a_output,
        engine_b_output,
    )


def _run_portfolio_chain(engine_a_output: object, engine_b_output: object) -> tuple[SmokeCheck, object]:
    from portfolio import OrchestratorConfig, run_portfolio_pipeline
    from portfolio_minimal.allocation_router.base_size_builder import SizeProfile
    from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate
    from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot

    candidates = (
        OpportunityCandidate(
            pair=engine_a_output.pair,
            engine_id=engine_a_output.engine_id,
            penalized_score=engine_a_output.raw_score,
            raw_score=engine_a_output.raw_score,
            ce_expected=engine_a_output.ce_expected,
            expected_cost=engine_a_output.expected_cost,
            ev_net=engine_a_output.ev_net,
            candidate_size=200.0,
            tier_suggestion=engine_a_output.tier_suggestion,
            cluster_id="btc_cluster",
            estimated_loss=10.0,
            beta_impact=0.20,
            holding_hours=engine_a_output.holding_hours,
            scoring_version=engine_a_output.scoring_version,
        ),
        OpportunityCandidate(
            pair=engine_b_output.pair,
            engine_id=engine_b_output.engine_id,
            penalized_score=engine_b_output.penalized_score,
            raw_score=engine_b_output.raw_score,
            ce_expected=engine_b_output.ce_expected,
            expected_cost=engine_b_output.expected_cost,
            ev_net=engine_b_output.ev_net,
            candidate_size=100.0,
            tier_suggestion=engine_b_output.tier_suggestion,
            cluster_id="eth_cluster",
            estimated_loss=5.0,
            beta_impact=0.10,
            holding_hours=engine_b_output.expected_holding_hours,
            scoring_version=engine_b_output.scoring_version,
        ),
    )

    config = OrchestratorConfig(
        size_profile=SizeProfile(
            available_capital=10000.0,
            base_fraction=0.02,
            min_size=10.0,
            max_size=500.0,
        ),
        initial_snapshot=PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={
                "btc_cluster": 500.0,
                "eth_cluster": 500.0,
            },
        ),
        position_cap=500.0,
        min_viable_size=10.0,
        cluster_crowding_threshold=3,
    )

    result = run_portfolio_pipeline(candidates, config)
    if result.pool_size != 2:
        return SmokeCheck("portfolio_chain", False, f"unexpected pool_size={result.pool_size}"), result
    if result.report.count_allocated < 1:
        return SmokeCheck("portfolio_chain", False, "portfolio produced no viable allocation"), result

    return (
        SmokeCheck(
            "portfolio_chain",
            True,
            f"portfolio allocated {result.report.count_allocated} opportunity(ies)",
        ),
        result,
    )


def _run_meta_chain(portfolio_result: object) -> SmokeCheck:
    from meta import (
        build_break_even_report,
        build_cra_report,
        build_dtr_summary,
        build_edge_report,
    )
    from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
    from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
    from meta_minimal.cra_monitor.sterilization_classifier import (
        SterilizationClass,
        SterilizationResult,
    )
    from meta_minimal.dtr_core.decision_state_encoder import DecisionState
    from meta_minimal.dtr_core.dtr_record_builder import build_dtr
    from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
        EdgeClassification,
        EdgeStatus,
    )

    allocated = portfolio_result.report.allocations
    if not allocated:
        return SmokeCheck("meta_chain", False, "meta chain requires at least one viable allocation")

    dtr_records = tuple(
        build_dtr(
            dtr_id=f"dtr_{idx}",
            pair=entry.pair,
            engine_id=entry.engine_id,
            decision_state=DecisionState.SELECTED,
            candidate_size=entry.modulated_size,
            final_size=entry.final_size,
            final_score=entry.ranking_score,
            timestamp=1000.0 + idx,
        )
        for idx, entry in enumerate(allocated, start=1)
    )
    dtr_summary = build_dtr_summary(dtr_records, total_opportunities=len(dtr_records))
    if dtr_summary.total_records != len(dtr_records):
        return SmokeCheck("meta_chain", False, "DTR summary record count mismatch")

    sterilization_results = tuple(
        SterilizationResult(
            pair=entry.pair,
            engine_id=entry.engine_id,
            classification=SterilizationClass.HEALTHY,
            multiplier=1.0,
            phantom_risk_score=0.0,
        )
        for entry in allocated
    )
    cra_report = build_cra_report(
        sterilization_results,
        alerts=(
            CRAAlert(
                scope=allocated[0].engine_id,
                sterilization_rate=0.0,
                total_trades=len(allocated),
                sterilized_count=0,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="smoke_only",
            ),
        ),
    )
    if cra_report.total_trades != len(allocated):
        return SmokeCheck("meta_chain", False, "CRA report trade count mismatch")

    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope=allocated[0].engine_id,
                sample_size=len(allocated),
                mean_realized_cost=0.0012,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0002,
                profitable_rate=1.0,
            ),
        )
    )
    if not break_even_report.views:
        return SmokeCheck("meta_chain", False, "break-even report is empty")

    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope=allocated[0].engine_id,
                status="credible",
                mean_net_return=0.002,
                standard_error=0.0005,
                sample_size=len(allocated),
                sharpe_per_trade=0.25,
                mean_cost_p90=0.001,
                ce_observed=0.0005,
                cluster_utilization=0.3,
            ),
        )
    )
    if edge_report.total_scopes != 1:
        return SmokeCheck("meta_chain", False, "edge report scope count mismatch")

    return SmokeCheck(
        "meta_chain",
        True,
        "meta facade builders summarize DTR, CRA, break-even, and edge outputs",
    )


def _format_report(checks: list[SmokeCheck], build1_text: str) -> str:
    lines = [
        "=" * 60,
        "  BUILD-1..9 CORE SMOKE REPORT",
        "=" * 60,
        "",
        "[Build-1]",
        build1_text.rstrip(),
        "",
        "[Build-2..9]",
    ]

    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- {check.name}: {status} - {check.message}")

    lines.extend(
        [
            "-" * 60,
            f"  VERDICT: {'PASS' if all(check.passed for check in checks) else 'FAIL'}",
            "=" * 60,
        ]
    )
    return "\n".join(lines)


def main() -> int:
    _configure_stdio()
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from smoke_bootstrap_recovery import format_smoke_report, run_build1_smoke
    except ModuleNotFoundError as exc:
        print(f"Dependency missing: {exc.name}. Install project runtime dependencies first.")
        return 2

    build1_report = run_build1_smoke()
    build1_text = format_smoke_report(build1_report)

    checks = [_bootstrap_module(module_name) for module_name in CORE_MODULES]

    if all(check.passed for check in checks):
        engine_check, engine_a_output, engine_b_output = _run_engine_chain()
        checks.append(engine_check)
        if engine_check.passed:
            portfolio_check, portfolio_result = _run_portfolio_chain(engine_a_output, engine_b_output)
            checks.append(portfolio_check)
            if portfolio_check.passed:
                checks.append(_run_meta_chain(portfolio_result))

    print(_format_report(checks, build1_text))

    passed = build1_report.passed and all(check.passed for check in checks)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
