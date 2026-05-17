# SB-001 / SB-002 True Economics Patch Report

Date: `2026-05-01`

## Scope

This patch closes the additive replay/shadow economics rails for:

- `SB-001` true executed-only net return
- `SB-002` true net-equity max drawdown

Non-negotiable doctrine preserved:

- `expected_ce_net` remains expected-only.
- `drawdown_proxy` remains diagnostic-only.
- Missing realized cost is not treated as zero.
- Missing capital base is not treated as zero.
- Missing executed/reduced records keep promotion economics non-green.
- No engine logic, side logic, leverage, or shorting behavior was changed.

## Code surfaces updated

- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/templates/partials/_replay_metrics.html`
- `src/cockpit/templates/partials/_economic_sterilization.html`
- `src/cockpit/templates/partials/_system_flow.html`

## Implemented rails

### Executed-only net return

Implemented formula:

```text
executed_only_net_return =
  sum(gross_return_i - realized_cost_i)
  for execution_state in {EXECUTED, REDUCED}
```

Implemented statuses:

- `EXECUTED_NET_RETURN_PROVEN`
- `EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS`
- `EXECUTED_NET_RETURN_MISSING_REALIZED_COST`
- `EXECUTED_NET_RETURN_NOT_PROVEN`

Explicit metadata now carried:

- `executed_count`
- `reduced_count`
- `no_fill_count`
- `hard_blocked_count`
- `rejected_count`
- `selected_count`
- `total_records`
- `missing_realized_cost_count`

### True net-equity max drawdown

Implemented formula:

```text
equity_t = initial_capital + cumulative_executed_net_pnl_t
running_peak_t = max(equity_0 ... equity_t)
drawdown_t = (running_peak_t - equity_t) / running_peak_t
max_drawdown = max(drawdown_t)
```

Implemented statuses:

- `TRUE_NET_EQUITY_DRAWDOWN_PROVEN`
- `TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL`
- `TRUE_NET_EQUITY_DRAWDOWN_MISSING_EXECUTED_PNL`
- `TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS`
- `TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN`

Explicit metadata now carried:

- `initial_capital`
- `true_net_equity_curve`
- `true_net_equity_max_drawdown`
- `true_net_equity_drawdown_status`

## Cockpit doctrine hardening

Operator-facing replay/cockpit surfaces now show:

- `EXPECTED_ONLY`
- `NOT_REALIZED_PNL`
- `DRAWDOWN_PROXY_ONLY`
- `EXECUTED_RETURN_NOT_PROVEN`
- `TRUE_DRAWDOWN_NOT_PROVEN`
- `PROMOTION_ECONOMICS_NOT_READY`

The cockpit now stays non-green when:

- executed-only return is not proven
- true drawdown is not proven
- record count is zero
- sample size is too small
- cost completeness remains partial

## Per-engine status carriage

Per-engine replay aggregates now carry:

- `engine_executed_only_net_return`
- `engine_executed_only_net_return_status`
- `engine_true_net_equity_max_drawdown`
- `engine_true_net_equity_drawdown_status`
- `engine_executed_count`
- `engine_reduced_count`
- `engine_no_fill_count`

Missing per-engine proof remains explicit rather than invented.

## Validation

Focused logic slice:

- `python -m pytest -q tests/test_local_replay_runtime/test_replay_executor.py tests/cockpit/test_state_replay_metrics.py tests/cockpit/test_state_economic_sterilization.py tests/cockpit/test_state_system_flow.py tests/cockpit/test_state_engine_why.py tests/cockpit/test_cockpit_server_routes.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_sb001_sb002_targeted`
- Result: `37 passed`

Requested replay/cockpit band:

- `python -m pytest -q tests/test_local_replay_runtime tests/test_backtest_artifact_import tests/cockpit --tb=short --disable-warnings --basetemp=.test_tmp\pytest_sb001_sb002_band1_escalated`
- Result: `362 passed`

Requested risk/scoring band:

- `python -m pytest -q tests/test_risk_backbone tests/test_scoring_backbone --tb=short --disable-warnings --basetemp=.test_tmp\pytest_sb001_sb002_band2_escalated`
- Result: `389 passed`

## Outcome

`SB-001` and `SB-002` are closed as implemented rails.

This does not close:

- replay fee provenance
- replay impact provenance
- fill-realism proof
- replay/live cost parity
- capital-bucket viability
- engine-specific promotion artifacts for C/D
