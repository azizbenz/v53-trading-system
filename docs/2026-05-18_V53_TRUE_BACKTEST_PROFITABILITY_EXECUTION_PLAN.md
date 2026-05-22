# V5.3 True Backtest Profitability Execution Plan

Date: 2026-05-18

## Objective

Obtain a defensible answer to the question:

`Is V5.3 economically profitable or not under governed replay conditions?`

This plan is not a generic roadmap. It is a concrete execution plan derived from the current repo truth and the latest governed workflow outputs.

Priority note updated on 2026-05-19:

- [2026-05-19_V53_EXPECTED_EDGE_PROXY_GATE_ADDENDUM.md](/E:/claude%20%20v5.3/v53_trading_system/docs/2026-05-19_V53_EXPECTED_EDGE_PROXY_GATE_ADDENDUM.md:1)
- governed expected-edge remains a major `P0`
- but it is not the unique unblocker on the fresh workflow because `ENGINE_NATIVE_NO_TRADE` remains independently active

## Current Ground Truth

### Current workflow truth

Reference workflow:

- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-03a3ffe88660751e`

Current B2 result:

- `final_status = STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES`
- `candidate_count = 1000`
- `detailed_replay_count = 2008`
- `executed_trade_count = 0`

Reference artifacts:

- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-03a3ffe88660751e\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-03a3ffe88660751e\run_manifest.json`
- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-03a3ffe88660751e\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-03a3ffe88660751e\reports\strategy_ladder_summary.json`
- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-03a3ffe88660751e\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-03a3ffe88660751e\reports\engine_no_trade_diagnosis.json`
- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-03a3ffe88660751e\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-03a3ffe88660751e\reports\expected_edge_readiness_audit.json`

### Current blocker truth

The current blocker is not workflow wiring anymore. The `A1 -> A2 -> B1 -> B2` chain now runs in one workflow tree.

The current blocker is economic and governance-related:

- `NO_EXECUTED_TRADES`
- `EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH`
- `SPREAD_MODEL_PROXY`
- `SLIPPAGE_MODEL_PROXY`
- `ADVERSE_SELECTION_PROXY`
- `STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS`

### Current ML truth

Reference ML handoff:

- `K:\v5.3 backtest\output2\ml_handoffstrategy\runs\strategy_ladder_ml_lab_handoff-1779100666253`

The multiframe bundle exists and is fresh enough for the requested backtest window, but it is still research-grade:

- `timeframe_scope = 1m, 5m, 10m, 15m`
- every timeframe slice is `ready = true` as an artifact
- every timeframe slice still has `label_fidelity = EXPECTED_EDGE_PROXY_DISCOVERY_ONLY`
- `replay_grounded_label_count = 0`

This means:

- the bundle is valid as a research artifact
- it is not yet valid as governed backtest truth
- therefore `TIMEFRAME_SLICE_NOT_READY` in B2 means `slice not promotion-grade`, not `slice missing`

## Non-Negotiable Scientific Rules

1. A profitability claim requires executed trades, not only candidates or replay records.
2. A net profitability claim requires measured execution costs, not proxy-only spread/slippage/adverse-selection placeholders.
3. A governed ML overlay cannot block or prove profitability while its labels remain proxy-only.
4. A 30-day or short-window run may be operationally useful, but it is not promotion-grade statistical proof.
5. Statistical validation must be based on executed returns with PSR, DSR, effective sample size, and MinTRL logic.

## Decision Framework

We split the problem into two truth surfaces.

### Surface A: Canonical strategy truth

Question:

`Can the canonical V5.3 strategy trade and produce net executed returns under governed replay?`

This must be answered first, without depending on a research-only ML gate.

### Surface B: ML overlay truth

Question:

`Does the governed expected-edge overlay improve or degrade canonical V5.3 on the same governed replay surface?`

This must be answered only after Surface A is healthy.

## Execution Plan

## Phase 0 — Stabilize the truth surface

### Goal

Stop mixing orchestration problems with economic problems.

### Required actions

1. Keep one workflow id per chain:
   - `A1 -> A2 -> B1 -> B2`
   - same dates
   - same raw roots
   - same output root

2. Treat cockpit state as an orchestration layer only.
   - If cockpit UI is stale, runner artifacts remain the source of truth.
   - Debug economics from the produced manifests, not from UI claims.

3. Freeze one canonical test window for current remediation.
   - Current working window:
   - `2025-07-18 -> 2025-07-28`

### Exit criteria

- one workflow folder
- one A2 folder
- one B1 folder
- one B2 folder
- no ambiguity about which artifacts are current

## Phase 1 — Make canonical B2 produce executed trades

### Goal

Move from:

- `candidate_count > 0`
- `selected_count = 0`
- `executed_count = 0`

to:

- `selected_count > 0`
- `executed_trade_count > 0`

### Current evidence

`engine_no_trade_diagnosis.json` currently says:

- `FIRST_GATE_BLOCKS_BEFORE_SELECTION`
- common blockers:
  - `BREAK_EVEN_PROXY_BLOCKED`
  - `ENGINE_NATIVE_NO_TRADE`
  - `EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH`
  - `EXPECTED_EDGE_PROXY_BLOCKED`
  - `FEE_AWARE_EDGE_PROXY_BLOCKED`

### Required actions

1. Stop using research-only expected-edge as a hard truth gate for canonical profitability.
   - Canonical profitability must be measurable with `ML_MODE_OFF` or with the ML overlay explicitly non-blocking.
   - A research-only overlay must not zero out the entire selected funnel.

2. Audit the first gate in replay order.
   - Identify the first boolean or economic veto that turns every replay record into `no trade`.
   - Trace it per engine and per capital bucket.

3. Repair Engine D historical dependency as diagnosis, not as folklore.
   - Confirm whether `closed_episode_journal` is structurally missing or correctly empty because there are no prior valid episodes.

4. Repair Engine C microstructure consumption only after the first gate is isolated.
   - Do not treat “microstructure missing” and “microstructure consumed but blocked” as the same issue.

### Exit criteria

- `selected_count > 0`
- `executed_trade_count > 0`
- `NO_EXECUTED_TRADES` disappears from the blocker set

## Phase 2 — Replace proxy execution realism with measured realism

### Goal

Make net PnL economically meaningful.

### Current evidence

Current gaps in B2:

- `SPREAD_MODEL_PROXY`
- `SLIPPAGE_MODEL_PROXY`
- `ADVERSE_SELECTION_PROXY`

### Required actions

1. Spread realism
   - Audit why the replay still falls back to proxy spread despite book/depth20 being present.
   - Ensure measured spread is transported end-to-end into B2 reports and engine economics.

2. Slippage realism
   - Replace proxy slippage with depth20 or replay-measured slippage.
   - Make the replay expose the slippage provenance per candidate and per execution.

3. Adverse selection realism
   - Replace blocked/proxy adverse-selection status with a measured replay-backed metric.

4. Cost completeness
   - Ensure break-even and fee-aware gates use measured cost inputs, not proxy placeholders.

### Exit criteria

- `SPREAD_MODEL_PROXY` removed
- `SLIPPAGE_MODEL_PROXY` removed
- `ADVERSE_SELECTION_PROXY` removed
- `economic_constants_provenance` no longer `PARTIALLY_MEASURED`

## Phase 3 — Establish canonical profitability without ML truth dependence

### Goal

Get the first honest answer to:

`Does V5.3 trade profitably under governed replay economics?`

### Required actions

1. Run the same governed replay with:
   - `ML_MODE_OFF`
   - same dates
   - same roots
   - same candidate discovery mode
   - same cost realism stack

2. Treat this canonical run as the baseline truth.

3. Record:
   - gross return
   - net executed return
   - drawdown
   - execution rate
   - block rate
   - cost completeness status

### Exit criteria

- a canonical B2 with executed trades
- measured net returns
- no dependence on research-only ML truth

## Phase 4 — Build a governed expected-edge dataset

### Goal

Upgrade the ML overlay from research artifact to governed backtest artifact.

### Current evidence

All timeframe slices in the current bundle are:

- `ready = true`
- but `label_fidelity = EXPECTED_EDGE_PROXY_DISCOVERY_ONLY`
- and `replay_grounded_label_count = 0`

### Required actions

1. Build a replay-grounded label store from B2.
   - Labels must come from replay-backed execution-aware truth.
   - Not from `ABS_FORWARD_CLOSE_RETURN` proxy discovery labels.

2. Produce promotion-grade fields for each timeframe slice:
   - replay-grounded label coverage
   - label fidelity
   - anti-leakage proof
   - walk-forward declaration
   - purge/embargo declaration

3. Re-run IA Lab on that governed dataset.

4. Ensure each slice reaches:
   - `EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY`

### Exit criteria

- bundle still multiframe
- every required timeframe slice promotion-grade
- `TIMEFRAME_SLICE_NOT_READY` removed for the consumed slices

## Phase 5 — Compare canonical vs ML overlay on the same governed window

### Goal

Answer whether the ML overlay improves or degrades the canonical strategy.

### Required actions

Run paired experiments:

1. canonical
   - `ML_MODE_OFF`

2. overlay
   - `ML_MODE_OVERLAY_FROZEN`
   - same dates
   - same candidates
   - same replay realism
   - same capital buckets

### Metrics to compare

- executed trade count
- net return
- drawdown
- execution rate
- refusal distribution
- cost distribution
- engine-level contribution
- pair-level contribution
- capital-bucket stability

### Exit criteria

- side-by-side governed comparison
- no proxy-only ML truth in the overlay path

## Phase 6 — Statistical proof layer

### Goal

Decide whether any observed profitability is statistically defensible.

### Required actions

1. Keep `TEMPORAL_STRATIFIED` candidate discovery for long windows.
2. Use executed returns only.
3. Require:
   - effective sample size
   - PSR
   - DSR
   - MinTRL satisfied

4. Distinguish clearly:
   - research-grade run
   - promotion-grade run

### Promotion-grade minimum

A promotion-grade profitability claim requires at least:

- executed returns measured
- non-proxy cost realism
- statistical validation ready
- evidence audit confirmed
- no false green from cockpit/UI

## Practical Patch Order

### P0

1. Make canonical B2 run without research-only ML veto.
2. Get `selected_count > 0`.
3. Get `executed_trade_count > 0`.

### P1

1. Fix measured spread transport.
2. Fix slippage realism.
3. Fix adverse-selection realism.

### P2

1. Build replay-grounded expected-edge label store.
2. Re-run IA Lab to get governed slices.
3. Compare `ML off` vs `ML overlay frozen`.

### P3

1. Run longer-window temporal-stratified backtests.
2. Apply PSR/DSR/MinTRL gating on executed returns.

## Done Definition

We can say:

`V5.3 is profitable`

or

`V5.3 is not profitable`

only if all of the following are true:

1. `executed_trade_count > 0`
2. net return is computed from measured execution realism
3. no spread/slippage/adverse-selection proxy blockers remain on the truth path
4. the strategy is not blocked by research-only ML governance
5. statistical validation is ready on executed returns
6. the claim is supported by governed artifacts, not by cockpit screenshots

## Immediate Next Action

The next correct move is:

1. run a canonical B2 on the same window with `ML_MODE_OFF`
2. verify whether executed trades appear
3. if still zero, debug the first gate before touching ML again

This is the shortest path to a real profitability verdict.
