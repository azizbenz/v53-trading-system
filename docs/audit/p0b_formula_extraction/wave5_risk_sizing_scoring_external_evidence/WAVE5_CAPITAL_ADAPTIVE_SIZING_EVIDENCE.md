# Wave 5 Capital-Adaptive Sizing Evidence

Role boundary:
- Evidence extraction only
- No new sizing model
- No code patch from this addendum

## 1. Live / shadow capital source evidence

Observed governed sizing rail:
- `src/portfolio_minimal/allocation_router/base_size_builder.py`
- `src/portfolio_minimal/allocation_router/vol_target_sizer.py`
- `src/portfolio_minimal/portfolio_orchestrator.py`

Proven source:
- current portfolio sizing consumes `available_capital`
- in the inspected orchestrator this comes from `config.size_profile.available_capital`

Not proven:
- governed live/shadow `free_quote_balance`
- governed exchange account-state injection into `available_capital`
- reserve-buffer subtraction before sizing
- explicit inclusion/exclusion doctrine for open spot inventory in the sizing capital base

Classifications:
- `CONFIG_CAPITAL_ONLY`
- `LIVE_BALANCE_ADAPTATION_NOT_PROVEN`
- `REQUIRES_RUNTIME_BALANCE_SOURCE`

## 2. Backtest capital source evidence

Proven:
- capital is scenario/config driven in the active `portfolio_minimal` rail
- `SizeProfile.available_capital` can be varied without code rewrite
- test support and portfolio-minimal tests already construct different capital values through config/profile inputs

