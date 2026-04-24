# V5.3 Repo Audit - Packages 1 to 6 - 2026-04-24

## Context

MemPalace check: performed.

MemPalace project memory: found under wing `v53_trading_system`, used only as historical context.

Current source of truth:

- Branch: `codex/full-shadow-abcd-migration-20260403`
- Commit audited: `d96ba891a25f3f1a09368ba540649c5dfd6a41d9`
- Truth hierarchy: current code/tests first, exact slice markdown packs second, active transversal canon third.
- Audit mode: audit-only for code. This markdown file records the audit result after the user explicitly requested a complete MD.

This audit does not treat green tests as semantic proof. Tests are reported as proof of exercised behavior only.

## Global Governing Invariants

- No new profiles beyond `LIGHT` and `COMPLETE`.
- Runtime modes remain `LOCAL_REPLAY`, `SHADOW`, `MICRO_LIVE`, `LIVE`.
- Shadow / Micro-live / Live-Light / Live-Complete gates must not be bypassed.
- `20_CARVER_NARANG_TALEB_INTEGRATION.md` is active transversal canon for no-bypass, Local/VPS separation, refusal logging, Taleb fail-closed discipline, and promotion gate doctrine.
- Local IA Lab may train / calibrate / replay / package artifacts.
- VPS must not train, run LightGBM fit, run Optuna, or become a Local Lab substitute.
- Local / Grafana / operator paths must not place orders or mutate VPS state directly.
- Credentials must remain sealed; no raw secrets in queue, logs, metrics, dashboard payloads, exports, or recovery reports.
- RegimeDetector VPS semantics must remain non-directional and artifact-only.
- ML enabler is additive only, never a fifth engine and never a sovereign promotion authority.

## Global Proof Commands

Executed during the audit:

```powershell
python scripts/run_dag_check.py
```

Result:

- PASS
- Files scanned: `674`
- Imports: `1405`
- Cycles: `0`
- Violations: `0`

```powershell
python scripts/run_engineering_guardrails.py
```

Result:

- PASS
- `new_violations=0`
- Baseline violations unchanged: `3361`

Git status after Package 6 audit:

- No tracked code edits.
- Existing untracked local browser export remains:
  - `docs/production_deployment_plan/Claude Code Cheat Sheet.html`
  - `docs/production_deployment_plan/Claude Code Cheat Sheet_files/`

## Package Status Summary

| Package | Scope | Final status |
|---|---|---|
| 1 | `src/interface_contracts/`, core `src/protocols/` | `PARTIAL` |
| 2 | Shadow VPS launcher / governed runtime / command plane scripts | `PARTIAL` |
| 3 | `src/monitoring/`, `src/ui/` | `PARTIAL` |
| 4 | `src/local_replay_runtime/` | `PARTIAL` |
| 5 | `src/data_backbone/` | `DOC_STALE` for broad Build 2 narrative; microstructure code `COMPLETE` |
| 6 | `src/complete_enablers/` | `PARTIAL` |

## Carry-Forward Finding Register

### P0

None found in Packages 1 to 6.

### P1

#### P1 - Plaintext Binance env bootstrap remains active

- File: `scripts/shadow_vps_service_io_support.py:201`
- Package: 2
- Why wrong: launcher startup still has an active plaintext Binance environment bootstrap path before recovery/credential validation.
- Violates:
  - `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`
  - `20_CARVER_NARANG_TALEB_INTEGRATION.md`
  - sealed credential / fail-closed runtime doctrine.

#### P1 - Monitoring/log projection lacks a local redaction boundary

- Files:
  - `src/monitoring/shadow_vps_service_log_retrieval.py:18`
  - `src/monitoring/shadow_vps_service_monitoring_payload_support.py:414`
  - `src/monitoring/shadow_vps_service_monitoring_payload_support.py:497`
- Package: 3
- Why wrong: `event.message`, `event.error`, `latest_error`, and `last_error` can be propagated into monitoring/dashboard payloads without a local redaction boundary.
- Violates:
  - `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`
  - `34_V53_BUILD17_OPERATOR_COCKPIT_CLOSURE.md`
  - Doc 20 fail-closed/no-survivorship audit discipline.

#### P1 - ML formalism rejected by governing doc is still promotable in code

- Files:
  - `src/calibration_methods/ml_trainer.py:299`
  - `src/complete_enablers/ml_confidence_enabler.py:94`
  - `src/complete_enablers/ml_model_promotion_gate.py:25`
