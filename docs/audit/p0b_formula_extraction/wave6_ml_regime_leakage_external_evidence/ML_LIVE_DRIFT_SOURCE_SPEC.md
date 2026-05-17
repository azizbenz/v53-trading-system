# ML Live Drift Source Spec

Date: 2026-04-30
Status: `LIVE_DRIFT_SOURCE_NOT_PROVEN`

## Current finding

`MlModelRiskRegistry` and drift signals exist, but no concrete governed live producer was proven for drift snapshots.

## Required future producers

The future drift pipeline must provide typed `MlModelDriftSnapshot` facts for:

- replay stage
- shadow stage
- live stage

Required producer responsibilities:

- compute `feature_ks_pvalue`
- compute `shadow_diff_pct`
- compute `live_diff_pct`
- compute `win_rate_delta`
- compute `ce_delta`
- bind each snapshot to the exact `artifact_id`
- bind each snapshot to the exact `feature_hash`

## Required data sources

- feature KS p-value source:
  governed comparison between current runtime feature distribution and artifact baseline
- shadow/live diff source:
  governed comparison of runtime vs expected model behavior over matched windows
- win-rate degradation source:
  governed realized or shadow-evaluated decision outcomes over a review window
- CE degradation source:
  governed expected/realized economics comparison over a review window

## Registry ingestion contract

Target sink:

- `meta_learning.model_risk_registry.MlModelRiskRegistry`

Required ingestion keys:

- `artifact_id`
- `feature_hash`
- `stage`
- `created_at`

Required invariant:

- a drift snapshot must never be attached to the wrong artifact hash

## Runtime rule

If no live drift source exists:

- model risk signal remains `INSUFFICIENT_DATA`
- promotion remains blocked
- no live-ready claim is allowed for ML

## Promotion implication

`ml.formalism.unresolved` still blocks promotion independently.

Even if that blocker is lifted later, live drift-source proof is still required before governed ML promotion.

