# V5.3 Post-Lot7 ML / Backtest Blocker Audit

Date: `2026-05-09`

## Context

- MemPalace check: `performed`
- MemPalace project memory: `found for wing v53_trading_system`
- Next source of truth: `current codebase`
- Audit mode: `read-only`
- Explicit constraint preserved: do **not** mark any `W3` / `W5` / `W6` / `CD` data-blocked gap resolved

## Executive Verdict

Post-Lot0-7, the V5.3 codebase contains real ML artifact rails, real transport/runtime rails, a real Strategy Ladder backtest pipeline, real capital-profile and promotion-artifact builders, and real operator evidence ledgers. Those rails are materially wired and broadly tested.

The blocker state is still real:

1. ML promotion is still fail-closed by doctrine and code through `ml.formalism.unresolved`.
2. No machine-verifiable `ml_anti_leakage_proof_artifact.json` exists.
3. No governed live `ml_live_drift_snapshot.json` exists.
4. No governed live `ml_supplementary_refs_source_summary.json` exists.
5. Strategy Ladder can produce backtest artifacts, but the repo still does not contain audited historical ladder evidence for capital buckets `400 / 500 / 1500 / 4000`.
6. Engine `C` and `D` remain `NOT_SHADOW_READY`; replay/backtest scaffolding exists, but promotion-grade shadow proof does not.

## Status Legend

- `YES`: present and materially implemented
- `PARTIAL`: present but not sufficient for promotion-grade proof
- `NO`: not found
- `SCRATCH_ONLY`: produced only in `.test_tmp` / test or scratch outputs
- `DOC_ONLY`: described by docs/specs, not materialized in code/artifacts

## Audit Method

I audited:

- source contracts, builders, runners, runtime loaders, and gates under `src/`
- scripts under `scripts/`
- canonical audit docs already present under `docs/audit/`
- ignored scratch outputs under `.test_tmp/` to distinguish real production of files from audited historical evidence
- targeted pytest bands

Pytest bands executed:

1. ML / capital / promotion / operator-artifact band:
   - `57 passed`
2. Regime / contract / transport band:
   - `19 passed`
3. Strategy Ladder ML handoff band:
   - `10 passed`
4. Strategy Ladder runner band:
   - `63 passed, 13 failed`
   - failure mode observed in this audit: local scratch-dir path creation / permission failures under `.test_tmp`, not a clear logic regression in ML/backtest contracts

## Table 1 - Existing Files

### ML artifact, transport, trainer, projection, and gate files