- Package: 6
- Why wrong: the current chain is `LightGBM regression -> prediction clipped to [0,1] -> ml_confidence`, while the arbitration doc explicitly rejects this as final prod-safe semantics.
- Violates:
  - `docs/production_deployment_plan/update_audit/2026-04-22_ml_classifier_regression_arbitration.md`
  - ML enabler scientific canon.

### P2

#### P2 - Non-atomic governed queue writes

- File: `src/protocols/dashboard_command_queue.py:151`
- Package: 1
- Why wrong: typed governed queue JSON is persisted via direct `Path.write_text()` rather than the repo atomic IO helper.
- Violates:
  - governed file-queue fail-closed invariant from Build 17 and `2026-04-24_grafana_operator_queue_bridge.md`.

#### P2 - Weak credential hash / sealed ref validation

- File: `src/interface_contracts/dashboard_command_contracts.py:166`
- Package: 1
- Why wrong: `secret_hash` requires only `min_length=1`, and `sealed://` is accepted by prefix alone.
- Violates:
  - `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`.

#### P2 - LiveComplete action surface is stringly typed

- Files:
  - `src/protocols/contracts_complete.py:72`
  - `src/protocols/live_complete_runtime.py:26`
  - `src/ui/complete_dashboard_view.py:74`
- Packages: 1 and 3
- Why wrong: Build 17 typed control surface is represented through raw string action lists.
- Violates:
  - `34_V53_BUILD17_OPERATOR_COCKPIT_CLOSURE.md`.

#### P2 - Dashboard halt event lacks reason-code detail

- File: `scripts/run_shadow_vps_service.py:190`
- Package: 2
- Why wrong: the active dashboard halt event is explicit, but the emitted event lacks structured `reason_codes` sufficient for Taleb-style refusal/no-trade audit.
- Violates:
  - Doc 20 refusal/no-trade honesty.

#### P2 - Runtime recovery sealed-ref validation remains weak

- File: `scripts/shadow_vps_service_recovery_support.py:266`
- Package: 2
- Why wrong: recovery path validates sealed credential references weakly, similar to Package 1 contract weakness.
- Violates:
  - `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`.

#### P2 - Runtime evidence/campaign summary writes are non-atomic

- Files:
  - `scripts/shadow_vps_service_projection_support.py:409`
  - `scripts/shadow_vps_service_campaign_support.py:457`
- Package: 2
- Why wrong: runtime evidence/campaign JSON is written directly.
- Violates:
  - fail-closed artifact/report persistence discipline.

#### P2 - ML final audit can report ready despite unresolved ML formalism

- File: `src/local_replay_runtime/ml_final_audit_report.py:115`
- Package: 4
- Why wrong: an uploaded ML artifact can match the Local Lab recommendation and produce a ready audit even though `UNKNOWN_FINAL_FORMALISM` is still active in the governing arbitration.
- Violates:
  - `2026-04-22_ml_classifier_regression_arbitration.md`.

#### P2 - Local artifact/report writers use direct write_text

- Files:
  - `src/local_replay_runtime/edge_gate_calibration.py:254`
  - `src/local_replay_runtime/live_complete_operator_audit_report.py:238`
- Package: 4
- Why wrong: governed local artifacts/reports are persisted via direct `write_text`.
- Violates:
  - repo atomic artifact/report persistence pattern.

#### P2 - Runtime-facing direct ml_confidence injection API remains exposed

- File: `src/complete_enablers/ml_confidence_enabler.py:222`
- Package: 6
- Why wrong: current hook path uses `supplementary_refs`, but `apply_to_engine_score(..., ml_confidence=...)` remains a public runtime-facing shortcut that weakens artifact-only doctrine.
- Violates:
  - ML artifact-only runtime doctrine.

## Package 1 Audit

### 1. Module Scope

Audited:

- `src/interface_contracts/`
- core `src/protocols/`

This pass covered placement, contracts, gates, profile/mode vocabulary, dashboard command queue contracts, recovery/warm-up contracts, and LiveComplete protocol surfaces.

Shadow service runtime implementation inside `src/protocols/shadow_*` was placement-checked here and deferred to Package 2/3 for semantic runtime audit.

### 2. Code Files Inspected

Enumerated all files under:

- `src/interface_contracts/*.py`
- `src/protocols/*.py`

Key files read:

- `src/interface_contracts/domain_types.py`
- `src/interface_contracts/atomic_io.py`
- `src/interface_contracts/dashboard_command_contracts.py`
- `src/interface_contracts/vps_recovery_contracts.py`
- `src/interface_contracts/shadow_vps_service_contracts.py`
- `src/protocols/contracts.py`
- `src/protocols/contracts_complete.py`
- `src/protocols/enums.py`
- `src/protocols/promotion_gates.py`
- `src/protocols/dashboard_command_queue.py`
- `src/protocols/dashboard_command_result_support.py`
- `src/protocols/vps_recovery_warmup.py`
- `src/protocols/live_complete_runtime.py`
- `src/protocols/live_complete_dashboard.py`

