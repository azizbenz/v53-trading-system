# Wave 5 Break-even / EV / CE Gate Evidence

## Shared gate evidence

Source file:
- `src/scoring_backbone/break_even_filter.py`

Function:
- `evaluate_break_even`

Exact code excerpt:
```python
expected_break_even = expected_cost + delta_safe
ev_net = candidate_size * (expected_gain - expected_cost)
```

```python
edge_cleared = expected_gain > expected_break_even
if not resolved_config.strict_break_even:
    edge_cleared = expected_gain >= expected_break_even

ce_cleared = True
if expected_ce is not None and ce_min is not None:
    ce_cleared = expected_ce >= ce_min

ev_cleared = ev_net > resolved_config.min_ev_net
allowed = edge_cleared and ce_cleared and ev_cleared
```

Reason-code excerpt:
```python
if not edge_cleared:
    reason_code = "BREAK_EVEN_NOT_CLEARED"
elif not ce_cleared:
    reason_code = "CE_BELOW_MINIMUM"
elif not ev_cleared:
    reason_code = "EV_NET_BELOW_FLOOR"
```

Implemented formula:
- `expected_break_even = expected_cost + delta_safe`
- `ev_net = candidate_size * (expected_gain - expected_cost)`
- allow iff break-even, CE floor, and EV floor all clear

Expected gain source:
- upstream engine/scoring candidate projection

Expected cost source:
- upstream projected cost field

Expected or realized:
- expected only

Cost completeness usage:
- no explicit consumption of `fee_source_status`, `impact_source_status`, `cost_model_completeness_status`, `fill_realism_status`, or `realized_slippage_status` was proven in the shared scoring, risk, portfolio, engine, execution, or interface-contract rails

Absence evidence:
- repo-wide search over `src/scoring_backbone`, `src/risk_backbone`, `src/portfolio_minimal`, `src/engines`, `src/execution_backbone`, and `src/interface_contracts` for `cost_model_completeness_status|fee_source_status|impact_source_status|fill_realism_status|realized_slippage_status|small_capital_exclusion_status` returned `NO_MATCH`

Tests:
- `tests/test_scoring_backbone/test_break_even_filter.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `COST_MODEL_PARTIAL`
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

## Fee-aware edge gate

Source file:
- `src/execution_backbone/fee_aware_edge_gate.py`

Function:
- `evaluate_fee_aware_edge`

Exact code excerpt:
```python
expected_cost_bps = expected_cost * 10_000.0
threshold_bps = max(
    thresholds.edge_multiplier * expected_cost_bps,
    thresholds.min_absolute_edge_bps,
)
allowed = expected_edge_bps >= threshold_bps
```

Reason-code excerpt:
```python
reason_code="" if allowed else "EDGE_INSUFFICIENT_VS_FEES"
```

Implemented formula:
- expected edge in bps must exceed a threshold derived from expected cost in bps and an absolute floor

Thresholds:
- `edge_multiplier`
- `min_absolute_edge_bps`

Units:
- bps

Expected or realized:
- expected only

Tests:
- `tests/test_scoring_backbone/test_fee_aware_edge_gate.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`

## Engine-local cost feasibility seams

### Engine A

Source file:
- `src/engines/engine_a/cost_feasibility_a.py`

Key implemented formula:
- `effective_expected_cost = expected_cost + kyle_lambda_cost_uplift`
- `break_even = effective_expected_cost + delta_safe`
- `edge = expected_gain - effective_expected_cost`
- `ev_net = candidate_size * edge`
- `ce = edge / holding_period if candidate_size > 0 else 0.0`

Meaning:
- Engine A is the only inspected engine-local seam that explicitly adds a Kyle-uplift term into cost feasibility.

### Engine B

Source file:
- `src/engines/engine_b/cost_feasibility_b.py`

Key implemented formula:
- `break_even = expected_cost + delta_safe`
- `edge = expected_gain - expected_cost`
- `ev_net = candidate_size * edge`
- `ce = edge / holding_period if holding_period > 0 and candidate_size > 0 else 0.0`

### Engine C

Source file:
- `src/engines/engine_c/cost_feasibility_c.py`

Key implemented formula:
- `ev_net = candidate_size * (expected_gain - expected_cost)`
- `ce_expected = (expected_gain - expected_cost) / holding_period` when `holding_period > 0`
- `cost_preference_score = clamp((expected_gain - expected_cost) / max(expected_gain, delta_safe, 1e-6))` when `expected_gain > 0`

Important metadata:
- `calibration_status="TO_CALIBRATE"`

### Engine D

Source file:
- `src/engines/engine_d/cost_feasibility_d.py`

Key implemented formula:
- same structure as Engine C with a different default CE floor

Engine-local conclusions:
- Engine-local CE/EV seams are expected, not realized.
- Engine C/D remain calibration-marked or partial by design.
- No engine-local seam was found that consumes Wave 3 replay cost-completeness statuses directly.

Tests:
- engine-local behavior is covered indirectly in `tests/test_engines/...` runtime and candidate tests

## Cockpit consequence

Source file:
- `src/cockpit/state_replay_metrics.py`

Evidence excerpt:
```python
def cost_model_is_complete(self) -> bool:
    return self.cost_model_completeness_status == "COMPLETE"

def cost_model_is_partial(self) -> bool:
    return not self.cost_model_is_complete
```

```python
if self.cost_model_is_partial:
    reason_codes.append("REPLAY_COST_MODEL_PARTIAL")
```

Meaning:
- Wave 3 cost completeness is proven as a replay/cockpit display safety seam.
- It is not proven as a governed runtime scoring/risk gate input.

False-green risk:
- if runtime rails can still score/rank candidates while replay cost completeness is partial, promotion or product narratives must not over-read runtime scoring as complete profitability proof

External-audit questions:
- Should governed score/risk rails consume `cost_model_completeness_status` directly, or is the current doctrine intentionally cockpit/report-only?
- Are engine-local expected-gain inputs already net of any missing replay fee/impact components, or only partially protected by separate edge gates?

