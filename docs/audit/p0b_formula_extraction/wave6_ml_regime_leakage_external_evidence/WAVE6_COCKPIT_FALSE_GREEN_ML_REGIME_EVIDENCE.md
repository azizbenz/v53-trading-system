# Wave 6 Cockpit False-Green ML / Regime Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `COCKPIT_ONLY`, `STALE_ARTIFACT_RISK`

## 1. Artifact-present vs runtime-consumed separation

Source file: `src/cockpit/state_feature_bridge.py`

Evidence:

- runtime-active statuses are explicit:
  - `RUNTIME_CONSUMED`
  - `ENGINE_CONSUMED`
  - `SCORING_CONSUMED`
  - `RISK_GATE_CONSUMED`
  - `COST_GATE_CONSUMED`
  - `EXECUTION_GATE_CONSUMED`
- absent proof defaults to `runtime_status="NOT_PROVEN"`
- artifact presence alone is represented as `ARTIFACT_PRESENT_ONLY`

Plain-text meaning:

- a feature artifact can exist without being shown as runtime-active

## 2. Replay economics panel keeps expected CE explicit

Source file: `src/cockpit/state_replay_metrics.py`

Exact code excerpt:

```python
expected_ce_label = "Expected CE net"
expected_ce_caveat = "Expected CE over replay DTR records; not realized profitability."
```

False-green protection:

- expected CE cannot be displayed as realized profitability by label alone
- cost completeness caveats remain explicit

## 3. System flow readiness stays non-green on partial economics and proof gaps

Source file: `src/cockpit/state_system_flow.py`

Evidence:

- placeholder replay economics stay out of green
- partial cost model stays out of green
- artifact-only feature bridge stays out of green
- small-capital `NOT_PROVEN` stays out of green
- true drawdown `NOT_PROVEN` stays out of green
- baseline portfolio caps only stay out of full-risk green

## 4. ML/regime-specific cockpit interpretation

From inspected cockpit rails:

- missing/stale ML or regime artifacts do not become runtime-consumed by artifact presence alone
- stale or missing economics/proof status is carried as non-green
- no dedicated cockpit state inspected here claimed ML live-readiness

Residual risk:

- cockpit shows status correctly only if upstream status fields are populated truthfully
- live non-empty ML source is still not proven, so cockpit can only show the absence of proof, not the presence of governed live ML

## 5. Tests

- `tests/cockpit/test_state_feature_bridge.py`
  - runtime consumption defaults to `NOT_PROVEN`
  - research-only / future-reserved rows stay non-runtime
- `tests/cockpit/test_state_replay_metrics.py`
  - CE label is expected-only
  - cost-model caveat includes fee-source proof gaps
  - true drawdown status remains `NOT_PROVEN`
  - stale replay is not green
  - economics only go green when cost model is complete
- `tests/cockpit/test_state_system_flow.py`
  - partial cost model not green
  - artifact-only feature bridge not green
  - small-capital `NOT_PROVEN` not green
  - missing true drawdown not green
  - baseline portfolio caps not full-risk green

## 6. External-audit questions

- Is there a dedicated cockpit ML/regime panel outside the inspected state rails that also needs anti-false-green hardening?
- Should stale ML/regime artifact state be surfaced as an explicit operator alert rather than a passive readiness downgrade only?

