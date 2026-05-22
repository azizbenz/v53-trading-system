# Engine B Calibration Audit - Run `f08fe2de918c2e79`

**Date:** 2026-05-22  
**Status:** Fine calibration audit completed  
**Reference run:** `strategy_ladder_workflow-f08fe2de918c2e79`  
**Scope:** `engine_b` blocker decomposition by family:

- `economics / break_even_not_cleared`
- `no_excess`

Related coarse audit:

- `E:\claude  v5.3\v53_trading_system\docs\2026-05-22_ENGINE_AUDIT_f08fe2de918c2e79.md`

---

## Executive Summary

Yes, this is the correct next step for `engine_b`: a **fine calibration audit**, not a blind threshold patch.

This audit shows three important truths:

1. the live `engine_b` blocker is **not proxy-only**
2. the `economics` family is **not** rescued by simply allowing proxy edge
3. the `no_excess` family is **not** a near-miss cluster around `z_marginal = 1.0`

So the correct conclusion is:

- do **not** lower `delta_safe` or `z_marginal` blindly
- do **not** treat `engine_b` as a simple proxy-governance victim
- first quantify the families, then decide if calibration is justified on a longer governed run

---

## Canonical Thresholds

### Native Expected-Gain Handling

Source:

- `src/local_replay_runtime/strategy_ladder_runner.py`

Live native rail logic:

- `edge_is_truth = is_expected_edge_backtest_truth(...)`
- `expected_gain = economic_provenance.expected_edge_bps / 10_000.0 if edge_is_truth else 0.0`

Relevant lines:

- `src/local_replay_runtime/strategy_ladder_runner.py:2014`
- `src/local_replay_runtime/strategy_ladder_runner.py:2017`

Meaning:

- in the current live run, `engine_b` native cost evaluation receives `expected_gain = 0`
- because `expected_edge` is still proxy, not governed truth

This makes the live economics fail-closed.

But this audit also checks the counterfactual:

- even if proxy edge were admitted as `expected_gain`
- would the current `engine_b` thresholds still reject these candidates?

### Engine B Cost Thresholds

Source:

- `src/engines/engine_b/cost_feasibility_b.py`

Relevant thresholds:

- `delta_safe = 0.0008` = `8.0 bps`
- `ce_min = 0.0002` = `2.0 bps`

Native rule:

- `break_even = expected_cost + delta_safe`
- blocker if `expected_gain <= break_even`

Relevant lines:

- `src/engines/engine_b/cost_feasibility_b.py:39`
- `src/engines/engine_b/cost_feasibility_b.py:40`
- `src/engines/engine_b/cost_feasibility_b.py:90`
- `src/engines/engine_b/cost_feasibility_b.py:105`

### Engine B Excess Thresholds

Source:

- `src/engines/engine_b/excess_detector_b.py`

Relevant thresholds:

- `z_marginal = 1.0`
- `z_star = 1.5`

Native rule:

- if `abs(z) < 1.0` -> `NO_EXCESS`
- if `1.0 <= abs(z) < 1.5` -> marginal
- if `abs(z) >= 1.5` -> potentially exploitable

Relevant lines:

- `src/engines/engine_b/excess_detector_b.py:64`
- `src/engines/engine_b/excess_detector_b.py:65`
- `src/engines/engine_b/excess_detector_b.py:141`
- `src/engines/engine_b/excess_detector_b.py:176`

---

## Live Population

Source artifacts:

- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b1_candidate_discovery\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\preselection_candidates.jsonl`
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79\phase_b2_detailed_replay\backtest_strategy_ladder\strategy_ladder_workflow-f08fe2de918c2e79\refusal_ledger.jsonl`

Live split already proven:

- `10` distinct `engine_b` candidates
- `40` replay records
- `5` candidates in `economics` family
- `5` candidates in `no_excess` family

Distinct family membership:

### Economics family

- `2eb012aed689557030b1c2a3`
- `9199c6b7a9bf0eaec9096b8d`
- `ad2d94e0c01df2ed770beade`
- `d6fc6786d9e43b7b9fa9335e`
- `ecfcc4786386390ee06a3fae`

### No-excess family

- `03f5da39d5f6f949c45e5944`
- `374fcb39867dc43051bc101b`
- `46de87ec9207bfcd4cea3f7f`
- `c3b7429ac7d3fdebb7ea811d`
- `f9aaf742b9b8db8ef00b382c`

---

## Family 1 - Economics

### Live Measurements

For this run:

- `production_expected_cost = 0.0002115`
- this is `2.115 bps`

So the **native** `engine_b` economics hurdle is:

- `native_break_even_bps = expected_cost_bps + delta_safe_bps`
- `native_break_even_bps = 2.115 + 8.0 = 10.115 bps`

This is distinct from the broader top-level payload field:

- `feature_values.break_even_bps = 16.0`

The `16.0 bps` payload hurdle is stricter, but the native `engine_b` blocker already fails before that.

### Per-Candidate Distances

| Candidate | TF | expected_edge_bps | native_break_even_bps | native_margin_bps | abs(z) |
|---|---:|---:|---:|---:|---:|
| `2eb012aed689557030b1c2a3` | 15m | 6.5701 | 10.115 | -3.5449 | 2.6813 |
| `9199c6b7a9bf0eaec9096b8d` | 10m | 1.6297 | 10.115 | -8.4853 | 2.6813 |
| `ad2d94e0c01df2ed770beade` | 1m | 1.5958 | 10.115 | -8.5192 | 2.2869 |
| `d6fc6786d9e43b7b9fa9335e` | 5m | 2.4443 | 10.115 | -7.6707 | 2.6813 |
| `ecfcc4786386390ee06a3fae` | 1m | 1.6344 | 10.115 | -8.4806 | 2.6813 |