| Area | File | Role | State |
|---|---|---|---|
| ML contract | `src/interface_contracts/ml_model_artifact.py` | governed ML artifact contract, hash, windows, drift baseline | `YES` |
| ML transport contract | `src/interface_contracts/ml_model_transport_contracts.py` | sidecar summary contract for transported ML artifact | `YES` |
| ML training contract | `src/interface_contracts/ml_backtest_training_contracts.py` | typed backtest-training dataset contract | `YES` |
| Regime contract | `src/interface_contracts/regime_detector_artifact.py` | governed regime-detector artifact contract | `YES` |
| Regime label contract | `src/interface_contracts/regime_detector_label_contracts.py` | regime dataset / label configuration contracts | `YES` |
| Regime shadow audit contract | `src/interface_contracts/regime_detector_shadow_audit_contracts.py` | regime shadow audit status contract | `YES` |
| ML trainer | `src/calibration_methods/ml_trainer.py` | LightGBM trainer, walk-forward split, KS feature drift, artifact emission | `YES` |
| ML projection | `src/calibration_methods/ml_backtest_projection.py` | ML backtest dataset projection helpers | `YES` |
| Local replay ML projection | `src/local_replay_runtime/ml_backtest_projection.py` | replay/DTR to ML dataset projection | `YES` |
| Local Lab ML training | `src/local_replay_runtime/local_lab_ml_artifact_training.py` | Local IA Lab training report over replay/backtest inputs | `YES` |
| ML final audit | `src/local_replay_runtime/ml_final_audit_report.py` | final ML audit against exported active artifact | `YES` |
| Local Lab promotion projection | `src/local_replay_runtime/local_lab_promotion_readiness.py` | packaging/readiness summary, not final promotion clearance | `YES` |
| Walk-forward human review | `src/local_replay_runtime/walk_forward_review.py` | human anti-leakage review template/summary | `YES` |
| ML transport packaging | `src/local_replay_runtime/ml_model_transport.py` | package artifact + summary for transport | `YES` |
| ML transport bridge | `src/backtest_artifact_import/ml_model_transport.py` | attach ML transport refs into import/upload flow | `YES` |
| ML runtime loader | `src/complete_enablers/ml_runtime_artifact_loader.py` | fail-closed runtime load from `supplementary_refs` | `YES` |
| ML supplementary governance | `src/complete_enablers/supplementary_refs_governance.py` | rejects directional refs | `YES` |
| ML runtime scorer | `src/complete_enablers/ml_confidence_enabler.py` | bounded ML score from governed supplementary refs | `YES` |
| ML promotion gate | `src/complete_enablers/ml_model_promotion_gate.py` | fail-closed ML promotion gate | `YES` |
| Regime trainer | `src/calibration_methods/regime_detector_trainer.py` | LightGBM regime detector training | `YES` |
| Regime projection | `src/calibration_methods/regime_detector_projection.py` | regime projection helpers | `YES` |
| Local Lab regime training | `src/local_replay_runtime/local_lab_regime_detector_artifact_training.py` | Local IA Lab regime training report | `YES` |
| Regime runtime loader | `src/complete_enablers/regime_detector_runtime_loader.py` | fail-closed regime runtime artifact load | `YES` |
| Regime runtime | `src/complete_enablers/regime_detector_runtime.py` | bounded runtime regime evaluation | `YES` |
| Strategy Ladder expected-edge training | `src/local_replay_runtime/strategy_ladder_expected_edge_training.py` | Ladder-specific ML training seam | `YES` |
| Strategy Ladder ML handoff | `src/local_replay_runtime/strategy_ladder_ml_lab_handoff.py` | frozen expected-edge artifact handoff into backtest | `YES` |
| Strategy Ladder edge provider | `src/local_replay_runtime/strategy_ladder_edge_model_provider.py` | governed expected-edge artifact loader/provider | `YES` |
| Global shadow/live gate | `src/protocols/promotion_gates.py` | profile-level shadow-day gate, not ML-specific | `YES` |

### Strategy Ladder backtest producers and evidence builders

| Area | File | Role | State |
|---|---|---|---|
| CLI | `scripts/run_backtest_strategy_ladder.py` | canonical ladder runner entrypoint | `YES` |
| CLI | `scripts/run_strategy_ladder_first_controlled_run.py` | first controlled run harness | `YES` |
| CLI | `scripts/run_strategy_ladder_ml_lab_handoff.py` | ladder ML handoff CLI | `YES` |
| Runner | `src/local_replay_runtime/strategy_ladder_runner.py` | orchestrates full ladder pipeline | `YES` |
| Candidate discovery | `src/local_replay_runtime/strategy_ladder_candidate_discovery.py` | candidate discovery/export | `YES` |
| Raw-window extraction | `src/local_replay_runtime/strategy_ladder_raw_window_extractor.py` | per-candidate raw-window extraction | `YES` |
| Detailed replay | `src/local_replay_runtime/strategy_ladder_detailed_replay.py` | candidate replay using existing economics/fill/parity rails | `YES` |
| Operator ledgers | `src/local_replay_runtime/strategy_ladder_operator_artifacts.py` | trade/refusal/loss/timeframe evidence ledgers | `YES` |
| Capital profiles | `src/local_replay_runtime/capital_profile_builder.py` | capital bucket artifact builder/validation/enforcement | `YES` |
| Import bridge | `src/backtest_artifact_import/capital_profile_builder.py` | back-compat export/import ownership shim | `YES` |
| Promotion artifacts | `src/local_replay_runtime/promotion_artifact_builder.py` | engine/pair/strategy/sample-size artifacts from replay | `YES` |
| Export discovery | `src/backtest_artifact_import/export_dir_bridge.py` | export dir discovery, supplementary refs, import/upload bridge | `YES` |

## Table 2 - Existing Strategy Ladder Outputs and Artifact Producers

