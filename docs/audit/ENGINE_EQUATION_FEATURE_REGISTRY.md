# ENGINE_EQUATION_FEATURE_REGISTRY

## A_DIRECTION_POLICY
- engine_id: engine_a
- module: src/engines/engine_a/engine_a_runner.py::run_engine_a
- formula_expected: long-only gate: direction_score must be > 0 before any trade path
- formula_implemented: if inputs.direction_score <= 0: NO_TRADE
- threshold: direction_score_non_long_gate = 0.0 signed_score_-1_to_1
- fail_reason_codes: engine_internal.engine_a.direction.non_long, engine_a.input.non_long_direction
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_a_input_payload
- existing_tests: tests/test_engines/test_engine_a/test_engine_a.py::test_non_long_direction_branch
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_a_negative_direction_never_becomes_long

## A_STRUCTURE_SCORE
- engine_id: engine_a
- module: src/engines/engine_a/structure_detector_a.py::detect_structure
- formula_expected: 0.30*abs(direction)+0.25*continuation+0.20*quality+0.10*zone+0.15*stability
- formula_implemented: ENGINE_A_STRUCTURE_WEIGHTS weighted sum with realized_kernel_vol_scale override for stability
- threshold: favorable/marginal/min_direction = 0.60/0.30/0.20 score_0_to_1
- fail_reason_codes: n/a
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_a_input_payload
- existing_tests: tests/test_engines/test_engine_a/test_engine_a.py::test_structure_unfavorable_branch
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_a_structure_detector_canary_cases

## A_COST_BREAK_EVEN
- engine_id: engine_a
- module: src/engines/engine_a/cost_feasibility_a.py::check_cost_feasibility
- formula_expected: break_even=(expected_cost+kyle_uplift)+delta_safe ; CE=(expected_gain-(expected_cost+kyle_uplift))/holding_period
- formula_implemented: effective_expected_cost = expected_cost + kyle_lambda_cost_uplift ; expected_gain <= break_even blocks ; CE < ce_min marginal
- threshold: delta_safe/ce_min = 0.0005/0.0001 decimal_return
- fail_reason_codes: engine_a.cost.break_even_not_cleared, engine_a.cost.ce_below_min
- pass_or_marginal_reason_codes: n/a
- expected_provenance: economic_provenance
- existing_tests: tests/test_engines/test_engine_a/test_engine_a.py::test_cost_marginal_branch
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_unit_conversions_and_expected_cost_sum

## B_Z_SCORE_EXCESS
- engine_id: engine_b
- module: src/engines/engine_b/excess_detector_b.py::detect_excess
- formula_expected: abs_z=abs(z_score); no_excess if abs_z<z_marginal; exploitable if abs_z>=z_star; invalid when z_score_valid is false
- formula_implemented: abs_z gating with z_marginal=1.0 z_star=1.5 z_max=4.0; excess_score=z_quality+range_bonus-expansion_penalty
- threshold: z_marginal/z_star/z_max = 1.0/1.5/4.0 sigma_units
- fail_reason_codes: engine_b.excess.no_excess, engine_b.excess.invalid
- pass_or_marginal_reason_codes: b.toxic_flow_fade, b.toxic_flow_fade_suppressed.correlation
- expected_provenance: engine_b_input_payload
- existing_tests: tests/test_engines/test_engine_b/test_engine_b.py::test_excess_detector
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_b_excess_threshold_cases

## B_DIRECTION_POLICY
- engine_id: engine_b
- module: src/engines/engine_b/engine_b_runner.py::run_engine_b
- formula_expected: long-only mean reversion: z_score must be <= 0 for a long-compatible candidate
- formula_implemented: if mean_result.z_score > 0: NO_TRADE non_long
- threshold: z_score_sign = 0.0 sigma_units
- fail_reason_codes: engine_internal.engine_b.direction.non_long, engine_b.direction.non_long
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_b_input_payload
- existing_tests: tests/test_engines/test_engine_b/test_engine_b.py::test_runner_rejects_positive_z_as_non_long
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_b_negative_z_is_math_excess_but_positive_z_is_long_only_block

