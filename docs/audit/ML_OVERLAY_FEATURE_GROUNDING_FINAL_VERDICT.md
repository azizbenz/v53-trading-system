# ML Overlay Feature Grounding Final Verdict

Date: 2026-05-24
Repository: `E:\claude  v5.3\v53_trading_system`
Status: governed doctrine/reporting patch completed

## Verdict

- `ML_OVERLAY_DOCTRINE_GOVERNED`
- `FEATURE_GROUNDING_REGISTRY_READY`
- `TRAINING_SOURCE_CONTRACT_READY`
- `ANTI_LEAKAGE_DATE_GUARD_READY`
- `ML_AUTHORITY_CONTRACT_READY`
- `LABEL_INPUT_LEAKAGE_GUARD_READY`
- `BACKTEST_PROFITABILITY_READY = false`

## What Changed

- Added `src/local_replay_runtime/feature_grounding_registry.py`.
- Added `src/local_replay_runtime/training_source_contract.py`.
- Added `src/local_replay_runtime/ml_overlay_authority_contract.py`.
- Added `src/local_replay_runtime/ml_label_leakage_guards.py`.
- Wired IA Lab handoff output to emit:
  - `reports/feature_grounding_contract_report.json`
  - `reports/training_source_contract_report.json`
  - `reports/ml_train_eval_overlap_report.json`
  - `reports/ml_overlay_authority_contract_report.json`
  - `reports/ml_feature_input_label_leakage_report.json`
  - `reports/feature_grounding_registry.json`
- Propagated those report refs into the handoff report and backtest ML input.
- Surfaced report refs/status in IA Lab and Backtest cockpit pages.
- Added focused tests for grounding, train/eval overlap, ML authority, label leakage,
  and handoff report propagation.

## Preserved Invariants

- No engine A/B/C/D rewrite.
- No `SignalCandidate` change.
- No threshold change.
- No `delta_safe`, `z_marginal`, `min_direction`, `marginal`, or `favorable` change.
- No `EXPECTED_EDGE_PROXY_BLOCKED` removal.
- No proxy promoted to backtest truth.
- No forced selected or executed counts.
- No fake executed trades.
- No second runtime.
- ML remains an overlay and cannot create candidates, change side, or bypass hard
  blockers.

## Verification

Passed:

```powershell
python -m compileall -q src tests
```

Run with `PYTHONPYCACHEPREFIX=.test_tmp\pycache_compile_ml_grounding` because the
default `__pycache__` tree contains locked `.pyc` files in this workspace.

Passed:

```powershell
pytest tests/test_local_replay_runtime/test_feature_grounding_registry.py tests/test_local_replay_runtime/test_training_source_contract.py tests/test_local_replay_runtime/test_ml_overlay_authority_contract.py tests/test_local_replay_runtime/test_ml_label_leakage_guards.py -q --tb=short
pytest tests/test_local_replay_runtime/test_strategy_ladder_ml_lab_handoff.py -q --tb=short
pytest tests/cockpit/test_lab_feature_picker.py tests/cockpit/test_backtest_feature_picker_chain.py -q --tb=short
```

Observed results:

- `18 passed`
- `6 passed`
- `20 passed`

## Residual Limits

This patch makes the doctrine explicit and auditable. It does not claim the
profitability backtest is ready. Cost realism, fill realism, expected-edge promotion,
and Shadow/Micro-live/Live gates still govern any production interpretation.