| Output path pattern | Producer | Observed state | Evidence class | Note |
|---|---|---|---|---|
| `backtest_strategy_ladder/<run_id>/run_manifest.json` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | run manifest | seen under `.test_tmp/shared/build/.../backtest_strategy_ladder/...` |
| `fast_candidates/candidate_events.jsonl` | `strategy_ladder_candidate_discovery.py` | `YES` | candidate export | part of runner contract and tests |
| `raw_windows/**/window_manifest.json` | `strategy_ladder_raw_window_extractor.py` | `YES` | raw-window evidence | part of runner contract and docs |
| `detailed_replay/**` per-candidate artifacts | `strategy_ladder_detailed_replay.py` | `PARTIAL` | replay evidence | producer exists; historical audited outputs not checked in |
| `capital_profiles/400.json` etc. | `capital_profile_builder.py` via `strategy_ladder_runner.py` | `SCRATCH_ONLY` | capital-bucket evidence | real producer exists; audited historical bucket outputs absent |
| `engine_promotion/<engine>/<run_id>.json` | `promotion_artifact_builder.py` | `SCRATCH_ONLY` | engine promotion evidence | real scratch outputs found |
| `pair_promotion/<pair>/<run_id>.json` | `promotion_artifact_builder.py` | `SCRATCH_ONLY` | pair promotion evidence | real scratch outputs found |
| `strategy_promotion/<strategy>/<run_id>.json` | `promotion_artifact_builder.py` | `SCRATCH_ONLY` | strategy promotion evidence | real scratch outputs found |
| `sample_size_survival/<scope>/<id>/<run_id>.json` | `promotion_artifact_builder.py` | `SCRATCH_ONLY` | sample-size evidence | real scratch outputs found |
| `reports/strategy_ladder_summary.json` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | summary report | real scratch outputs found |
| `reports/capital_bucket_matrix.json` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | bucket matrix | scratch/test level only |
| `reports/engine_matrix.json` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | engine matrix | scratch/test level only |
| `reports/pair_matrix.json` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | pair matrix | scratch/test level only |
| `reports/strategy_matrix.json` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | strategy matrix | scratch/test level only |
| `reports/strategy_ladder_report.md` | `strategy_ladder_runner.py` | `SCRATCH_ONLY` | human-readable report | scratch/test level only |
| `trade_detail_ledger.jsonl` | `strategy_ladder_operator_artifacts.py` | `SCRATCH_ONLY` | executed/reduced trade evidence | producer is tested |
| `refusal_ledger.jsonl` | `strategy_ladder_operator_artifacts.py` | `SCRATCH_ONLY` | refusal/non-execution evidence | producer is tested |
| `loss_analysis_ledger.jsonl` | `strategy_ladder_operator_artifacts.py` | `SCRATCH_ONLY` | loss cause evidence | producer is tested |
| `reports/timeframe_matrix.json` | `strategy_ladder_operator_artifacts.py` | `SCRATCH_ONLY` | timeframe matrix | producer is tested |
| `strategy_ladder_expected_edge_ml_model_artifact.json` | `strategy_ladder_ml_lab_handoff.py` | `SCRATCH_ONLY` | frozen ML artifact | found in scratch handoff outputs |
| `strategy_ladder_expected_edge_ml_model_artifact.summary.json` | `strategy_ladder_ml_lab_handoff.py` | `SCRATCH_ONLY` | frozen ML summary | found in scratch handoff outputs |
| `strategy_ladder_backtest_ml_input.json` | `strategy_ladder_ml_lab_handoff.py` | `SCRATCH_ONLY` | backtest ML input sidecar | found in scratch handoff outputs |

## Table 3 - ML Artifact Rail Classification

| ML rail | EXISTS | WIRED | TESTED | PROMOTION_BLOCKED | MISSING_PROOF | Notes |
|---|---|---|---|---|---|---|
| Core ML artifact contract + trainer | `YES` | `YES` | `YES` | `YES` | `YES` | trainer and contract exist; promotion still blocked by doctrine |
| ML transport packaging + runtime load | `YES` | `YES` | `YES` | `PARTIAL` | `YES` | fail-closed load from supplementary refs works, but live provenance summary is missing |
| ML supplementary refs directional governance | `YES` | `YES` | `YES` | `PARTIAL` | `YES` | rejects directional refs, but does not prove governed live source provenance |
| ML final audit / readiness rail | `YES` | `YES` | `YES` | `YES` | `YES` | `ml_final_audit_report.py` hard-blocks on `ml.formalism.unresolved` |
| Walk-forward human review rail | `YES` | `PARTIAL` | `NO` | `YES` | `YES` | review template exists, but not wired to clear the ML doctrinal blocker |
| Strategy Ladder expected-edge frozen handoff rail | `YES` | `YES` | `YES` | `YES` | `YES` | backtest handoff exists, but still replay/frozen only and not promotion-grade |
| Regime detector artifact + runtime rail | `YES` | `YES` | `YES` | `PARTIAL` | `PARTIAL` | runtime loader blocks promoted artifacts without shadow evidence; separate W6 ML gaps still not solved by this rail |
| Anti-leakage proof artifact rail | `NO` | `NO` | `NO` | `YES` | `YES` | no `ml_anti_leakage_proof_artifact.json` found in code or artifacts |
| Live drift source rail | `NO` | `NO` | `NO` | `YES` | `YES` | no `ml_live_drift_snapshot.json` found |
| Governed supplementary refs source-summary rail | `NO` | `NO` | `NO` | `YES` | `YES` | no `ml_supplementary_refs_source_summary.json` found |
| Human formalism decision rail clearing `ml.formalism.unresolved` | `PARTIAL` | `NO` | `NO` | `YES` | `YES` | blocker exists in code; clearing mechanism is not wired |

