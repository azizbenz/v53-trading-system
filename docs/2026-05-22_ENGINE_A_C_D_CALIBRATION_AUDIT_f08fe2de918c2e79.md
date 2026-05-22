# 2026-05-22 Engine A/C/D Calibration Audit - f08fe2de918c2e79

## Scope

Run audited:
- `L:\output backtest\runs\strategy_ladder_workflow-f08fe2de918c2e79`

Question:
- perform the same fine-grained calibration-style test already done for `engine_b`
- but for `engine_a`, `engine_c`, and `engine_d`

Rule:
- do **not** treat proxy blockers as the only explanation
- do **not** recommend threshold changes when the live run is clearly blocked upstream

---

## Executive Verdict

- `engine_a`: calibration audit is meaningful, but it does **not** support an immediate threshold patch.
  - The dominant live issue is **long-only direction eligibility**, not a soft structure threshold.
  - Only **1/10** candidates is a true near-miss on `min_direction`.
- `engine_c`: calibration audit is **premature** on this run.
  - All `10/10` live candidates fail earlier at the builder layer with `NO_BREAKOUT_IN_LOOKBACK`.
  - This is not a near-threshold issue on `breakout_score_min`, `breakout_strength_min`, or `range_quality_min`.
- `engine_d`: calibration audit is **not meaningful yet** on this run.
  - The prerequisite source for history is missing:
    - `closed_episode_manifest.record_count = 0`
    - `source_status = REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE`
  - No serious threshold conclusion should be drawn for `history` or `reformation` until valid closed episodes exist.

---

## Engine A

### Canonical thresholds

Source:
- `src/engines/engine_a/structure_detector_a.py`

Thresholds:
- `favorable = 0.60`
- `marginal = 0.30`
- `min_direction = 0.20`

Important semantic point:
- `engine_a` uses `abs(direction_score)` for the native structure detector
- but the live pipeline remains long-only, so a strongly negative direction can still be rejected upstream as `non_long_direction`

### Live candidate population

Live source:
- `phase_b1_candidate_discovery/.../fast_candidates/candidate_events.jsonl`

Population:
- `10` engine_a candidates in B1
- `9` hard-rejected in B1 with `non_long_direction`
- `1` candidate reaches B2 and is blocked by `structure_unfavorable`

### Live reconstruction

Inputs rebuilt from:
- `phase_b1_candidate_discovery/.../raw_windows/BTCUSDT/<candidate_id>/window_manifest.json`
- `src/local_replay_runtime/strategy_ladder_engine_a_input_builder.py`
- `src/engines/engine_a/structure_detector_a.py`

Per-candidate results:

| candidate_id | tf | direction_score | abs(direction) | gap vs 0.20 | structure_score | gap vs 0.30 | verdict | live reason |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `6d5d3daef65f2b110fa08330` | `10m` | `-0.058048` | `0.058048` | `-0.141952` | `0.186563` | `-0.113437` | `unfavorable` | `non_long_direction` |
| `b69f0bdc0de4b829b5608837` | `15m` | `-0.075401` | `0.075401` | `-0.124599` | `0.306692` | `+0.006692` | `unfavorable` | `non_long_direction` |
| `bcd3a16173c9f3db86c789a8` | `1m` | `-0.015758` | `0.015758` | `-0.184242` | `0.325954` | `+0.025954` | `unfavorable` | `non_long_direction` |
| `983749c1cf72f78456aea38b` | `5m` | `-0.456727` | `0.456727` | `+0.256727` | `0.623113` | `+0.323113` | `favorable` | `non_long_direction` |
| `b0bfb59a14346067468e29ad` | `1m` | `-0.007134` | `0.007134` | `-0.192866` | `0.308847` | `+0.008847` | `unfavorable` | `non_long_direction` |
| `aa2a43bfb742ce30322415d2` | `1m` | `-0.133295` | `0.133295` | `-0.066705` | `0.367577` | `+0.067577` | `unfavorable` | `non_long_direction` |
| `4b352371c1668b87124e1123` | `10m` | `-0.261945` | `0.261945` | `+0.061945` | `0.397543` | `+0.097543` | `marginal` | `non_long_direction` |
| `e001b8bb6e9eb4bcba44ba08` | `15m` | `-0.344956` | `0.344956` | `+0.144956` | `0.381357` | `+0.081357` | `marginal` | `non_long_direction` |
| `e0f9230964ad600a55bf3d06` | `1m` | `+0.033528` | `0.033528` | `-0.166472` | `0.345315` | `+0.045315` | `unfavorable` | `structure_unfavorable` |
| `06e5e46ab94fd3bf0fc72681` | `5m` | `-0.195185` | `0.195185` | `-0.004815` | `0.379803` | `+0.079803` | `unfavorable` | `non_long_direction` |

### Interpretation

This run does **not** say:
- "engine_a threshold is slightly too strict on structure"

It says:
- many cases already satisfy or nearly satisfy `structure_score >= 0.30`
- but they still fail because they are:
  - weak on direction magnitude, or
  - strong enough but **negative**, therefore non-long

Important live facts:
- strong-but-negative candidates:
  - `983749c1cf72f78456aea38b`
  - `4b352371c1668b87124e1123`
  - `e001b8bb6e9eb4bcba44ba08`
