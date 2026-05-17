# Wave 3 External Evidence Summary

Scope: execution-cost, slippage, spread, fees, market-impact, fill realism, timeout, latency, rate-limit, venue constraints, replay/shadow/live cost parity, cockpit false-green execution surfaces, and side/halal execution safety.

Role boundary:
- This pack is evidence only.
- It does not self-certify scientific correctness.
- It does not approve patches as final.
- It does not rewrite formulas or normalize ambiguities away.

Primary source files inspected:
- `src/local_replay_runtime/shadow_execution_simulator.py`
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
- `src/execution_backbone/execution_runtime.py`
- `src/execution_backbone/execution_runtime_support.py`
- `src/execution_backbone/execution_routing_bridge.py`
- `src/execution_backbone/order_decider/hybrid_router_equations.py`
- `src/execution_backbone/order_decider/order_type_selector.py`
- `src/execution_backbone/slippage_model.py`
- `src/execution_backbone/rate_limiter.py`
- `src/execution_backbone/spread_guard.py`
- `src/execution_backbone/venue_constraints_provider.py`
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `src/execution_backbone/execution_cost_meter/fee_meter.py`
- `src/execution_backbone/execution_cost_meter/cost_aggregator.py`
- `src/execution_backbone/fill_tracker/fill_aggregator.py`
- `src/execution_backbone/fill_tracker/latency_meter.py`
- `src/meta_minimal/break_even_dashboard/expected_break_even_calculator.py`
- `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`
- `src/meta_minimal/cost_drift_monitor/monitor.py`
- `src/venue_adapters/binance_spot/rest_client.py`
- `src/venue_adapters/binance_spot/order_translator.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/state_run_comparison.py`
- `src/cockpit/state_data_quality.py`
- `src/cockpit/templates/partials/_replay_metrics.html`

Summary classifications:
- Fee seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `FEE_SOURCE_NOT_PROVEN` for replay expected-cost seam
- Spread seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`
- Slippage seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `EXPECTED_REALIZED_AMBIGUITY`
- Market-impact seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `IMPACT_SOURCE_NOT_PROVEN` for replay expected-cost seam
- Break-even/cost gate seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`
- Fill realism seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `FILL_REALISM_NOT_PROVEN` for calibration-to-real-market realism
- Latency/rate-limit seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`
- Venue constraints seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`
- Replay/shadow/live parity seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `EXPECTED_REALIZED_AMBIGUITY`
- Cockpit execution seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `COCKPIT_FALSE_GREEN_RISK`, `PLACEHOLDER_RISK`
- Side/halal safety seam: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`

Key evidence points:
- Replay `expected_cost` is explicitly `spread + slippage * multiplier + latency_penalty * multiplier`, divided by `10_000`. No explicit fee or market-impact term was proven in that replay seam.
- Replay `realized_cost` is simulated as `expected_cost * execution_factor`; partial fills are represented through `execution_factor`, not a separate replay partial-fill penalty term.
- Live/shadow execution runtime has explicit fee, implicit cost, adverse selection, partial-fill cost, and market-impact seams in the execution cost meter.
- Hybrid routing equations include maker/taker fees, taker slippage, adverse selection, latency staleness, and participation-based impact terms.
- Venue constraints are normalized before adapter submission. Quantity is quantized down to step size; buy limit price is quantized down to tick; sell limit price is quantized up to tick; min-notional violations are fail-closed.
- Cockpit replay pages now carry semantic labels for expected CE, exec-rate denominator, and drawdown proxy, but execution-facing zero defaults still exist in some cockpit adapters.

Detailed evidence files:
- [WAVE3_FEE_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_FEE_SOURCE_EVIDENCE.md)
- [WAVE3_SPREAD_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_SPREAD_SOURCE_EVIDENCE.md)
- [WAVE3_SLIPPAGE_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_SLIPPAGE_SOURCE_EVIDENCE.md)
- [WAVE3_MARKET_IMPACT_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_MARKET_IMPACT_SOURCE_EVIDENCE.md)
- [WAVE3_BREAK_EVEN_COST_GATE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_BREAK_EVEN_COST_GATE_EVIDENCE.md)
- [WAVE3_FILL_REALISM_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_FILL_REALISM_SOURCE_EVIDENCE.md)
- [WAVE3_LATENCY_RATE_LIMIT_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_LATENCY_RATE_LIMIT_SOURCE_EVIDENCE.md)
- [WAVE3_VENUE_CONSTRAINTS_SOURCE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_VENUE_CONSTRAINTS_SOURCE_EVIDENCE.md)
- [WAVE3_REPLAY_SHADOW_LIVE_COST_PARITY_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_REPLAY_SHADOW_LIVE_COST_PARITY_EVIDENCE.md)
- [WAVE3_COCKPIT_FALSE_GREEN_EXECUTION_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_COCKPIT_FALSE_GREEN_EXECUTION_EVIDENCE.md)
- [WAVE3_SIDE_HALAL_EXECUTION_SAFETY_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_SIDE_HALAL_EXECUTION_SAFETY_EVIDENCE.md)
- [WAVE3_TEST_COVERAGE_EVIDENCE.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_TEST_COVERAGE_EVIDENCE.md)
- [WAVE3_EXTERNAL_AUDIT_QUESTIONS.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit/p0b_formula_extraction/wave3_execution_cost_external_evidence/WAVE3_EXTERNAL_AUDIT_QUESTIONS.md)
