# Wave 6 ML Artifact Governance Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`, `STALE_ARTIFACT_RISK`

## 1. Typed artifact schema

Source file: `src/interface_contracts/ml_model_artifact.py`

Exact code excerpt:

```python
class MlModelArtifact(BaseModel, frozen=True):
    schema_version: str = "ml_model_artifact.v1"
    model_family: str = Field(default="lightgbm", min_length=1)
    feature_names: tuple[str, ...]
    feature_hash: str
    pair_universe: tuple[str, ...]
    train_window: MlModelWindow
    validation_window: MlModelWindow
    oos_sharpe: float
    backtest_sharpe: float
    ks_test_features_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_diff_pct: float | None = Field(default=None, ge=0.0)
    promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    training_seed: int
    created_at: datetime
    calibration_version: str
    dataset_hash: str
    ...
    stale_after: datetime | None = None
```

Artifact fields evidenced:

- schema version
- feature hash
- pair universe
- train/validation windows
- OOS and backtest Sharpe
- KS-based feature drift indicator
- shadow diff metric
- promotion state
- calibration version
- dataset hash
- stale horizon

## 2. Hash enforcement

Same source file, exact code excerpt:

```python
@model_validator(mode="after")
def _validate_hashes(self) -> "MlModelArtifact":
    if self.artifact_hash != self.artifact_hash_sha256():
        raise ValueError("artifact_hash must match serialized content hash")
    if self.stale_after is not None and self.stale_after < self.created_at:
        raise ValueError("stale_after must be on or after created_at")
    return self
```

Plain-text behavior:

- serialized content hash is validated at contract level
- stale horizon cannot predate creation time

## 3. Runtime loader governance

Source file: `src/complete_enablers/ml_runtime_artifact_loader.py`

Exact code excerpt:

```python
class MlRuntimeArtifactLoadStatus(StrEnum):
    MISSING_SUPPLEMENTARY_REFS = "missing_supplementary_refs"
    SUMMARY_NOT_FOUND = "summary_not_found"
    SUMMARY_INVALID = "summary_invalid"
    TRANSPORT_ARTIFACT_NOT_DECLARED = "transport_artifact_not_declared"
    TRANSPORT_ARTIFACT_UNREADABLE = "transport_artifact_unreadable"
    TRANSPORT_ARTIFACT_INVALID = "transport_artifact_invalid"
    HASH_MISMATCH = "hash_mismatch"
    STALE = "stale"
    LOADED = "loaded"
```

Loader decision rules:

- missing refs -> not ready
- summary missing or invalid -> not ready
- transport artifact not declared/unreadable/invalid -> not ready
- hash mismatch -> not ready
- stale artifact -> not ready
- only `LOADED` is artifact-ready

Hash mismatch behavior:

```python
if artifact.artifact_hash != summary.artifact_hash:
    return MlRuntimeArtifactSelection(
        status=MlRuntimeArtifactLoadStatus.HASH_MISMATCH,
        artifact_ready=False,
        summary=summary,
    )
```

Stale behavior:

```python
if artifact.stale_after is not None and artifact.stale_after <= as_of:
    return MlRuntimeArtifactSelection(
        status=MlRuntimeArtifactLoadStatus.STALE,
        artifact_ready=False,
        artifact=artifact,
        summary=summary,
    )
```

## 4. Transport summary sidecar

Source file: `src/backtest_artifact_import/ml_model_transport.py`

Evidence:

- summary sidecar filename: `ml_model_artifact.summary.json`
- sidecar carries artifact hash, schema version, calibration version, dataset hash, feature hash, transport path reference
- package loop reloads the transport artifact and compares hashes before returning packaged refs

## 5. Promotion and final-audit rails

### 5.1 Promotion gate

Source file: `src/complete_enablers/ml_model_promotion_gate.py`

Exact code excerpt:

```python
blocking_reasons: list[str] = ["ml.formalism.unresolved"]
```

Further gates check:

- model family must be `lightgbm`
- `backtest_sharpe > 0`
- `ks_test_features_pvalue` required and `> 0.05`
- `shadow_diff_pct` required and `< 0.1`
- `oos_sharpe / backtest_sharpe >= 0.80`
- artifact hash valid

Classification:

- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`
- `AMBIGUITY_FOUND`

Reason:

- current gate is intentionally fail-closed because `ml.formalism.unresolved` is always present in tests and source

### 5.2 Final audit report

Source file: `src/local_replay_runtime/ml_final_audit_report.py`

Exact code excerpt:

```python
def _ml_formalism_blocking_reasons() -> tuple[str, ...]:
    return ("ml.formalism.unresolved",)
```

Plain-text behavior:

- even when uploaded and recommended artifacts match, final audit remains blocked until formalism is explicitly accepted

## 6. Cockpit/runtime behavior

No dedicated inspected cockpit page claimed ML live-readiness.

Observed behavior from connected rails:

- missing or stale ML artifacts degrade scoring inputs to neutral
- no inspected cockpit surface promotes missing/stale ML artifact to green runtime proof

## 7. Tests

- `tests/test_complete_enablers/test_ml_runtime_artifact_loader.py`
  - covers `MISSING_SUPPLEMENTARY_REFS`, `SUMMARY_NOT_FOUND`, `HASH_MISMATCH`, `STALE`, and `artifact_ready`
- `tests/test_backtest_artifact_import/test_ml_model_transport.py`
  - covers summary projection, packaging, and governed upload request shape
- `tests/test_complete_enablers/test_ml_model_promotion_gate.py`
  - asserts block on `ml.formalism.unresolved`
  - asserts missing metrics remain blocked
  - asserts OOS ratio and KS/shadow thresholds block as expected
- `tests/test_local_replay_runtime/test_ml_final_audit_report.py`
  - asserts final report stays blocked even when artifact matches recommendation

## 8. External-audit questions

- Is `ml.formalism.unresolved` intended to block all promotion indefinitely until a later governance wave?
- What live runtime source is supposed to provide the active ML artifact and its freshness proof on VPS?
- Should stale ML artifacts hard-block even scoring-time neutral use, or is neutral degradation the intended compatibility doctrine?

