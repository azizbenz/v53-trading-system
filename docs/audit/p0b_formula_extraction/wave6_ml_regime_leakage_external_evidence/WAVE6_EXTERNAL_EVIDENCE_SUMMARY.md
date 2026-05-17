# Wave 6 External Evidence Summary

Date: 2026-04-30
Scope: ML, regime, anti-leakage, artifact governance, cockpit false-green, and side/halal safety evidence.
Method: source inspection plus targeted test evidence. This summary reflects the current codebase after Wave 6 doctrine hardening.

## Doctrine anchor

- V5.3 remains crypto spot-only, halal-strict, VPS non-HFT.
- Local IA Lab trains and evaluates.
- VPS consumes frozen governed artifacts only.
- ML is non-sovereign.
- ML must not create trades or mutate side.
- Regime runtime outputs are non-directional only.
- Dataset-builder future labels may exist only in Local Lab training seams.

## Source rails inspected

- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/ml_scoring_soft_penalty_hook.py`
- `src/complete_enablers/ml_runtime_artifact_loader.py`
- `src/complete_enablers/ml_fusion.py`
- `src/complete_enablers/ml_model_promotion_gate.py`
- `src/complete_enablers/regime_detector_runtime.py`
- `src/complete_enablers/regime_detector_runtime_loader.py`
- `src/complete_enablers/supplementary_refs_governance.py`
- `src/local_replay_runtime/regime_detector_dataset_builder.py`
- `src/local_replay_runtime/ml_backtest_projection.py`
- `src/local_replay_runtime/local_lab_ml_artifact_training.py`
- `src/local_replay_runtime/regime_detector_shadow_audit_diagnosis.py`
- `src/local_replay_runtime/regime_detector_final_audit_report.py`
- `src/local_replay_runtime/ml_final_audit_report.py`
- `src/calibration_methods/walkforward.py`
- `src/calibration_methods/ml_trainer.py`
- `src/calibration_methods/regime_detector_trainer.py`
- `src/backtest_artifact_import/ml_model_transport.py`
- `src/backtest_artifact_import/regime_detector_transport.py`
- `src/scoring_backbone/scoring_runtime_support.py`
- `src/risk_backbone/risk_runtime_models.py`
- `src/risk_backbone/risk_runtime_explainability.py`
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_system_flow.py`

## High-signal findings

### 1. Supplementary refs are governed transport, not free-form ML side channels

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`

- Forbidden directional keys are explicitly blocked in `supplementary_refs_governance.py`.
- ML and regime loaders fail closed or degrade to neutral on missing refs, stale refs, invalid summaries, missing transport artifacts, and hash mismatches.
- Transport packaging exists for both ML and regime artifacts.
- Live non-empty upstream source for `supplementary_refs` is still not proven from the inspected runtime rails.

### 2. ML score modulation is bounded and non-positive

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `CONSUMER_FOUND`

- `ml_scoring_soft_penalty_hook.py` computes a bounded multiplier delta.
- `ml_fusion.py` now clamps the delta with `min(0.0, alpha * (confidence - 0.5))`.
- `ml_confidence > 0.5` leaves score unchanged.
- `ml_confidence == 0.5` leaves score unchanged.
- `ml_confidence < 0.5` reduces score.
- The seam still does not create candidates and does not mutate side.

### 3. ML artifact governance is typed and hash-aware, but promotion remains deliberately blocked

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

- `MlModelArtifact` and its summary sidecar carry schema, feature hash, dataset hash, calibration version, and stale horizon.
- Runtime loader validates summary presence, artifact declaration, artifact JSON validity, artifact hash, and stale horizon.
- Final audit and promotion gate both carry an explicit doctrinal blocker: `ml.formalism.unresolved`.

### 4. Regime runtime remains non-directional and shadow-only

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `NON_DIRECTIONAL_RUNTIME`

- Runtime outputs are limited to `regime_transition_risk`, `regime_stability_score`, `market_toxicity_score`, and `expected_duration_bucket`.
- Directional keys are forbidden at governance level and by runtime constants.
- Runtime signal has no `side` attribute and `shadow_only` is true.

### 5. Future labels exist in Local Lab, not governed runtime

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `LOCAL_LAB_ONLY`

- `regime_detector_dataset_builder.py` uses future windows to create training labels.
- The module explicitly exports `DATASET_BUILDER_LABEL_SCOPE = "LOCAL_LAB_TRAINING_ONLY"`.
- Builder fails closed when future windows are absent instead of inventing labels.

### 6. Anti-leakage discipline is partly proven, not fully closed end-to-end

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `LEAKAGE_PROOF_MISSING`

- Snapshot builders filter `timestamp_ns <= anchor`.
- Walk-forward planning includes both purge and embargo.
- Trainers enforce temporal windows and reject schema drift.
- Human review rails require explicit no-future-data-leak confirmation.
- A single end-to-end proof artifact for all ML/runtime seams was not found.

### 7. Model-risk and drift seams exist, but live source and governance depth remain partial

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `LIVE_SOURCE_NOT_PROVEN`

- `MlModelRiskRegistry` and drift signals exist with fail-closed behavior on missing data.
- Regime shadow audit diagnosis exists and blocks on schema/hash/profile mismatches and high `shadow_diff_pct`.
- Promotion thresholds are encoded, but live drift feed provenance is not proven in the inspected runtime paths.

### 8. Cockpit false-green protection is present but still status-driven rather than profitability-driven

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`, `COCKPIT_ONLY`

- Feature bridge distinguishes artifact presence from runtime consumption.
- Replay metrics label CE as expected-only and keep incomplete economics out of green.
- System flow keeps artifact-only, small-capital-not-proven, true-drawdown-not-proven, and baseline-caps-only states out of green.

### 9. Side/halal safety remains intact in the ML/regime seams inspected

Evidence status: `EVIDENCE_EXTRACTED`, `TEST_COVERED`

- ML does not create candidates.
- ML does not mutate side in the inspected score application.
- Regime runtime does not emit side or directional trade instructions.
- No shorting or leverage path was found in the inspected Wave 6 rails.

## Residual gaps for external audit

- Live non-empty `supplementary_refs` source is not proven.
- End-to-end leakage closure still depends on human review attestations and training/report rails, not one unified governed proof artifact.
- Live drift source, promotion-state governance, and shadow-to-live ML promotion remain partial and intentionally blocked.

## Validation snapshot

- focused complete-enablers band: `33 passed`
- ML doctrine core band: `23 passed`
- scoring runtime carriage band: `17 passed`
- broad Wave 6 validation band: `941 passed`
- initial sandboxed pytest runs hit Windows permission failures in temp/build paths; escalated reruns cleared them
