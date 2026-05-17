# Build-4 Risk Backbone Evidence

Date: `2026-05-01`

## Scope

Primary source rails:

- `src/risk_backbone/risk_runtime.py`
- `src/risk_backbone/risk_runtime_runtime.py`
- `src/risk_backbone/risk_runtime_models.py`
- `src/risk_backbone/risk_runtime_explainability.py`
- `src/risk_backbone/risk_runtime_evaluation_support.py`
- `src/risk_backbone/btc_factor_guard/*`
- `src/risk_backbone/exposure_budgeter/*`
- `src/risk_backbone/loss_budgeter/*`
- `src/risk_backbone/correlation_cluster_guard/*`
- `src/risk_backbone/emergency_kill_switch/*`

## Proved Capabilities

### Risk candidate model exists

Evidence:

- `risk_runtime_models.py`

### Risk gates exist

Evidence:

- `risk_runtime_runtime.py`
- `risk_runtime_evaluation_support.py`

### BTC factor guard exists

Evidence:

- `btc_factor_guard/projected_beta_checker.py`
- `btc_factor_guard/portfolio_beta_calculator.py`
- `btc_factor_guard/beta_cap_guard.py`

### Beta caps exist

Status: `PROVEN`

### Exposure caps exist

Evidence:

- `exposure_budgeter/projected_exposure_checker.py`
- `exposure_budgeter/position_cap_guard.py`
- `exposure_budgeter/gross_cap_guard.py`

### Daily breaker / circuit breaker exist

Evidence:

- `loss_budgeter/daily_pnl_breaker.py`
- `emergency_kill_switch/circuit_breaker.py`
- `daily_pnl_breaker_entry_gate.py`

### Portfolio beta calculator exists

Status: `PROVEN`

### Risk explainability exists

Evidence:

- `risk_runtime_explainability.py`

### Kill switch / halt behavior exists

Evidence:

- `emergency_kill_switch/circuit_breaker.py`

## Semantic Safety Checks

### Risk does not create side

Status: `PROVEN`

Reason:

- the risk rail audits and gates candidate state; it does not synthesize directional trade side

### Missing risk fields are explicit, not zero

Status: `PROVEN`

Evidence:

- `risk_runtime_models.py`
- `risk_runtime_explainability.py`

Observed statuses:

- `UNKNOWN`
- `NOT_PROVEN`
- `PARTIAL`
- `RISK_INPUTS_UNKNOWN`
- `RISK_INPUTS_PARTIAL`

### Cost completeness is visible

Status: `PROVEN`

Observed fields:

- `cost_model_completeness_status`
- `fee_source_status`
- `impact_source_status`
- `fill_realism_status`
- `realized_slippage_status`

### Small-capital status is visible

Status: `PARTIAL`

Reason:

- explicit small-capital readiness states are surfaced downstream
- measured viability is still blocked by backtest evidence

### Drawdown proxy is not promotion-grade

Status: `PROVEN`

Reason:

- the current doctrine keeps true drawdown separate and explicit

### True drawdown status is explicit

Status: `PROVEN`

Reason:

- downstream readiness rails explicitly treat true drawdown as `NOT_PROVEN` when absent

### Covariance status is explicit

Status: `PROVEN`

Reason:

- baseline caps are separated from richer covariance control in operator-facing readiness logic

## Test Evidence

Relevant suites found:

- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_risk_backbone/test_risk_integration.py`
- `tests/test_risk_backbone/test_btc_factor_guard.py`
- `tests/test_risk_backbone/test_exposure_budgeter.py`
- `tests/test_risk_backbone/test_loss_budgeter.py`
- `tests/test_risk_backbone/test_daily_pnl_breaker.py`
- `tests/test_risk_backbone/test_circuit_breaker.py`
- `tests/test_risk_backbone/test_correlation_cluster_guard.py`

Executed in the combined Build-2..5 band:

- `912 passed`

## Remaining Gaps

- true executed-only profitability and true drawdown rails are still external/open
- small-capital readiness remains blocked by capital-ladder evidence
- baseline caps are not a full covariance model
- measured fee/impact/fill realism still depend on Build-3/Wave-3 closure

## Verdict

Build-4 verdict: `PARTIAL`

Reason:

- risk semantics and fail-close posture are implemented and tested
- promotion-grade economics, capital readiness, and richer portfolio risk proof remain incomplete
