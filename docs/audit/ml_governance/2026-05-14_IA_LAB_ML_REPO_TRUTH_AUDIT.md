# 2026-05-14 IA Lab ML Repo Truth Audit

Date: `2026-05-14`

## Context

- MemPalace check: `performed`
- MemPalace project memory: `found for wing v53_trading_system`
- Next source of truth: `current codebase`
- Audit mode: `docs + code + targeted tests`

## Scope

Audited docs:

- `docs/audit/ml_governance/2026-05-14_ML_HANDOFF_FROM_BACKTEST_B2.md`
- `docs/audit/ml_governance/ML_TEST_RESULTS.md`
- `docs/audit/ml_governance/ML_SUPPLEMENTARY_REFS_GOVERNANCE_DECISION.md`
- `docs/audit/ml_governance/ML_SUPPLEMENTARY_REFS_PATCH_REPORT.md`
- `docs/audit/ml_governance/ML_FORBIDDEN_DIRECTIONAL_KEYS.md`
- `docs/audit/claude/00_INDEX.md`
- `docs/audit/claude/06_ML_PIPELINE_AUDIT.md`
- `docs/audit/claude/09_BACKTEST_ML_CHAIN.md`
- `docs/audit/v53_post_lot7_ml_backtest_blocker_audit.md`
- `docs/audit/V53_CODEX_FULL_GAP_CLOSURE_CHANTIER.md`
- `docs/audit/V53_CODEX_EXECUTION_FIDELITY_GAP_CLOSURE.md`
- `docs/production_deployment_plan/V5_3_CODEX_MASTER_IA_LAB_GOVERNED_ML.md`
- `docs/production_deployment_plan/V5_3_CODEX_ML_ENABLER_*`
- `docs/production_deployment_plan/V5_3_CODEX_WALLS_SPOOFING_*`
- `docs/backtest/V5_3_CODEX_IA_LAB_DASHBOARD_ML_POSTTRADE_SPEC.md`

Audited code families:

- `src/calibration_methods/`
- `src/local_replay_runtime/`
- `src/complete_enablers/`
- `src/backtest_artifact_import/`
- `src/interface_contracts/`
- `src/meta_learning/`
- `src/meta_minimal/`
- `src/data_backbone/microstructure/`
- targeted `tests/`

## Executive verdict

The V5.3 repo already contains a real IA Lab / governed ML rail.
The main blocker is no longer "ML code missing".
The main blocker is that promotion-grade proof is still incomplete and intentionally fail-closed.

Current repo truth:

1. Local IA Lab training, governed transport, runtime loading, bounded ML scoring, and Strategy Ladder ML handoff are materially present.
2. Several docs written earlier in the chantier understate the current wiring and must be downgraded to historical context.
3. The fail-closed blockers are still valid:
   - `ml.formalism.unresolved`
   - no durable business producer for `ml_anti_leakage_proof_artifact.json`
   - no durable business producer for `ml_live_drift_snapshot.json`
   - expected-edge backtest truth still blocked until governed proof exists
4. Walls/spoofing is not doc-only. The backbone calculator and calibration seams exist. What remains partial is direct Strategy Ladder / engine-native consumption and later promotion proof.

## Decision table for the docs

### Keep as active doctrine

- `docs/production_deployment_plan/V5_3_CODEX_MASTER_IA_LAB_GOVERNED_ML.md`
- `docs/production_deployment_plan/V5_3_CODEX_ML_ENABLER_*`
- `docs/production_deployment_plan/V5_3_CODEX_AUDIT_CHECKLIST_IA_LAB_GOVERNED_ML.md`
- `docs/audit/V53_CODEX_FULL_GAP_CLOSURE_CHANTIER.md`
- `docs/audit/V53_CODEX_EXECUTION_FIDELITY_GAP_CLOSURE.md`

Why:

- these files are still aligned on the key invariants: local-only training, artifact-only runtime, ML non-sovereignty, fail-closed promotion, no bypass of A/B/C/D or Shadow gates

### Keep as historical handoff only

- `docs/audit/ml_governance/2026-05-14_ML_HANDOFF_FROM_BACKTEST_B2.md`
- `docs/audit/claude/06_ML_PIPELINE_AUDIT.md`
- `docs/audit/claude/09_BACKTEST_ML_CHAIN.md`

Why:

