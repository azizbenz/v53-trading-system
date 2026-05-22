# V5.3 Expected-Edge Proxy Gate Addendum

Date: 2026-05-19

## Purpose

This addendum corrects one important overstatement in the backtest diagnosis:

- `expected_ce_net < 0` is indeed a mechanical artifact when expected edge is still proxy-only
- but `expected-edge governed truth` is **not** the only blocker on the fresh workflow

The correct doctrine is:

- `expected-edge governed truth` is a major `P0`
- `ENGINE_NATIVE_NO_TRADE` remains an independent blocker on the same workflow

## Scope of verification

Fresh workflow used for verification:

- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-20260519-113403`

Code surfaces verified:

- [strategy_ladder_runner.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_runner.py:1937>)
- [strategy_ladder_runner.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_runner.py:1739>)
- [strategy_ladder_economic_provenance.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_economic_provenance.py:144>)

Artifact surfaces verified:

- [refusal_ledger.jsonl](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/refusal_ledger.jsonl:1>)
- [preselection_candidates.jsonl](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/preselection_candidates.jsonl:1>)
- [engine_no_trade_diagnosis.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/engine_no_trade_diagnosis.json:1>)
- [preselection_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/preselection_summary.json:1>)

## Finding 1

`expected_ce_net` is negative by construction when expected edge is proxy-only.

The code is explicit:

```python
edge_is_truth = is_expected_edge_backtest_truth(
    economic_provenance.expected_edge_provenance
)
expected_gain = (
    economic_provenance.expected_edge_bps / 10_000.0
    if edge_is_truth
    else 0.0
)
expected_cost = _expected_cost_from_provenance(economic_provenance)
```

So when provenance is:

- `PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE`

the runner forces:

- `expected_gain = 0.0`

while still keeping:

- `expected_cost > 0`

Therefore:

- `expected_ce_net <= 0`

This part of the diagnosis is correct.

## Finding 2

Several sampled candidates do carry positive proxy gross edge.

Verified examples:

- `54b7b55d...` `engine_d`
  - `expected_edge_bps = 12.7512`
- `f599d561...` `engine_d`
  - `expected_edge_bps = 5.9022`
- `f830a9c1...` `engine_b`
  - `expected_edge_bps = 7.5648`

So the negative `ce_net` does **not** prove that the engines predict negative edge.

It proves only that the governed runner refuses to score proxy edge as backtest truth.

## Finding 3

The overstatement is here:

- `expected-edge governed truth is the single unblocker`

This is not supported by the fresh workflow evidence.

Why:

The runner selects only if both conditions hold:

```python
target_state = "selected" if is_emit and edge_is_truth else "hard_blocked"
```

So even if expected edge becomes governed truth, a candidate is still blocked when:

- `is_emit == False`

That is exactly what the fresh workflow still shows.

## Finding 4

`ENGINE_NATIVE_NO_TRADE` is an independent blocker on the fresh workflow.

Verified in:

- [engine_no_trade_diagnosis.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/engine_no_trade_diagnosis.json:1>)

Common blockers:

- `BREAK_EVEN_PROXY_BLOCKED`
- `ENGINE_NATIVE_NO_TRADE`
- `EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH`
- `EXPECTED_EDGE_PROXY_BLOCKED`
- `FEE_AWARE_EDGE_PROXY_BLOCKED`

This means:

- proxy edge governance is one blocker
- engine-native no-trade remains another blocker

## Finding 5

The native engines are still rejecting for engine-specific reasons that are not reducible to the proxy edge gate.

Examples on the fresh workflow:

- `engine_a`
  - `structure_unfavorable`
  - `cost_infeasible`
- `engine_b`
  - `no_excess`
  - `cost_infeasible`
- `engine_d`
  - `history_weak`
  - `ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL`

These are real engine-native blockers, not just a scoring artifact.

## Finding 6

The fresh `B1.5` surface already proves that native engines are not all waiting only on expected-edge truth.

Verified in:

- [preselection_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/preselection_summary.json:1>)

Observed:

- `engine_native_preselected_count = 493`
- `preselection_hard_rejected_count = 507`

Top hard rejection reasons are already engine-native:

- `non_long_direction`
- `engine_c.no_trade.non_long_breakout`
- `engine_a.input.non_long_direction`
- `engine_b.direction.non_long`

So some blockers happen even before the expected-edge truth gate matters.

## Corrected conclusion

The correct conclusion is:

1. `expected_ce_net < 0` is a mechanical artifact under proxy expected edge.
2. This artifact does **not** prove that V5.3 predicts negative edge.
3. But it is not valid to conclude that governed expected-edge is the unique blocker.
4. The fresh workflow has two independent blocker classes:
   - `expected-edge not governed backtest truth`
   - `engine-native no-trade / native hard blockers`

## Corrected prioritization

### P0-A

Build `EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH`.

Why:

- it is necessary to remove the mechanical `expected_gain = 0` fail-closed behavior

### P0-B

Close the dominant `ENGINE_NATIVE_NO_TRADE` blockers that remain independent of expected-edge truth.

Why:

- even with governed expected edge, `is_emit` must still be true

### P1

Upgrade spread/slippage/adverse-selection from partial/proxy realism toward measured execution realism.

### P2

Only after first executed trades:

- statistical validation
- PSR
- DSR
- MinTRL

## What this addendum changes

It changes:

- the statement that expected-edge governed truth is the unique unblocker

It does not change:

- the fact that governed expected-edge is still a major `P0`
- the fact that profitability is still unproven
- the fact that the canonical workflow remains blocked by `0 executed trades`

## Final operator summary

The fresh workflow does **not** show:

- `V5.3 loses money`

It also does **not** show:

- `expected-edge model alone will unblock everything`

What it shows is:

- proxy edge can be positive
- proxy scoring is fail-closed by doctrine
- native engines still reject many candidates for their own reasons

So the correct next move is:

- treat governed expected-edge as a major `P0`
- but keep native no-trade closure in the same top tier
