# P0-B Addendum 2 - ML Supplementary Refs Audit

## Shared producer/consumer path

Shared scoring hook path:
- `ScoringCandidateInput.supplementary_refs`
- `build_scoring_soft_penalty_hook_input(...)`
- `ml_scoring_soft_penalty_hook`
- `MlConfidenceEnabler.score_candidate_from_supplementary_refs(...)`

Artifact loaders:
- `complete_enablers/ml_runtime_artifact_loader.py`
- `complete_enablers/regime_detector_runtime_loader.py`

## Per-engine packaging status

| Engine | supplementary_refs packaged into scoring candidate | Verdict |
|---|---|---|
| A | no proven packaging | not proven |
| B | no proven packaging | not proven |
| C | no proven packaging | not proven |
| D | no proven packaging | not proven |

## Generic hook safety
What is proven:
- missing refs degrade to neutral / missing / invalid states
- stale artifact degrades to stale state with neutral confidence
- direct ML confidence override is blocked by default
- bounded ML fusion does not mutate canonical engine side

Proof points:
- `MlConfidenceEnabler.apply_to_engine_score(...)`
- `allow_direct_ml_confidence_override: bool = False`
- `ML_DIRECT_OVERRIDE_FORBIDDEN`

## Strategic verdict
`GENERIC_HOOK_PROVEN_ENGINE_LIVE_PACKAGING_NOT_PROVEN`

## Operational interpretation
- Backtest / lab / artifact paths clearly know about supplementary transport concepts.
- Current live engine carriage into the shared scoring hook is not proven.
- This is safe from a side-safety standpoint.
- It is incomplete from a governed shared-ML carriage standpoint.
