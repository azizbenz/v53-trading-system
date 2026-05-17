# C/D Partial-By-Design Operator Doctrine

Date: `2026-05-01`
Scope: operator-facing explanation for Engine C and Engine D shared-physics status.

## Doctrine

Engine C and Engine D are not defective because they do not fully populate A/B shared scoring physics.

Current governed state:

- `Engine C shared_physics_mapping_status = PARTIAL_BY_DESIGN`
- `Engine D shared_physics_mapping_status = PARTIAL_BY_DESIGN`

This means:

- local C/D engine math is active
- local C/D raw features and reason codes must stay complete
- supplementary refs may remain additive and non-directional
- replay/shadow economics still decide readiness

## Operator Caveat

```text
Engine C/D local math is active, but A/B-style shared scoring physics mapping is PARTIAL_BY_DESIGN.
This is not a defect.
Promotion readiness still requires engine-specific replay/shadow economics.
```

## Forbidden Force-Mapping

### Engine C

- `false_breakout_risk -> execution_fragility`
- `queue_pressure -> execution_fragility`
- `raw_vpin -> market_toxicity`
- `raw_ofi -> market_toxicity`
- `false_breakout_risk -> spread_regime_penalty`

### Engine D

- `stale_signal_score -> spread_regime_penalty`
- `realized_vol_current -> execution_fragility`
- `reformation_score -> market_toxicity`
- `anti_revenge_state -> generic risk_penalty`

## Allowed Future Condition

Future mapping is allowed only if:

- a normalized semantic bridge exists
- the bridge is source-proven
- tests prove the mapping
- external audit accepts the mapping
