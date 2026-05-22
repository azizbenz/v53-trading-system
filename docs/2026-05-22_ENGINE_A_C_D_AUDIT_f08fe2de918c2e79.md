# Engine A / C / D Audit - Run `f08fe2de918c2e79`

**Date:** 2026-05-22  
**Status:** Audit completed  
**Reference run:** `strategy_ladder_workflow-f08fe2de918c2e79`  
**Scope:** Root-cause audit for `engine_a`, `engine_c`, and `engine_d` on the live research run

Related engine-b audit:

- `E:\claude  v5.3\v53_trading_system\docs\2026-05-22_ENGINE_AUDIT_f08fe2de918c2e79.md`

---

## Executive Summary

The correct reading for this run is:

- `engine_a` is blocked by a **real upstream direction gate** on most candidates, and by a **real structure gate** on the single candidate that reaches `B2`
- `engine_c` is blocked **upstream in B1**, not in `B2`
- `engine_d` is blocked by a **missing historical prerequisite**: no closed episode journal is available

So for `A/C/D`, the blockers are **not proxy-only**.

The proxy layer is present everywhere, but:

- `engine_a` has real native reasons
- `engine_c` fails before replay because the breakout is not long/usable
- `engine_d` has no valid history source to support a second-chance re-entry

This is the same doctrinal pattern already proven by:

- `expected_edge_single_unblocker_status = EXPECTED_EDGE_SINGLE_UNBLOCKER_NOT_PROVEN`
- `native_no_trade_independent_blocker_count = 84`

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\expected_edge_readiness_audit.json`

---

## Run Context

The run is structurally coherent:

- `A1 -> A2 -> B1 -> B2` on one workflow id
- `A2` is `DATA_FACTORY_READY`
- `B1 candidate_count = 40`
- `B1 preselected_count = 21`
- `B2 replay_record_count = 84`
- `executed_trade_count = 0`

Key artifacts:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\workflow_manifest.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\preselection_summary.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\strategy_ladder_summary.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\engine_no_trade_diagnosis.json`

---

## Aggregate Distribution

### Preselected Candidates

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_candidates.jsonl`

Observed live counts:

- `engine_a = 1`
- `engine_c = 0`
- `engine_d = 10`

### B1 Hard Rejections

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_rejection_ledger.jsonl`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\preselection_summary.json`

Observed hard rejects:

- `engine_a`: `9`
  - reason family: `engine_internal.engine_a.direction.non_long`
  - surface codes:
    - `engine_a.input.non_long_direction`
    - `non_long_direction`
- `engine_c`: `10`
  - reason family: `engine_c.no_trade.non_long_breakout`
  - surface code:
    - `non_long_breakout`

### B2 Replay Records

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\refusal_ledger.jsonl`

Observed replay counts:

- `engine_a = 4`
- `engine_c = 0`
- `engine_d = 40`

Interpretation:

- `engine_c` is not a `B2` blocker on this run because it is filtered out in `B1`
- `engine_a` and `engine_d` do reach `B2`, but remain native `no_trade`

---

## Engine A

### Root Cause on This Run

`engine_a` has **two distinct live blockers**:

1. upstream `B1` hard reject on most candidates:
   - `non_long_direction`
2. native `B2` structure refusal on the one candidate that survives preselection:
   - `structure_unfavorable`

So `engine_a` is **not** blocked only by the proxy gate.

### B1 Hard-Reject Surface

