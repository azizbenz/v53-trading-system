# Wave 3 Cockpit False-Green Execution Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `COCKPIT_FALSE_GREEN_RISK`
- `PLACEHOLDER_RISK`

## 1. Replay economics display-state guard

Source file: `src/cockpit/state_replay_metrics.py`

```python
def economics_display_state(self) -> str:
    if self.source_is_unavailable:
        return "placeholder"
    if self.source_status == "stale":
        return "stale"
    if self.total_records <= 0:
        return "placeholder"
    if self.total_records < MIN_REPLAY_SAMPLE_RECORDS:
        return "insufficient_sample"
    return "measured"
```

Evidence:
- zero-record replay metrics are placeholder, not measured
- stale replay metrics are explicit
- thin samples are explicit

## 2. Positive-tone gating

Source file: `src/cockpit/state_replay_metrics.py`

```python
def allow_positive_economics_tone(self) -> bool:
    return self.economics_display_state == "measured"

def ce_net_value_class(self) -> str:
    if self.allow_positive_economics_tone:
        return "value-up" if self.ce_net >= 0 else "value-down"
    return "value-warn" if self.ce_net >= 0 else "value-down"
```

Evidence:
- positive CE does not render green unless display state is `measured`

## 3. Operator-facing semantic labels

Source file: `src/cockpit/state_replay_metrics.py`

```python
def expected_ce_label(self) -> str:
    return "Expected CE net"

def expected_ce_caveat(self) -> str:
    return "Expected CE over replay DTR records; not realized profitability."

def exec_rate_label(self) -> str:
    return "Exec rate (executed / total records)"

def drawdown_proxy_caveat(self) -> str:
    return "Gross-return proxy; not net-equity max drawdown and not promotion-grade."
```

Evidence:
- semantic clarification exists in state layer

## 4. Template enforcement

Source file: `src/cockpit/templates/partials/_replay_metrics.html`

```html
{% if vm.replay.economics_display_state == 'placeholder' %}
    <p class="muted small value-warn">Replay metrics are present but not measured yet: total_records = 0, so expected CE and execution rate are placeholders only.</p>
{% elif vm.replay.economics_display_state == 'stale' %}
    <p class="muted small value-warn">Latest replay metrics are stale. Economics stay visible for inspection only and must not be treated as green.</p>
{% elif vm.replay.economics_display_state == 'insufficient_sample' %}
    <p class="muted small value-warn">Replay sample is thin. Economics are visible, but positive values stay cautionary until the sample is large enough.</p>
{% endif %}
```

Evidence:
- template makes placeholder/stale/thin-sample warnings operator-visible

## 5. Remaining execution placeholder risks

Source file: `src/cockpit/state_economic_sterilization.py`

```python
cost_blocked_count=0,
min_notional_blocked_count=0,
slippage_blocked_count=0,
```

Source file: `src/cockpit/state_engine_why.py`

```python
expected_cost=agg.expected_cost_mean if agg is not None else 0.0,
realized_cost=agg.realized_cost_mean if agg is not None else 0.0,
```

Evidence:
- some execution-facing cockpit adapters still surface zero defaults when richer data is absent
- those zeros are not automatically proven measured values

Classification:
- `PLACEHOLDER_RISK`
- `COCKPIT_FALSE_GREEN_RISK`

Tests:
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_economic_sterilization.py`
- `tests/cockpit/test_cockpit_server_routes.py`

External-audit questions:
- Should engine-level expected/realized cost default to `None`/explicit unavailable state instead of `0.0` in future hardening?
- Should sterilization sub-counts remain visibly partial until real blocked-by-cause producers are wired?
