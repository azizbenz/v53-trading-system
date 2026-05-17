# Wave 6 Side / Halal / Spot-Only ML Regime Safety Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`

## 1. ML cannot create a trade

Observed seam:

- `ml_scoring_soft_penalty_hook.py` consumes an already-built scoring candidate
- `ml_confidence_enabler.py` consumes an existing `base_score` and engine side

No inspected ML seam constructs a new `SignalCandidate` or a new trade record.

Classification:

- `CONSUMER_FOUND` for score modulation
- no evidence of trade creation

## 2. ML cannot mutate side

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

Plain-text meaning:

- returned side is the normalized input engine side, not an ML-generated side

Test evidence:

- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
  - asserts `result.engine_side == Side.SELL`

## 3. ML cannot direct override by default

Same source file, exact code excerpt:

```python
if not allow_direct_ml_confidence_override:
    signal = signal.model_copy(
        update={
            "artifact_status": MlArtifactStatus.INVALID,
            "reason_codes": ("ML_DIRECT_OVERRIDE_FORBIDDEN",),
        }
    )
```

Meaning:

- direct ML confidence override is invalid unless explicitly opted into

## 4. Regime cannot create side

Source file: `src/complete_enablers/regime_detector_runtime.py`

Evidence:

- runtime outputs are limited to four non-directional keys
- `signal.shadow_only is True`
- tests assert `not hasattr(signal, "side")`

## 5. Directional refs are blocked

Source file: `src/complete_enablers/supplementary_refs_governance.py`

Evidence:

- forbidden directional keys include `buy_probability`, `sell_probability`, `side`, `long`, `short`, and `direct_trade_decision`

Consequences:

- directional ML or regime refs are rejected before becoming governed runtime inputs

## 6. Shorting, leverage, and fake-flat

Inspected ML/regime seams do not:

- create short side
- introduce leverage
- create a fake flat trade record
- turn `NO_TRADE` into an actual trade

This is evidence from inspected seams only, not a claim about uninspected files.

## 7. Tests

- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
  - preserves engine side
  - blocks direct override
  - rejects directional refs
- `tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py`
  - directional refs produce zero modulation, not a trade path
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
  - runtime is `NON_DIRECTIONAL_ONLY`
  - signal has no `side`
  - directional refs rejected

## 8. External-audit questions

- Is the research/debug-only `MlDirection` enum acceptable as long as it never mutates governed runtime side, or should it be renamed to reduce audit confusion?