### 3. Document Resolution Ledger

Stable for the contract / queue / gate layer.

Not stable enough to mark every runtime protocol file complete, because several runtime protocol files are governed by later package-specific packs.

### 4. Authorized Governing Docs

- `25_UPDATE_AUDIT_PROTOCOL.md`
- `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`
- `34_V53_BUILD17_OPERATOR_COCKPIT_CLOSURE.md`
- `update_audit/2026-04-24_grafana_operator_queue_bridge.md`
- `update_audit/2026-04-21_build_1_dependency_architecture_repo_truth_audit.md`
- `update_audit/2026-04-21_dag_unauthorized_imports_engine_d_execution_backbone.md`
- `update_audit/2026-04-21_build_1_to_14_repo_truth_drift_audit_matrix.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md` as transversal canon.

### 5. Superseded / Stale Docs Ignored

Older broad planning docs were not blended into the verdict:

- `02_V53_PRODUCTION_AUDIT.md`
- `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md`
- `19_MULTIPAIR_MODERNIZATION_PLAN.md`

Doc 20 was later reclassified by user instruction as active transversal canon, subordinate to exact slice packs.

### 6. Repo-Truth Findings

- `interface_contracts` is correctly the DAG root.
- `protocols` is a late governed rail allowed to import runtime modules.
- Canonical profiles remain `LIGHT` and `COMPLETE`.
- Runtime modes remain `LOCAL_REPLAY`, `SHADOW`, `MICRO_LIVE`, `LIVE`.
- Build 17 queue / credential / recovery contracts exist and are exercised.
- Legacy LIGHT promotion helpers remain compatibility surface, not new profiles.

### 7. Code-vs-MD Alignment Findings

Aligned:

- typed dashboard command kinds
- sealed credential metadata
- halted/blocked profile activation gate
- recovery/warm-up blockers
- LiveComplete gate groups

Partial:

- command queue persistence is not atomic
- credential hash / sealed ref validation is weak
- LiveComplete action surface is stringly typed

### 8. File-by-File Verdict

`COMPLETE`:

- `src/interface_contracts/domain_types.py`
- `src/interface_contracts/atomic_io.py`
- `src/interface_contracts/closed_episode_contracts.py`
- `src/interface_contracts/engine_coordination_contracts.py`
- `src/interface_contracts/venue_error_contracts.py`
- `src/interface_contracts/vps_recovery_contracts.py`

`PARTIAL`:

- `src/interface_contracts/dashboard_command_contracts.py`
- `src/interface_contracts/shadow_vps_service_contracts.py`
- remaining ML / microstructure / regime contracts deferred to later package audits
- `src/protocols/dashboard_command_queue.py`
- `src/protocols/contracts_complete.py`
- `src/protocols/live_complete_runtime.py`
- `src/protocols/live_complete_dashboard.py`
- `src/protocols/promotion_gates.py`
- `src/protocols/enums.py`
- `src/protocols/contracts.py`
- remaining runtime protocol files deferred to package-specific audits

### 9. Tests / Proof Verdict

Executed:

- `python scripts/run_dag_check.py` -> PASS
- `python scripts/run_engineering_guardrails.py` -> PASS, `new_violations=0`
- core interface/protocol targeted bundle -> `404 passed`

No blind full-repo pytest was run.

### 10. P0 / P1 / P2 Findings

P0: none.

P1: none.

P2:

- non-atomic governed queue writes
- weak credential hash / sealed ref validation
- LiveComplete stringly typed action surface

### 11. Safe Next Move

Continue with Package 2 and do not patch in audit-only mode.

### 12. Module Final Status

`PARTIAL`

## Package 2 Audit

### 1. Module Scope

Audited:

- `scripts/run_shadow_vps_service.py`
- `scripts/shadow_vps_service_*.py`
- launcher-side dashboard queue consumption
- recovery / warm-up artifacts
- graceful shutdown
- Build 17 supervision refresh
- Shadow VPS state/event/monitoring surfaces

### 2. Code Files Inspected

Key files inspected:

