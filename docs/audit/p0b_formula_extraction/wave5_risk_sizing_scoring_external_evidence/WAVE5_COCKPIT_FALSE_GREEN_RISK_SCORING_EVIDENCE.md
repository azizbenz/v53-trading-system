# Wave 5 Cockpit False-Green Risk / Scoring Evidence

## Evidence 1: Replay economics labels and non-green gating

Source file:
- `src/cockpit/state_replay_metrics.py`

Exact code excerpt:
```python
def expected_ce_label(self) -> str:
    return "Expected CE net"

def expected_ce_caveat(self) -> str:
    return "Expected CE over replay DTR records; not realized profitability."
```

```python
def exec_rate_label(self) -> str:
    return "Exec rate (executed / total records)"
```

```python
def economics_display_state(self) -> str:
    if self.source_is_unavailable:
        return "placeholder"
    if self.source_status == "stale":
        return "stale"
    if self.total_records <= 0:
        return "placeholder"
```

```python
def allow_positive_economics_tone(self) -> bool:
    return self.economics_display_state == "measured"

def ce_net_value_class(self) -> str:
    if self.allow_positive_economics_tone:
        return "value-up" if self.ce_net >= 0 else "value-down"
    return "value-warn" if self.ce_net >= 0 else "value-down"
```

Meaning:
- expected CE cannot be presented as realized profitability
- missing, stale, zero-record, thin-sample, or partial-cost replay states do not get positive tone

Tests:
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_cockpit_server_routes.py`

## Evidence 2: Partial cost model is explicit

Source file:
- `src/cockpit/state_replay_metrics.py`

Evidence excerpt:
```python
fee_source_status: str = "NOT_PROVEN"
impact_source_status: str = "NOT_PROVEN"
cost_model_completeness_status: str = "PARTIAL_NO_FEE_NO_IMPACT"
```

```python
if self.cost_model_is_partial:
    reason_codes.append("REPLAY_COST_MODEL_PARTIAL")
if self.fee_source_status in {"NOT_PROVEN", "MISSING"}:
    reason_codes.append("FEE_SOURCE_NOT_PROVEN")
if self.impact_source_status in {"NOT_PROVEN", "MISSING"}:
    reason_codes.append("IMPACT_SOURCE_NOT_PROVEN")
```

Meaning:
- replay cost partiality is visible in cockpit state

Limitation:
- this is a cockpit protection seam; runtime consumption of these statuses was not proven

Classifications:
- `EVIDENCE_EXTRACTED`
- `COCKPIT_FALSE_GREEN_RISK`

## Evidence 3: Engine-why cost fields stay explicit when unavailable

Source file:
- `src/cockpit/state_engine_why.py`

Exact code excerpt:
```python
expected_cost: float | None = None
expected_cost_status: str = "SOURCE_UNAVAILABLE"
realized_cost: float | None = None
realized_cost_status: str = "SOURCE_UNAVAILABLE"
```

```python
expected_cost_status=(
    "PARTIAL_EXECUTION_EVIDENCE"
    if agg is not None and agg.cost_model_completeness_status != "COMPLETE"
    else ("OK" if agg is not None else "SOURCE_UNAVAILABLE")
),
```

Meaning:
- missing execution-cost evidence does not become measured zero in this seam

Tests:
- `tests/cockpit/test_state_engine_why.py`

## Evidence 4: Economic sterilization seam keeps blocked sub-counts unavailable rather than zero

Source file:
- `src/cockpit/state_economic_sterilization.py`

Exact code excerpt:
```python
blocked_or_rejected = max(opportunities - replay.selected_count, 0)
ratio = blocked_or_rejected / max(opportunities, 1)
```

```python
cost_blocked_count=None,
cost_blocked_count_status="SOURCE_UNAVAILABLE",
min_notional_blocked_count=None,
min_notional_blocked_count_status="SOURCE_UNAVAILABLE",
slippage_blocked_count=None,
slippage_blocked_count_status="SOURCE_UNAVAILABLE",
```

Meaning:
- the seam reports missing blocked sub-count evidence explicitly

Tests:
- `tests/cockpit/test_state_economic_sterilization.py`

## Evidence 5: Feature artifact presence is not runtime proof

Source file:
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/templates/partials/_feature_bridge.html`

Exact code excerpt:
```python
artifact_status: str = "ARTIFACT_PRESENT_ONLY"
runtime_status: str = "NOT_PROVEN"
runtime_lifecycle_status: str = "NOT_PROVEN"
registry_intent_status: str | None = None
```

```python
runtime_consumption_status: str = "NOT_PROVEN"
runtime_active: bool = False
```

```html
<p class="muted small value-down"><strong>Runtime caveat:</strong> feature-bridge artifact presence is not runtime-consumption proof.</p>
```

Tests:
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_system_flow.py`
- `tests/cockpit/test_cockpit_server_routes.py`

## Evidence 6: System-flow verdict stays non-green under partial economics or artifact-only proof

Source file:
- `src/cockpit/state_system_flow.py`

Exact code excerpt:
```python
economics_label = (
    "SAMPLE_TOO_SMALL"
    if economics.status == "insufficient_sample"
    else (
        "REPLAY_ECONOMICS_NOT_MEASURED"
        if economics.status in {"placeholder", "stale"}
        else (
            "COST_MODEL_PARTIAL"
            if economics.status == "partial"
            else (
                "CE_NET_POSITIVE"
                if economics.status == "ok" and economics.ce_net > 0.0
                else "CE_NET_NEGATIVE"
            )
        )
    )
)
```

Meaning:
- system flow keeps partial or unmeasured economics out of green trading-readiness interpretation

External-audit questions:
- Should the same artifact/runtime-consumption separation be extended beyond the current feature-bridge and replay-economics surfaces?
- Are portfolio and small-capital readiness states still under-specified for cockpit green/yellow/red semantics?

