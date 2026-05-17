# Wave 5 Portfolio Exposure / Correlation Evidence

## Evidence 1: Gross exposure aggregation

Source file:
- `src/risk_backbone/exposure_budgeter/gross_exposure_calculator.py`

Function:
- `calculate_gross_exposure`

Exact code excerpt:
```python
for p in positions:
    by_pair[p.pair] = by_pair.get(p.pair, 0.0) + p.size
    by_engine[p.engine_id] = by_engine.get(p.engine_id, 0.0) + p.size

return GrossExposure(
    gross_exposure=sum(p.size for p in positions),
    position_count=len(positions),
    by_pair=by_pair,
    by_engine=by_engine,
)
```

Implemented formula:
- gross exposure is the sum of open position sizes
- by-pair and by-engine exposure are aggregated explicitly

Scope:
- portfolio/global

Tests:
- `tests/test_risk_backbone/test_exposure_budgeter.py`

## Evidence 2: Pair and global exposure caps

Source file:
- `src/risk_backbone/exposure_budgeter/gross_cap_guard.py`

Function:
- `evaluate_gross_cap`

Exact code excerpt:
```python
projected = current_gross + candidate_size
projected_pair = current_pair_exposure + candidate_size
if projected_pair > position_cap:
```

```python
if projected > gross_cap:
```

Meaning:
- pair cap and global gross cap are both enforced

Tests:
- `tests/test_risk_backbone/test_exposure_budgeter.py`
- `tests/test_risk_backbone/test_risk_integration.py`

## Evidence 3: Cluster correlation cap

Source file:
- `src/risk_backbone/correlation_cluster_guard/cluster_cap_guard.py`

Observed behavior:
- reject if no `cluster_id`
- reject if projected cluster exposure exceeds `cluster_cap`

Evidence summary:
- fail-closed cluster mapping is part of runtime risk doctrine

Tests:
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_portfolio_minimal/test_opportunity_selector_minimal.py`

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`

## Evidence 4: Beta cap

Source file:
- `src/risk_backbone/btc_factor_guard/projected_beta_checker.py`

Function:
- `check_projected_beta`

Exact code excerpt:
```python
current = calculate_portfolio_beta(current_positions, betas)

projected_positions = dict(current_positions)
projected_positions[candidate_pair] = projected_positions.get(candidate_pair, 0.0) + candidate_size
projected_betas = dict(betas)
projected_betas[candidate_pair] = candidate_beta
projected = calculate_portfolio_beta(projected_positions, projected_betas)
```

```python
within_cap=abs(projected.beta_port) <= beta_cap
```

Implemented formula:
- projected portfolio beta after adding the candidate must stay within `beta_cap`

Scope:
- portfolio/global

Tests:
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_risk_backbone/test_risk_integration.py`

## Evidence 5: Ranking under cluster utilization

Source file:
- `src/portfolio_minimal/opportunity_selector/comparative_ranker.py`

Function:
- `compute_ranking_score`

Exact code excerpt:
```python
return (
    _W_SCORE * candidate.penalized_score
    + _W_CE * candidate.ce_expected
    - _W_COST * candidate.expected_cost
    - _W_CORR * cluster_utilization
)
```

Implemented formula:
- `R_i = 0.35 * penalized_score + 0.30 * ce_expected - 0.20 * expected_cost - 0.15 * cluster_utilization`

Meaning:
- correlation pressure enters ranking as a penalty via cluster utilization

Tests:
- `tests/test_portfolio_minimal/test_opportunity_selector_minimal.py`

## Evidence 6: Portfolio arbitration metrics

Source file:
- `src/portfolio_minimal/arbitration_record.py`

Function:
- `build_arbitration_snapshot`

Exact code excerpt:
```python
capital_lockup_utilisation = candidate.ce_expected / effective_holding_hours
```

```python
scaled_loss = candidate.estimated_loss * size_ratio
scaled_beta = abs(candidate.beta_impact) * size_ratio
```

```python
correlated_budget_consumption = (final_size / cluster_scale) + (scaled_beta / beta_scale)
hidden_structural_risk_addition = (scaled_loss / loss_scale) + (scaled_beta / beta_scale)
```

Meaning:
- the portfolio audit rail computes correlation and structural-risk consumption metrics after sizing

Consumer status:
- report / audit oriented; not proven as a direct runtime gate

Tests:
- indirect coverage in portfolio orchestrator and report tests

Portfolio questions for external audit:
- Is current 12-pair multi-asset control sufficiently captured by pair caps, gross caps, cluster caps, and beta caps?
- Is cluster-based control enough without a richer empirical cross-pair covariance rail?

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