- `scripts/run_shadow_vps_service.py`
- `scripts/shadow_vps_service_io_support.py`
- `scripts/shadow_vps_service_recovery_support.py`
- `scripts/shadow_vps_service_monitoring_support.py`
- `scripts/shadow_vps_service_projection_support.py`
- `scripts/shadow_vps_service_campaign_support.py`
- `scripts/shadow_vps_service_complete_support.py`
- `scripts/shadow_vps_service_telemetry_support.py`
- dashboard governed command launcher/queue protocol files

### 3. Document Resolution Ledger

Stable.

Doc 20 was used as active transversal canon. Newer exact packs governed concrete launcher implementation.

### 4. Authorized Governing Docs

- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`
- `34_V53_BUILD17_OPERATOR_COCKPIT_CLOSURE.md`
- `update_audit/2026-04-24_grafana_operator_queue_bridge.md`
- `update_audit/2026-04-19_shadow_vps_service_graceful_signal_shutdown.md`

### 5. Superseded / Stale Docs Ignored

Older broad launcher/runtime planning docs were not used to override Build 17 closure or exact queue bridge docs.

### 6. Repo-Truth Findings

- Dashboard queue is consumed by launcher before cycle execution.
- Halted dashboard control can skip runtime cycles.
- Recovery/warm-up reports are produced.
- Graceful signal shutdown tests exist.
- No evidence of VPS training / Optuna / LightGBM fit in launcher path.
- Grafana/operator commands do not directly place orders; they go through queue.

### 7. Code-vs-MD Alignment Findings

Aligned:

- queue consumption path
- dashboard halt gate
- recovery/warm-up startup reports
- controlled runtime gating
- no Local/Grafana direct order placement

Partial:

- plaintext Binance env bootstrap remains active
- dashboard halt event lacks structured reason codes
- recovery sealed-ref validation is weak
- some runtime evidence writes are non-atomic

### 8. File-by-File Verdict

`COMPLETE`:

- launcher command queue consumption path in `scripts/run_shadow_vps_service.py`
- graceful shutdown path
- runtime gate tests / startup report paths

`PARTIAL`:

- `scripts/shadow_vps_service_io_support.py`
- `scripts/shadow_vps_service_recovery_support.py`
- `scripts/shadow_vps_service_projection_support.py`
- `scripts/shadow_vps_service_campaign_support.py`

### 9. Tests / Proof Verdict

Executed targeted bundle:

- shadow VPS service launcher / runtime gates / signal shutdown / BS122 regression
- dashboard governed command launcher
- dashboard command queue
- VPS recovery warm-up credentials
- DAG
- guardrails

Result:

- targeted Package 2 tests: `57 passed` plus neighboring package 2 tests
- DAG: PASS
- guardrails: PASS, `new_violations=0`

### 10. P0 / P1 / P2 Findings

P0: none.

P1:

- plaintext Binance env bootstrap in `scripts/shadow_vps_service_io_support.py:201`

P2:

- dashboard halt event lacks reason codes in `scripts/run_shadow_vps_service.py:190`
- weak sealed-ref validation in `scripts/shadow_vps_service_recovery_support.py:266`
- non-atomic runtime evidence/campaign writes in:
  - `scripts/shadow_vps_service_projection_support.py:409`
  - `scripts/shadow_vps_service_campaign_support.py:457`

### 11. Safe Next Move

Continue with Package 3. Do not patch launcher/security issues in audit-only mode.

### 12. Module Final Status

`PARTIAL`

## Package 3 Audit

### 1. Module Scope

Audited:

- `src/monitoring/`
- `src/ui/`

Scope:

- Build 17 operator cockpit
- local Grafana
- dashboard queue bridge instructions
- Shadow VPS log projection
- Complete dashboard
- technical dashboard / operator controls

### 2. Code Files Inspected

All files under:

- `src/monitoring/`
- `src/ui/`

Key files:

- `src/monitoring/grafana_operator_bridge_markdown.py`
- `src/monitoring/local_grafana_dashboard.py`
- `src/monitoring/local_grafana_dashboard_build17.py`
- `src/monitoring/local_grafana_api.py`
- `src/monitoring/shadow_vps_service_log_retrieval.py`
- `src/monitoring/shadow_vps_service_monitoring_payload_support.py`
- `src/monitoring/shadow_vps_service_monitoring_observability_support.py`
- `src/ui/complete_dashboard_view.py`
- `src/ui/complete_dashboard_control_plane.py`
- `src/ui/operator_actions.py`
- `src/ui/technical_dashboard_html.py`

### 3. Document Resolution Ledger

Stable.

Doc 20 used as active transversal canon. Build 17 and Grafana queue bridge docs govern the cockpit/queue surface.

### 4. Authorized Governing Docs

- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `31_V53_SECURITY_CREDENTIALS_BUILD17_CLOSURE.md`
- `34_V53_BUILD17_OPERATOR_COCKPIT_CLOSURE.md`
- `update_audit/2026-04-24_grafana_operator_queue_bridge.md`
- `update_audit/2026-04-21_build_10_monitoring_operator_ui_repo_truth_audit.md`
- `update_audit/2026-04-17_shadow_vps_service_process_metrics_service_path.md`

### 5. Superseded / Stale Docs Ignored

Old single-dashboard / narrow monitoring narratives are stale where the Build 10 repo-truth audit says current code is broader.

### 6. Repo-Truth Findings

- Grafana bridge is observation/operator guidance only.
- Grafana does not mutate VPS state directly.
- Operator commands are routed through governed command scripts/queue.
- Credential surfaces expose metadata only.
- Recovery/warm-up/Build 17 panels are present.
- No training, Optuna, LightGBM fit, or order placement found in monitoring/UI.

### 7. Code-vs-MD Alignment Findings

Aligned:

- no direct Grafana-to-VPS mutation
- governed queue operator bridge
- sealed credential metadata in dashboard
- hard blockers visible
- Local/VPS separation respected

Partial:

- recent log and monitoring projections lack explicit redaction boundary
- Complete dashboard action surface remains stringly typed

### 8. File-by-File Verdict

`COMPLETE`:

- `src/monitoring/grafana_operator_bridge_markdown.py`
- `src/monitoring/local_grafana_dashboard.py`
- `src/monitoring/local_grafana_dashboard_build17.py`
- `src/monitoring/local_grafana_api.py`
- `src/monitoring/shadow_vps_service_monitoring.py`
- `src/monitoring/shadow_vps_service_monitoring_observability_support.py`
- `src/monitoring/shadow_vps_service_scrape_manifest.py`
- `src/monitoring/shadow_vps_scrape_discovery.py`
- `src/monitoring/process_metrics.py`
- `src/ui/operator_actions.py`
- `src/ui/complete_dashboard_control_plane.py`
- `src/ui/technical_dashboard_html.py`
- `src/ui/technical_dashboard_view.py`

`PARTIAL`:

- `src/monitoring/shadow_vps_service_log_retrieval.py`
- `src/monitoring/shadow_vps_service_monitoring_payload_support.py`
- `src/ui/complete_dashboard_view.py`
- `src/monitoring/local_lab_*` pending Package 4 semantics
- `src/monitoring/regime_detector_*` pending Package 6 semantics

### 9. Tests / Proof Verdict

Executed:

```powershell
rtk pytest -q tests/test_monitoring tests/test_ui tests/test_local_replay_runtime/test_live_complete_operator_audit_report.py tests/test_local_replay_runtime/test_ml_final_audit_report.py --tb=short --basetemp=.test_tmp\pytest_audit_package3_monitoring_ui
```

Result:

- `278 passed`

Global:

- DAG: PASS
- guardrails: PASS

### 10. P0 / P1 / P2 Findings

P0: none.

P1:

- non-redacted recent log / monitoring projection path

P2:

- Complete dashboard stringly typed actions

### 11. Safe Next Move

Continue with Package 4.

### 12. Module Final Status

`PARTIAL`

## Package 4 Audit

### 1. Module Scope

Audited:

- `src/local_replay_runtime/`

Scope:

- Local IA Lab
- local replay runtime
- artifact export
- ML training reports
- RegimeDetector local dataset/training/profile/shadow/final audit loop
- dry-run shadow handoff proof

### 2. Code Files Inspected

All files under `src/local_replay_runtime/`.

Key files:

- `src/local_replay_runtime/ml_backtest_projection.py`
- `src/local_replay_runtime/local_lab_ml_artifact_training.py`
- `src/local_replay_runtime/local_lab_regime_detector_artifact_training.py`
- `src/local_replay_runtime/regime_detector_dataset_builder.py`
- `src/local_replay_runtime/regime_detector_shadow_audit_diagnosis.py`
- `src/local_replay_runtime/regime_detector_profile_comparison.py`
- `src/local_replay_runtime/regime_detector_final_audit_report.py`
- `src/local_replay_runtime/ml_final_audit_report.py`
- `src/local_replay_runtime/artifact_exporter.py`
- `src/local_replay_runtime/artifact_release_candidate.py`
- `src/local_replay_runtime/artifact_proof_summary_builder.py`
- `src/local_replay_runtime/edge_gate_calibration.py`
- `src/local_replay_runtime/live_complete_operator_audit_report.py`

### 3. Document Resolution Ledger

Stable.

`2026-04-22_ia_lab_governed_repo_truth_closure.md` supersedes the red state of the older 2026-04-21 IA Lab slices note for the governed IA Lab base.

ML formalism remains unresolved by governing arbitration.

### 4. Authorized Governing Docs

- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `update_audit/2026-04-22_ia_lab_governed_repo_truth_closure.md`
- `update_audit/2026-04-22_ia_lab_ml_doctrine_freeze.md`
- `update_audit/2026-04-22_ml_backtest_input_spec_repo_truth.md`
- `update_audit/2026-04-22_ml_classifier_regression_arbitration.md`
- `update_audit/2026-04-23_regime_detector_feature_schema_v2.md`
- `update_audit/2026-04-23_regime_detector_feature_profiles_v1.md`
- `update_audit/2026-04-23_regime_detector_shadow_audit_and_final_report.md`

### 5. Superseded / Stale Docs Ignored

- `2026-04-21_ia_lab_slices_0_to_5.md` red-front status is historical after 2026-04-22 closure.
- Broad ML master/spec docs are subordinate to the classifier/regression arbitration.

### 6. Repo-Truth Findings

- Local replay rail is real and tested.
- Local IA Lab trains only in local runtime package / calibration methods.
- No order placement or VPS mutation found.
- ML training uses governed replay/backtest input projection.
- RegimeDetector dataset builder uses current snapshot features and future snapshots only for labels.
- RegimeDetector final/shadow audit remains non-directional.
- Artifact export uses atomic writes in the main export path.

### 7. Code-vs-MD Alignment Findings

Aligned:

- Local/VPS separation
- artifact-driven Local -> VPS handoff
- replay/backtest evidence path
- dry-run shadow candidate path
- RegimeDetector non-directional audit loop

Partial:

- ML final audit can report `ready` despite unresolved ML formalism.
- two local output writers use direct `write_text`.

### 8. File-by-File Verdict

`COMPLETE`:

- replay core files
- `artifact_exporter.py`
- `artifact_release_candidate.py`
- `artifact_proof_summary_builder.py`
- RegimeDetector local dataset/training/profile/shadow/final audit files
- `replay_state_store.py`
- `runtime_evidence.py`

`PARTIAL`:

- `local_lab_ml_artifact_training.py`
- `ml_final_audit_report.py`
- `edge_gate_calibration.py`
- `live_complete_operator_audit_report.py`

### 9. Tests / Proof Verdict

Initial sandbox and RTK attempts failed due Windows tmpdir permission errors, not functional failures.

Escalated targeted proof:

```powershell
python -m pytest -q tests/test_local_replay_runtime --tb=short --basetemp=tmp_pytest_audit_package4_escalated
```

Result:

- `179 passed`

### 10. P0 / P1 / P2 Findings

P0: none.

P1: none.

P2:

- ML final audit can report ready despite unresolved ML formalism.
- direct `write_text` in governed local output writers.

### 11. Safe Next Move

Carry the ML formalism issue into Package 6 and do not patch during audit-only run.

### 12. Module Final Status

`PARTIAL`

## Package 5 Audit

### 1. Module Scope

Audited:

- `src/data_backbone/`
- especially `src/data_backbone/microstructure/`

Scope:

- Build 2 data backbone
- websocket/rest/event normalization/freshness/consistency/router/pair-health
- microstructure math
- LOB regime features
- walls/spoofing detector

### 2. Code Files Inspected

All files under `src/data_backbone/`.

Key files:

- `src/data_backbone/microstructure/walls_and_spoofing.py`
- `src/data_backbone/microstructure/lob_regime_features.py`
- `src/data_backbone/microstructure/feature_registry.py`
- `src/data_backbone/microstructure/order_flow_imbalance.py`
- `src/data_backbone/microstructure/vpin.py`
- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/amihud_illiquidity.py`
- `src/data_backbone/microstructure/roll_spread.py`
- `src/data_backbone/microstructure/corwin_schultz_spread.py`
- `src/data_backbone/microstructure/realized_kernel_vol.py`
- `src/data_backbone/microstructure/hawkes_intensity.py`
- `src/data_backbone/microstructure/pin.py`
- `src/data_backbone/microstructure/queue_pressure.py`
- `src/data_backbone/microstructure/realized_effective_spread.py`
- `src/data_backbone/market_physics_math.py`

