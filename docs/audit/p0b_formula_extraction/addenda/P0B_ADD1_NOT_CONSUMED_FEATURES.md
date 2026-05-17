# P0-B Addendum 1 - Not Consumed Features

This file lists features that were **not proven consumed anywhere** across:
- direct engine imports
- scoring backbone
- risk backbone
- execution backbone
- complete enablers
- regime / ML artifact runtime
- audited runtime artifact seams

If a feature was only found in its own library, registry, or tests, it is listed here.

## Future reserved features

| Feature | Classification | Evidence | Notes |
|---|---|---|---|
| `pin` | `future_reserved_feature` | No consumer found in engines, scoring, risk, execution, complete_enablers, or local replay runtime consumer rails. | Present in microstructure library/test surface, but current engine wiring does not prove live or replay consumption. |
| `amihud_illiquidity` | `future_reserved_feature` | No audited consumer found outside estimator/test surface. | Reasonable execution-cost research feature, but not wired to current proven engine/runtime rails. |
| `roll_spread` | `future_reserved_feature` | No audited consumer found outside estimator/test surface. | Historical / estimator-only in current proof scope. |
| `corwin_schultz_spread` | `future_reserved_feature` | No audited consumer found outside estimator/test surface. | Historical / estimator-only in current proof scope. |
| `hawkes_intensity` | `future_reserved_feature` | No audited consumer found in current engine, scoring, risk, execution, or artifact runtime rails. | Advanced microstructure feature bank exists, but current V5.3 engine proof does not consume it. |

## Doctrine unclear / manual decision

| Feature | Classification | Evidence | Notes |
|---|---|---|---|
| `pin` as a live toxic-flow veto | `manual_decision_required` | Feature exists, but current engines already use `VPIN` and toxicity-derived context. | Wiring `PIN` as well may be useful, but doctrine is not explicit. |
| `amihud_illiquidity` as a live cost gate | `manual_decision_required` | Cost/execution rail already uses spread, toxicity, volatility, and fee-aware routing. | Could be added later, but no current doctrine proves it must be present now. |
| `hawkes_intensity` as a VPS trigger | `manual_decision_required` | No current consumer proof. | Could be overkill for VPS non-HFT unless explicitly governed. |

## Explicitly not listed here

The following families are **not** treated as not-consumed, because artifact or downstream consumers were proven:
- `kyle_lambda`
- `ofi`
- `vpin`
- `queue_pressure`
- `realized_kernel_volatility`
- `order_book_imbalance`
- `microprice_pressure`
- `market_toxicity_score`
- `regime_transition_risk`
- `regime_stability_score`
- `deceptive_liquidity_score`
- `spoof_like_suspicion_*`

Those families are handled in the main wiring proof as:
- direct engine inputs
- shared downstream execution/risk/scoring inputs
- or `CONSUMED_VIA_ARTIFACT`
