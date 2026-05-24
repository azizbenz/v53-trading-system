# GPT 5.5 Continuation Handoff

Date: 2026-05-24
Repository: `E:\claude  v5.3\v53_trading_system`
Audience: next GPT 5.5 conversation continuing ML Lab / Backtest / B2 governance work
Status: operator handoff, code-grounded, audit-first

## 1. Mandatory startup protocol

The next model must begin by checking MemPalace and then grounding itself in the current codebase.

Required opening pattern:

1. `MemPalace check: performed`
2. `MemPalace project memory: found for wing <wing>` or `not found`
3. `Next source of truth: current codebase`
4. Explicit module brief:
   - current module
   - global invariants
   - connected modules / interfaces
   - forbidden defaults
   - post-generation verification checklist

Important facts for this repository:

- MemPalace server is enabled.
- Project memory for this repo was **not found** in the latest checks.
- Do **not** claim project memory exists unless it is explicitly found.
- If memory is still absent, say that the project must be initialized and mined first.
- If MemPalace and the current code disagree, trust the current code and use memory only as historical context.

## 2. Global V5.3 invariants

These must remain true unless the user explicitly orders a doctrinal change:

- Do not change thresholds A/B/C/D.
- Do not lower `delta_safe`, `z_marginal`, `min_direction`, `marginal`, `favorable`.
- Do not rewrite engines A/B/C/D.
- Do not promote proxy to truth.
- Do not remove `EXPECTED_EDGE_PROXY_BLOCKED`.
- Do not force `selected_count > 0`.
- Do not create fake executed trades.
- Do not bypass `spot-only`, `long-only`, `sharia`.
- Do not create a second runtime.
- Keep audit outputs machine-readable and operator-readable.

## 3. Modules that matter for this slice

### Cockpit

- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py>)
- [state.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/state.py>)
- [action_support.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/action_support.py>)
- [runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/runtime_support.py>)
- [backtest.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/backtest.html>)
- [lab.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/lab.html>)

### ML / replay runtime

- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py>)
- [strategy_ladder_b2_label_store_builder.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py>)
- [strategy_ladder_runner.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_runner.py>)

### Tests already relevant

- [test_lab_feature_picker.py](</E:/claude  v5.3/v53_trading_system/tests/cockpit/test_lab_feature_picker.py>)
- [test_backtest_feature_picker_chain.py](</E:/claude  v5.3/v53_trading_system/tests/cockpit/test_backtest_feature_picker_chain.py>)
- [test_lab_multipair_form_state.py](</E:/claude  v5.3/v53_trading_system/tests/cockpit/test_lab_multipair_form_state.py>)
- [test_backtest_multipair_form_state.py](</E:/claude  v5.3/v53_trading_system/tests/cockpit/test_backtest_multipair_form_state.py>)
- [test_strategy_ladder_runner.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_strategy_ladder_runner.py>)
- [test_e2e_multi_pair_lab_to_backtest_smoke.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_e2e_multi_pair_lab_to_backtest_smoke.py>)

## 4. Current implemented state

### 4.1 IA Lab and Backtest feature picker

The picker is already implemented on both pages:

- `/lab` has the governed feature picker.
- `/backtest` also has the governed feature picker.
- `/backtest` has explicit `training_timeframe` choices: `1m`, `5m`, `10m`, `15m`.

Code proof:

- [backtest.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/backtest.html:403>)
- [lab.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/lab.html:219>)

### 4.2 Submit-proof UI mirror

The browser-side deselection/reset issue was addressed with a hidden CSV mirror:

- `selected_features_csv` is mirrored from the checked boxes on change and on submit.
- The backend normalization prefers that CSV mirror if the checkbox payload is missing.

Code proof:

- [lab.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/lab.html:1259>)
- [backtest.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/backtest.html:3512>)
- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py:227>)

### 4.3 Non-legacy features are fail-closed without B2 grounding

Current rule in the cockpit:

- legacy-only selection can run without B2 root
- non-legacy selection is blocked if no `b2_run_root` is available

This is deliberate and aligned with the current implementation.

Code proof:

- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py:1925>)
- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py:2553>)

### 4.4 Backtest auto-chain behavior

If the user selects features from `/backtest`:

- no selected features => native backtest remains unchanged
- selected features + no frozen artifact => cockpit launches ML handoff first, then replay
- frozen artifact present => artifact remains authoritative

This is persisted in `BacktestMlChainState`.

Code proof:

- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py:2531>)
- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py:2609>)
- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py:2673>)