Representative artifact:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_rejection_ledger.jsonl`

Example rows:

- `6d5d3daef65f2b110fa08330`
- `b69f0bdc0de4b829b5608837`
- `bcd3a16173c9f3db86c789a8`
- `983749c1cf72f78456aea38b`

Observed live properties:

- `engine_native_builder_status = ENGINE_A_INPUT_BUILDER_READY`
- `preselection_decision = REJECTED_HARD`
- `preselection_reason_primary = engine_internal.engine_a.direction.non_long`
- hard rejection codes include:
  - `engine_internal.engine_a.direction.non_long`
  - `engine_a.input.non_long_direction`
  - `non_long_direction`

Interpretation:

- the builder is present and alive
- the primary failure is directional eligibility, not missing payload construction

### B2 Native Blocker

Preselected candidate:

- `e0f9230964ad600a55bf3d06`

Source artifacts:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_candidates.jsonl`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\e0f9230964ad600a55bf3d06.json`

Observed live properties:

- timeframe: `1m`
- `expected_edge_bps = 4.900880500856955`
- `engine_native_builder_status = ENGINE_A_INPUT_BUILDER_READY`
- `engine_native_reason_codes = ["engine_internal.engine_a.structure.unfavorable", "engine_a.structure.unfavorable"]`
- each capital bucket in `B2` remains:
  - `execution_state = hard_blocked`
  - `expected_ce_net = -0.000721`
  - reason codes include:
    - `engine_internal.engine_a.structure.unfavorable`
    - `engine_a.structure.unfavorable`
    - `structure_unfavorable`

### Canonical Thresholds

Source:

- `src/engines/engine_a/structure_detector_a.py`

Relevant thresholds:

- `favorable = 0.60`
- `marginal = 0.30`
- `min_direction = 0.20`

Canonical logic:

- if `direction_strength < 0.20` -> `UNFAVORABLE`
- else if `score >= 0.60` -> `FAVORABLE`
- else if `score >= 0.30` -> `MARGINAL`
- else -> `UNFAVORABLE`

Interpretation:

- `engine_a` is behaving as a real native filter
- this run shows both an upstream direction gate and a downstream structure gate

### Verdict for Engine A

- **Not proxy-only**
- **Not an obvious builder bug**
- Real blocker class:
  - upstream direction gating
  - native structure quality gating

---

## Engine C

### Root Cause on This Run

`engine_c` does **not** reach `B2` on this run.

It is fully blocked in `B1` by:

- `engine_c.no_trade.non_long_breakout`

And all live rejected candidates show:

- `engine_native_builder_status = ENGINE_C_INPUT_BUILDER_NO_BREAKOUT`

So the correct diagnosis is:

- this is an **upstream breakout eligibility problem**
- not a `B2` runtime blocker
- not a proxy-only blocker

### Live Evidence

Source:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_rejection_ledger.jsonl`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\reports\preselection_summary.json`

Observed live counts:

- rejected candidates: `10`
- timeframe split:
  - `1m = 4`
  - `5m = 2`
  - `10m = 2`
  - `15m = 2`
- builder status:
  - `ENGINE_C_INPUT_BUILDER_NO_BREAKOUT = 10`
- hard rejection codes:
  - `engine_c.no_trade.non_long_breakout = 10`
  - `non_long_breakout = 10`

Representative candidates:

- `9f62ced7d3826ee6117be4b0`
- `05f189da1f74fd865872376e`
- `783d1df8ff29dbb34b64a810`

Observed soft advisory layer on the same rows:

- `ENGINE_C_INPUT_BUILDER_NO_BREAKOUT`
- `engine_internal.engine_c.breakout.non_long`
- `engine_internal.engine_c.breakout.structured_breakout`
- `engine_c.breakout.structured_breakout`
- `engine_internal.engine_c.continuation.fresh_breakout`
- `engine_c.continuation.fresh_breakout`
- `engine_c.microstructure.contradictory`
- plus the standard proxy research-only blockers

Interpretation:

- the candidate windows are still not materializing a long breakout that `engine_c` can legally take
- the issue is upstream setup eligibility, not replay execution

### Canonical Thresholds

Source:

- `src/engines/engine_c/engine_c_runner.py`

Relevant thresholds:

- `breakout_score_min = 0.62`
- `breakout_strength_min = 0.55`
- `range_quality_min = 0.50`
- `fake_breakout_risk_max = 0.65`

Important nuance:

- on this run, the dominant surface is even earlier than those thresholds:
  - `ENGINE_C_INPUT_BUILDER_NO_BREAKOUT`
  - `NON_LONG_BREAKOUT`

So `engine_c` does not yet meaningfully enter the downstream `B2` decision wall.

### Verdict for Engine C

- **Not proxy-only**
- **Upstream blocker**
- Real blocker class:
  - no long breakout materialized at `B1`
  - builder/no-breakout surface dominates

---

## Engine D

### Root Cause on This Run

`engine_d` is blocked by a missing historical prerequisite:

- no valid closed episode journal

This is visible both in the builder surface and in the replay outcome:

- builder status:
  - `ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE`
- closed episode manifest:
  - `record_count = 0`
  - `status = CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES`
- replay reasons:
  - `ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL`
  - `engine_internal.engine_d.history.weak`
  - `engine_d.no_trade.history_weak`

So `engine_d` is **not** primarily blocked by proxy gating.  
It is blocked because its historical re-entry contract is not satisfied.

### Live Evidence

Source artifacts:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_candidates.jsonl`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\closed_episode_manifest.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\f52d2c3a86d2e394e25007b6.json`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\detailed_replay\shared\f52d2c3a86d2e394e25007b6.json`