## Table 4 - Backtest Evidence Rail Classification

| Backtest rail | PIPELINE_EXISTS | ARTIFACTS_PRODUCED | HISTORICAL_EVIDENCE_PRESENT | PROMOTION_GRADE | BLOCKED_BY_BACKTEST | Notes |
|---|---|---|---|---|---|---|
| Strategy Ladder orchestration | `YES` | `SCRATCH_ONLY` | `NO` | `NO` | `YES` | canonical runner exists; audited first historical run absent |
| Candidate export + raw-window + detailed replay | `YES` | `PARTIAL` | `NO` | `NO` | `YES` | rails exist, but intended historical universe evidence is not checked in |
| Capital bucket profiles `400/500/1500/4000` | `YES` | `SCRATCH_ONLY` | `NO` | `NO` | `YES` | builder is real; audited historical bucket outputs still absent |
| Engine/pair/strategy promotion artifacts | `YES` | `SCRATCH_ONLY` | `NO` | `NO` | `YES` | promotion artifacts are fed from replay, but not historically promoted evidence |
| Sample-size survival artifacts | `YES` | `SCRATCH_ONLY` | `NO` | `NO` | `YES` | builder blocks correctly when not proven |
| Operator ledgers: trade/refusal/loss/timeframe | `YES` | `SCRATCH_ONLY` | `NO` | `NO` | `YES` | execution/refusal evidence rails exist but are not audited historical evidence |
| Strategy Ladder expected-edge frozen ML input | `YES` | `SCRATCH_ONLY` | `NO` | `NO` | `YES` | handoff exists, not a promotion-grade live proof rail |
| Engine C/D promotion readiness | `YES` | `PARTIAL` | `NO` | `NO` | `YES` | engine-level replay artifacts exist; shadow proof remains absent |

## Required Verification Findings

### 1. ML artifact promotion prerequisites

#### Anti-leakage proof

Result: `NOT SATISFIED BY DEDICATED ARTIFACT`

- `src/calibration_methods/ml_trainer.py` does enforce bounded walk-forward geometry and computes KS feature-drift statistics.
- `src/local_replay_runtime/walk_forward_review.py` provides a human anti-leakage review template.
- No machine-verifiable `ml_anti_leakage_proof_artifact.json` was found in code or produced artifacts.
- `src/complete_enablers/ml_model_promotion_gate.py` does **not** require a dedicated anti-leakage artifact. Promotion is still blocked anyway by `ml.formalism.unresolved`.

#### Drift source

Result: `PARTIAL / MISSING GOVERNED LIVE SOURCE`

- `MlModelArtifact` can carry `drift_baseline`.
- `ml_trainer.py` computes `ks_test_features_pvalue`.
- No governed live drift snapshot artifact or source-summary artifact was found.
- Therefore the live drift-source proof remains open.

#### Non-empty governed supplementary refs

Result: `PARTIAL`

- `src/complete_enablers/ml_runtime_artifact_loader.py` fails closed if `supplementary_refs` are missing.
- `src/complete_enablers/supplementary_refs_governance.py` rejects forbidden directional refs.
- No governed live provenance artifact summarizing the source of non-empty supplementary refs was found.
- So runtime loading is guarded, but the proof of governed live source is still missing.

#### Human formalism decision

Result: `EXPLICITLY UNSATISFIED`

- `src/complete_enablers/ml_model_promotion_gate.py` starts with `blocking_reasons = ["ml.formalism.unresolved"]`.
- `src/local_replay_runtime/ml_final_audit_report.py` also injects `ml.formalism.unresolved`.
- This blocker is tested and intentional.
- `walk_forward_review.py` exists, but no code path was found that uses a reviewed artifact to clear the blocker.

### 2. Capital bucket promotion prerequisites

#### Audited historical Strategy Ladder run

