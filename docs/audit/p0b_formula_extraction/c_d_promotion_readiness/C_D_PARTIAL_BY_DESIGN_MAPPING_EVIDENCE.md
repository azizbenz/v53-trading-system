# C/D Partial-By-Design Mapping Evidence

## Proven Governance State

Required current state:
- Engine C shared physics mapping status = `PARTIAL_BY_DESIGN`
- Engine D shared physics mapping status = `PARTIAL_BY_DESIGN`

Exact field status:
- `shared_physics_mapping_status` exact field: `NOT_FOUND`
- equivalent governed runtime semantics: `PROVEN`

Primary source:

```text
src/engines/engine_c/engine_c_runtime_support.py
  carriage_statuses=("local_math_only", "shared_scoring_physics_partial")

src/engines/engine_d/engine_d_runtime_support.py
  carriage_statuses=("local_math_only", "shared_scoring_physics_partial")
```

Doc proof:

```text
docs/audit/p0b_formula_extraction/addenda_scoring_risk_ml_carriage/P0B_ADD2_CARRIAGE_FIX_REPORT.md
  Engine C: not force-mapped
  Engine D: not force-mapped
```

## Engine C Shared-Physics Mapping Check

| Candidate local field | Shared field | Classification | Why |
|---|---|---|---|
| `false_breakout_risk` | `execution_fragility` | `DO_NOT_MAP_YET` | False-breakout setup risk is not the same as shared execution fragility. |
| `queue_pressure` | `execution_fragility` | `MAP_ONLY_IF_NORMALIZED_SCORE_EXISTS` | Queue pressure can matter for fragility, but no normalized semantic bridge is proven here. |
| raw `vpin` | `market_toxicity` | `MAP_ONLY_IF_NORMALIZED_SCORE_EXISTS` | Raw VPIN is used as local veto/context, not yet as shared toxicity metric. |
| raw `ofi` | `market_toxicity` | `DO_NOT_MAP_YET` | OFI continuation persistence is not equivalent to toxicity by source proof. |
| `false_breakout_risk` | `spread_regime_penalty` | `DO_NOT_MAP_YET` | Breakout failure risk is not a spread regime penalty. |

## Engine D Shared-Physics Mapping Check

| Candidate local field | Shared field | Classification | Why |
|---|---|---|---|
| `stale_signal_score` | `spread_regime_penalty` | `DO_NOT_MAP_YET` | Exact local field not found; no mapping proof exists. |
| `realized_vol_current` | `execution_fragility` | `DO_NOT_MAP_YET` | Realized-vol context is not the same as shared execution fragility. |
| `reformation_score` | `market_toxicity` | `DO_NOT_MAP_YET` | Reformation quality is a re-entry setup signal, not toxicity. |
| `anti_revenge_state` | `risk_penalty` | `DO_NOT_MAP_YET` | Anti-revenge is a local gating doctrine, not a generic additive risk penalty. |

## Risk-Rail Partiality

Source proof:

```text
src/engines/engine_c/engine_c_runtime_support.py
src/engines/engine_d/engine_d_runtime_support.py

RiskCandidate(
  carriage_statuses=("risk_micro_friction_missing", "not_carried_to_risk_rail"),
  carriage_reason_codes=(
    "RISK_MICRO_FRICTION_FIELD_MISSING",
    "RISK_INFO_STRESS_FIELD_MISSING",
    "RISK_REGIME_STATE_MISSING",
  ),
)
```

Interpretation:
- C/D do enter the common risk runtime
- C/D do not prove populated shared micro-friction inputs
- missing shared risk physics are explicit, not silently zeroed

## Conclusion

- Engine C = `PARTIAL_BY_DESIGN` proven by runtime carriage and ADD2 docs
- Engine D = `PARTIAL_BY_DESIGN` proven by runtime carriage and ADD2 docs
- exact `shared_physics_mapping_status` field remains `NOT_FOUND`
- no safe bridge to `execution_fragility`, `market_toxicity`, `spread_regime_penalty`, or `participation_penalty` is proven for C/D

