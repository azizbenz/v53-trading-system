# P0-B Addendum 2 - Scoring Backbone Field Audit

## Shared schema
`src/scoring_backbone/scoring_runtime_support.py::ScoringCandidateInput`

Relevant fields present in schema:
- `supplementary_refs`
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`
- `expected_cost`
- `expected_ce`
- `corr_penalty`
- `risk_penalty`

## Fields actually used by scoring runtime
`src/scoring_backbone/scoring_runtime_support.py`

Used in `build_physics_projection(...)`:
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`

Used in `build_scoring_soft_penalty_hook_input(...)`:
- `supplementary_refs`
- `expected_cost`
- `expected_ce`
- `corr_penalty`
- `risk_penalty`
- projected physics scores

Used in `ScoringRuntime.run_round(...)`:
- raw features and weights
- score penalties
- size penalties
- hard blockers
- ranking and selection

## Per-engine population of shared scoring fields

| Field | A | B | C | D | Verdict |
|---|---|---|---|---|---|
| `execution_fragility` | not populated | not populated | not populated | not populated | confirmed absent on shared field |
| `market_toxicity` | not populated | not populated | not populated | not populated | confirmed absent on shared field |
| `spread_regime_penalty` | not populated | not populated | not populated | not populated | confirmed absent on shared field |
| `participation_penalty` | not populated | not populated | not populated | not populated | confirmed absent on shared field |
| `supplementary_refs` | not populated | not populated | not populated | not populated | ML hook carriage not proven |
| `expected_cost` | populated | populated | populated | populated | carried |
| `expected_ce` | populated | populated | populated | populated | carried |
| `corr_penalty` | populated | populated | populated | populated | carried |
| `risk_penalty` | populated | populated | populated | populated | carried |

## Equivalent derived carriage

### Engine A
Shared scoring receives via `raw_features`:
- `fragility_score`
- `toxicity_score`
- `micro_friction_score`

These are weighted in `_build_engine_a_scoring_weights(...)`.

### Engine B
Shared scoring receives via `raw_features`:
- `fragility_score`
- `toxicity_score`
- `micro_friction_score`

These are weighted in `_build_engine_b_scoring_weights(...)`.

### Engine C
No equivalent derived shared physics carriage was proven for the named fields above.

### Engine D
No equivalent derived shared physics carriage was proven for the named fields above.

## No-op / false-green risk
- The shared scoring physics rail is live code.
- The named fields default to zeros.
- Because builders do not populate them, a reader can incorrectly believe shared friction physics is active when it is actually a silent no-op.

This is a real audit risk.

## Side safety
Scoring runtime does not invent side.
It scores candidates already emitted by engines.
No hidden short generation was proven in scoring.

## Backbone verdict
`PARTIAL_CARRIAGE`

Reason:
- schema is richer than live engine population
- A/B partially compensate through derived raw features
- C/D do not show the same compensation
- ML supplementary refs carriage into scoring hook is not proven
