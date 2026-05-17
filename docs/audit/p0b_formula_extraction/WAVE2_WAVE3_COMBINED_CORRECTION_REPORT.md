# Wave 2 + Wave 3 Combined Correction Report

## 1. Files modified
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/shadow_execution_simulator.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/artifact_ablation_study.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/state_decision_trace.py`
- `src/cockpit/state_system_flow.py`
- `src/execution_backbone/rate_limiter.py`
- `src/execution_backbone/spread_guard.py`
- `src/execution_backbone/gatekeeper/gatekeeper_support.py`
- `src/execution_backbone/execution_runtime_support.py`
- `src/cockpit/templates/partials/_replay_metrics.html`
- `src/cockpit/templates/partials/_economic_sterilization.html`
- `src/cockpit/templates/partials/_engine_why.html`
- `src/cockpit/templates/partials/_decision_trace.html`
- targeted tests in cockpit, replay runtime, and execution runtime

## 2. Fields added
- Replay semantics/completeness:
  - `replay_expected_cost_model_mean`
  - `expected_total_cost_mean`
  - `selected_execution_rate`
  - `non_execution_rate`
  - `fee_source_status`
  - `impact_source_status`
  - `cost_model_completeness_status`
  - `fill_ratio_source`
  - `fill_realism_status`
  - `realized_slippage_status`
  - `small_capital_exclusion_rate`
  - `small_capital_exclusion_status`
- Execution telemetry:
  - `telemetry_status`
- Cockpit adapter state:
  - explicit unavailable/partial statuses for cost and blocked sub-count display seams

## 3. Compatibility notes
- Existing serialized replay fields were preserved.
- `ce_net` was not renamed destructively.
- `expected_cost_mean` was not renamed destructively.
- New semantics were added through labels, caveats, aliases, and status fields.

## 4. CE semantic status
- `ce_net` is now operator-facing `Expected CE net`.
- CE caveat explicitly states expected CE over replay DTR records, not realized profitability.
- Decision-trace row display now reads from `ce_expected` semantics, not a misleading realized label.

## 5. Exec-rate denominator status
- Formula unchanged.
- Operator-facing label now remains explicit: `Exec rate (executed / total records)`.
- Additive `selected_execution_rate` exists as a distinct concept rather than an implicit reinterpretation.

## 6. Drawdown proxy status
- `drawdown_proxy` name preserved.
- Caveat preserved and reinforced: gross-return proxy, not net-equity max drawdown, not promotion-grade.

## 7. Replay false-green status
- Green replay economics are blocked when:
  - replay source is unavailable,
  - replay source is stale,
  - `total_records == 0`,
  - sample is insufficient,
  - or cost model completeness is partial/unknown.

## 8. Fee status
- Replay expected-cost fee coverage remains explicit `NOT_PROVEN`.
- Missing fee is no longer silently treated as measured zero in replay-facing semantics.

## 9. Impact status
- Replay expected-cost impact coverage remains explicit `NOT_PROVEN`.
- Missing impact is no longer silently treated as measured zero in replay-facing semantics.

## 10. Fill realism status
- Replay fill realism remains explicit `PARTIAL`.
- `fill_ratio_source` defaults to `UNKNOWN` until measured provenance is proven.

## 11. Realized slippage status
- Replay realized slippage remains explicit `NOT_PROVEN`.
- No standalone zero-valued realized slippage is presented as measured.

## 12. Fail-open hardening status
- Invalid spread telemetry no longer silently passes on governed shadow/live rails.
- Missing or invalid critical rate-limit telemetry no longer silently passes on governed shadow/live rails.
- Reason codes:
  - `SPREAD_INVALID_NO_SUBMIT`
  - `RATE_LIMIT_TELEMETRY_MISSING_NO_SUBMIT`

## 13. Venue constraints status
- Existing fail-closed venue constraint normalization was preserved.
- No venue-constraint producer formula was widened or weakened.

## 14. Small capital status
- `small_capital_exclusion_rate` was added as an additive placeholder seam.
- Current source remains `NOT_PROVEN`; no measured zero is claimed.

## 15. Cockpit zero-default hardening status
- Economic sterilization blocked sub-counts now surface as unavailable when no source exists.
- Engine-why expected/realized execution-cost fields now surface `n/a` plus status when no source exists.
- Replay card now calls out partial cost completeness explicitly.

## 16. Side/halal status
- PASS.
- No side mutation.
- No short path.
- No leverage path.
- No fake-flat order path.

## 17. Tests run
- Focused syntax validation over all modified source and test files: PASS
- Focused logic slice:
  - cockpit replay/economic/engine-why/decision-trace/system-flow tests
  - replay executor / shadow simulator / ablation tests
  - execution runtime tests
  - PASS
- Full requested broad command rerun:
  - `tests/test_local_replay_runtime`
  - `tests/test_backtest_artifact_import`
  - `tests/test_execution_backbone`
  - `tests/test_meta_minimal`
  - `tests/cockpit`
  - patch-related logic passed; nonzero exit remained due environment/build permission failures and unrelated pre-existing tests

## 18. Remaining gaps
- true executed-only net return
- true net-equity max drawdown
- empirical `p_fill_proxy` calibration
- `fill_ratio` measured-vs-synthetic proof
- realized-slippage standalone metric or folded-cost doctrine
- impact calibration doctrine
- replay-vs-live expected/realized cost parity mapping
- full small-capital viability report
