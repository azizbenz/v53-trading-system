# V5.3 IA Lab / Backtest White Book

## 1. Purpose

This document is the operator white book for:

- launching a Strategy Ladder ML training run from **IA Lab**
- launching a **backtest** with or without ML
- understanding when a feature set is scientifically allowed
- diagnosing why a run was fast, blocked, or apparently "lost" its selected features

This document is grounded in the current codebase and in the audited run:

- `strategy_ladder_ml_lab_handoff-1779581789540`
- run root: `K:\v5.3 backtest\output2\ml_handoffstrategy\runs\strategy_ladder_ml_lab_handoff-1779581789540`

## 2. Core Doctrine

V5.3 keeps these invariants:

- spot-only, long-only, sharia-safe
- engines A/B/C/D remain native and canonical
- cockpit feature selection does **not** modify engine A/B/C/D logic directly
- feature selection only affects the **ML training / frozen artifact rail**
- proxy discovery is not backtest truth
- non-legacy ML features require replay-grounded B2 evidence

Practical rule:

- **legacy 3 features** can train from `kline_root` only
- **non-legacy / microstructure / F16 features** require `b2_run_root` or a replay-grounded label store

## 3. Case Study: What Happened on Run `1779581789540`

### Observed facts

- run duration was about `8.93s`, not a crash
- status finished `READY`
- the run used only:
  - `close_return`
  - `high_low_range`
  - `volume`
- the run did **not** use the full selected feature universe

### Proof artifacts

- cockpit job request:
  - `build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job_request.json`
- cockpit job status:
  - `build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job_status.json`
- persisted lab form state:
  - `build/cockpit/backtest_jobs/_last_lab_ml_handoff_form_state.json`
- handoff report:
  - `strategy_ladder_ml_lab_handoff_report.json`
- model bundle summary:
  - `strategy_ladder_expected_edge_ml_model_bundle.summary.json`

### Why it was fast

The run was:

- `gold_store_kline_features`
- `EXPECTED_EDGE_PROXY_DISCOVERY_ONLY`
- no `b2_run_root`
- no replay-grounded label store
- effectively a 4-timeframe lightweight LightGBM legacy training slice

### What was wrong

The operator intent was "all features selected", but the effective submitted feature set was already collapsed to the legacy 3 before the trainer ran.

### Patch now in place

- the picker now mirrors current checkbox state into hidden submit-proof CSV fields
- cockpit persists the effective selected feature set more explicitly in the job request
- IA Lab now blocks non-legacy launch without `b2_run_root`
- backtest ML-chain now blocks non-legacy auto-handoff without a Phase B2 replay root

## 4. Feature Families

### Legacy features

- `close_return`
- `high_low_range`
- `volume`

These are the only features allowed for pure kline-only training.

### Replay / microstructure / F16 family

Examples:

- `spread_bps`
- `slippage_bps`
- `book_depth_levels`
- `break_even_bps`
- `vpin`
- `cumulative_ofi`
- `queue_pressure`
- `kyle_lambda`
- `realized_vol_current`
- `realized_vol_at_break`
- `latency_penalty_bps`
- `micro_edge_exit_governor_observed`
- `micro_edge_entry_timing_observed`
- `history_score`
- `marginal_value_score`
- `reentry_lateness`
- `concentration_headroom`
- `anti_revenge_state__active`
- `anti_revenge_state__cooling`
- `anti_revenge_state__idle`

These require replay grounding.

## 5. Engines vs ML: Who Uses What

### Native engines

Engines A/B/C/D do **not** read the cockpit feature picker directly.

They keep their own native gates and equations:

- Engine A: structure / direction
- Engine B: excess / cost feasibility
- Engine C: breakout structure
- Engine D: history / re-entry governance

### ML overlay

The ML overlay consumes:

- the selected feature set used during training
- the frozen artifact feature list
- runtime feature hydration provided by the replay rail

So:

- engines produce some native context that may later be hoisted into ML features
- cockpit feature selection controls **ML training scope**, not engine decision policy

## 6. IA Lab: Correct Operator Flow

### A. Legacy kline-only training

