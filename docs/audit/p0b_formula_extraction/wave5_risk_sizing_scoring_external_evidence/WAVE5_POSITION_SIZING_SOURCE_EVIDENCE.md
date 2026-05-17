# Wave 5 Position Sizing Source Evidence

## Portfolio sizing rail presence

Path evidence:
- `src/portfolio_backbone/` was not present in the inspected tree
- active sizing and allocation source evidence lives in `src/portfolio_minimal/`

Classification:
- `CONSUMER_NOT_FOUND` for `portfolio_backbone`
- `EVIDENCE_EXTRACTED` for `portfolio_minimal`

## Evidence 1: Base size from capital fraction

Source file:
- `src/portfolio_minimal/allocation_router/base_size_builder.py`

Function:
- `compute_base_size`

Exact code excerpt:
```python
raw = profile.available_capital * profile.base_fraction
clamped = max(profile.min_size, min(raw, profile.max_size))
```

Implemented formula:
- base size is a fraction of available capital, clamped to `[min_size, max_size]`

Capital base:
- `profile.available_capital`

Units:
- quote-currency-like size

Min-notional interaction:
- indirect only; this seam uses `min_size`, not venue `min_notional`

Small-capital risk:
- if raw allocation falls below `min_size`, the clamp pushes size upward locally, but venue constraints still apply later

Tests:
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`

## Evidence 2: Tier + score modulation

Source file:
- `src/portfolio_minimal/allocation_router/score_size_mapper.py`

Function:
- `compute_modulated_size`

Exact code excerpt:
```python
score_boost = 0.0
if ranking_score > _HIGH_SCORE_THRESHOLD and multiplier > 0.0:
    score_boost = min(
        (ranking_score - _HIGH_SCORE_THRESHOLD) / (1.0 - _HIGH_SCORE_THRESHOLD) * _MAX_SCORE_BOOST,
        _MAX_SCORE_BOOST,
    )

effective_multiplier = multiplier + score_boost
modulated = base_size * effective_multiplier
```

Implemented formula:
- size is tier-multiplied
- very high ranking scores get up to a +20% boost

Units:
- quote-currency-like size

Boundedness:
- boost capped at `_MAX_SCORE_BOOST`
- `tier_1=1.0`, `tier_2=0.6`, `no_trade=0.0`

Tests:
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`

## Evidence 3: Carver-style vol-target size

Source file:
- `src/portfolio_minimal/allocation_router/vol_target_sizer.py`

Function:
- `compute_vol_target_size`

Exact code excerpt:
```python
instrument_value_vol = (
    candidate.instrument_price * candidate.instrument_pct_vol * candidate.point_value
)
daily_cash_vol_target = (
    candidate.available_capital * profile.annual_vol_target
) / math.sqrt(profile.trading_days_per_year)
vol_scalar = daily_cash_vol_target / instrument_value_vol
raw_position_size = (candidate.forecast_strength / profile.forecast_scale) * vol_scalar
```

Implemented formula:
- Carver-style daily cash-vol targeting scaled by forecast strength

Capital base:
- `candidate.available_capital`

Units:
- base quantity / position size

Capping:
- optional `max_position_size`

Tests:
- `tests/test_portfolio_minimal/test_vol_target_sizing.py`

## Evidence 4: Portfolio caps after modulation

Source file:
- `src/portfolio_minimal/allocation_router/portfolio_cap_applier.py`

Function:
- `apply_caps`

Exact code excerpt:
```python
if (
    candidate_size > 0.0
    and estimated_loss_at_candidate_size > 0.0
    and remaining_loss_capacity < float("inf")
):
    loss_per_unit = estimated_loss_at_candidate_size / candidate_size
    max_size_for_loss = remaining_loss_capacity / loss_per_unit
```

```python
if (
    candidate_size > 0.0
    and abs(beta_impact_at_candidate_size) > 0.0
    and remaining_beta_capacity < float("inf")
):
    beta_per_unit = abs(beta_impact_at_candidate_size) / candidate_size
    max_size_for_beta = remaining_beta_capacity / beta_per_unit
```

Implemented formula:
- tightest remaining cap wins across position, gross, cluster, loss, and beta budgets

Units:
- size units

Tests:
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`
- `tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py`

## Evidence 5: Phantom-allocation sterilization

Source file:
- `src/portfolio_minimal/allocation_router/phantom_trade_guard.py`

Function:
- `check_phantom`

Exact code excerpt:
```python
if final_size < min_viable_size:
    ...
```

```python
size_ratio = final_size / candidate_size
scaled_ev_net = ev_net * size_ratio
scaled_expected_cost = expected_cost * size_ratio
if scaled_ev_net <= scaled_expected_cost:
```

Implemented formula:
- reject if allocation is too small to be viable
- reject if scaled EV after allocation does not clear scaled expected cost

Units:
- size units
- EV / expected cost in economics units

Tests:
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`
- `tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py`

## Kelly / fractional Kelly search

Search result:
- repo-wide search over `src/scoring_backbone`, `src/risk_backbone`, `src/portfolio_minimal`, `src/engines`, and `src/interface_contracts` for `Kelly|kelly|fractional_kelly` returned `NO_MATCH`

Interpretation:
- Kelly or fractional Kelly sizing was not proven in the inspected rails

Classification:
- `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

Sizing risks:
- `SMALL_CAPITAL_RISK` because sizing is capital-fraction and cap based, but no explicit small-capital viability optimizer was found
- no evidence found that sizing explicitly prices in fee/impact completeness before sizing, only downstream economics and execution gates

External-audit questions:
- Is the current sizing doctrine intentionally fixed-fraction plus vol-target plus caps, or is a Kelly-like seam expected but missing?
- Should venue `min_notional` and fee/impact completeness be reflected earlier in sizing rather than only in later execution or replay/cockpit seams?