Observed live counts:

- preselected candidates: `10`
- replay records: `40`
- timeframe split:
  - `1m = 16`
  - `5m = 8`
  - `10m = 8`
  - `15m = 8`

Representative candidate:

- `f52d2c3a86d2e394e25007b6`

Observed live properties:

- `expected_edge_bps = 1.6296748498974916`
- `engine_native_reason_codes = ["engine_internal.engine_d.history.weak", "engine_d.no_trade.history_weak"]`
- `engine_native_builder_status = ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE`
- compatibility notes include:
  - `BUILDER_NO_FIRST_EPISODE_DEFAULTS`

Closed-episode state:

- `record_count = 0`
- `status = CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES`
- `source_status = REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE`

Replay outcome:

- every capital bucket remains `hard_blocked`
- reason codes include:
  - `ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL`
  - `engine_internal.engine_d.history.weak`
  - `engine_d.no_trade.history_weak`
  - `history_weak`

### Canonical Thresholds

Source:

- `src/engines/engine_d/engine_d_runner.py`

Relevant thresholds:

- `_HISTORY_MIN = 0.55`
- `_REFORMATION_MIN = 0.58`
- `_CONCENTRATION_MAX = 0.64`

Canonical history logic:

- `history_score = compute_history_score(inputs)`
- if `history_score < 0.55` -> `HISTORY_WEAK`

Interpretation:

- on this run, the history gate is blocked before any meaningful re-entry opportunity can be asserted
- the empty closed-episode journal is the decisive live root cause

### Build-14 Note

`engine_d` rows also carry Build-14 shadow advisory reasons:

- `BUILD14_SHADOW_ENABLED_ACTIVE`
- `BUILD14_READER:execution_fragility_score:ELEVATED`
- `BUILD14_READER:micro_edge_exit_governor:ELEVATED`

These are **not** the primary root cause here.

The primary root cause remains:

- missing closed-episode history
- hence `history_weak`

### Verdict for Engine D

- **Not proxy-only**
- **Not primarily a code bug in the engine core**
- Real blocker class:
  - missing historical prerequisite
  - builder defaults because no first episode is available
  - native `history_weak`

---

## Final Verdict

For run `f08fe2de918c2e79`:

- `engine_a` is blocked by real direction/structure filters
- `engine_c` is blocked upstream in `B1` by no valid long breakout
- `engine_d` is blocked by missing closed-episode history

Therefore:

- `P0-A` alone will **not** unlock `A/C/D`
- `P0-B` remains necessary
- and for `engine_d`, `closed_episode_journal` is still a hard prerequisite before any serious profitability claim

Recommended next order after `engine_b`:

1. `engine_d` prerequisite closure: `closed_episode_journal`
2. `engine_a` calibration review only after more live candidates accumulate
3. `engine_c` upstream candidate-generation / breakout eligibility audit

