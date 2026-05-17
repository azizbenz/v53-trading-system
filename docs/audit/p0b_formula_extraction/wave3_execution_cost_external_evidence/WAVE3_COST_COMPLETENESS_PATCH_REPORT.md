# Wave 3 Cost Completeness Patch Report

## Files modified
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/shadow_execution_simulator.py`
- `src/execution_backbone/rate_limiter.py`
- `src/execution_backbone/spread_guard.py`
- `src/execution_backbone/gatekeeper/gatekeeper_support.py`
- `src/execution_backbone/execution_runtime_support.py`
- replay/cockpit templates and tests listed in the combined report

## Fields added
- Replay summary:
  - `replay_expected_cost_model_mean`
  - `expected_total_cost_mean`
  - `fee_source_status`
  - `impact_source_status`
  - `cost_model_completeness_status`
  - `fill_ratio_source`
  - `fill_realism_status`
  - `realized_slippage_status`
  - `small_capital_exclusion_rate`
  - `small_capital_exclusion_status`
  - `non_execution_rate`
- Parity diagnostics:
  - `fill_ratio_source`
  - `fill_realism_status`
  - `realized_slippage_status`
- Execution guard decisions:
  - `telemetry_status`

## Compatibility notes
- Existing replay `expected_cost_mean` was preserved.
- No all-in replay fee or impact number was invented.
- No existing execution cost meter formula was rewritten.
- Missing fee or impact is now explicit partial status, not measured zero.

## Guard hardening
- `SPREAD_INVALID_NO_SUBMIT`
- `RATE_LIMIT_TELEMETRY_MISSING_NO_SUBMIT`
- strict no-submit behavior for governed `shadow`, `micro_live`, and `live` execution modes when critical telemetry is missing or invalid

## Validation
- Focused execution/replay/cockpit tests covering these seams passed.
- Broad suite rerun showed remaining nonzero exit caused by build-root permission failures and pre-existing unrelated tests, not by Wave 3 patch regressions.
