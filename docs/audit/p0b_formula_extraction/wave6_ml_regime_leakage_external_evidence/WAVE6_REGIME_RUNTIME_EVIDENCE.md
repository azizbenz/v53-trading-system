# Wave 6 Regime Runtime Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `NON_DIRECTIONAL_RUNTIME`, `CONSUMER_NOT_FOUND`

## 1. Allowed runtime outputs

Source file: `src/complete_enablers/regime_detector_runtime.py`

Exact code excerpt:

```python
RUNTIME_REGIME_OUTPUTS: tuple[str, ...] = (
    "regime_transition_risk",
    "regime_stability_score",
    "market_toxicity_score",
    "expected_duration_bucket",
)
RUNTIME_REGIME_OUTPUT_MODE = "NON_DIRECTIONAL_ONLY"
```

Allowed outputs:

- `regime_transition_risk`
- `regime_stability_score`
- `market_toxicity_score`
- `expected_duration_bucket`

Forbidden outputs:

- `direction_up_300s_fee_safe`
- `buy_probability`
- `sell_probability`
- `market_will_go_up`
- `side`
- `long`
- `short`
- `target_return`
- `future_return`
- `label`
- `direct_trade_decision`

## 2. Runtime signal properties

Same source file, exact code excerpt:

```python
class RegimeDetectorSignal(BaseModel, frozen=True):
    status: RegimeDetectorSignalStatus = RegimeDetectorSignalStatus.NEUTRAL
    ...
    @property
    def shadow_only(self) -> bool:
        return True
```

Plain-text interpretation:

- runtime regime output is explicitly shadow-only
- no side or directional trade command is part of the signal

## 3. Missing/stale/hash behavior

Source file: `src/complete_enablers/regime_detector_runtime_loader.py`

Exact code excerpt:

```python
class RegimeDetectorArtifactLoadStatus(StrEnum):
    MISSING_SUPPLEMENTARY_REFS = "missing_supplementary_refs"
    SUMMARY_NOT_FOUND = "summary_not_found"
    SUMMARY_INVALID = "summary_invalid"
    TRANSPORT_ARTIFACT_NOT_DECLARED = "transport_artifact_not_declared"
    TRANSPORT_ARTIFACT_UNREADABLE = "transport_artifact_unreadable"
    TRANSPORT_ARTIFACT_INVALID = "transport_artifact_invalid"
    HASH_MISMATCH = "hash_mismatch"
    FEATURE_SET_VERSION_MISMATCH = "feature_set_version_mismatch"
    FEATURE_HASH_MISMATCH = "feature_hash_mismatch"
    STALE = "stale"
    SHADOW_EVIDENCE_MISSING = "shadow_evidence_missing"
    LOADED = "loaded"
```

Decision rule in plain text:

- missing, invalid, mismatched, stale, or shadow-evidence-missing artifacts are not runtime-ready
- only `LOADED` is artifact-ready

Additional guard:

- if promotion state is micro-live or live candidate but `shadow_metrics` is empty, loader returns `SHADOW_EVIDENCE_MISSING`

## 4. Evaluation behavior

Source file: `src/complete_enablers/regime_detector_runtime.py`

Exact code excerpt:

```python
if artifact is None:
    return RegimeDetectorSignal(
        status=RegimeDetectorSignalStatus.NEUTRAL,
        reason_codes=("REGIME_DETECTOR_ARTIFACT_MISSING",),
    )
...
except KeyError:
    return RegimeDetectorSignal(
        status=RegimeDetectorSignalStatus.INVALID_ARTIFACT,
        reason_codes=("REGIME_DETECTOR_FEATURE_SCHEMA_MISMATCH",),
    )
```

Decision rule:

- missing artifact -> neutral, not active
- insufficient features -> insufficient data
- pair unsupported -> invalid artifact
- feature schema mismatch -> invalid artifact
- success -> active shadow signal only

Can regime create side?

- No evidence found.
- Tests assert there is no `side` attribute.

## 5. Consumer path

Inspected direct consumers:

- scoring: `CONSUMER_NOT_FOUND` as direct runtime regime output consumer in the inspected Wave 6 rail
- risk: `CONSUMER_NOT_FOUND`
- execution: `CONSUMER_NOT_FOUND`
- cockpit: indirect via artifact/readiness documentation and feature bridge style states
- Local Lab only: dataset building, training, profile comparison, shadow audit diagnosis

This does not prove absence everywhere; it proves no direct consumer was found in the inspected paths.

## 6. Tests

- `tests/test_complete_enablers/test_regime_detector_runtime.py`
  - asserts `signal.shadow_only is True`
  - asserts `not hasattr(signal, "side")`
  - asserts directional refs are rejected with `REGIME_DIRECTIONAL_REF_FORBIDDEN`
  - asserts `RUNTIME_REGIME_OUTPUT_MODE == "NON_DIRECTIONAL_ONLY"`
  - asserts runtime outputs equal the four allowed keys
  - asserts stale, feature-set-version mismatch, and feature-hash mismatch reject readiness
- `tests/test_backtest_artifact_import/test_regime_detector_transport.py`
  - covers summary projection and governed packaging

## 7. External-audit questions

- Is regime runtime intended to remain shadow-only indefinitely, or is there a future governed promotion path for non-directional runtime use?
- If regime runtime eventually feeds scoring/risk, which direct consumer must prove that governance boundary?