Family summary:

- average `expected_edge_bps = 2.7748`
- average `native_margin_bps = -7.3402`
- min `native_margin_bps = -8.5192`
- max `native_margin_bps = -3.5449`

### Critical Interpretation

This is the key result:

- the live rail currently feeds `expected_gain = 0` to native `engine_b`
- **but even if proxy edge were admitted as expected_gain**, all `5/5` economics candidates still fail the current native break-even hurdle

So:

- this family is **not** just a fail-closed artifact
- it is also **truly weak under current engine_b economics thresholds**

### Sensitivity - How Much `delta_safe` Would Need To Move?

For a candidate to pass native economics:

- required `delta_safe_bps <= expected_edge_bps - expected_cost_bps`

Required `delta_safe_bps` by candidate:

- `2eb012aed689557030b1c2a3` -> `4.4551`
- `9199c6b7a9bf0eaec9096b8d` -> `-0.4853`
- `ad2d94e0c01df2ed770beade` -> `-0.5192`
- `d6fc6786d9e43b7b9fa9335e` -> `0.3293`
- `ecfcc4786386390ee06a3fae` -> `-0.4806`

Interpretation:

- with the current `delta_safe = 8.0 bps`, none pass
- to let the **best** economics candidate pass, `delta_safe` would need to fall from `8.0` to `4.4551 bps`
- most of the family is so weak that even `delta_safe = 0` would not save them

Calibration decision:

- lowering `delta_safe` enough to save this family would be a **major doctrine change**, not a light calibration tweak

---

## Family 2 - No-Excess

### Live Measurements

Per-candidate `abs(z)` reconstructed from the live raw windows:

| Candidate | TF | expected_edge_bps | abs(z) | gap to `z_marginal=1.0` | native_margin_bps |
|---|---:|---:|---:|---:|---:|
| `03f5da39d5f6f949c45e5944` | 15m | 7.4766 | 0.5477 | 0.4523 | -2.6384 |
| `374fcb39867dc43051bc101b` | 5m | 5.8404 | 0.5477 | 0.4523 | -4.2746 |
| `46de87ec9207bfcd4cea3f7f` | 10m | 10.0826 | 0.5477 | 0.4523 | -0.0324 |
| `c3b7429ac7d3fdebb7ea811d` | 1m | 1.5958 | 0.8367 | 0.1633 | -8.5192 |
| `f9aaf742b9b8db8ef00b382c` | 1m | 4.9009 | 0.5477 | 0.4523 | -5.2141 |

Family summary:

- average `expected_edge_bps = 5.9793`
- average `abs(z) = 0.6055`
- min `abs(z) = 0.5477`
- max `abs(z) = 0.8367`
- average `native_margin_bps = -4.1357`

### Critical Interpretation

This family is **not** a cluster of near-threshold misses around `0.95-0.99`.

Instead:

- `4/5` candidates sit around `abs(z) = 0.5477`
- `1/5` candidate sits at `abs(z) = 0.8367`

So the live cluster is materially below `z_marginal = 1.0`.

### Sensitivity - What Happens If `z_marginal` Moves?

Observed live result:

- current `z_marginal = 1.0` clears `0/5`

Counterfactual sensitivity:

- `z_marginal = 0.9` -> clears `0/5`
- `z_marginal = 0.8` -> clears `1/5`
- `z_marginal = 0.7` -> clears `1/5`
- `z_marginal = 0.6` -> clears `1/5`
- `z_marginal = 0.55` -> clears `1/5`
- `z_marginal = 0.54` -> clears `5/5`

Interpretation:

- there is **no smooth incremental unlock**
- the family sits on a cliff:
  - moderate threshold loosening changes almost nothing
  - a sharp drop to about `0.54` suddenly unlocks almost everything

Calibration decision:

- lowering `z_marginal` enough to change this run materially would be a **large semantic shift** in `engine_b`, not a minor calibration

### Additional Critical Nuance

Even if `z_marginal` were lowered enough to admit the `no_excess` family:

- `4/5` candidates would still remain native economics-negative
- the strongest case `46de87ec9207bfcd4cea3f7f` is still slightly below native economics:
  - `native_margin_bps = -0.0324`

So:

- a pure `z_marginal` tweak is not enough
- the family is blocked by **both** weak excess and weak economics

---

## What This Means for Calibration

### What We Should Not Do

Do **not**:

- drop `delta_safe` from `8.0` to `4.4` or below based on this 2-day run
- drop `z_marginal` from `1.0` to `0.54` based on this 2-day run

Those are not surgical calibrations.
They would rewrite the engine semantics.

### What We Can Legitimately Conclude

1. `engine_b` is not blocked only by proxy governance
2. the `economics` family is truly uneconomic under current native thresholds
3. the `no_excess` family is mostly far from the current excess threshold
4. `engine_b` on this run is not a near-miss engine waiting for a tiny threshold nudge

### Correct Next Step

The correct next step is:

1. get a **longer governed run**
2. keep the current canonical thresholds frozen
3. rerun the same audit on a larger sample
4. only then decide whether:
   - candidate quality is the real issue
   - economics realism is the real issue
   - or a modest threshold move is justified

---

## Final Verdict

For run `f08fe2de918c2e79`, the fine calibration answer is:

- `economics` family: **not saved** by admitting proxy edge
- `no_excess` family: **not close enough** to justify a light `z_marginal` tweak

So the correct conclusion is:

- **yes**, we should do this kind of fine audit before any calibration
- **no**, this run does not justify immediate threshold changes in `engine_b`

The proper decision is:

- freeze thresholds
- collect more governed evidence
- rerun the same calibration audit on a larger window

