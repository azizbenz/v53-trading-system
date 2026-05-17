# Wave 2 Semantic Safety Patch Report

## Files modified
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/artifact_ablation_study.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/state_decision_trace.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/templates/partials/_replay_metrics.html`
- `src/cockpit/templates/partials/_economic_sterilization.html`
- `src/cockpit/templates/partials/_engine_why.html`
- `src/cockpit/templates/partials/_decision_trace.html`

## Wave 2 changes
- Added operator-safe `Expected CE net` labeling and caveats.
- Preserved the existing `exec_rate` formula while exposing its denominator explicitly.
- Preserved `drawdown_proxy` and added explicit non-promotion caveats.
- Added replay display states and cost-completeness gating so incomplete replay economics cannot present as green.
- Added additive `selected_execution_rate` and `non_execution_rate` semantics without changing the existing replay formula rail.
- Added additive ablation aliases so existing `block_rate` is explicitly treated as a non-execution proxy when surfaced.

## Tests added or updated
- Replay snapshot semantic-label and green-gating tests.
- Economic sterilization partial-cost-model tests.
- Engine-why unavailable/partial cost-display tests.
- Decision-trace expected-CE test.
- System-flow partial-economics test.
- Replay summary completeness-status tests.
- Ablation non-execution proxy alias test.

## Outcome
- Wave 2 replay profitability semantics are now operator-safe on the patched replay/cockpit rail.
- No replay profitability producer formula was rewritten.