Result: `NOT SATISFIED`

- `docs/audit/backtest_strategy_ladder_status/BACKTEST_STRATEGY_LADDER_STATUS_SUMMARY.md` states that audited historical Strategy Ladder outputs are not present for `400 / 500 / 1500 / 4000`.
- Scratch/test outputs do exist under `.test_tmp`, but those do not qualify as audited historical governed evidence.

#### Measured fields

Result: `PARTIAL BUT REAL`

- `src/local_replay_runtime/capital_profile_builder.py` requires execution return, drawdown, cost completeness, fill realism, depth, and sample-size statuses before a bucket can become `CAPITAL_BUCKET_READY`.
- This is real fail-closed logic.
- What is still missing is provenance that those measured fields came from an audited historical Strategy Ladder run rather than from scratch or synthetic assembly.

#### Freshness/hash state

Result: `PARTIAL`

- `artifact_hash` is always materialized and validated.
- `validate_capital_profile()` rejects invalid hash and stale artifacts.
- `expires_at` is optional. A ready capital profile is not forced to carry freshness.
- Therefore freshness enforcement is incomplete.

#### Execution fidelity status

Result: `PARTIAL`

- `StrategyLadderRunManifest`, `StrategyLadderReportSummary`, and promotion artifacts carry execution fidelity gap codes and source-status fields.
- `CapitalBucketProfile` itself does not carry a dedicated execution-fidelity status field.
- Capital bucket readiness is therefore not independently bound to an explicit fidelity artifact/state at the bucket contract level.

### 3. Engine C / D promotion prerequisites

#### Measured replay/backtest/shadow artifact

Result: `PARTIAL`

- Engine promotion artifacts exist and are fed from replay/backtest.
- Local status carriers for `engine_c` and `engine_d` exist in `promotion_artifact_contracts.py`.
- Current audits still state `NOT_SHADOW_READY`.
- No separate governed shadow confirmation artifact for C/D was found.

#### Sample-size survival evidence

Result: `SATISFIED AS A BLOCKER`

- `promotion_artifact_builder.py` emits `SampleSizeSurvivalArtifact`.
- Promotion is blocked when sample-size survival is not proven.

#### Execution / refusal evidence

Result: `PARTIAL`

- `trade_detail_ledger.jsonl`, `refusal_ledger.jsonl`, `loss_analysis_ledger.jsonl`, and `timeframe_matrix.json` are real producers.
- These rails are tested and scratch outputs exist.
- Audited historical C/D evidence is still absent.

## Table 5 - Missing Proofs

| Missing proof | Expected form | Current state | Why it matters |
|---|---|---|---|
| ML anti-leakage proof artifact | `ml_anti_leakage_proof_artifact.json` | `DOC_ONLY` | required to turn anti-leakage from doctrine/review into machine-verifiable promotion evidence |
| ML live drift proof | `ml_live_drift_snapshot.json` | `DOC_ONLY` | required to prove monitored live drift source rather than offline baseline only |
| ML supplementary refs provenance | `ml_supplementary_refs_source_summary.json` | `DOC_ONLY` | required to prove governed non-empty live refs source |
| Human formalism acceptance | reviewed artifact that clears `ml.formalism.unresolved` | `MISSING` | current code intentionally blocks all ML promotion |
| Audited historical Strategy Ladder bucket outputs | governed `capital_profiles/400|500|1500|4000.json` from audited run | `MISSING` | required for capital-bucket viability claims |
| Audited historical ladder promotion artifacts | engine/pair/strategy/sample-size artifacts from audited run | `MISSING` | required for promotion-grade backtest evidence |
| Audited historical C/D proof set | replay + backtest + shadow confirmation artifacts | `MISSING` | required before any C/D shadow readiness claim |
| Capital bucket freshness requirement | non-optional `expires_at` or equivalent freshness state | `PARTIAL` | current ready bucket can exist without explicit freshness deadline |
| Capital bucket execution fidelity binding | explicit bucket-level fidelity field / ref | `PARTIAL` | current fidelity evidence is carried above the bucket, not enforced inside bucket contract |

## Safe Next Patches

These patches are safe because they improve proof carriage without falsely resolving data-blocked gaps.

1. Add typed contracts and producers for:
   - `ml_anti_leakage_proof_artifact.json`
   - `ml_live_drift_snapshot.json`
   - `ml_supplementary_refs_source_summary.json`
