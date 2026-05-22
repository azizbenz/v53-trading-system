# Engine Audit - Run `f08fe2de918c2e79`

**Date:** 2026-05-22  
**Status:** Audit completed  
**Reference run:** `strategy_ladder_workflow-f08fe2de918c2e79`  
**Scope:** Engine-level blockers after a full `A1 -> A2 -> B1 -> B2` research run

---

## Executive Summary

This run does **not** support the claim that the failure is caused by proxy blockers alone.

The live engine layer still carries **independent native no-trade blockers**:

- `engine_a`: real `structure_unfavorable`
- `engine_b`: real split between `economics / break_even_not_cleared` and `no_excess`
- `engine_c`: rejected earlier in `B1`
- `engine_d`: real `history_weak / missing closed episode journal`

So the correct reading is:

- `EXPECTED_EDGE_PROXY_BLOCKED` is present on all replay records
- but it is **not** the only blocker
- removing proxy gating alone would **not** automatically create executed trades on this run

This is consistent with:

- `expected_edge_single_unblocker_status = EXPECTED_EDGE_SINGLE_UNBLOCKER_NOT_PROVEN`
- `native_no_trade_independent_blocker_count = 84`

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\expected_edge_readiness_audit.json`

---

## Run Context

The run is structurally coherent:

- `A1 -> A2 -> B1 -> B2` completed on the same workflow id
- `A2` is `DATA_FACTORY_READY`
- `A2` remains research-only because of:
  - `RAW_SOURCE_TYPE_INFERRED`
  - `CURRENT_METADATA_PROXY`
  - `SINGLE_PAIR_RESEARCH_ONLY`

Relevant artifacts:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\workflow_manifest.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_a2_data_factory\data_factory_manifest.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\preselection_summary.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\strategy_ladder_summary.json`

Key run outcomes:

- `B1 candidate_count = 40`
- `B1 preselected_count = 21`
- `B2 detailed_replay_count = 84`
- `B2 executed_trade_count = 0`
- `final_status = STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES`

---

## Engine-Level Distribution

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\engine_no_trade_diagnosis.json`

### Engine A

- replay records: `4`
- dominant blocker: `structure_unfavorable`

Interpretation:

- this is a real structure-quality refusal
- not a proxy-only refusal

### Engine B

- replay records: `40`
- dominant real blockers:
  - `economics.engine_b.cost.infeasible`
  - `break_even_not_cleared`
  - `engine_internal.engine_b.excess.no_excess`
  - `engine_b.excess.no_excess`

This is the densest actionable blocker on the run.

### Engine C

- replay records: `0`
- rejected earlier in `B1`

Interpretation:

- `engine_c` does not explain the `B2` no-trade wall on this run because it barely reaches `B2`

### Engine D

- replay records: `40`
- dominant blocker: `history_weak`
- missing prerequisite: closed episode journal

Interpretation:

- this is a real historical-prerequisite blocker
- not a proxy-only blocker

---

## Deep Audit - Engine B

### Aggregate Counts

Source files:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_candidates.jsonl`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\refusal_ledger.jsonl`

Observed live counts:

- `engine_b` preselected candidates: `10`
- `engine_b` replay records: `40`

Timeframe distribution:

- preselection:
  - `1m = 4`
  - `5m = 2`
  - `10m = 2`
  - `15m = 2`
- replay:
  - `1m = 16`
  - `5m = 8`
  - `10m = 8`
  - `15m = 8`

Reason-code distribution:

- present on all `40` replay records:
  - `ENGINE_NATIVE_NO_TRADE`
  - `EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH`
  - `EXPECTED_EDGE_PROXY_BLOCKED`
  - `FEE_AWARE_EDGE_PROXY_BLOCKED`
  - `BREAK_EVEN_PROXY_BLOCKED`
- real engine-local split:
  - `economics.engine_b.cost.infeasible` on `20`
  - `break_even_not_cleared` on `20`
  - `cost_infeasible` on `20`
  - `engine_internal.engine_b.excess.no_excess` on `20`
  - `engine_b.excess.no_excess` on `20`
  - `no_excess` on `20`

Conclusion from the counts:

- the `40` replay records split cleanly into:
  - `20` economics-blocked
  - `20` excess-blocked

This is the core proof that `engine_b` is **not** blocked by proxy gates alone.

---

## Engine B - Economics Family

Distinct candidate count in this family: `5`

Timeframes:

- `1m = 2`
- `5m = 1`
- `10m = 1`
- `15m = 1`

Observed proxy expected-edge range:

- min: `1.5958 bps`
- max: `6.5701 bps`
- average: `2.7748 bps`

Representative live candidates:

- `9199c6b7a9bf0eaec9096b8d`
- `2eb012aed689557030b1c2a3`
- `ecfcc4786386390ee06a3fae`
- `d6fc6786d9e43b7b9fa9335e`
- `ad2d94e0c01df2ed770beade`

Example evidence:

- candidate: `9199c6b7a9bf0eaec9096b8d`
- timeframe: `10m`
- file:
  - `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_candidates.jsonl`
- relevant payload:
  - `expected_edge_bps = 1.6296748498974916`
  - `spread_bps = 0.5`
  - `slippage_bps = 0.1`
  - `latency_penalty_bps = 1.5`
  - `production_expected_cost = 0.0002115`
  - `fee_bps = 10.0`
  - `feature_values.break_even_bps = 16.0`
  - `engine_native_reason_codes = ["economics.engine_b.cost.infeasible", "break_even_not_cleared"]`

Cross-check in replay:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\9199c6b7a9bf0eaec9096b8d.json`
- each capital bucket remains:
  - `execution_state = hard_blocked`
  - `expected_ce_net = -0.001049`
  - reason codes include:
    - `economics.engine_b.cost.infeasible`
    - `break_even_not_cleared`
    - `cost_infeasible`