### 3. Document Resolution Ledger

Stable.

Exact microstructure / walls docs govern the package slice. Broad Build 2 docs are underdescriptive and classified as stale/partial narrative where they compress the current repo surface.

### 4. Authorized Governing Docs

- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `V5_3_WALLS_SPOOFING_DETECTOR_FULL_SPEC.md`
- `V5_3_CODEX_WALLS_SPOOFING_DETECTOR_PROOF_SPEC.md`
- `V5_3_CODEX_WALLS_SPOOFING_ML_INTEGRATION_PART2.md`
- `update_audit/2026-04-23_walls_and_spoofing_dual_persistence_metrics.md`
- `update_audit/2026-04-22_build_2_data_backbone_repo_truth_audit.md`

### 5. Superseded / Stale Docs Ignored

- older Build 2 summaries describing only WS / normalization / quality / pair health are stale or undercomplete.
- walls/spoofing ML Part 2 is future integration doctrine, not proof that the ML dataset/trainer is complete in Package 5.

### 6. Repo-Truth Findings

Implemented and tested:

- OFI
- VPIN
- Kyle lambda
- Amihud illiquidity
- Roll spread
- Corwin-Schultz spread
- realized kernel volatility
- Hawkes intensity
- PIN
- queue pressure
- realized/effective spread
- walls/spoofing
- LOB regime feature V1/V2 schema
- feature registry