Use this when you want a quick legacy training run.

Required:

- `kline_root`
- train window
- selected features limited to legacy 3

Not required:

- `b2_run_root`

Expected behavior:

- fast run
- proxy-discovery-only labels
- no replay-grounded microstructure features

### B. Full / extended / non-legacy training

Use this when you want replay-grounded ML.

Required:

- `kline_root`
- `b2_run_root`
- train window
- selected non-legacy features

Expected behavior:

- slower than legacy-only
- replay-backed features and labels available
- scientifically auditable for richer expected-edge training

### C. What is now blocked

If the selected IA Lab feature set contains any non-legacy feature and `b2_run_root` is empty:

- the launch is blocked before training
- selection remains persisted on the page
- operator sees a clear blocker instead of a misleading short run

## 7. Backtest: Correct Operator Flow

### A. Native backtest without ML

Use:

- `ML_MODE_OFF`
- no feature selection

Behavior:

- native backtest path only
- no ML handoff, no frozen artifact training

### B. Backtest with features selected from `/backtest`

Use:

- `ML_MODE_OFF`
- one or more features selected
- explicit `training_timeframe`

Behavior:

- cockpit launches ML handoff first
- then replays with the produced frozen artifact

If selected features are legacy-only:

- no B2 replay root is required

If selected features are non-legacy:

- a Phase B2 replay root must exist
- otherwise the chain is blocked before handoff

### C. Backtest with frozen ML artifact

Use:

- `ML_MODE_OVERLAY_FROZEN`
- authoritative handoff run root / artifact path / hash

Behavior:

- artifact feature list is authoritative
- picker is informational / read-only
- replay scores against the frozen artifact contract

## 8. Operator Audit Checklist

Before launch:

- confirm whether the selection is legacy-only or non-legacy
- if non-legacy, confirm `b2_run_root` exists
- confirm train dates
- confirm `training_timeframe`
- confirm the selected feature count shown on the page

After launch:

- inspect `job_request.json`
- inspect `job_status.json`
- inspect `_last_lab_ml_handoff_form_state.json` or `_last_form_state.json`
- inspect `strategy_ladder_ml_lab_handoff_report.json`
- inspect `strategy_ladder_backtest_ml_input.json`
- inspect `strategy_ladder_expected_edge_ml_model_bundle.summary.json`

What must match:

- selected feature count
- feature names
- timeframe scope
- train window
- artifact mode
- presence or absence of replay grounding

## 9. Common Failure / Confusion Modes

### "The run finished too quickly"

Usually means one of these:

- legacy-only training
- no replay grounding
- no Optuna-heavy slice
- low row count / early stopping

It does **not** automatically mean failure.

### "All features were selected but only 3 were used"

This is now audited via:

- hidden feature mirror on submit
- persisted form state
- job request feature payload

If it happens again, compare:

- page selection count
- persisted form state
- job request `feature_names_csv`

### "Why is non-legacy blocked?"

Because the trainer code forbids microstructure/replay features without replay-grounded source truth.

This is intentional fail-closed behavior.

## 10. File Map

Relevant UI / controller modules:

- `src/cockpit/templates/pages/lab.html`
- `src/cockpit/templates/pages/backtest.html`
- `src/cockpit/server.py`
- `src/cockpit/state.py`
- `src/cockpit/action_support.py`

Relevant training/runtime modules:

- `src/local_replay_runtime/strategy_ladder_expected_edge_training.py`
- `src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py`
- `src/local_replay_runtime/strategy_ladder_runner.py`

Relevant tests:

- `tests/cockpit/test_lab_feature_picker.py`
- `tests/cockpit/test_backtest_feature_picker_chain.py`

## 11. Current Operational Rule

If you want:

- **fast exploratory training**: use the legacy 3 with `kline_root`
- **real extended feature training**: supply `b2_run_root`
- **native backtest only**: keep ML off and leave feature selection empty
- **ML-assisted backtest from `/backtest`**: choose features, set timeframe, let cockpit handoff first, then replay

This is the safe mental model:

- **Legacy 3 = kline-only allowed**
- **Anything beyond legacy 3 = replay grounding required**