### 4.5 Candidate feature table and wiring audit

The cockpit already exposes:

- candidate feature table
- dynamic feature columns
- candidate drilldown
- `Feature / Engine / ML Wiring Audit`
- machine-readable report written into run reports

Code proof:

- [runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/runtime_support.py:2434>)
- [runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/runtime_support.py:2467>)
- [backtest.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/backtest.html:2308>)
- [backtest.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/backtest.html:2511>)

## 5. Critical doctrinal nuance: A2-first expectation vs current code

This is the most important conceptual point for the next conversation.

### 5.1 What the user expects doctrinally

The user expects:

- ML training should fundamentally come from raw historical data associated with A2.
- Replay/B2 should not automatically replace the canonical training corpus unless explicitly justified.

### 5.2 What the code currently does

The code currently has **two training rails** in [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py>):

1. Legacy / kline-only rail
   - used when no replay label store is provided
   - uses kline-derived rows
   - limited to the legacy 3 features
   - marked as `EXPECTED_EDGE_PROXY_DISCOVERY_ONLY`
   - feature source is `gold_store_kline_features`

2. Replay-grounded / B2 rail
   - used when `b2_run_root` or `label_store_dataset_path` is present
   - reads row values from the B2 label store
   - reads features through `row.feature_values.get(name)`
   - uses `executed_only_net_return`, else fallback `expected_ce_net`

Code proof:

- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py:444>)
- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py:561>)
- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py:562>)
- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py:617>)
- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py:625>)
- [strategy_ladder_expected_edge_training.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_expected_edge_training.py:664>)

### 5.3 Correct statement for GPT 5.5

Do **not** say:

- `ML inherently needs B2`
- `Replay is the canonical source of ML training by doctrine`

Say instead:

- `In the current implementation, non-legacy features are only materialized for training through the B2 replay-grounded label-store rail.`
- `A2-first training for the full feature set is not yet implemented as a canonical factory in the current code.`

## 6. Audited real run that exposed the confusion

Run path:

- [strategy_ladder_ml_lab_handoff-1779581789540](</K:/v5.3 backtest/output2/ml_handoffstrategy/runs/strategy_ladder_ml_lab_handoff-1779581789540>)

What was observed:

- The run did **not** crash.
- It completed in about `8.93s`.
- It ran with only the legacy 3 features:
  - `close_return`
  - `high_low_range`
  - `volume`
- It did **not** carry the full feature selection at execution time.

Artifacts proving that:

- [job_request.json](</E:/claude  v5.3/v53_trading_system/build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job_request.json>)
- [job_status.json](</E:/claude  v5.3/v53_trading_system/build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job_status.json>)
- [job.json](</E:/claude  v5.3/v53_trading_system/build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/job.json>)
- [stdout.log](</E:/claude  v5.3/v53_trading_system/build/cockpit/backtest_jobs/strategy_ladder_ml_lab_handoff-1779581789540/stdout.log>)
- [strategy_ladder_ml_lab_handoff_report.json](</K:/v5.3 backtest/output2/ml_handoffstrategy/runs/strategy_ladder_ml_lab_handoff-1779581789540/strategy_ladder_ml_lab_handoff_report.json>)
- [strategy_ladder_expected_edge_ml_model_bundle.summary.json](</K:/v5.3 backtest/output2/ml_handoffstrategy/runs/strategy_ladder_ml_lab_handoff-1779581789540/strategy_ladder_expected_edge_ml_model_bundle.summary.json>)

Important reading of that run:

- it was not a heavy replay-grounded F16 run
- it was effectively a kline-only / legacy-3 run
- the short duration is therefore coherent

## 7. What was already patched after that audit

Already fixed:

1. Lab feature picker submit-proof mirror
2. Backtest feature picker submit-proof mirror
3. Backend preference for `selected_features_csv`
4. Hard block when non-legacy features are requested without B2 grounding
5. Richer operator/job artifacts recording feature selection intent
6. Dashboard/state hints for replay-grounding readiness

Code proof:

- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py>)
- [action_support.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/action_support.py>)
- [state.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/state.py>)
- [lab.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/lab.html>)
- [backtest.html](</E:/claude  v5.3/v53_trading_system/src/cockpit/templates/pages/backtest.html>)

## 8. White books already available

English:

- [2026-05-24_IA_LAB_ML_TRAINING_AND_BACKTEST_WHITE_BOOK.md](</E:/claude  v5.3/v53_trading_system/docs/audit/2026-05-24_IA_LAB_ML_TRAINING_AND_BACKTEST_WHITE_BOOK.md>)