Walls/spoofing implements:

- real wall strength
- absolute persistence
- conditional persistence
- observation coverage
- pullaway
- near-touch cancel ratio
- executed-vs-displayed
- book shape skew
- microprice pressure
- deterministic input hash
- anti-future event filtering

### 7. Code-vs-MD Alignment Findings

Aligned:

- real cancel-vs-execution logic is present
- pullaway and cancel-heavy behavior are not inferred from price only
- future events are ignored for current evaluation
- low coverage is separated from conditional persistence
- V2 schema is explicit
- no direct live stop from spoof suspicion

Partial:

- broad Build 2 narrative is stale/too compressed compared to current code.

### 8. File-by-File Verdict

`COMPLETE` for current governed microstructure scope:

- all `src/data_backbone/microstructure/*.py`
- `src/data_backbone/market_physics_math.py`
- websocket/rest/event/freshness/consistency/router/pair-health rails

`DOC_STALE`:

- broad Build 2 narrative docs that underdescribe current repo-truth surface.

### 9. Tests / Proof Verdict

Executed:

```powershell
python -m pytest -q tests/test_data_backbone tests/test_microstructure/test_paper_repro.py --tb=short --basetemp=tmp_pytest_audit_package5_data_backbone
```

Result:

- `343 passed`

### 10. P0 / P1 / P2 Findings

