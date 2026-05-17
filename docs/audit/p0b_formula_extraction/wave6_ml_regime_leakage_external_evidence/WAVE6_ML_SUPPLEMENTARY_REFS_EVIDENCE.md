# Wave 6 ML Supplementary Refs Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`, `ARTIFACT_SOURCE_NOT_PROVEN`

## 1. Governance seam

Source file: `src/complete_enablers/supplementary_refs_governance.py`

Exact code excerpt:

```python
FORBIDDEN_DIRECTIONAL_SUPPLEMENTARY_REF_KEYS: tuple[str, ...] = (
    "direction_up_300s_fee_safe",
    "buy_probability",
    "sell_probability",
    "market_will_go_up",
    "side",
    "long",
    "short",
    "label",
    "direct_trade_decision",
)
```

Decision rule in plain text:

- Any supplementary ref whose filename stem or JSON-like payload exposes one of the forbidden directional keys is rejected.
- Rejection is explicit, not silent.

Directional-key rejection behavior:

- ML path emits `ML_DIRECTIONAL_REF_FORBIDDEN`
- Regime path emits `REGIME_DIRECTIONAL_REF_FORBIDDEN`

Allowed outputs:

- governed transport refs
- summary refs
- non-directional audit metadata

Forbidden outputs:

- directional labels
- buy/sell probabilities
- side override fields
- direct trade decisions

## 2. Packaging and transport seam

Source files:

- `src/backtest_artifact_import/ml_model_transport.py`
- `src/backtest_artifact_import/regime_detector_transport.py`

Exact code excerpt:

```python
def attach_ml_model_transport_refs(
    bundle: ArtifactPayloadRefBundle,
    *,
    export_dir: str | Path,
    artifact: MlModelArtifact,
) -> ArtifactPayloadRefBundle:
    packaged = package_ml_model_for_transport(export_dir=export_dir, artifact=artifact)
    return bundle.model_copy(
        update={
            "supplementary_refs": bundle.supplementary_refs
            + (
                str(packaged.transport_artifact_path.resolve()),
                str(packaged.summary_path.resolve()),
            )
        }
    )
```

Decision rule in plain text:

- The Local Lab export loop materializes typed transport artifacts plus summary sidecars, then appends those refs into `supplementary_refs`.

Artifact source:

- Local Lab export directory via governed transport packagers.

Artifact hash / schema / version behavior:

- packaging reloads the JSON through typed contracts
- packaging raises if the packaged artifact hash drifts from the source artifact

## 3. ML runtime load from supplementary refs

Source file: `src/complete_enablers/ml_confidence_enabler.py`

Exact code excerpt:

```python
if not supplementary_refs:
    return MlConfidenceSignal(
        ml_confidence=0.5,
        ml_direction=MlDirection.FLAT,
        artifact_status=MlArtifactStatus.MISSING,
        reason_codes=("ML_REFS_MISSING_NEUTRAL",),
    )
...
if selection.status == MlRuntimeArtifactLoadStatus.HASH_MISMATCH:
    return MlConfidenceSignal(
        ml_confidence=0.5,
        ml_direction=MlDirection.FLAT,
        artifact_status=MlArtifactStatus.INVALID,
        reason_codes=("ML_ARTIFACT_HASH_MISMATCH",),
    )
```

Decision rule in plain text:

- Empty refs are explicit neutral, not active.
- Hash mismatch invalidates the artifact and returns neutral confidence.
- Stale refs return neutral confidence with stale status.

Missing behavior:

- `ML_REFS_MISSING_NEUTRAL`
- `ML_REFS_NOT_AVAILABLE:<loader_status>` for summary/transport availability failures

Stale behavior:

- `ML_ARTIFACT_STALE`

Hash mismatch behavior:

- `ML_ARTIFACT_HASH_MISMATCH`

## 4. Consumer path

Source file: `src/scoring_backbone/scoring_runtime_support.py`

Exact code excerpt:

```python
def build_scoring_soft_penalty_hook_input(
    candidate: ScoringCandidateInput,
) -> MlScoringSoftPenaltyHookInput:
    return MlScoringSoftPenaltyHookInput(
        base_score=candidate.score,
        feature_values=candidate.feature_values,
        supplementary_refs=candidate.supplementary_refs,
    )
```

Consumer path classification:

- scoring: `CONSUMER_FOUND`
- risk: `CONSUMER_NOT_FOUND` as a direct supplementary-refs reader in inspected risk rails
- execution: `CONSUMER_NOT_FOUND`
- cockpit: indirect through scoring/risk/readiness views
- Local Lab only: transport packaging and training/export preparation

Can refs mutate side?

- No proof found.
- The inspected scoring application preserves `engine_side` unchanged.

## 5. Missing/stale/hash behavior at cockpit/readiness layer

Source files:

- `src/scoring_backbone/scoring_runtime_support.py`
- `src/cockpit/state_feature_bridge.py`

Exact code excerpt:

```python
if not candidate.supplementary_refs:
    carriage_statuses.append("ml_refs_missing_neutral")
    carriage_reason_codes.append("ML_REFS_MISSING_NEUTRAL")
```

Plain-text consequence:

- Missing refs are surfaced into explainability and then into cockpit readiness; they are not silently treated as active ML.

## 6. Tests

- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
  - empty refs produce `ML_REFS_MISSING_NEUTRAL`
  - hash mismatch produces `ML_ARTIFACT_HASH_MISMATCH`
  - directional refs produce `ML_DIRECTIONAL_REF_FORBIDDEN`
- `tests/test_complete_enablers/test_ml_runtime_artifact_loader.py`
  - covers `MISSING_SUPPLEMENTARY_REFS`, `SUMMARY_NOT_FOUND`, `HASH_MISMATCH`, and `STALE`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
  - asserts `ml_refs_missing_neutral` carriage status and `ML_REFS_MISSING_NEUTRAL` reason code

## 7. False-green risk and audit questions

False-green risk:

- artifact transport exists, but live non-empty upstream source of `supplementary_refs` is not proven in the inspected runtime rails

External-audit questions:

- Which live/shadow component is expected to populate non-empty governed `supplementary_refs` in production?
- Should stale refs hard-block scoring readiness rather than degrade to neutral?

