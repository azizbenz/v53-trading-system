# Wave 6 Test Coverage Evidence

Status: updated after pytest execution on 2026-04-30.

## Test files inspected

- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
- `tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py`
- `tests/test_complete_enablers/test_ml_runtime_artifact_loader.py`
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
- `tests/test_complete_enablers/test_ml_model_promotion_gate.py`
- `tests/test_local_replay_runtime/test_regime_detector_dataset_builder.py`
- `tests/test_local_replay_runtime/test_ml_backtest_projection.py`
- `tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py`
- `tests/test_local_replay_runtime/test_regime_detector_shadow_audit_diagnosis.py`
- `tests/test_local_replay_runtime/test_ml_final_audit_report.py`
- `tests/test_backtest_artifact_import/test_ml_model_transport.py`
- `tests/test_backtest_artifact_import/test_regime_detector_transport.py`
- `tests/test_calibration_methods/test_walkforward.py`
- `tests/test_calibration_methods/test_ml_trainer.py`
- `tests/test_calibration_methods/test_regime_detector_trainer.py`
- `tests/test_meta_learning/test_model_risk_registry.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_system_flow.py`

## Exact high-signal assertions found before execution

- ML confidence preserves engine side and blocks direct override.
- Empty supplementary refs become `ML_REFS_MISSING_NEUTRAL`.
- ML artifact hash mismatch becomes `ML_ARTIFACT_HASH_MISMATCH`.
- Directional refs are rejected for both ML and regime runtime seams.
- Regime runtime is `NON_DIRECTIONAL_ONLY`, `shadow_only`, and has no `side`.
- Dataset builder emits future labels only in Local Lab and fails closed without future windows.
- Walk-forward plan enforces embargo and purged training rows.
- ML trainer and regime trainer are deterministic and time-ordered.
- Model-risk registry blocks on missing drift evidence and synthetic drift.
- Feature bridge keeps runtime consumption at `NOT_PROVEN` without direct proof.
- Replay metrics keep CE expected-only and keep incomplete economics out of green.
- System flow keeps partial cost, artifact-only, small-capital-not-proven, and true-drawdown-not-proven states out of green.

## Missing or thin test areas

- direct live non-empty `supplementary_refs` source on VPS was not proven
- direct scoring/risk/execution consumer path for regime runtime outputs was not proven
- unified end-to-end anti-leakage governance artifact was not found
- live drift snapshot ingestion path was not proven

## Validation commands and results

Initial broad sandboxed attempt:

```text
rtk pytest -q tests/test_complete_enablers tests/test_scoring_backbone tests/test_risk_backbone tests/test_local_replay_runtime tests/test_backtest_artifact_import tests/test_calibration_methods tests/cockpit --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_evidence
```

Result:

- environment failure during pytest session finish:
  - `PermissionError: [WinError 5] Accès refusé: 'E:\claude  v5.3\v53_trading_system\.test_tmp\pytest_wave6_evidence'`
- RTK wrapper also reported `No tests collected`, so that run is not the authoritative logic result.

Focused sandboxed logic run:

```text
python -m pytest -q tests/test_complete_enablers/test_ml_confidence_enabler.py tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py tests/test_complete_enablers/test_ml_runtime_artifact_loader.py tests/test_complete_enablers/test_regime_detector_runtime.py tests/test_complete_enablers/test_ml_model_promotion_gate.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_complete_enablers
```

Result:

- `33 passed`

Broader targeted sandboxed run before escalation:

```text
python -m pytest -q tests/test_local_replay_runtime/test_regime_detector_dataset_builder.py tests/test_local_replay_runtime/test_ml_backtest_projection.py tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py tests/test_local_replay_runtime/test_regime_detector_shadow_audit_diagnosis.py tests/test_local_replay_runtime/test_ml_final_audit_report.py tests/test_backtest_artifact_import/test_ml_model_transport.py tests/test_backtest_artifact_import/test_regime_detector_transport.py tests/test_calibration_methods/test_walkforward.py tests/test_calibration_methods/test_ml_trainer.py tests/test_calibration_methods/test_regime_detector_trainer.py tests/test_meta_learning/test_model_risk_registry.py tests/test_scoring_backbone/test_scoring_runtime.py tests/test_risk_backbone/test_risk_runtime.py tests/cockpit/test_state_feature_bridge.py tests/cockpit/test_state_replay_metrics.py tests/cockpit/test_state_system_flow.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_targeted
```

Result before escalation:

- most tests executed and passed
- sandboxed environment hit:
  - pytest cleanup `PermissionError` on `.test_tmp\pytest_wave6_targeted`
  - one file-level setup error in `tests/test_risk_backbone/test_risk_runtime.py` when creating `build\pytest-risk-runtime-daily-breaker\...`

Escalated targeted rerun:

```text
python -m pytest -q tests/test_local_replay_runtime/test_regime_detector_dataset_builder.py tests/test_local_replay_runtime/test_ml_backtest_projection.py tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py tests/test_local_replay_runtime/test_regime_detector_shadow_audit_diagnosis.py tests/test_local_replay_runtime/test_ml_final_audit_report.py tests/test_backtest_artifact_import/test_ml_model_transport.py tests/test_backtest_artifact_import/test_regime_detector_transport.py tests/test_calibration_methods/test_walkforward.py tests/test_calibration_methods/test_ml_trainer.py tests/test_calibration_methods/test_regime_detector_trainer.py tests/test_meta_learning/test_model_risk_registry.py tests/test_scoring_backbone/test_scoring_runtime.py tests/test_risk_backbone/test_risk_runtime.py tests/cockpit/test_state_feature_bridge.py tests/cockpit/test_state_replay_metrics.py tests/cockpit/test_state_system_flow.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_targeted_escalated
```

Result:

- `94 passed`

Escalated broad rerun:

```text
python -m pytest -q tests/test_complete_enablers tests/test_scoring_backbone tests/test_risk_backbone tests/test_local_replay_runtime tests/test_backtest_artifact_import tests/test_calibration_methods tests/cockpit --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_broad_escalated
```

Result:

- `937 passed`

Wave 6 doctrine-focused reruns after the stale-artifact test helper fix:

```text
python -m pytest -q tests/test_complete_enablers/test_ml_fusion.py tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py tests/test_complete_enablers/test_ml_confidence_enabler.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_ml_core_rerun
python -m pytest -q tests/test_scoring_backbone/test_scoring_runtime.py --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_scoring_runtime_rerun2
python -m pytest -q tests/test_complete_enablers tests/test_scoring_backbone tests/test_risk_backbone tests/test_local_replay_runtime tests/test_backtest_artifact_import tests/test_calibration_methods tests/cockpit --tb=short --disable-warnings --basetemp=.test_tmp\pytest_wave6_doctrine_escalated
```

Results:

- ML doctrine core band: `23 passed`
- scoring runtime carriage band: `17 passed`
- final broad Wave 6 validation band: `941 passed`

## Final status

- `LOGIC_TEST_STATUS: PASS`
- `ENVIRONMENT_FAILURES: sandboxed pytest temp/build permission failures were observed, then cleared by escalated reruns`