P0: none.

P1: none.

P2: none for code.

Documentation drift:

- broad Build 2 markdown story is narrower than current repo-truth.

### 11. Safe Next Move

Do not change microstructure code. Carry walls/spoofing ML integration questions to ML/calibration audit.

### 12. Module Final Status

`DOC_STALE` for broad Build 2 narrative.

Microstructure / walls code status: `COMPLETE`.

## Package 6 Audit

### 1. Module Scope

Audited:

- `src/complete_enablers/`

Scope:

- ML runtime enabler
- ML artifact loader
- ML promotion gate
- ML fusion
- RegimeDetector runtime
- RegimeDetector runtime loader
- Build 14 governed enablers

### 2. Code Files Inspected

All files under `src/complete_enablers/`.

Key files:

- `src/complete_enablers/ml_fusion.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/ml_runtime_artifact_loader.py`
- `src/complete_enablers/ml_model_promotion_gate.py`
- `src/complete_enablers/ml_scoring_soft_penalty_hook.py`
- `src/complete_enablers/regime_detector_runtime.py`
- `src/complete_enablers/regime_detector_runtime_loader.py`
- `src/complete_enablers/limited_influence.py`
- `src/complete_enablers/execution_fragility_score.py`
- `src/complete_enablers/false_breakout_model.py`
- `src/complete_enablers/hurst_regime_classifier.py`
- `src/complete_enablers/lob_deep_filter_vwa.py`
- `src/complete_enablers/market_toxicity_snapshot.py`
- `src/complete_enablers/micro_edge_entry_timing_layer.py`
- `src/complete_enablers/micro_edge_exit_governor.py`
- `src/complete_enablers/order_book_imbalance.py`

Related files inspected:

- `src/calibration_methods/ml_trainer.py`
- `src/interface_contracts/ml_model_artifact.py`
- `src/interface_contracts/regime_detector_artifact.py`

### 3. Document Resolution Ledger

Stable but adverse for ML.

RegimeDetector docs from 2026-04-23 are exact and current.

ML enabler is governed by the 2026-04-22 classifier/regression arbitration, which explicitly rejects the current regression-clipped-as-confidence chain as final prod-safe semantics.

