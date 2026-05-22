# ENGINE_THRESHOLD_BOUNDARY_REPORT

## engine_a::min_direction
- threshold_value: 0.2
- exact_operator_used: < blocks ; >= survives
- tested_values: [0.199999999, 0.2, 0.200000001]
- output_decision: ['unfavorable', 'favorable', 'favorable']
- expected_decision: ['unfavorable', 'favorable', 'favorable']
- pass: True

## engine_a::marginal
- threshold_value: 0.3
- exact_operator_used: score >= threshold
- tested_values: [0.899999996, 0.9, 0.900000004]
- output_decision: ['unfavorable', 'marginal', 'marginal']
- expected_decision: ['unfavorable', 'marginal', 'marginal']
- pass: True

## engine_a::favorable
- threshold_value: 0.6
- exact_operator_used: score >= threshold
- tested_values: [0.299999996, 0.3, 0.300000004]
- output_decision: ['marginal', 'favorable', 'favorable']
- expected_decision: ['marginal', 'favorable', 'favorable']
- pass: True

## engine_b::z_marginal
- threshold_value: 1.0
- exact_operator_used: < no_excess ; >= threshold survives
- tested_values: [0.999999999, 1.0, 1.000000001]
- output_decision: ['no_excess', 'marginal', 'marginal']
- expected_decision: ['no_excess', 'marginal', 'marginal']
- pass: True

## engine_b::z_star
- threshold_value: 1.5
- exact_operator_used: < no_excess ; >= threshold survives
- tested_values: [1.499999999, 1.5, 1.500000001]
- output_decision: ['marginal', 'exploitable', 'exploitable']
- expected_decision: ['marginal', 'exploitable', 'exploitable']
- pass: True

## engine_b::delta_safe
- threshold_value: 0.0008
- exact_operator_used: expected_gain <= break_even blocks ; CE < ce_min marginal
- tested_values: [0.0010114990000000001, 0.0010115, 0.001011501]
- output_decision: ['infeasible', 'infeasible', 'feasible']
- expected_decision: ['infeasible', 'infeasible', 'feasible']
- pass: True

## engine_b::ce_min
- threshold_value: 0.0002
- exact_operator_used: CE < ce_min marginal ; CE >= ce_min feasible once break-even is cleared
- tested_values: [0.001211499, 0.0012115, 0.0012115009999999998]
- output_decision: ['marginal', 'feasible', 'feasible']
- expected_decision: ['marginal', 'feasible', 'feasible']
- pass: True

## engine_c::breakout_strength_min
- threshold_value: 0.55
- exact_operator_used: < blocks ; >= survives
- tested_values: [0.5499999990000001, 0.55, 0.550000001]
- output_decision: ['no_trade', 'emit', 'emit']
- expected_decision: ['no_trade', 'emit', 'emit']
- pass: True

## engine_c::range_quality_min
- threshold_value: 0.5
- exact_operator_used: < blocks ; >= survives
- tested_values: [0.499999999, 0.5, 0.500000001]
- output_decision: ['no_trade', 'emit', 'emit']
- expected_decision: ['no_trade', 'emit', 'emit']
- pass: True

## engine_c::breakout_score_min
- threshold_value: 0.62
- exact_operator_used: < blocks ; >= survives
- tested_values: [0.842857142, 0.842857143, 0.842857144]
- output_decision: ['no_trade', 'emit', 'emit']
- expected_decision: ['no_trade', 'emit', 'emit']
- pass: True

## engine_c::fake_breakout_risk_max
- threshold_value: 0.65
- exact_operator_used: >= blocks ; < survives
- tested_values: [0.222222222, 0.222222223, 0.222222224]
- output_decision: ['emit', 'no_trade', 'no_trade']
- expected_decision: ['emit', 'no_trade', 'no_trade']
- pass: True

## engine_d::history_min
- threshold_value: 0.55
- exact_operator_used: < blocks ; >= survives
- tested_values: [0.59090909, 0.590909091, 0.590909092]
- output_decision: ['no_trade', 'emit', 'emit']
- expected_decision: ['no_trade', 'emit', 'emit']
- pass: True

## engine_d::reformation_min
- threshold_value: 0.58
- exact_operator_used: < blocks ; >= survives
- tested_values: [0.566666666, 0.566666667, 0.566666668]
- output_decision: ['no_trade', 'emit', 'emit']
- expected_decision: ['no_trade', 'emit', 'emit']
- pass: True

## engine_d::concentration_max
- threshold_value: 0.64
- exact_operator_used: >= blocks ; < survives
- tested_values: [0.066666667, 0.066666666666, 0.066666665]
- output_decision: ['emit', 'no_trade', 'no_trade']
- expected_decision: ['emit', 'no_trade', 'no_trade']
- pass: True