- they remain useful to understand older milestones and the B2 blocker state
- they are not safe as repo-wide execution truth without code re-check

### Downgrade specific stale claims

1. `docs/audit/ml_governance/2026-05-14_ML_HANDOFF_FROM_BACKTEST_B2.md`
   - stale claim: MemPalace not found
   - repo truth now: MemPalace project memory exists for wing `v53_trading_system`

2. `docs/audit/claude/06_ML_PIPELINE_AUDIT.md`
   - stale claim: no runtime artifact loading / prediction path is wired yet
   - repo truth now:
     - `src/local_replay_runtime/strategy_ladder_edge_model_provider.py`
     - `src/complete_enablers/ml_runtime_artifact_loader.py`
     - `src/complete_enablers/ml_confidence_enabler.py`
     - `src/complete_enablers/ml_scoring_soft_penalty_hook.py`

3. `docs/audit/v53_post_lot7_ml_backtest_blocker_audit.md`
   - partially stale claim: no `ml_supplementary_refs_source_summary.json` rail exists
   - repo truth now:
     - contract exists in `src/interface_contracts/ml_governance_proof_contracts.py`
     - builder exists in `src/local_replay_runtime/ml_model_transport.py`
     - runtime loader consumes it in `src/complete_enablers/ml_runtime_artifact_loader.py`
   - what remains true:
     - there is still no durable governed live-cycle proof that all engines receive a non-empty upstream source in production conditions

## What the code already has

### A. Core ML artifact and training rail: `YES`

- `src/interface_contracts/ml_model_artifact.py`
- `src/interface_contracts/ml_model_transport_contracts.py`
- `src/interface_contracts/ml_backtest_training_contracts.py`
- `src/calibration_methods/ml_trainer.py`
- `src/local_replay_runtime/ml_backtest_projection.py`
- `src/local_replay_runtime/local_lab_ml_artifact_training.py`

Meaning:

- typed artifact
- deterministic LightGBM trainer
- backtest/replay dataset projection
- local IA Lab training report

### B. Governed transport and runtime ML loading rail: `YES`

- `src/local_replay_runtime/ml_model_transport.py`
- `src/backtest_artifact_import/ml_model_transport.py`
- `src/complete_enablers/ml_runtime_artifact_loader.py`
- `src/complete_enablers/supplementary_refs_governance.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/ml_scoring_soft_penalty_hook.py`

Meaning:

- transport packaging exists
- `supplementary_refs` governance exists
- directional keys are explicitly rejected
- runtime loading is artifact-only and fail-closed

### C. Strategy Ladder expected-edge rail: `YES`, but still blocked for truth promotion

- `src/local_replay_runtime/strategy_ladder_expected_edge_training.py`
- `src/local_replay_runtime/strategy_ladder_ml_lab_handoff.py`
- `src/local_replay_runtime/strategy_ladder_edge_model_provider.py`
- `src/local_replay_runtime/strategy_ladder_economic_provenance.py`
- `src/local_replay_runtime/strategy_ladder_runner.py`

Meaning:

- there is a real frozen expected-edge training and handoff path
- the provider can load governed artifacts
- the provider still keeps the rail fail-closed when proof is missing

### D. Human review / audit / final readiness rail: `PARTIAL`

- `src/local_replay_runtime/walk_forward_review.py`
- `src/local_replay_runtime/ml_final_audit_report.py`
- `src/local_replay_runtime/local_lab_promotion_readiness.py`
- `src/local_replay_runtime/live_complete_operator_audit_report.py`

Meaning:

- human review and final audit surfaces exist
- promotion remains intentionally blocked
- there is no implemented formal acceptance mechanism that clears `ml.formalism.unresolved`

### E. Regime detector rail: `YES`

- `src/interface_contracts/regime_detector_artifact.py`
- `src/interface_contracts/regime_detector_label_contracts.py`
- `src/calibration_methods/regime_detector_trainer.py`
- `src/calibration_methods/regime_detector_projection.py`
- `src/local_replay_runtime/local_lab_regime_detector_artifact_training.py`
- `src/complete_enablers/regime_detector_runtime_loader.py`
- `src/complete_enablers/regime_detector_runtime.py`

### F. Drift / model-risk support rail: `PARTIAL`

- `src/meta_learning/strategy_drift_monitor/monitor.py`
- `src/meta_minimal/cost_drift_monitor/`
- cockpit/model-risk reading surfaces exist