## B_COST_BREAK_EVEN
- engine_id: engine_b
- module: src/engines/engine_b/cost_feasibility_b.py::check_cost_feasibility_b
- formula_expected: break_even=expected_cost+delta_safe ; EV_net=x*(expected_gain-expected_cost) ; CE=(expected_gain-expected_cost)/holding_period
- formula_implemented: expected_gain <= break_even infeasible ; ev_net <= 0 infeasible ; CE < ce_min marginal
- threshold: delta_safe/ce_min = 0.0008/0.0002 decimal_return
- fail_reason_codes: break_even_not_cleared, ce_below_minimum
- pass_or_marginal_reason_codes: n/a
- expected_provenance: economic_provenance
- existing_tests: tests/test_engines/test_engine_b/test_engine_b.py::test_cost_equality_to_break_even_is_infeasible
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_b_cost_threshold_cases

## C_BREAKOUT_SCORE
- engine_id: engine_c
- module: src/engines/engine_c/signal_math_c.py::compute_breakout_score
- formula_expected: 0.35*breakout_strength+0.25*range_quality+0.20*compression_quality+0.20*volume_confirmation
- formula_implemented: compute_breakout_score weighted sum clamped to [0,1]
- threshold: breakout_score_min = 0.62 score_0_to_1
- fail_reason_codes: engine_c.breakout.unstructured
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_c_input_payload
- existing_tests: tests/test_engines/test_engine_c/test_engine_c.py::test_breakout_unstructured_branch
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_c_breakout_threshold_cases

## C_FAKE_BREAKOUT_RISK
- engine_id: engine_c
- module: src/engines/engine_c/signal_math_c.py::compute_fake_breakout_risk
- formula_expected: 0.45*retrace_risk+0.30*rejection_wick_ratio+0.25*(1-volume_confirmation)
- formula_implemented: compute_fake_breakout_risk weighted sum clamped to [0,1]
- threshold: fake_breakout_risk_max = 0.65 score_0_to_1
- fail_reason_codes: engine_c.fake_breakout.blocked
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_c_input_payload
- existing_tests: tests/test_engines/test_engine_c/test_engine_c.py::test_fake_breakout_blocked_branch
- missing_tests: tests/engine_canary/test_engine_threshold_boundaries.py::test_engine_c_threshold_boundaries_with_epsilon

## D_HISTORY_SCORE
- engine_id: engine_d
- module: src/engines/engine_d/signal_math_d.py::compute_history_score
- formula_expected: 0.55*prior_trade_quality+0.25*pair_health+0.20*data_freshness
- formula_implemented: compute_history_score weighted sum clamped to [0,1]
- threshold: history_min = 0.55 score_0_to_1
- fail_reason_codes: engine_internal.engine_d.history.weak, engine_d.no_trade.history_weak
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_d_input_payload
- existing_tests: tests/test_engines/test_engine_d/test_engine_d.py::test_history_weak_branch
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_d_missing_history_and_threshold_cases

## D_REFORMATION_SCORE
- engine_id: engine_d
- module: src/engines/engine_d/signal_math_d.py::compute_reformation_score
- formula_expected: 0.45*reformation_quality+0.30*pullback_quality+0.25*context_score
- formula_implemented: compute_reformation_score weighted sum clamped to [0,1]
- threshold: reformation_min = 0.58 score_0_to_1
- fail_reason_codes: engine_internal.engine_d.reformation.weak, engine_d.no_trade.reformation_weak
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_d_input_payload
- existing_tests: tests/test_engines/test_engine_d/test_engine_d.py::test_reformation_weak_branch
- missing_tests: tests/engine_canary/test_engine_threshold_boundaries.py::test_engine_d_threshold_boundaries_with_epsilon

