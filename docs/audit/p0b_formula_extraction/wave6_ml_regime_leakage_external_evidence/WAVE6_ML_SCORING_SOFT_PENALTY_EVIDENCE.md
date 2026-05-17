# Wave 6 ML Scoring Soft Penalty Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`

## 1. Hook seam

Source file: `src/complete_enablers/ml_scoring_soft_penalty_hook.py`

Exact code excerpt:

```python
multiplier_delta = confidence_to_multiplier_delta(
    ml_confidence=signal.ml_confidence,
    alpha=validate_alpha(self._config.alpha),
)
return ScoringSoftPenaltyLayerOutcome(
    raw_score_multiplier_delta=multiplier_delta,
    reason_codes=(*signal.reason_codes, "ML_SCORE_MODULATION_ACTIVE"),
    detail=(
        "ml non-positive scoring modulation applied for "
        f"{hook_input.pair}/{hook_input.engine_id}"
    ),
)
```

Implemented decision rule:

- If the ML artifact is active, compute a multiplier delta from `ml_confidence`.
- If the artifact is missing, stale, invalid, or rejected, return zero adjustment and carry reason codes.

Input fields:

- `feature_values`
- `supplementary_refs`
- config `alpha`

Output fields:

- `raw_score_multiplier_delta`
- `reason_codes`

## 2. Fusion formula and bounds

Source file: `src/complete_enablers/ml_fusion.py`

Exact code excerpt:

```python
def confidence_to_multiplier_delta(*, ml_confidence: float, alpha: float) -> float:
    normalized_alpha = validate_alpha(alpha)
    normalized_confidence = _clip_ml_confidence(ml_confidence)
    return min(
        0.0,
        normalized_alpha * (normalized_confidence - 0.5),
    )
...
fused_score = base_score * (1 + multiplier_delta)
```

Implemented formula in plain text:

- `multiplier_delta = min(0, clamp(alpha, 0, 0.5) * (clamp(ml_confidence, 0, 1) - 0.5))`
- `fused_score = base_score * (1 + multiplier_delta)`

Bounds:

- `alpha` is clipped into `[0.0, 0.5]`
- `ml_confidence` is clipped into `[0.0, 1.0]`
- therefore `multiplier_delta` is bounded into `[-0.25, 0.0]`

## 3. Non-positive behavior

Decision rule:

- if `ml_confidence < 0.5`, score decreases
- if `ml_confidence == 0.5`, score is unchanged
- if `ml_confidence > 0.5`, score is unchanged
- score uplift is not available in the current release

## 4. Candidate creation and acceptance behavior

Consumer path:

- scoring: `CONSUMER_FOUND`
- risk: `CONSUMER_NOT_FOUND` as direct hook consumer
- execution: `CONSUMER_NOT_FOUND`

Can ML create a candidate?

- No evidence found.
- The hook consumes an existing `ScoringCandidateInput`.

Can ML convert no candidate into candidate?

- No evidence found in inspected hooks.

Can ML mutate side?

- No.

Source file: `src/complete_enablers/ml_confidence_enabler.py`

Exact code excerpt:

```python
return MlScoreApplication(
    engine_side=normalized_side,
    base_score=base_score,
    fused_score=fusion.fused_score,
    ...
)
```

The same file also blocks direct override by default:

```python
if not allow_direct_ml_confidence_override:
    signal = signal.model_copy(
        update={
            "artifact_status": MlArtifactStatus.INVALID,
            "reason_codes": ("ML_DIRECT_OVERRIDE_FORBIDDEN",),
        }
    )
```

## 5. Tests

- `tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py`
  - asserts exact zero delta for high-confidence active artifact path
  - asserts exact zero delta for neutral-confidence path
  - asserts exact `-0.12` delta for low-confidence path
  - asserts `ML_SCORE_MODULATION_ACTIVE`
  - asserts zero delta when artifact is missing or rejected
  - asserts zero delta for directional refs
- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
  - asserts `engine_side == Side.SELL`
  - asserts `fusion.multiplier_delta == 0.0` and unchanged fused score on high-confidence path
  - asserts `ML_DIRECT_OVERRIDE_FORBIDDEN`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
  - asserts high-confidence governed refs stay neutral without uplift
  - asserts stale refs are neutral, not active
  - asserts hash-mismatch refs are disabled, not active

## 6. External-audit questions

- Should positive ML score modulation remain `FUTURE_RESERVED` until separate OOS and governance proof exists?
- Should operator-facing language continue to expose the compatibility term "soft penalty", or should it prefer "non-positive modulation" everywhere except backward-compatible hook ids?
