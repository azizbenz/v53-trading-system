# Wave 5 Drawdown / Loss Control Evidence

## Evidence 1: Replay drawdown proxy remains a proxy

Source file:
- `src/local_replay_runtime/replay_metrics_collector.py`

Function:
- `_drawdown_proxy`

Exact code excerpt:
```python
running = 0.0
peak = 0.0
worst = 0.0
for record in records:
    running += record.gross_return
    peak = max(peak, running)
    worst = min(worst, running - peak)
return abs(worst)
```

Implemented formula:
- cumulative gross-return peak-to-trough proxy

Semantics:
- gross-return proxy
- not net-equity drawdown
- replay/report-only

Consumer evidence:
- `src/cockpit/state_replay_metrics.py`
- `src/local_replay_runtime/replay_executor.py`

Classification:
- `EVIDENCE_EXTRACTED`
- `EXPECTED_REALIZED_AMBIGUITY`
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

## Evidence 2: Cockpit caveat keeps replay proxy non-promotion-grade

Source file:
- `src/cockpit/state_replay_metrics.py`

Exact code excerpt:
```python
def drawdown_proxy_caveat(self) -> str:
    return "Gross-return proxy; not net-equity max drawdown and not promotion-grade."
```

Tests:
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_cockpit_server_routes.py`

Meaning:
- the UI seam explicitly prevents promotion-grade interpretation

## Evidence 3: Runtime drawdown guard uses actual session equity

Source file:
- `src/risk_backbone/loss_budgeter/drawdown_guard.py`

Function:
- `evaluate_drawdown_guard`

Exact code excerpt:
```python
drawdown_pct = max(0.0, (session_peak_equity - current_equity) / session_peak_equity)
```

```python
if drawdown_pct >= observe_threshold_pct:
    ...
    verdict=DrawdownVerdict.OBSERVE_ONLY

if drawdown_pct >= warning_threshold_pct:
    ...
    verdict=DrawdownVerdict.REDUCE_EXPOSURE
```

Implemented formula:
- session drawdown on runtime equity

Semantics:
- realized runtime risk control

Tests:
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_risk_backbone/test_risk_integration.py`

## Evidence 4: Daily loss breaker and kill-switch hook

Source file:
- `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py`
- `src/execution_backbone/emergency_circuit_breaker.py`

Evidence excerpt:
```python
class DailyPnlBreakerVerdict(StrEnum):
    ACCEPTED = "accepted"
    SHADOW_RECOMMENDED = "shadow_recommended"
    SHADOW_LOCKED = "shadow_locked"
```

```python
if circuit_breaker is None or not trip_circuit_breaker_on_breach:
    return False
circuit_breaker.trip(KillSwitchReason.LOSS_BUDGET_BREACH, detail)
```

Meaning:
- runtime loss-control rail can force shadow and optionally trip an emergency breaker

Tests:
- `tests/test_risk_backbone/test_daily_pnl_breaker.py`

## Promotion / live gate question

Search and evidence outcome:
- replay `drawdown_proxy` is clearly a diagnostic proxy
- runtime drawdown guard is real, but a true executed-only replay/shadow/live net-equity max-drawdown rail was not proven in this Wave 5 pack

Classification:
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

External-audit questions:
- Is current runtime drawdown protection sufficient for shadow/live gating even while replay promotion evidence lacks a true executed-only net-equity drawdown rail?
- Should future capital-ladder or promotion reports consume the runtime drawdown guard, a new replay equity curve rail, or both?

