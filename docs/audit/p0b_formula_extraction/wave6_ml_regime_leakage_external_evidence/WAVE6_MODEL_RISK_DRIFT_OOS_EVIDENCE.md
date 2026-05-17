# Wave 6 Model Risk / Drift / OOS Evidence

Status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `LIVE_SOURCE_NOT_PROVEN`, `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

## 1. ML artifact drift baseline

Source file: `src/interface_contracts/ml_model_artifact.py`

Evidence:

- `MlModelArtifact` carries `drift_baseline`
- drift baseline can include:
  - `forecast_mean`
  - `win_rate`
  - `ce_mean`
  - `feature_ks_reference_pvalue`
  - `sample_count`

This is an artifact-side place to store baseline comparison context, not a live runtime proof by itself.

## 2. ML risk registry

Source file: `src/meta_learning/model_risk_registry/registry.py`

Exact code excerpt:

```python
if not record.drift_snapshots:
    return MlModelRiskSignal(
        state=MlModelRiskState.INSUFFICIENT_DATA,
        promotion_block=True,
        reasons=("ML_DRIFT_EVIDENCE_REQUIRED",),
    )
...
if snapshot.feature_ks_pvalue is not None and snapshot.feature_ks_pvalue <= 0.05:
    return MlModelRiskSignal(
        state=MlModelRiskState.PROMOTION_BLOCK,
        pause_signal=True,
        promotion_block=True,
        reasons=("ML_FEATURE_DRIFT_BLOCK",),
    )
```

Implemented rule:

- no drift evidence -> insufficient data and promotion block
- low feature KS p-value -> promotion block
- high shadow diff -> promotion block
- high live diff, large win-rate degradation, or large CE degradation -> pause

## 3. Promotion gate thresholds

Source file: `src/complete_enablers/ml_model_promotion_gate.py`

Evidence:

- blocks when `backtest_sharpe <= 0`
- blocks when `ks_test_features_pvalue` is missing or `<= 0.05`
- blocks when `shadow_diff_pct` is missing or `>= 0.1`
- blocks when `oos_sharpe / backtest_sharpe < 0.80`
- blocks when artifact hash is invalid

Important ambiguity:

- the gate also starts with `blocking_reasons = ["ml.formalism.unresolved"]`
- in the inspected code and tests, this means promotion is intentionally fail-closed

Classification:

- `AMBIGUITY_FOUND`
- `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`

## 4. Local Lab final audit for ML

Source file: `src/local_replay_runtime/ml_final_audit_report.py`

Evidence:

- compares uploaded VPS artifact vs Local Lab recommendation
- checks upload manifest hash
- checks feature-hash compatibility
- still blocks on `ml.formalism.unresolved`

Meaning:

- artifact identity comparison exists
- doctrinal green promotion does not yet exist

## 5. Regime shadow diagnosis

Source file: `src/local_replay_runtime/regime_detector_shadow_audit_diagnosis.py`

Exact code excerpt:

```python
if bundle.schema_match_status == RegimeDetectorShadowAuditSchemaMatchStatus.MISMATCHED:
    blocking_reasons.append("REGIME_DETECTOR_SCHEMA_MISMATCH")
...
if resolved_shadow_diff_pct is not None and resolved_shadow_diff_pct >= 0.1:
    blocking_reasons.append("REGIME_DETECTOR_SHADOW_DIFF_PCT_HIGH")
```

Evidence of monitored fields:

- schema match status
- artifact hash
- feature hash at runtime
- feature-set version
- pair in universe
- `shadow_diff_pct`
- observation coverage ratio
- stale runtime count
- insufficient-data count

## 6. Regime final audit

Source file: `src/local_replay_runtime/regime_detector_final_audit_report.py`

Evidence:

- joins profile-comparison report with VPS shadow diagnosis
- missing shadow bundle yields partial/blocked audit, not ready
- blocked diagnosis yields blocked final report
- uploaded profile differing from lab default yields partial, not ready

## 7. Tests

- `tests/test_meta_learning/test_model_risk_registry.py`
  - registry stores artifact identity and drift metadata
  - synthetic drift produces `PROMOTION_BLOCK` or `PAUSE`
  - missing drift data yields `INSUFFICIENT_DATA` and promotion block
- `tests/test_complete_enablers/test_ml_model_promotion_gate.py`
  - asserts `ml.formalism.unresolved` block
  - asserts missing KS and shadow metrics block
  - asserts OOS/backtest Sharpe ratio block
- `tests/test_local_replay_runtime/test_ml_final_audit_report.py`
  - final audit remains blocked even when artifact matches recommendation
- `tests/test_local_replay_runtime/test_regime_detector_shadow_audit_diagnosis.py`
  - matching bundle -> healthy
  - schema/hash/drift/profile/pair mismatches -> blocked
  - low coverage, no predictions, stale runtime -> caution

## 8. Gaps

- live drift source provenance was not proven in inspected VPS/runtime code
- no evidence was found that an ML model can move past formalism-blocked promotion into governed live readiness
- OOS and drift metrics exist, but the end-to-end live governance loop remains partial

## 9. External-audit questions

- Is the permanent `ml.formalism.unresolved` block intentional for the current release line?
- Which runtime or monitoring process is expected to populate live drift snapshots into the registry?
- Are regime shadow diagnostics sufficient for future promotion, or must a separate live-regime governance layer exist?