## D_CONCENTRATION_RISK
- engine_id: engine_d
- module: src/engines/engine_d/context_resolver_d.py::resolve_engine_d_context
- formula_expected: 0.60*(1-concentration_headroom)+0.40*reentry_lateness
- formula_implemented: concentration_risk = clamp(0.60*(1-headroom)+0.40*lateness)
- threshold: concentration_max = 0.64 score_0_to_1
- fail_reason_codes: engine_internal.engine_d.concentration.blocked, engine_d.no_trade.concentration_blocked
- pass_or_marginal_reason_codes: n/a
- expected_provenance: engine_d_input_payload
- existing_tests: tests/test_engines/test_engine_d/test_engine_d.py::test_concentration_blocked_branch
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_engine_d_missing_history_and_threshold_cases

## SHARED_EXPECTED_EDGE_TRUTH
- engine_id: shared_b2
- module: src/local_replay_runtime/strategy_ladder_economic_provenance.py::is_expected_edge_backtest_truth
- formula_expected: only MEASURED_* or GOVERNED_* provenance is usable as B2 truth; proxy/default/to_calibrate blocked
- formula_implemented: TO_CALIBRATE/DEFAULT/PROXY/UNKNOWN => false ; MEASURED_/GOVERNED_ => true
- threshold: expected_edge_truth_gate = governed_or_measured_only label
- fail_reason_codes: EXPECTED_EDGE_PROXY_BLOCKED, EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH
- pass_or_marginal_reason_codes: EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH
- expected_provenance: economic_provenance
- existing_tests: tests/test_local_replay_runtime/test_strategy_ladder_economic_provenance.py::test_expected_edge_backtest_truth_status
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_b2_proxy_expected_edge_never_becomes_truth

## SHARED_SPREAD_AND_DEPTH
- engine_id: shared_b2
- module: src/local_replay_runtime/strategy_ladder_replay_evidence.py::build_measured_spread_payload/build_measured_slippage_payload
- formula_expected: spread_bps=(ask-bid)/mid*10000 ; depth_topk_notional=sum(price*size) ; depth_fill_ratio=filled_notional/planned_notional
- formula_implemented: spread from reconstructed book state; depth_top1/top5/top20 from top levels; walk_cost_bps from volume walk
- threshold: book_freshness_warn_ms = 5000 milliseconds
- fail_reason_codes: SPREAD_MEASURED_STALE_AUDIT_ONLY, SPREAD_BLOCKED_BY_MISSING_BOOK
- pass_or_marginal_reason_codes: SPREAD_MEASURED_FROM_BOOK, SLIPPAGE_ESTIMATED_FROM_DEPTH20
- expected_provenance: replay_evidence
- existing_tests: tests/test_local_replay_runtime/test_strategy_ladder_replay_evidence.py::test_measured_spread
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_orderbook_depth_and_spread_canary

## SHARED_SHARIA_SIDE_POLICY
- engine_id: shared_policy
- module: src/sharia_compliance/trade_type_guard.py::authorize_trade_type
- formula_expected: short forbidden; non-spot forbidden; leverage forbidden; margin forbidden
- formula_implemented: SHORT_FORBIDDEN / NON_SPOT_FORBIDDEN / LEVERAGE_FORBIDDEN / MARGIN_FORBIDDEN
- threshold: sharia_spot_long_only = buy_or_inventory_reduce_only policy_label
- fail_reason_codes: SHORT_FORBIDDEN, NON_SPOT_FORBIDDEN, LEVERAGE_FORBIDDEN, MARGIN_FORBIDDEN
- pass_or_marginal_reason_codes: n/a
- expected_provenance: execution_policy
- existing_tests: tests/test_sharia_compliance/test_trade_type_guard.py
- missing_tests: tests/engine_canary/test_engine_equations_canary.py::test_sharia_spot_long_only_canary