Relevant evidence:
- `tests/test_portfolio_minimal/_portfolio_support.py`
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`
- `tests/test_portfolio_minimal/test_vol_target_sizing.py`

Backtest-planning dependency:
- `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md` explicitly calls for 400 / 500 / 1000 / 2000 / 4000 capital studies

Conclusion:
- capital-level scenario testing is structurally possible without code rewrite
- measured capital-ladder artifacts are still absent

## 3. Adaptive sizing formula evidence

### Fixed-fraction base sizing

Source:
- `src/portfolio_minimal/allocation_router/base_size_builder.py`

Implemented formula:
- `raw_base_size = available_capital * base_fraction`
- `base_size = clamp(raw_base_size, min_size, max_size)`

### Vol-target sizing

Source:
- `src/portfolio_minimal/allocation_router/vol_target_sizer.py`

Implemented formula:
- `instrument_value_vol = instrument_price * instrument_pct_vol * point_value`
- `daily_cash_vol_target = (available_capital * annual_vol_target) / sqrt(trading_days_per_year)`
- `vol_scalar = daily_cash_vol_target / instrument_value_vol`
- `raw_position_size = (forecast_strength / forecast_scale) * vol_scalar`
- `position_size = min(raw_position_size, max_position_size)` when capped

### Portfolio cap reduction

Source:
- `src/portfolio_minimal/allocation_router/portfolio_cap_applier.py`

Implemented cap order:
1. position cap
2. remaining gross capacity
3. remaining cluster capacity
4. proportional remaining loss capacity
5. proportional remaining beta capacity

### Post-cap viability

Source:
- `src/portfolio_minimal/allocation_router/phantom_trade_guard.py`

Implemented evidence:
- if `final_size < min_viable_size` -> phantom
- if `final_size / candidate_size` shrinks EV so that `scaled_ev_net <= scaled_expected_cost` -> reject as `COST_EXCEEDS_EDGE_AFTER_ALLOCATION`

Conclusion:
- capital-aware sizing is proven at config/profile level
- explicit live account-state doctrine is not proven

Classification:
- `CAPITAL_ADAPTIVE_SIZING_NOT_PROVEN` for governed live account-state adaptation
- adaptive config/profile-driven sizing is proven for backtest/runtime config use

## 4. Venue min-notional interaction evidence

Proven from current rails:
- execution normalization checks venue constraints fail-closed
- invalid normalized notional blocks submission before venue order send
- blocked reason is recorded in execution tests

Relevant evidence:
- `tests/test_execution_backbone/test_execution_runtime.py`
- `tests/test_execution_backbone/test_venue_constraints_provider.py`
- `tests/test_execution_backbone/test_gatekeeper.py`

Not proven:
- dedicated sizing-stage min-notional viability awareness before execution normalization
- pair-level measured min-notional exclusion rate

Classifications:
- `MIN_NOTIONAL_FAIL_CLOSED`
- `MIN_NOTIONAL_ONLY_EXECUTION_STAGE`
- `SMALL_CAPITAL_EXCLUSION_NOT_MEASURED`
- `SMALL_CAPITAL_FRAGMENTATION_RISK`

## 5. Fee / slippage / impact adaptation by capital

Proven:
- phantom guard rescales `expected_cost` and `ev_net` after cap reduction via `size_ratio`
- therefore cost-vs-edge viability after allocation shrink is not ignored

Not proven:
- explicit fee recomputation from live fee source after each cap reduction
- explicit impact recomputation from order size after each cap reduction
- explicit slippage recomputation as capital changes from 400 to 4000
- explicit participation-ratio doctrine tied to reduced order size in this rail

Classifications:
- `CAPITAL_COST_RECOMPUTED` for post-cap phantom scaling of expected economics
- `COST_NOTIONAL_NOT_PROVEN` for full all-in cost recomputation
- `IMPACT_NOTIONAL_NOT_PROVEN`
- `FEE_NOTIONAL_NOT_PROVEN`

## 6. Multi-pair capital fragmentation evidence

Proven:
- baseline pair/gross/cluster/beta/loss caps exist
- portfolio arbitration and cap application can reduce or sterilize trades

Not proven:
- dedicated fragmentation warning for 12-pair universe vs 400-500 EUR capital
- minimum viable capital per pair artifact
- dynamic pair-universe shrink based on available capital

Classifications:
- `CAPITAL_FRAGMENTATION_NOT_PROVEN`
- `PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL_RISK`

## 7. 400 / 500 / 1500 / 4000 readiness

Proven:
- current config/profile rails can accept different capital values without code rewrite

Not proven:
- measured viability for 400 / 500 / 1500 / 4000
- pair-level rejection rates
- fee/slippage/impact survival across those capital buckets
- min-notional survival by pair and capital bucket

Current doctrine:
- scenario readiness is a Backtest Strategy Ladder dependency
- no live claim should be made from config flexibility alone

## 8. Safety rules status

Observed safety posture:
- missing live balance source is not proven as a safe measured value
- missing venue constraints are already treated fail-closed in the execution rail
- small-capital no-trade remains expected to be logged honestly through execution/runtime refusal paths
- capital changes can be config/account-state driven; no code rewrite is structurally required

## 9. Tests found

Relevant tests:
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`
- `tests/test_portfolio_minimal/test_vol_target_sizing.py`
- `tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py`
- `tests/test_execution_backbone/test_execution_runtime.py`
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_system_flow.py`

Observed coverage:
- base size math
- vol-target math
- cap application ordering
- phantom viability handling
- execution-stage min-notional blocking
- cockpit non-green handling for small-capital `NOT_PROVEN`

## 10. External audit questions

1. Should governed live/shadow sizing be fed from actual free quote balance rather than config-only `available_capital`?
2. Is reserve-buffer subtraction required before usable capital becomes sizing capital?
3. Should min-notional feasibility be visible at sizing stage rather than only execution normalization?
4. Is phantom post-cap scaling sufficient, or should fees / impact / slippage be fully recomputed after cap reduction?
5. What pair-universe shrink or capital-fragmentation policy is required for 400-500 EUR operation?
6. Which Backtest Strategy Ladder artifact will govern the 400 / 500 / 1500 / 4000 capital promotion decision?
