# Wave 3 Break-Even / Cost Gate Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## 1. Replay CE / expected-cost seam

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Function: `simulate_shadow_compatible_dtrs`

```python
expected_cost=round(expected_cost, 6),
realized_cost=round(expected_cost * execution_factor, 6),
gross_return=gross_return,
ce_expected=round((row.expected_edge_bps / 10_000.0) - expected_cost, 6),
```

Plain-text formulas:
- `expected_cost = prudent replay cost fraction`
- `realized_cost = expected_cost * execution_factor`
- `ce_expected = expected_edge_fraction - expected_cost`

Scope:
- per-record replay DTR

Expected/realized semantics:
- `expected_cost`: expected
- `realized_cost`: simulated realized
- `ce_expected`: expected CE, not realized PnL

Non-executed records:
- can carry non-zero `expected_cost`
- can carry non-zero `ce_expected`
- carry zero `realized_cost` when `execution_factor = 0`

## 2. Break-even filter seam

Source file: `src/scoring_backbone/break_even_filter.py`  
Function: `evaluate_break_even_filter`

```python
expected_break_even = expected_cost + delta_safe
ev_net = candidate_size * (expected_gain - expected_cost)
...
if not edge_cleared:
    reason_code = "BREAK_EVEN_NOT_CLEARED"
elif not ce_cleared:
    reason_code = "CE_BELOW_MINIMUM"
elif not ev_cleared:
    reason_code = "EV_NET_BELOW_FLOOR"
```

Plain-text formulas:
- `expected_break_even = expected_cost + delta_safe`
- `ev_net = candidate_size * (expected_gain - expected_cost)`

Units:
- `expected_gain`, `expected_cost`, `expected_break_even`, `expected_ce`: fraction
- `ev_net`: notional-scaled fraction / account-value proxy

Scope:
- per-candidate selection gate

Reason codes:
- `BREAK_EVEN_NOT_CLEARED`
- `CE_BELOW_MINIMUM`
- `EV_NET_BELOW_FLOOR`

## 3. Order-type selector economics gate

Source file: `src/execution_backbone/order_decider/order_type_selector.py`  
Function: `select_order_type`

```python
net_expected = expected_gain - expected_cost - safety_margin
if net_expected <= 0:
    return OrderTypeDecision(order_type=OrderType.NO_TRADE, ...)
if spread_bps > max_spread_for_market:
    return OrderTypeDecision(order_type=OrderType.NO_TRADE, ...)
if spread_bps > use_limit_threshold_bps:
    return OrderTypeDecision(order_type=OrderType.LIMIT, ...)
return OrderTypeDecision(order_type=OrderType.MARKET, ...)
```

Evidence:
- Candidate is blocked when `expected_gain <= expected_cost + safety_margin`
- Wide spread can also veto or force limit path

Reason behavior:
- no-trade rather than synthetic side change

## 4. Fee-aware edge gate

Source file: `src/execution_backbone/fee_aware_edge_gate.py`  
Evidence already verified in runtime tests:
- blocks with context `reason_code = EDGE_INSUFFICIENT_VS_FEES`
- uses `expected_edge_bps`, `expected_cost_bps`, and threshold

Primary proving test:
- `tests/test_execution_backbone/test_execution_runtime.py::test_runtime_blocks_trade_when_fee_aware_edge_gate_rejects`

## 5. Meta break-even seams

Source file: `src/meta_minimal/break_even_dashboard/expected_break_even_calculator.py`

```python
simple = expected_fee + expected_spread + expected_slippage + expected_adverse
prudent = expected_fee + spread_p90 + slippage_p90 + adverse_p90
```

Source file: `src/meta_minimal/break_even_dashboard/realized_break_even_calculator.py`

```python
net = gross_return - realized_cost
cost_drift=realized_cost - expected_cost
```

Evidence:
- Meta dashboard separately models ex-ante and ex-post break-even
- Fees are explicitly present in meta expected break-even

Tests:
- `tests/test_meta_minimal/test_break_even_dashboard_minimal.py::TestExpectedBreakEven::*`
- `tests/test_meta_minimal/test_break_even_dashboard_minimal.py::TestRealizedBreakEven::*`

External-audit questions:
- Replay expected-cost seam omits explicit fee while meta expected break-even includes expected fee. Is that a designed split between replay DTR economics and post-hoc dashboard doctrine?
