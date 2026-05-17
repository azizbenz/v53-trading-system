# P0-B Addendum 2 - Risk and Execution Gate Audit

## Risk gate audit

### Shared risk schema
`src/risk_backbone/risk_runtime_models.py::RiskCandidate` includes:
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`
- `spread_bps`
- `reference_spread_bps`
- `depth_ratio`
- `order_cancellation_rate`
- `taker_imbalance`
- `micro_vol_divergence`

### Shared risk consumers
`src/risk_backbone/risk_runtime_runtime.py`
- `_run_micro_friction_precheck_hook(...)`
- `_run_info_stress_precheck_hook(...)`
- `_run_regime_precheck_hook(...)`

`src/risk_backbone/risk_runtime_explainability.py`
- `_evaluate_candidate_physics(...)`
- derives `fragility_score`, `toxicity_score`, `execution_survivability_score`, `micro_friction_score`

### Actual engine population
Current A/B/C/D risk builders pass only:
- `pair`
- `engine_id`
- `size`
- `planned_loss`
- `pair_beta`

They do not pass shared micro-friction or info-stress inputs.

### Fail-open / fail-closed behavior

Micro-friction:
- `RiskCandidate` defaults:
  - `execution_fragility = 0.0`
  - `market_toxicity = 0.0`
  - `spread_regime_penalty = 0.0`
  - `participation_penalty = 0.0`
- `_evaluate_candidate_physics(...)` computes nominal scores from those defaults
- result: effective fail-open / neutral if builders omit the fields

Info-stress:
- `spread_bps`, `reference_spread_bps`, `depth_ratio`, `order_cancellation_rate`, `taker_imbalance`, `micro_vol_divergence` default to `None`
- `InfoStressMonitor` returns empty reasons when values are `None` or invalid
- result: effective fail-open / neutral if builders omit the fields

Regime precheck:
- `RiskRegimePrecheckInput` supports `regime_state`, `entries_blocked`, `entries_blocked_until_ts`, `reason_codes`
- current `_run_regime_precheck_hook(...)` does not populate those fields from engine runtime context
- result: regime precheck carriage is partial unless an external hook resolves state out-of-band

### Risk result
`PARTIAL_CARRIAGE_FAIL_OPEN_ON_MISSING_FIELDS`

## Execution gate audit

### Shared execution bridge
`src/execution_backbone/execution_routing_bridge.py`

Consumes:
- `spread_bps`
- `order_book_imbalance`
- `microprice_pressure`
- `aggressive_trade_imbalance`
- `short_window_volatility`
- `market_toxicity_score`
- `regime_transition_risk`
- `regime_stability_score`
- `expected_duration_bucket`
- maker/taker fees

### Fail-open / fail-closed behavior

Fail-closed:
- `stale_snapshot`
- `low_coverage`
- missing required routing fields
- NaN/inf routing fields
- unsupported execution side

Fail-open or degraded:
- volatility z-score unavailable -> reason code `vol_zscore_unavailable`, returns `0.0`

### Execution equations
`src/execution_backbone/order_decider/hybrid_router_equations.py`

Decisional effects:
- routing same-side pressure
- fill probability proxy
- adverse selection estimate
- taker slippage estimate
- maker EV
- taker EV
- latency staleness cost
- participation ratio cost

### Does execution create side?
No.

Proven path:
- `protocols/execution_opportunity_bridge.py` resolves side from the selected candidate direction
- `execution_routing_bridge._normalize_side(...)` only normalizes `buy/sell`
- `execution_runtime` reuses `intent.side` when building or converting opportunities

Execution can change order type or timeout.
It does not create a new trade side.

### Can candidate pass without microstructure?
Yes, upstream selection can still exist without shared scoring/risk carriage.
But downstream hybrid routing itself is materially guarded and fail-closed on stale or low-coverage routing snapshots.

### Execution result
`HEALTHY_DOWNSTREAM_NON_DIRECTIONAL_CONTEXT`

Execution is better wired than shared risk carriage.