Interpretation:

- for this family, the economics refusal is legitimate under the current canonical thresholds
- this is not a runner wiring bug

---

## Engine B - No-Excess Family

Distinct candidate count in this family: `5`

Timeframes:

- `1m = 2`
- `5m = 1`
- `10m = 1`
- `15m = 1`

Observed proxy expected-edge range:

- min: `1.5958 bps`
- max: `10.0826 bps`
- average: `5.9793 bps`

Representative live candidates:

- `03f5da39d5f6f949c45e5944`
- `374fcb39867dc43051bc101b`
- `46de87ec9207bfcd4cea3f7f`
- `c3b7429ac7d3fdebb7ea811d`
- `f9aaf742b9b8db8ef00b382c`

Example replay evidence:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\46de87ec9207bfcd4cea3f7f.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\374fcb39867dc43051bc101b.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\by_bucket\400\f9aaf742b9b8db8ef00b382c.json`

Observed replay outcome for this family:

- `execution_state = hard_blocked`
- reason codes include:
  - `engine_internal.engine_b.excess.no_excess`
  - `engine_b.excess.no_excess`
  - `no_excess`

Interpretation:

- some `engine_b` candidates still have positive proxy edge but are rejected because the mean-reversion setup is not strong enough
- so even with a governed expected-edge rail, these candidates would still need to clear the native excess gate

---

## Canonical Engine B Thresholds

### Excess Detection

Source:

- `src/engines/engine_b/excess_detector_b.py`

Relevant thresholds:

- `z_marginal = 1.0`
- `z_star = 1.5`

Canonical interpretation:

- if `abs(z_score) < 1.0` -> `NO_EXCESS`
- if `1.0 <= abs(z_score) < 1.5` -> marginal
- if `abs(z_score) >= 1.5` -> potentially exploitable

So the `no_excess` family is a real doctrine-level refusal, not a replay artifact.

### Cost Feasibility

Source:

- `src/engines/engine_b/cost_feasibility_b.py`

Relevant thresholds:

- `delta_safe = 0.0008`
- `ce_min = 0.0002`

Canonical condition:

- `expected_gain > expected_cost + delta_safe`

And then:

- `CE >= ce_min`

So the economics family is also a real doctrine-level refusal under the current thresholds.

---

## Builder / Wiring Assessment

Source:

- `src/local_replay_runtime/strategy_ladder_engine_b_input_builder.py`

Observed status on live candidates:

- `engine_native_builder_status = ENGINE_B_INPUT_BUILDER_READY`

The builder is expected to materialize:

- `current_price`
- `local_mean`
- `local_std`
- `vpin_current`

No evidence in this run shows a dominant `ENGINE_B_INPUT_BUILDER_*` failure mode.

Conclusion:

- this audit does **not** support a primary builder/wiring bug hypothesis for `engine_b`
- the dominant live failures are native economics and native excess selection

---

## Final Verdict

For run `f08fe2de918c2e79`, the correct statement is:

- `engine_b` is **not** blocked only by proxy expected-edge governance
- `engine_b` is also blocked by two real native families:
  - economics / break-even insufficiency
  - insufficient mean-reversion excess

Therefore:

- `P0-A` alone will **not** unlock `engine_b`
- `P0-B` remains necessary

The next engine-level audit priority should stay:

1. `engine_b` economics calibration and candidate quality
2. `engine_d` closed-episode prerequisite
3. only then broader re-evaluation of `P0-A governed expected-edge`