Meaning:

- drift logic exists
- but the repo does not yet materialize a durable business producer for `MlLiveDriftSnapshot`

### G. Walls / spoofing slice: `YES` in backbone, `PARTIAL` in downstream use

- `src/data_backbone/microstructure/walls_and_spoofing.py`
- `src/data_backbone/microstructure/feature_registry.py`
- `src/calibration_methods/walls_and_spoofing_calibration.py`
- regime detector feature calibration already knows these fields

Meaning:

- the detector exists
- typed features exist
- calibration feature-set selection exists
- direct Strategy Ladder / engine-native use is still intentionally deferred in places like `strategy_ladder_engine_b_input_builder.py`

## What is still missing or not promotion-grade

### 1. Anti-leakage proof producer: `MISSING`

Found:

- contract: `MlAntiLeakageProofArtifact`
- tests that fabricate it synthetically
- expected-edge loader that can consume the file if present

Not found:

- a real business producer that writes `ml_anti_leakage_proof_artifact.json` from actual IA Lab outputs
- a persisted operator workflow that binds approved walk-forward review to this artifact

### 2. Live drift snapshot producer: `MISSING`

Found:

- contract: `MlLiveDriftSnapshot`
- drift monitor logic
- tests that fabricate the snapshot synthetically

Not found:

- a real producer that emits `ml_live_drift_snapshot.json`
- a durable export/import/runtime path proving this snapshot is current and governed

### 3. Formalism acceptance rail: `MISSING BY DESIGN`

Current code explicitly blocks promotion through:

- `src/complete_enablers/ml_model_promotion_gate.py`
- `src/local_replay_runtime/ml_final_audit_report.py`

This is correct fail-closed behavior.
What is missing is not a bypass.
What is missing is an explicit, reviewable, human-governed acceptance mechanism if the doctrine is ever intentionally opened.

### 4. Expected-edge truth promotion: `BLOCKED`

The expected-edge rail exists, but the blocker codes remain valid:

- `EXPECTED_EDGE_PROXY_BLOCKED`
- `EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH`

This should stay blocked until:

- anti-leakage proof exists
- label source is truly governed
- execution-fidelity doctrine allows the label class to advance

### 5. B2 engine-specific blockers still remain real

From the current B2 handoff, still treat as real until the current code/artifacts disprove them:

- Engine C replay payload missing required microstructure groups in B2 evidence
- Engine D missing closed-episode journal in B2 evidence

These are not reasons to weaken ML governance.

## What should be abandoned or redone

### Abandon

- any idea of a sovereign `local_ai_lab` top-level package
- any buy/sell or long/short directional transport through `supplementary_refs`
- any idea that scratch-only artifacts are audited evidence
- any claim that proxy replay labels can become promotion-grade by wording alone
- any plan to make walls/spoofing a direct live hard blocker before Shadow proof

### Redo cleanly

1. Redo the next ML sprint around proof producers, not around new trainers.
2. Redo old task framing that still says "runtime ML not wired" into:
   - "runtime wiring exists"
   - "promotion proof is incomplete"
3. Redo any backlog item that treats walls/spoofing as the first blocker.
   - The right order is proof/gating first, richer microstructure exploitation second.

## Recommended next coding order

1. Produce `ml_anti_leakage_proof_artifact.json` from real training metadata plus approved walk-forward review.
2. Produce `ml_live_drift_snapshot.json` from the existing drift/model-risk rails.
3. Define a deliberate human-governed formalism acceptance sidecar if and only if doctrine allows it.
4. Keep Strategy Ladder expected-edge truth fail-closed until 1-3 exist.
5. Only after that, revisit deeper use of walls/spoofing features in the IA Lab ML layer.

## Validation performed in this audit

Targeted pytest band:

- `tests/test_complete_enablers/test_ml_runtime_artifact_loader.py`
- `tests/test_complete_enablers/test_ml_model_promotion_gate.py`
- `tests/test_backtest_artifact_import/test_ml_model_transport.py`
- `tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider.py`
- `tests/test_local_replay_runtime/test_strategy_ladder_ml_lab_handoff.py`
- `tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py`

Result:

- `33 passed`

Note:

- the runtime-loader test suite required a small refresh to match the current validation order and the current `MlSupplementaryRefsSourceSummary` contract
- no production ML logic was loosened in this audit