- true near-miss on `min_direction`:
  - `06e5e46ab94fd3bf0fc72681`
  - gap only `-0.004815`

### Engine A conclusion

- `engine_a` is **not** primarily blocked by a soft structure threshold on this run
- the dominant live blocker is:
  - `long-only direction eligibility`
- a direct patch to `marginal` or `favorable` thresholds would attack the wrong problem
- a patch to `min_direction` also lacks support from this sample:
  - only `1/10` is a true near-miss

Decision:
- **no immediate calibration patch justified for engine_a**

---

## Engine C

### Canonical thresholds

Source:
- `src/engines/engine_c/engine_c_runner.py`

Thresholds:
- `breakout_score_min = 0.62`
- `breakout_strength_min = 0.55`
- `range_quality_min = 0.50`
- `fake_breakout_risk_max = 0.65`

### Live candidate population

Live source:
- `phase_b1_candidate_discovery/.../fast_candidates/candidate_events.jsonl`

Population:
- `10` engine_c candidates in B1
- `10/10` hard-rejected in B1 with `non_long_breakout`
- `0` candidates reach B2

### Live reconstruction

Inputs rebuilt from:
- `phase_b1_candidate_discovery/.../raw_windows/BTCUSDT/<candidate_id>/window_manifest.json`
- `src/local_replay_runtime/strategy_ladder_engine_c_input_builder.py`

Observed builder status on all `10/10` candidates:
- `builder_status = ENGINE_C_INPUT_BUILDER_NO_BREAKOUT`
- `breakout_detector_status = NO_BREAKOUT_IN_LOOKBACK`

Observed structural fields on all `10/10` candidates:
- `breakout_strength = 0.0`
- `range_quality = 0.0`
- `compression_quality = 0.0`
- `volume_confirmation = 0.0`
- `followthrough_room = 0.0`
- `extension_pct = 0.0`

Representative candidate ids:
- `9f62ced7d3826ee6117be4b0`
- `05f189da1f74fd865872376e`
- `783d1df8ff29dbb34b64a810`
- `ba1811d56e6a4f559a28d68d`
- `e308ee7203c49cbae535d037`
- `d667a72db0c91d73ff3f4d55`
- `055ba77cc063c723d23c9e8a`
- `a1eb933481320d6325e901b5`
- `25617bd09119f11871e7f436`
- `40ee8e1dca69fcf9671c3e7a`

### Interpretation

This run does **not** support a threshold conversation like:
- should `breakout_score_min` be `0.62` vs `0.58`?
- should `range_quality_min` be `0.50` vs `0.45`?

Why:
- the live candidates never reached those margins
- the builder sees **no breakout at all**

So the problem is upstream:
- breakout eligibility
- window geometry
- or live discovery quality

It is **not** a near-threshold calibration problem on this run.

### Engine C conclusion

- `engine_c` is **not calibration-ready** on this run
- threshold tuning would be premature and misleading

Decision:
- **no immediate calibration patch justified for engine_c**
- the right next question remains upstream breakout eligibility, not native threshold softness

---

## Engine D

### Canonical thresholds

Source:
- `src/engines/engine_d/engine_d_runner.py`

Thresholds:
- `_HISTORY_MIN = 0.55`
- `_REFORMATION_MIN = 0.58`

### Live candidate population

Live sources:
- `phase_b1_candidate_discovery/.../preselection_candidates.jsonl`
- `phase_b2_detailed_replay/.../reports/engine_no_trade_diagnosis.json`

Population:
- `10` engine_d candidates preselected
- `40` replay records in B2
- `40/40` blocked by `history_weak`

### Critical prerequisite state

Live source:
- `phase_b2_detailed_replay/.../closed_episode_manifest.json`

State:
- `record_count = 0`
- `status = CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES`
- `source_status = REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE`

Meaning:
- the first valid history source required by `engine_d` does not exist on this run
- therefore the `history` gate is failing on an empty upstream source, not on a rich population of valid prior episodes

### Interpretation

This run does **not** justify:
- lowering `_HISTORY_MIN`
- lowering `_REFORMATION_MIN`
- recalibrating `engine_d` conviction/economics thresholds

Why:
- there is no valid closed-episode population to calibrate against
- the live result is dominated by a prerequisite absence, not by a nuanced threshold edge

### Engine D conclusion

- `engine_d` is **not calibration-ready** on this run
- the right next move is to produce valid closed episodes from real `A/C` executions first

Decision:
- **no immediate calibration patch justified for engine_d**

---

## Final Decision

On run `f08fe2de918c2e79`:

- `engine_a`: calibration audit meaningful, but does **not** justify threshold changes
- `engine_c`: calibration audit premature
- `engine_d`: calibration audit not meaningful yet

So the correct conclusion is:

- `engine_b` was the only engine on this 2-day run where a true fine-grained threshold test was materially worth doing
- and even there, the result still did **not** justify immediate recalibration

For `A/C/D`, the blockers remain mostly:
- long-only direction eligibility (`engine_a`)
- upstream breakout absence (`engine_c`)
- missing closed-episode source (`engine_d`)

Therefore:
- `P0-B` still matters
- but the next productive work is **not** "lower thresholds everywhere"
- it is:
  - improve governed evidence and live sample size
  - obtain valid closed episodes
  - and only then revisit calibration on a materially larger run
