# Wave 5 Risk Candidate / Gate Evidence

## Evidence 1: RiskCandidate fields

Source file:
- `src/risk_backbone/risk_runtime_models.py`

Class:
- `RiskCandidate`

Exact code excerpt:
```python
class RiskCandidate(BaseModel, frozen=True):
    pair: str
    engine_id: str
    size: float
    planned_loss: float | None
    pair_beta: float | None = None
    side: str = "buy"
    carriage_statuses: tuple[str, ...] = ()
    carriage_reason_codes: tuple[str, ...] = ()
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    participation_penalty: float = 0.0
    spread_bps: float | None = Field(default=None, ge=0.0)
    reference_spread_bps: float | None = Field(default=None, gt=0.0)
    depth_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    order_cancellation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    taker_imbalance: float | None = Field(default=None, ge=-1.0, le=1.0)
    micro_vol_divergence: float | None = Field(default=None, ge=0.0)
```

Meaning:
- The risk rail carries explicit micro-friction, spread, depth, and imbalance inputs.
- `side` defaults to `"buy"` in the public model.

Scope:
- per-candidate

Missing-field behavior:
- some risk/micro fields default numerically in the candidate contract
- explicit carriage statuses and reason codes exist as a parallel audit rail

Side/halal risk:
- no short side is created here

Classifications:
- `EVIDENCE_EXTRACTED`

## Evidence 2: Gross / position cap

Source file:
- `src/risk_backbone/exposure_budgeter/gross_cap_guard.py`

Function:
- `evaluate_gross_cap`

Exact code excerpt:
```python
projected = current_gross + candidate_size

# Position cap: check projected pair exposure, not candidate alone
projected_pair = current_pair_exposure + candidate_size
if projected_pair > position_cap:
```

```python
verdict=GrossCapVerdict.REJECTED_POSITION_CAP
```

```python
if projected > gross_cap:
    ...
    verdict=GrossCapVerdict.REJECTED_GROSS_CAP
```

Implemented formula:
- projected pair exposure and projected gross exposure must stay within caps

Units:
- candidate size / exposure units

Scope:
- per-candidate against portfolio/global state

Tests:
- `tests/test_risk_backbone/test_exposure_budgeter.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`

## Evidence 3: Position loss estimate

Source file:
- `src/risk_backbone/loss_budgeter/position_loss_estimator.py`

Function:
- `estimate_position_loss`

Exact code excerpt:
```python
loss_pct = abs(entry_price - stop_price) / entry_price
loss_amount = size * loss_pct
```

Implemented formula:
- planned loss is size times absolute stop distance as a fraction of entry

Units:
- `loss_pct`: fraction
- `loss_amount`: quote-currency-like loss amount

Tests:
- covered in risk integration and runtime tests via planned-loss gating

Classifications:
- `EVIDENCE_EXTRACTED`

## Evidence 4: Drawdown guard

Source file:
- `src/risk_backbone/loss_budgeter/drawdown_guard.py`

Function:
- `evaluate_drawdown_guard`

Exact code excerpt:
```python
drawdown_pct = max(0.0, (session_peak_equity - current_equity) / session_peak_equity)
```

```python
verdict=DrawdownVerdict.OBSERVE_ONLY
```

```python
verdict=DrawdownVerdict.REDUCE_EXPOSURE
```

Implemented formula:
- runtime intraday drawdown as loss from session peak equity

Semantics:
- realized runtime equity guard
- distinct from replay `drawdown_proxy`

Tests:
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_risk_backbone/test_risk_integration.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`

## Evidence 5: Daily PnL breaker

Source file:
- `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py`
- `src/risk_backbone/daily_pnl_breaker_entry_gate.py`

Functions:
- `DailyPnlBreaker.assess`
- `build_daily_pnl_entry_gate`

Exact code excerpt:
```python
class DailyPnlBreakerVerdict(StrEnum):
    ACCEPTED = "accepted"
    SHADOW_RECOMMENDED = "shadow_recommended"
    SHADOW_LOCKED = "shadow_locked"
```

```python
reason_codes=assessment.reason_codes or ("RISK_DAILY_PNL_BREAKER",),
```

Important behavior excerpt:
```python
"no automatic same-day reactivation"
```

Meaning:
- after breach, same-day shadow lock persists
- risk precheck can block with `RISK_DAILY_PNL_BREAKER`
- breaker can optionally trip the execution-owned emergency circuit breaker

Tests:
- `tests/test_risk_backbone/test_daily_pnl_breaker.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## Evidence 6: Runtime timestamp and mapping discipline

Source file:
- `src/risk_backbone/risk_runtime_evaluation_support.py`

Exact code excerpt:
```python
timestamp = _require_runtime_timestamp(now, context="RiskRuntime.evaluate_candidate")
```

Meaning:
- risk evaluation requires explicit runtime timestamp
- missing/stale mapping states are tracked in the risk audit helpers

Tests:
- `tests/test_risk_backbone/test_risk_runtime.py`
- assertions cover missing `now`, missing explicit beta mapping, fail-closed no-cluster behavior, carriage metadata preservation

## Wave 3 cost-completeness usage check

Search result:
- repo-wide search over `src/scoring_backbone`, `src/risk_backbone`, `src/portfolio_minimal`, `src/engines`, `src/execution_backbone`, and `src/interface_contracts` for `cost_model_completeness_status|fee_source_status|impact_source_status|fill_realism_status|realized_slippage_status|small_capital_exclusion_status` returned `NO_MATCH`

Interpretation:
- no governed risk-runtime consumer for those statuses was proven

Risk significance:
- missing fee, impact, fill-realism, or replay cost completeness is not proven as an explicit runtime risk blocker

Classifications:
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`
- `FAIL_OPEN_RISK`

External-audit questions:
- Should risk runtime fail closed or at least downgrade when fee/impact/fill realism is partial or unknown?
- Are numeric defaults on `RiskCandidate` sufficiently protected by carriage statuses, or should some missing micro-friction inputs be made more explicit in a later patch?

