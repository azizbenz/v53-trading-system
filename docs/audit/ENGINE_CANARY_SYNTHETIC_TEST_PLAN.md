# ENGINE_CANARY_SYNTHETIC_TEST_PLAN

- runtime_mode: TEST
- all_ok: True

## SCENARIO_A_LONG_PASS_NATIVE
- engine_id: engine_a
- expected_decision: emit
- actual_decision: emit
- expected_builder_status: ENGINE_A_INPUT_BUILDER_READY
- actual_builder_status: ENGINE_A_INPUT_BUILDER_READY
- expected_reason_codes: ()
- actual_reason_codes: ('engine_a.emit.valid', 'engine_internal.engine_a.structure.favorable', 'engine_internal.engine_a.context.neutral', 'economics.engine_a.cost.feasible', 'scoring.engine_a.conviction.medium', 'engine_a.structure.favorable', 'engine_a.context.neutral', 'engine_a.cost.feasible', 'engine_a.conviction.medium')
- ok: True

## SCENARIO_A_NEGATIVE_DIRECTION_BLOCK
- engine_id: engine_a
- expected_decision: no_trade
- actual_decision: no_trade
- expected_builder_status: ENGINE_A_INPUT_BUILDER_READY
- actual_builder_status: ENGINE_A_INPUT_BUILDER_READY
- expected_reason_codes: ('engine_internal.engine_a.direction.non_long', 'engine_a.input.non_long_direction')
- actual_reason_codes: ('engine_internal.engine_a.direction.non_long', 'engine_a.input.non_long_direction')
- ok: True

## SCENARIO_B_EXCESS_PASS
- engine_id: engine_b
- expected_decision: emit
- actual_decision: emit
- expected_builder_status: ENGINE_B_INPUT_BUILDER_READY
- actual_builder_status: ENGINE_B_INPUT_BUILDER_READY
- expected_reason_codes: ()
- actual_reason_codes: ('scoring.engine_b.conviction.medium', 'engine_internal.engine_b.excess.exploitable', 'economics.engine_b.cost.feasible', 'engine_b.conviction.medium', 'engine_b.excess.exploitable')
- ok: True

## SCENARIO_B_NO_EXCESS
- engine_id: engine_b
- expected_decision: no_trade
- actual_decision: no_trade
- expected_builder_status: ENGINE_B_INPUT_BUILDER_READY
- actual_builder_status: ENGINE_B_INPUT_BUILDER_READY
- expected_reason_codes: ('engine_internal.engine_b.excess.no_excess', 'engine_b.excess.no_excess')
- actual_reason_codes: ('engine_internal.engine_b.excess.no_excess', 'engine_b.excess.no_excess')
- ok: True

## SCENARIO_B_COST_FAIL
- engine_id: engine_b
- expected_decision: no_trade
- actual_decision: no_trade
- expected_builder_status: ENGINE_B_INPUT_BUILDER_READY
- actual_builder_status: ENGINE_B_INPUT_BUILDER_READY
- expected_reason_codes: ('economics.engine_b.cost.infeasible', 'break_even_not_cleared')
- actual_reason_codes: ('economics.engine_b.cost.infeasible', 'break_even_not_cleared')
- ok: True

## SCENARIO_C_BREAKOUT_PASS
- engine_id: engine_c
- expected_decision: emit
- actual_decision: emit
- expected_builder_status: ENGINE_C_INPUT_BUILDER_READY
- actual_builder_status: ENGINE_C_INPUT_BUILDER_READY
- expected_reason_codes: ()
- actual_reason_codes: ('engine_internal.engine_c.breakout.range_expansion', 'engine_c.breakout.range_expansion', 'engine_internal.engine_c.continuation.fresh_breakout', 'engine_c.continuation.fresh_breakout', 'scoring.engine_c.conviction.medium', 'engine_c.conviction.medium', 'engine_c.tier.tier_1', 'engine_c.microstructure.confirmed', 'economics.engine_c.cost.feasible', 'engine_c.invalidation.present')
- ok: True

## SCENARIO_C_NO_BREAKOUT
- engine_id: engine_c
- expected_decision: no_trade
- actual_decision: no_trade
- expected_builder_status: ENGINE_C_INPUT_BUILDER_NO_BREAKOUT
- actual_builder_status: ENGINE_C_INPUT_BUILDER_NO_BREAKOUT
- expected_reason_codes: ('engine_c.no_trade.non_long_breakout',)
- actual_reason_codes: ('engine_internal.engine_c.breakout.non_long', 'engine_c.no_trade.non_long_breakout', 'engine_internal.engine_c.breakout.structured_breakout', 'engine_c.breakout.structured_breakout', 'engine_internal.engine_c.continuation.fresh_breakout', 'engine_c.continuation.fresh_breakout', 'engine_c.microstructure.confirmed')
- ok: True

## SCENARIO_D_REENTRY_PASS
- engine_id: engine_d
- expected_decision: emit
- actual_decision: emit
- expected_builder_status: ENGINE_D_INPUT_BUILDER_READY_WITH_FIRST_EPISODE
- actual_builder_status: ENGINE_D_INPUT_BUILDER_READY_WITH_FIRST_EPISODE
- expected_reason_codes: ()
- actual_reason_codes: ('scoring.engine_d.conviction.high', 'engine_internal.engine_d.link_type.prior_trade', 'engine_internal.engine_d.anti_revenge.reset_required', 'engine_internal.engine_d.reformation.detected', 'economics.engine_d.cost.feasible', 'engine_d.conviction.high', 'engine_d.link_type.prior_trade', 'engine_d.anti_revenge.reset_required', 'engine_d.reformation.detected')
- ok: True

## SCENARIO_D_NO_HISTORY
- engine_id: engine_d
- expected_decision: no_trade
- actual_decision: no_trade
- expected_builder_status: ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE
- actual_builder_status: ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE
- expected_reason_codes: ('engine_internal.engine_d.history.weak', 'engine_d.no_trade.history_weak')
- actual_reason_codes: ('engine_internal.engine_d.history.weak', 'engine_d.no_trade.history_weak')
- ok: True
