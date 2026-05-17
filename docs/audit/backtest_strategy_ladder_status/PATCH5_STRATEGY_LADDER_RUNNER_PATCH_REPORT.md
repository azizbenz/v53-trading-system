# V5.3 Patch 5 Strategy Ladder Runner Patch Report

Date: `2026-05-03`

## Scope

This patch implements the canonical Backtest Strategy Ladder runner and wires it into existing governed rails.

It does not rewrite engines, scoring, risk, or execution formulas.

## What changed

- Added `scripts/run_backtest_strategy_ladder.py` as the canonical ladder entrypoint.
- Added dedicated ladder request/result models with explicit per-stage statuses.
- Added a governed feature/gold-store seam with JSONL/CSV support and optional Parquet support when already installed.
- Added canonical fast candidate discovery with deterministic candidate IDs and explicit `COMPAT_FEATURE_DISCOVERY` labeling.
- Added canonical candidate export:
  - `fast_candidates/candidate_events.jsonl`
  - `fast_candidates/candidate_summary.json`
- Added deterministic raw-window extraction with explicit missing-book, missing-trades, missing-OHLCV, and limited-depth handling.
- Added candidate-window detailed replay on top of the existing execution-realism rail.
- Wired measured `capital_profiles/{bucket}.json` generation into the Strategy Ladder runner for `400 / 500 / 1500 / 4000`.
- Wired the existing promotion and sample-size artifact rails from detailed replay output:
  - `engine_promotion/*`
  - `pair_promotion/*`
  - `strategy_promotion/*`
  - `sample_size_survival/*`
- Added Strategy Ladder reports and cockpit visibility.

## Doctrine preserved

- `expected_ce_net` remains expected-only.
- `drawdown_proxy` remains diagnostic-only.
- Missing cost, fill, depth, parity, or sample-size proof does not become green readiness.
- `COMPAT_FEATURE_DISCOVERY` is accepted for v1, but it is explicitly not live-engine parity.
- Engine C and Engine D remain `PARTIAL_BY_DESIGN` where shared physics would otherwise be over-claimed.

## What did not change

- No engine logic rewrite.
- No strategy logic rewrite.
- No side logic change.
- No shorting.
- No leverage.
- No fake measured candidates, fills, returns, drawdowns, or `allowed_pairs`.
- No duplicate promotion-artifact rail family.

## Validation

- Syntax validation on new/changed ladder files: `passed`
- Targeted ladder/cockpit band:
  - `tests/test_local_replay_runtime/test_strategy_ladder_runner.py`
  - `tests/cockpit/test_cockpit_server_routes.py`
  - result: `18 passed`
- Ladder + replay-export compatibility band:
  - `tests/test_local_replay_runtime/test_strategy_ladder_runner.py`
  - `tests/test_local_replay_runtime/test_local_replay_export_launcher.py`
  - `tests/test_local_replay_runtime/test_replay_executor.py`
  - `tests/test_local_replay_runtime/test_promotion_artifact_builder.py`
  - `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
  - `tests/cockpit/test_cockpit_server_routes.py`
  - result: `72 passed`

Requested broad regression band:

- The ladder-specific tests passed inside the requested broad band.
- The band remained red because of unrelated failures/errors in:
  - `tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py`
  - `tests/test_local_replay_runtime/test_regime_detector_shadow_audit_diagnosis.py`
  - `tests/test_execution_backbone/test_build9_core_smoke_script.py`
  - `tests/test_execution_backbone/test_gatekeeper.py`
  - `tests/test_execution_backbone/test_reconciliation_scheduler.py`
  - `tests/test_execution_backbone/test_venue_constraints_provider.py`
  - `tests/test_risk_backbone/test_circuit_breaker.py`
  - `tests/test_risk_backbone/test_daily_pnl_breaker.py`
  - `tests/test_risk_backbone/test_daily_pnl_breaker_entry_gate.py`
  - `tests/test_risk_backbone/test_risk_runtime.py`
  - `tests/test_risk_backbone/test_risk_runtime_drawdown_calibration.py`
  - `tests/test_scoring_backbone/test_fee_aware_edge_gate.py`
- The broad band also ended with a Windows temp-dir cleanup failure:
  - `PermissionError: [WinError 5]` under `.test_tmp\pytest_strategy_ladder_broad_final`

The patch-local logic status is therefore based on the targeted and compatibility passes above, with the broad-suite failures separated as unrelated repo-wide debt plus environment cleanup noise.

## Current correct reading

- The canonical Strategy Ladder runner now exists.
- Candidate export, raw-window extraction, and detailed replay are implemented and tested.
- Capital profiles can now be generated from detailed replay output rather than remaining contract-only.
- Existing engine/pair/strategy/sample-size rails can now be fed by the canonical runner.

What is still not proven:

- live-engine parity from raw-history recomputation
- audited historical measured bucket artifacts
- audited historical Engine C/D promotion evidence
- telemetry-backed fill realism and replay/live cost parity

## Outcome

Patch 5 closes the architectural runner gap.

It does not close the evidence gaps that still require governed historical runs, depth quality, and later shadow/telemetry confirmation.
