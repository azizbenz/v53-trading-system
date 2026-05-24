# V5.3 Backtest Decision Report Handoff

Date: 2026-05-24

## Scope

Module worked on:

- `src/local_replay_runtime/backtest_decision_report_builder.py`
- B2 runner wiring in `src/local_replay_runtime/strategy_ladder_runner.py`
- Cockpit Backtest summary/link surface in `src/cockpit/runtime_support.py`
- Cockpit Backtest template in `src/cockpit/templates/pages/backtest.html`

Global invariants preserved:

- No Engine A/B/C/D logic changed for this decision-report slice.
- No thresholds, gates, side, `SignalCandidate`, or live policy changed.
- No forced trade, selected count, executed count, or proxy promotion.
- ML remains overlay/reporting only.
- Profitability claim remains blocked when executions/proxy/cost/fill governance are not proven.

MemPalace:

- Checked: yes.
- Project memory found: yes.
- Wing used: `v53_trading_system`.
- Source of truth after memory check: current codebase.

## Implemented

Added reporting-only builder:

- `src/local_replay_runtime/backtest_decision_report_builder.py`

It reads existing B2 artifacts and writes under `run_dir/reports/`:

- `backtest_decision_capability_audit.json`
- `backtest_decision_report.json`
- `timeframe_ranking_report.json`
- `feature_ranking_report.json`
- `ml_vs_no_ml_delta_report.json`
- `engine_by_regime_report.json`
- `pair_ranking_report.json`
- `capital_bucket_ranking_report.json`
- `cost_fill_realism_report.json`
- `threshold_near_miss_report.json`
- `backtest_decision_report_final_verdict.json`

Integrated into B2 runner:

- `write_backtest_decision_reports(run_dir)` runs after candidate trade semantics audit and before replay performance profile finalization.
- Workflow artifact refs include the new report files.

Cockpit UI:

- Backtest page now surfaces a compact Decision Report card:
  - report status
  - top timeframe
  - top pair
  - top capital bucket
  - ML benefit status
  - profitability readiness
  - next blocker
  - report paths

Docs added:

- `docs/audit/BACKTEST_DECISION_CAPABILITY_AUDIT.md`
- `docs/audit/BACKTEST_DECISION_REPORT_FINAL_VERDICT.md`

Tests added:

- `tests/test_local_replay_runtime/test_backtest_decision_capability_audit.py`
- `tests/test_local_replay_runtime/test_backtest_decision_report_builder.py`
- `tests/cockpit/test_backtest_decision_report_links.py`

## Verified

Compile:

- `python -m compileall -q src tests`
- Passed with `PYTHONPYCACHEPREFIX=.test_tmp/compileall_pycache`.
- Raw compile without redirected pycache failed due existing locked `__pycache__` files, not due syntax errors.

New targeted tests:

- `pytest tests/test_local_replay_runtime/test_backtest_decision_capability_audit.py tests/test_local_replay_runtime/test_backtest_decision_report_builder.py tests/cockpit/test_backtest_decision_report_links.py -q --tb=short --basetemp=.test_tmp/pytest_basetemp_decision -p no:cacheprovider`
- Result: `8 passed`.

ML grounding regression tests requested by plan:

- `pytest tests/test_local_replay_runtime/test_feature_grounding_registry.py tests/test_local_replay_runtime/test_training_source_contract.py tests/test_local_replay_runtime/test_ml_overlay_authority_contract.py tests/test_local_replay_runtime/test_ml_label_leakage_guards.py -q --tb=short --basetemp=.test_tmp/pytest_basetemp_ml -p no:cacheprovider`
- Result: `18 passed`.

## Current Status

Decision-report capability status expected for current blocked B2 runs:

- `BACKTEST_DECISION_REPORT_PARTIAL`
- `PROFITABILITY_BACKTEST_READY=false`

Reason:

- The report surface exists, but current profitability truth remains blocked when:
  - `executed_count=0`
  - expected edge is proxy/ungoverned
  - fee/adverse-selection/cost-fill realism are partial or proxy-contaminated
  - no aligned ML-off vs ML-overlay baseline pair is supplied

The builder intentionally returns `insufficient_executions` instead of electing a fake best timeframe/pair/bucket when no measured executions exist.

## Git State Notes

The worktree was already dirty before this slice and still contains many modified/untracked files not owned by this decision-report patch.

Files owned by this slice:

- `src/local_replay_runtime/backtest_decision_report_builder.py`
- `src/local_replay_runtime/strategy_ladder_runner.py` decision-report import, refs, B2 hook
- `src/cockpit/runtime_support.py` decision-report summary fields and loader
- `src/cockpit/templates/pages/backtest.html` Decision Report card
- `docs/audit/BACKTEST_DECISION_CAPABILITY_AUDIT.md`
- `docs/audit/BACKTEST_DECISION_REPORT_FINAL_VERDICT.md`
- `docs/audit/2026-05-24_BACKTEST_DECISION_REPORT_HANDOFF.md`
- `tests/test_local_replay_runtime/test_backtest_decision_capability_audit.py`
- `tests/test_local_replay_runtime/test_backtest_decision_report_builder.py`
- `tests/cockpit/test_backtest_decision_report_links.py`

Do not blindly commit all modified files in the worktree without reviewing unrelated changes.

## Next Step

Run a real B2 after this patch to generate the new report artifacts on a live run directory, then inspect:

- `run_dir/reports/backtest_decision_report.json`
- `run_dir/reports/backtest_decision_capability_audit.json`
- `run_dir/reports/backtest_decision_report_final_verdict.json`

If `executed_count` remains 0 or proxy blockers remain, the correct verdict remains research-only.
