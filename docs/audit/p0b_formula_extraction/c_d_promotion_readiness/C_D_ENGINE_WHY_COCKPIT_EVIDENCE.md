# C/D Engine Why / Cockpit Evidence

## Inspected Surfaces

- `src/cockpit/state_engine_why.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/templates/partials/_engine_why.html`
- `src/cockpit/templates/partials/_replay_metrics.html`
- `src/cockpit/templates/partials/_system_flow.html`
- `src/cockpit/templates/partials/_feature_bridge.html`

## Visibility Matrix

| Surface question | Classification | Evidence |
|---|---|---|
| engine role | `NOT_VISIBLE` | engine-why shows status/why/records/costs, not C or D role |
| `PARTIAL_BY_DESIGN` doctrine | `NOT_VISIBLE` | not shown on inspected cockpit templates |
| raw feature status | `PARTIAL` | feature bridge shows family runtime status, not C/D raw feature rows |
| reason codes | `PARTIAL` | engine-why only shows `blocked_reasons_top3`; replay/system flow show reason/caveat surfaces |
| expected CE caveat | `VISIBLE` | replay metrics labels `Expected CE net` and explicit caveat |
| cost completeness status | `VISIBLE` | engine-why and replay/system flow show cost completeness |
| promotion readiness | `PARTIAL` | system flow shows overall operability, not per-engine promotion status |
| calibration status | `NOT_VISIBLE` | no C/D calibration status surfaced on inspected pages |
| shadow status | `PARTIAL` | system flow shows operability/shadow-thin style readiness, not engine-specific shadow confirmation |
| missing fields as `NOT_PROVEN`, not zero | `PARTIAL` | replay/system flow use non-green statuses; engine-why uses `SOURCE_UNAVAILABLE` for missing costs |

## Key Source Proof

Source: `src/cockpit/state_engine_why.py`

```text
EngineWhyRow:
  expected_cost_status = "SOURCE_UNAVAILABLE" or "PARTIAL_EXECUTION_EVIDENCE"
  cost_model_completeness_status = "UNKNOWN" if aggregate missing
```

Source: `src/cockpit/state_replay_metrics.py`

```text
expected_ce_caveat:
  "Expected CE over replay DTR records; not realized profitability."

drawdown_proxy_caveat:
  "Gross-return proxy; not net-equity max drawdown and not promotion-grade."
```

Source: `src/cockpit/state_system_flow.py`

```text
operability score includes:
  scoring_cost_completeness_status
  risk_input_completeness_status
  small_capital_viability_status
  sizing_doctrine_status
  portfolio_multi_asset_status
  true_drawdown_status
```

## False-Green Risk

Current state:
- broad Wave 5 false-green hardening is real
- C/D-specific role and partial-by-design doctrine are still weak on engine-why

Classification:
- `PARTIAL`
- `FALSE_GREEN_RISK` for operator interpretation of C/D-specific doctrine, not for global cost/readiness green-gating

## Tests

- `tests/cockpit/test_state_engine_why.py`
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_system_flow.py`
- `tests/cockpit/test_state_feature_bridge.py`

