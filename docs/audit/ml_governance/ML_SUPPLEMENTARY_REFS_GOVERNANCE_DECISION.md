# ML Supplementary Refs Governance Decision

## Decision
- `supplementary_refs` remains a transport of governed artifact references only
- wire format remains `tuple[str, ...]`
- ML remains non-sovereign
- ML may modulate confidence or penalty only
- ML may not create trades
- ML may not mutate side
- ML may not introduce shorting or leverage

## Allowed transport intent
- `ml_model_artifact.summary.json`
- transport artifact refs associated with that summary
- non-directional regime/runtime/model-risk references already governed by existing artifact loaders

## Forbidden directional keys
- `direction_up_300s_fee_safe`
- `buy_probability`
- `sell_probability`
- `market_will_go_up`
- `side`
- `long`
- `short`
- `label`
- `direct_trade_decision`

## Runtime behavior
- missing refs:
  - neutral
  - `ML_REFS_MISSING_NEUTRAL`
- transport present but unusable:
  - explicit
  - `ML_REFS_NOT_AVAILABLE`
- stale artifact:
  - safe degrade
  - `ML_ARTIFACT_STALE`
- hash mismatch:
  - disable ML contribution
  - `ML_ARTIFACT_HASH_MISMATCH`
- direct override request:
  - forbidden
  - `ML_DIRECT_OVERRIDE_FORBIDDEN`
- directional ref detected:
  - reject
  - `ML_DIRECTIONAL_REF_FORBIDDEN`

## Scope of this patch
- carrier support added
- validation added
- neutral fallback made explicit
- no new ML payload invented
- no directional label accepted
- no live trade direction created