2. Wire `WalkForwardReviewSummary` into `ml_model_promotion_gate.py` and `ml_final_audit_report.py` so the ML blocker can only clear through an explicit reviewed artifact.
3. Require `expires_at`, `input_data_hash`, `method_version_hash`, `run_id`, and a Strategy Ladder manifest reference before any `CapitalBucketProfile` can validate as promotion-ready.
4. Add an explicit capital-bucket execution-fidelity field or reference so readiness is directly bound to measured fidelity state, not only to higher-level summary/blocker aggregation.
5. Add a first-class C/D shadow-proof contract instead of relying only on global doctrine and partial local-status carriers.
6. Stabilize `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` scratch-path handling so the runner band can be fully re-verified in one pass.
7. Add a governed audit index file that distinguishes `SCRATCH_ONLY` artifacts from audited historical promotion evidence.

## Gaps That Must Remain Open

These gaps must remain open after this audit.

1. `W3` replay/live cost parity is not proven green.
2. `W5` capital-bucket audited historical evidence for `400 / 500 / 1500 / 4000` is not present.
3. `W6-OPEN-001` live governed non-empty ML `supplementary_refs` source is not proven.
4. `W6-OPEN-002` live ML drift source is not proven.
5. `W6-OPEN-003` ML anti-leakage promotion proof artifact is not implemented.
6. `W6-OPEN-004` `ml.formalism.unresolved` remains an intentional blocker.
7. `CD` shadow readiness remains blocked by missing measured promotion-grade replay/shadow evidence.

## Test Evidence Collected In This Audit

Passed:

- `python -m pytest -q tests/test_complete_enablers/test_ml_model_promotion_gate.py tests/test_complete_enablers/test_ml_runtime_artifact_loader.py tests/test_complete_enablers/test_ml_confidence_enabler.py tests/test_local_replay_runtime/test_ml_backtest_projection.py tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py tests/test_local_replay_runtime/test_ml_final_audit_report.py tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py tests/test_local_replay_runtime/test_local_lab_regime_detector_artifact_training.py tests/test_backtest_artifact_import/test_ml_model_transport.py tests/test_backtest_artifact_import/test_capital_profile_builder.py tests/test_local_replay_runtime/test_promotion_artifact_builder.py tests/test_local_replay_runtime/test_strategy_ladder_operator_artifacts.py --tb=short --basetemp=tmp_pytest_post_lot7_audit_no_runner`
- `python -m pytest -q tests/test_complete_enablers/test_regime_detector_runtime.py tests/test_backtest_artifact_import/test_regime_detector_transport.py tests/test_interface_contracts/test_regime_detector_artifact.py tests/test_interface_contracts/test_ml_model_artifact.py --tb=short --basetemp=tmp_pytest_post_lot7_audit_regime`
- `python -m pytest -q tests/test_local_replay_runtime/test_strategy_ladder_ml_lab_handoff.py tests/test_local_replay_runtime/test_strategy_ladder_expected_edge_training.py tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider.py --tb=short --basetemp=tmp_pytest_post_lot7_audit_ladder_ml`

Partially blocked in this audit environment:

- `rtk pytest -q tests/test_complete_enablers/test_ml_model_promotion_gate.py tests/test_complete_enablers/test_ml_runtime_artifact_loader.py tests/test_complete_enablers/test_ml_confidence_enabler.py tests/test_local_replay_runtime/test_ml_backtest_projection.py tests/test_local_replay_runtime/test_local_lab_ml_artifact_training.py tests/test_local_replay_runtime/test_ml_final_audit_report.py tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py tests/test_local_replay_runtime/test_local_lab_regime_detector_artifact_training.py tests/test_backtest_artifact_import/test_ml_model_transport.py tests/test_backtest_artifact_import/test_capital_profile_builder.py tests/test_local_replay_runtime/test_promotion_artifact_builder.py tests/test_local_replay_runtime/test_strategy_ladder_operator_artifacts.py tests/test_local_replay_runtime/test_strategy_ladder_runner.py --tb=short --basetemp=tmp_pytest_post_lot7_audit`
  - observed result: `63 passed, 13 failed`
  - observed failure class: `.test_tmp` scratch path creation / permission issues on `test_strategy_ladder_runner.py`

## Final Audit Position

- ML rails: `implemented, wired, tested, still promotion-blocked`
- Backtest rails: `implemented, can produce artifacts, still missing audited historical evidence`
- Capital buckets: `not promotion-grade`
- Engine C/D: `not shadow-ready`
- No `W3`, `W5`, `W6`, or `CD` data-blocked gap is resolved by this audit