### 4. Authorized Governing Docs

- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `update_audit/2026-04-22_build_14_governed_enablers_repo_truth_audit.md`
- `update_audit/2026-04-22_ml_classifier_regression_arbitration.md`
- `update_audit/2026-04-22_ml_backtest_input_spec_repo_truth.md`
- `V5_3_CODEX_ML_ENABLER_CANON_SCIENTIFIQUE_V1.md`
- `update_audit/2026-04-23_regime_detector_feature_schema_v2.md`
- `update_audit/2026-04-23_regime_detector_feature_profiles_v1.md`
- `update_audit/2026-04-23_regime_detector_shadow_audit_and_final_report.md`

### 5. Superseded / Stale Docs Ignored

ML docs demanding a broad 29-feature/classifier implementation are not canon V1 where the scientific canon marks them research/unknown.

Exact arbitration controls the current ML formalism verdict.

### 6. Repo-Truth Findings

- RegimeDetector runtime is artifact-only.
- RegimeDetector runtime does not train.
- RegimeDetector outputs are non-directional: transition risk, stability, toxicity, duration bucket.
- Runtime loader checks artifact hash, feature set version, feature hash, staleness, and shadow evidence for promotion states.
- ML scoring hook consumes artifact through `supplementary_refs`.
- ML fusion is bounded: alpha max `0.5`.
- Build 14 enablers remain limited influence and do not become autonomous engines.

### 7. Code-vs-MD Alignment Findings

Aligned:

- RegimeDetector artifact-only loader/runtime
- RegimeDetector no directional VPS semantics
- schema/hash/profile checks
- Build 14 limited influence
- ML additive score modulation point

Partial:

- ML formalism remains unresolved.
- regression output is still treated as `ml_confidence`.
- direct `ml_confidence` injection API remains exposed.

### 8. File-by-File Verdict

`COMPLETE`:

- `src/complete_enablers/regime_detector_runtime.py`
- `src/complete_enablers/regime_detector_runtime_loader.py`
- Build 14 governed reader/enabler files:
  - `competition_monitor.py`
  - `execution_fragility_score.py`
  - `false_breakout_model.py`
  - `hurst_regime_classifier.py`
  - `limited_influence.py`
  - `lob_deep_filter_vwa.py`
  - `market_toxicity_snapshot.py`
  - `micro_edge_entry_timing_layer.py`
  - `micro_edge_exit_governor.py`
  - `order_book_imbalance.py`

`PARTIAL`:

- `src/complete_enablers/ml_fusion.py`
- `src/complete_enablers/ml_runtime_artifact_loader.py`
- `src/complete_enablers/ml_scoring_soft_penalty_hook.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/ml_model_promotion_gate.py`

### 9. Tests / Proof Verdict

Executed:

```powershell
python -m pytest -q tests/test_complete_enablers tests/test_local_replay_runtime/test_regime_detector_dataset_builder.py tests/test_local_replay_runtime/test_local_lab_regime_detector_artifact_training.py tests/test_local_replay_runtime/test_regime_detector_profile_comparison.py tests/test_local_replay_runtime/test_regime_detector_shadow_audit_diagnosis.py tests/test_local_replay_runtime/test_regime_detector_final_audit_report.py tests/test_monitoring/test_regime_detector_shadow_projection.py tests/test_monitoring/test_regime_detector_shadow_audit_bundle.py tests/test_interface_contracts/test_regime_detector_artifact.py tests/test_interface_contracts/test_regime_detector_label_contracts.py tests/test_interface_contracts/test_regime_detector_shadow_audit_contracts.py --tb=short --basetemp=tmp_pytest_audit_package6_complete_enablers
```

Result:

- `88 passed`

### 10. P0 / P1 / P2 Findings

P0: none.

P1:

- ML formalism rejected by governing doc is still promotable in code.

P2:

- runtime-facing direct `ml_confidence` injection API remains exposed.

### 11. Safe Next Move

Continue with Package 7 security / credentials / venue seams.

Do not fix ML formalism until an implementation run explicitly opens that slice.

### 12. Module Final Status

`PARTIAL`

## Overall Safe Next Move

Next audit package:

- Package 7: `src/venue_adapters/` plus credential/security seams discovered under `src/`

Required focus:

- sealed Binance credentials
- no plaintext secrets in repr/dumps/logs/metrics/dashboard payloads
- fail-closed LIVE/VPS credential profile activation
- governed dashboard queue only
- recovery/warm-up blockers
- recent-log and operator report redaction

Package 1 to 6 findings should remain open until a separate implementation run is requested.