French:

- [2026-05-24_IA_LAB_ML_TRAINING_AND_BACKTEST_WHITE_BOOK_FR.md](</E:/claude  v5.3/v53_trading_system/docs/audit/2026-05-24_IA_LAB_ML_TRAINING_AND_BACKTEST_WHITE_BOOK_FR.md>)

The next model should read them, but still verify every claim against the code before changing anything.

## 9. Exact tests already run and known green slices

These were green after the latest cockpit/UI governance patch:

```powershell
python -m pytest tests/cockpit/test_lab_feature_picker.py tests/cockpit/test_backtest_feature_picker_chain.py -q --tb=short --basetemp=tmp_pytest_lab_backtest_picker_fix2
python -m pytest tests/cockpit/test_lab_multipair_form_state.py tests/cockpit/test_backtest_multipair_form_state.py -q --tb=short --basetemp=tmp_pytest_form_state_picker_fix
```

Status:

- `20 passed`
- `15 passed`

Also validated earlier in this workstream:

```powershell
python -m pytest tests/test_local_replay_runtime/test_strategy_ladder_runner.py -q --tb=short
python -m pytest tests/test_local_replay_runtime/test_e2e_multi_pair_lab_to_backtest_smoke.py -q --tb=short
```

Status:

- `51 passed`
- `2 passed`

If the next model modifies cockpit, runner, or expected-edge training, it should rerun the impacted shards rather than claiming broad green status without proof.

## 10. Recommended verification procedure for GPT 5.5

### 10.1 First pass: read-only audit

Before patching:

1. verify MemPalace status
2. inspect the current code in the modules listed above
3. inspect the latest relevant run artifacts if the task concerns a real run
4. state exactly whether the issue is:
   - doctrine mismatch
   - UI state bug
   - backend normalization bug
   - runtime feature wiring gap
   - report-only ambiguity

### 10.2 Second pass: patch scope discipline

Allowed patch scope by default:

- cockpit form-state
- cockpit templates
- audit/reporting fields
- ML handoff normalization
- replay-grounding governance
- tests and docs

Patch only with explicit justification if touching:

- `strategy_ladder_expected_edge_training.py`
- `strategy_ladder_b2_label_store_builder.py`
- `strategy_ladder_runner.py`

Do not casually alter those files just to make the cockpit appear simpler.

### 10.3 Third pass: proof

After any patch:

1. rerun the targeted tests
2. if runtime wiring changed, rerun the relevant local replay tests
3. if template/forms changed, rerun cockpit picker and form-state tests
4. if claims concern a real run, point to exact artifacts and dates

## 11. Open questions that remain unresolved

These are still live questions, not yet closed facts:

1. Should the architecture be realigned so that ML training is canonically A2-first for the full feature set?
2. Which non-legacy features can be computed directly from A2 without needing B2 replay?
3. Which features are inherently replay-dependent because they need execution realism, book-depth, or candidate-level post-engine context?
4. Should B2 remain a technical training rail, or become only a labeling/enrichment stage layered on top of A2?

The next model must not answer these by intuition. It must verify code and then separate:

- current implementation truth
- desired doctrine
- proposed migration path

## 12. Safe wording to use in future answers

Preferred wording:

- `In the current implementation...`
- `Code-grounded fact...`
- `Doctrinal expectation vs current code...`
- `This run proves X, but does not prove Y...`

Avoid wording like:

- `This is definitely how V5.3 doctrine works`
- `B2 is the true ML source by design`
- `The UI bug is fixed everywhere` unless a full proof exists

## 13. If GPT 5.5 needs a concrete next task

The safest next substantial task is:

1. perform an `A2-first vs current code` doctrinal audit
2. classify each expected-edge feature into:
   - computable directly from A2
   - computable from A2 plus deterministic transformations
   - requires B2 replay grounding
3. produce a migration plan that preserves:
   - no proxy->truth drift
   - no threshold changes
   - no engine rewrites
   - no fake profitability claims

## 14. Short operator summary

If the next model needs the shortest possible summary:

- The feature picker is implemented on IA Lab and Backtest.
- The submit-reset UI issue was patched with a CSV mirror and backend fallback.
- Non-legacy features are currently blocked without B2 replay grounding.
- The current training code has a legacy A2/kline rail and a replay-grounded B2 rail.
- The user believes training should be A2-first by doctrine.
- That doctrinal expectation is not yet fully aligned with the current code.
- The next step is likely an A2-first doctrinal audit, not a threshold patch.
