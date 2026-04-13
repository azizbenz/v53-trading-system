# 2026-04-07 V5.3 Master Development Tracker

## Purpose

This file is the canonical development tracker for multi-session execution.
It exists to prevent context drift, false closure claims, and memory-only work.

Use this tracker together with:
- `docs/ia lab vps v5.3/2026-04-05_V53_CORPUS_WORKING_MEMORY.md`
- `docs/ia lab vps v5.3/2026-04-06_SESSION_DOCTRINE_HARD_CORE.md`

## Canon Hierarchy

Primary canon:
- `2026-04-04_V53_LOCAL_AI_LAB_FINAL_UNIQUE_CANON.md`
- `2026-04-05_V53_P0_CORPUS_FREEZE_PATCH.md`
- `2026-04-05_V53_P1_TRANSVERSE_POLICIES_PATCH.md`
- `2026-04-05_V53_P2_MATH_CORRECTION_AND_NORMALIZATION_PATCH.md`

Architecture addendum:
- `2026-04-05_V53_CANON_SHARED_CORE_DIFFERENT_SHELLS_OBSERVABILITY.md`

Execution memory only:
- `2026-04-05_V53_CORPUS_WORKING_MEMORY.md`

## Active System Invariants

- Runtime rail is `LOCAL_REPLAY -> SHADOW -> MICRO_LIVE -> LIVE`.
- Governed import/promotion currently requires `source_profile=COMPLETE`.
- No new profiles beyond canonical profiles already present in the repo.
- No bypass of `Shadow`, `Micro-live`, or `Live` gates.
- Shared-core typed governance is preferred over implicit local logic.
- Runtime safety and foundational governance take priority over UI refinement.
- No opening of `local_ai_lab`, `control_plane`, or global multihook runtime until gating foundations are closed.

## Multi-Session Anti-Hallucination Protocol

Every new session must:

1. Read this tracker.
2. Read `2026-04-05_V53_CORPUS_WORKING_MEMORY.md`.
3. Start with an explicit context brief:
   - current module
   - global invariants
   - connected modules and interface
   - forbidden defaults
   - explicit verification checklist
4. Choose exactly one bounded slice unless the slice is naturally coupled.
5. Do not mark anything `closed` without one of:
   - targeted green tests
   - code-level inspection proof for non-runtime/documentation slices
6. Update both tracker and working memory after every real slice.
7. If documentation state is corrupted or missing, rebuild it from verified code/tests before continuing runtime work.

## Status Vocabulary

- `closed`: implemented and verified
- `partial`: risk reduced, but canonical target not fully reached
- `open`: no verified closure
- `blocked`: cannot proceed without a prerequisite or deliberate decision

## Current Development Strategy

Priority order:

1. Canonical foundations
2. Typed governance
3. Runtime safety
4. Wiring on already-open rails
5. Monitoring/UI projection

Decision rules:

- If a choice opposes foundation vs visible improvement, choose foundation.
- If a choice opposes typed governance vs implicit behavior, choose typed governance.
- If a choice opposes safe VPS rail vs heavier platform opening, keep the safe VPS rail.

## Current Solution State

Closed foundations already in place:
- artifact governance baseline
- feature dictionary / transform whitelist / lineage lock
- runtime error policy on the open execution hook rail
- timestamp policy on open runtime rails
- circuit breaker gating on engine runtimes
- risk/scoring safety hardening
- typed `load_error` propagation for compiled hook plan loading
- A/B calibration governance for active `TO_CALIBRATE` surfaces
- local replay governed exports now default to `COMPLETE`, matching the governed import rail while preserving explicit `LIGHT` override only by caller choice
- completed local replay resumes are now revalidated against persisted session/manifest metadata, with launcher-side hydration of missing resume identifiers
- persisted LOCAL_REPLAY state/evidence stores now fail safe on corruption instead of silently resetting
  - `src/local_replay_runtime/replay_state_store.py` now backs up corrupted persisted session state to `.corrupted` and rebuilds with a typed `last_error`
  - `src/local_replay_runtime/runtime_evidence.py` now backs up corrupted persisted evidence state to `.corrupted`, rebuilds with a typed `last_error`, and exposes `build_state()` for audit/test verification
- upload/import dry-run governance is now deterministic: `ArtifactUploadRequest` carries an explicit `governance_reference_date` and the bridge no longer injects `date.today()`
- governed export directories now materialize typed `ReplayExecutionPlan`, `ArtifactImportRequest`, and `ArtifactUploadRequest` through `src/backtest_artifact_import/export_dir_bridge.py`
- the export-dir bridge preserves governed manifest versions from `replay_run_manifest` and reuses shared feature-lock derivation in `run_local_replay_shadow.py`
- active launcher consumers no longer rebuild governed imports locally: `run_local_replay_shadow.py` and `run_technical_dashboard.py` now reuse a shared `ReplayExecutionPlan + payload bundle -> ArtifactImportRequest` builder
- governed artifact signature policy now carries real Ed25519 public keys and a built-in pure-Python verifier on the active trust-store
- the technical dashboard and Shadow runner now consume real signed fixture envelopes on that built-in verification path, while keeping onboarding/import contracts on the same shared rail
- the technical dashboard is now the first real launcher on the active rail to consume a shared `ReplayExecutionPlan + payload bundle -> ArtifactUploadRequest` builder
- its governed demo path now flows through `ArtifactUploadRequest -> ArtifactImportRequest -> import validation -> onboarding`, with upload dry-run sidecars emitted for operator/audit proof
- the shared bridge now also exposes `ReplayExecutionPlan + replay evidence -> ArtifactExportBundle`
- the dashboard no longer builds `ArtifactExportBundle` locally
- the Shadow runner now consumes the same upload-derived import path and emits upload dry-run sidecars before Shadow validation
- TTL on upload-derived governed artifacts is now anchored on `governance_reference_date`, not replay-history timestamps
- bounded `T4` foundation slice is now landed on the Binance venue adapter rail
  - `src/venue_adapters/binance_spot/order_translator.py` now turns `ExecutionIntent` into a typed Binance Spot order request
  - `src/venue_adapters/binance_spot/error_classifier.py` now maps bounded Binance order API failure classes
  - `src/venue_adapters/binance_spot/rest_client.py` now supports signed `POST /api/v3/order`, signed `GET /api/v3/openOrders`, and signed `DELETE /api/v3/order`
  - `src/venue_adapters/binance_spot/execution_adapter.py` now provides a bounded `ExecutionVenueAdapter` implementation on top of that REST client
  - `src/venue_adapters/binance_spot/user_data_events.py` now provides a bounded authenticated user-data event source and parser for `executionReport`
  - `src/venue_adapters/binance_spot/user_data_ws_client.py` now provides a bounded authenticated websocket client for `userDataStream.subscribe.signature`
  - `src/venue_adapters/binance_spot/bootstrap.py` now builds the adapter from `BinanceAdapterConfig + credentials`, with optional injection of that websocket source
  - `src/protocols/execution_runtime_bootstrap.py` now consumes that builder via `build_binance_execution_runtime(...)`
  - `scripts/run_build9_core_smoke.py` now consumes that runtime bootstrap on a bounded local smoke path
  - replace is now modeled explicitly as cancel + submit on the adapter rail
  - remote-state reconciliation now has a minimal live bridge through `openOrders + account snapshot`
  - `poll_order_events()` now drains an injected bounded user-data source instead of staying structurally empty
  - a bounded `socket -> payloads -> event source -> execution adapter` path now exists locally
  - deterministic `clientOrderId` now uses `engine_id + intent_id`, because the governed repo contract carries `engine_id`, not `strategy_id`
  - proof:
    - `rtk pytest tests/test_venue_adapters/test_binance_spot tests/test_execution_backbone tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
    - `193 passed`
  - honest residual:
    - no real Binance Testnet submit proof yet
    - live fills/rejections/cancellations are not yet flowing from Binance events into `ExecutionRuntime`
- bounded `T5` halal-compliance slice is now advanced beyond the initial veto-only core
  - `src/sharia_compliance/contracts.py`, `policy_loader.py`, `asset_whitelist.py`, `asset_blacklist.py`, `stablecoin_policy.py`, `trade_type_guard.py`, `pair_screening.py`, `pair_screening_registry.py`, `pair_screening_audit.py`, `purification_calculator.py`, `policy_audit_logger.py`, `account_features_audit.py`, `sharia_alerts.py`, and `sharia_runtime.py` now exist
  - `src/venue_adapters/binance_spot/account_feature_provider.py` and `scripts/run_sharia_account_audit.py` now land the bounded Binance read-only provider + weekly audit launcher path
  - `scripts/run_sharia_pair_screening_audit.py` now lands a bounded HC-4 launcher path for traded-pair screening checks against a versioned local registry
  - `config/sharia/policy_v1.yml` now carries the active conservative spot-halal policy root
  - `src/execution_backbone/execution_runtime.py` now calls `sharia_trade_authorizer.authorize_trade()` before any venue submit
  - `NoTradeReason.SHARIA_BLOCKED` now exists on the execution runtime rail
  - `trade_type_guard.py` now enforces deterministic AAOIFI pair-screening from `opportunity.metadata["pair_screening"]`, with explicit fail-close reasons for invalid, missing, mismatched, or failed screening evidence
  - proof:
    - `rtk pytest tests/test_sharia_compliance/test_purification_calculator.py tests/test_sharia_compliance/test_account_features_audit.py -q`
    - `6 passed`
    - `rtk pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_account_feature_provider.py tests/test_sharia_compliance/test_account_features_audit.py tests/test_sharia_compliance/test_account_features_audit_launcher.py -q`
    - `13 passed`
    - `rtk pytest tests/test_sharia_compliance/test_sharia_alerts.py tests/test_sharia_compliance/test_account_features_audit_launcher.py tests/test_venue_adapters/test_binance_spot/test_account_feature_provider.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
    - `11 passed`
    - `python -m pytest tests/test_sharia_compliance/test_pair_screening.py tests/test_sharia_compliance/test_trade_type_guard.py tests/test_execution_backbone/test_execution_runtime.py -q`
    - `31 passed`
    - `python -m pytest tests/test_sharia_compliance/test_pair_screening_registry.py tests/test_sharia_compliance/test_pair_screening_audit.py tests/test_sharia_compliance/test_pair_screening_audit_launcher.py tests/test_sharia_compliance/test_pair_screening.py tests/test_sharia_compliance/test_trade_type_guard.py tests/test_execution_backbone/test_execution_runtime.py -q`
    - `37 passed`
    - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py -q`
    - `39 passed`
    - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py -q`
    - `29 passed`
    - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py tests/test_venue_adapters/test_binance_spot tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
    - `82 passed`
    - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone tests/test_venue_adapters/test_binance_spot tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
    - `208 passed`
  - honest residual:
    - no real Testnet proof yet for the weekly audit launcher
    - no kill switch or external alert backend is wired from the emitted `AlertRecord`s yet
    - no live/external provider is wired yet to feed AAOIFI pair-screening snapshots automatically; the bounded local dataset registry now exists
- bounded Build-17 Complete pair-scope selection is now wired on the local dashboard launcher rail
  - `scripts/run_complete_dashboard.py` now accepts governed `--pair` and `--pair-count` selection over the canonical 12-pair COMPLETE universe
  - `src/ui/complete_dashboard_view.py` now projects `selected_pairs`, `available_pairs`, and `pair_selection_source` explicitly
  - the selected scope now propagates consistently to HTML, payload JSON, view JSON, and supplement JSON instead of remaining a local-only launcher filter
  - proof:
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py -q`
    - `6 passed`
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py -q`
    - `67 passed`
- bounded Build-17 Complete pair-scope assistant is now clickable in the local HTML without breaking runtime truth
  - `src/ui/technical_dashboard_html.py` now accepts optional injected local control sections/scripts
  - `scripts/run_complete_dashboard.py` now renders a `Governed Complete Pair Selection` panel with canonical pair checkboxes, `first N` helper, and copyable PowerShell relaunch command
  - the current dashboard payload does not mutate in-browser; the page now makes the required relaunch explicit instead of pretending to re-scope runtime state client-side
  - proof:
    - `rtk pytest tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_complete_dashboard_launcher.py -q`
    - `8 passed`
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_monitoring/test_monitoring_backend.py -q`
    - `69 passed`
- bounded `13-A / T6-prep` Local IA Lab EDGE calibration slice is now real
  - `src/local_replay_runtime/edge_gate_calibration.py` now calibrates `THR-E01` and `THR-E02` from governed replay `DTRRecord` evidence
  - publication is conservative: upper bootstrap CI bound + human floor, with explicit failure on weak evidence
  - `build_edge_gate_calibration_artifact(...)` now converts that report into a shared `CalibrationArtifact`
  - `scripts/run_edge_gate_calibration.py` now reads governed `replay_dtr.jsonl` evidence and writes a signed `edge_gate.yml` artifact
  - `scripts/run_local_replay_export.py` now exposes the same emission path behind `--emit-edge-calibration`
  - `src/scoring_backbone/fee_aware_edge_gate.py` now exists as the exact future consumer surface resolved through `calibration_loader`
  - current scope is intentionally bounded:
    - Local IA Lab/backtest producer exists
    - shared artifact shape exists
    - dedicated launcher exists
    - the main governed replay-export launcher can emit the artifact explicitly
    - future scoring/runtime consumer exists as pure helper
    - no runtime wiring has been added yet
  - proof:
    - `rtk pytest tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
    - `18 passed`
    - `rtk pytest tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_artifact_exporter.py tests/test_scoring_backbone/test_scoring_runtime.py -q`
    - `23 passed`
- bounded Local IA Lab EDGE calibration launcher now ingests governed export directories directly
  - `scripts/run_edge_gate_calibration.py` now accepts `--export-dir` as an alternative to raw `--replay-dtr-path`
  - it recovers replay provenance through `discover_local_replay_export(...)` before calibrating `THR-E01` / `THR-E02`
  - it now emits `edge_gate.input_summary.json` beside the YAML artifact as the future-facing audit/dashboard sidecar
  - proof:
    - `rtk pytest tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
    - `19 passed`
- bounded Local IA Lab post-trade review launcher is now safe on direct script execution
  - `scripts/run_local_lab_post_trade_review.py` now bootstraps `src/` internally instead of relying on ambient `PYTHONPATH`
  - this matches the governed launcher pattern already used by `run_local_replay_export.py`, `run_local_replay_shadow.py`, and `run_technical_dashboard.py`
  - direct invocation regression now exists in `tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py`
  - proof:
    - `rtk pytest tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py tests/test_meta_minimal/test_meta_runtime.py tests/test_meta_learning/test_build9x_integration.py tests/test_meta_learning/test_replay_bundle_and_persistence.py -q`
    - `17 passed`
- bounded Local IA Lab post-trade review launcher now ingests governed export directories directly
  - `scripts/run_local_lab_post_trade_review.py` now accepts `--export-dir` as an alternative to raw `--replay-dtr`
  - the launcher now uses `discover_local_replay_export(...)` to recover governed manifest + payload refs before rebuilding Build-9 reports
  - it now emits a future-facing provenance sidecar `governed_input_summary.json` for later dashboard/monitoring use
  - when fed from `export_dir`, `total_opportunities` now defaults from `ReplayRunManifest.record_count`
  - proof:
    - `rtk pytest tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py tests/test_meta_minimal/test_meta_runtime.py tests/test_meta_learning/test_build9x_integration.py tests/test_meta_learning/test_replay_bundle_and_persistence.py -q`
    - `18 passed`
- bounded Local IA Lab chained analysis launcher now exists on the governed export rail
  - `scripts/run_local_lab_analysis_bundle.py` now chains `export_dir -> post_trade_review -> edge_calibration`
  - it reuses the already-governed launchers instead of creating a parallel Lab path
  - it emits `local_lab_analysis_summary.json` as the future-facing summary for a Local IA Lab dashboard / monitoring surface
  - it now also emits a canonical `artifact_proof_summary.json` and a conservative `artifact_proof_assessment.json`
  - it now also supports governed multi-scope analysis with `--all-scopes`
  - `src/local_replay_runtime/local_lab_scope_matrix.py` now provides the typed `pair x engine` matrix surface
  - the same launcher can now emit `local_lab_scope_matrix.json` plus per-scope subdirectories under `output-root/scopes/<pair>__<engine>/`
  - each scope now carries its own:
    - `post_trade_review/`
    - `artifact_ablation_study.json`
    - `artifact_proof_summary.json`
    - `artifact_proof_assessment.json`
  - the multi-scope path remains fail-close:
    - scope `total_opportunities` is recomputed from the scope evidence itself
    - walk-forward approval stays human-gated and global to the analyzed export
    - no scope becomes `ready` without aligned baseline evidence
  - `src/local_replay_runtime/artifact_release_candidate.py` now provides the packaging-side Local IA Lab release verdict
  - the same launcher now emits `artifact_release_candidate.json`
  - that sidecar does not yet build the VPS import request directly; it bounds the bridge with:
    - `release_status`
    - `ready_for_shadow_import`
    - `blocking_reasons`
    - `release_scopes` when a multi-scope matrix exists
  - `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now provides the next bounded step:
    - `release_candidate -> ArtifactUploadRequest / ArtifactImportRequest` dry-run bridge
  - the same launcher now emits:
    - `artifact_import_dry_run_bridge.json`
    - `artifact_upload_request.dry_run.json`
    - `artifact_import_request.dry_run.json`
    - `artifact_import_decision.dry_run.json`
    - `artifact_upload_decision.dry_run.json`
  - this bridge stays fail-close:
    - no hidden governance-date fallback
    - no implicit artifact class/scope
    - no payload materialization while the release candidate is still blocked
  - this bridge now also makes the current semantic limitation explicit:
    - source artifact = Local IA Lab calibration artifact
    - transport artifact = current replay-derived governed `review_packet`
    - the sidecar now projects that duality instead of silently treating them as one artifact identity
  - honest residual:
    - current semantics still ride on the existing governed replay/import rail
    - final live packaging semantics for future calibration artifacts remain open
  - the proof layer is fail-close by construction:
    - present evidence is projected into typed proof dimensions
    - missing ablation evidence is surfaced as explicit validation failure, not hidden fallback
  - the bundle summary now carries `artifact_proof_ready` plus typed `artifact_proof_validation_reasons`
  - direct script execution now bootstraps both `REPO_ROOT` and `src/`
  - proof:
    - `python -m pytest tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py tests/test_meta_minimal/test_meta_runtime.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
    - `32 passed`
    - `python -m pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
    - `282 passed`
    - `python -m pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
    - `87 passed`
- `BS-44` is now closed on the bounded `portfolio_minimal` surface by requiring an explicit `freshness_policy` at the orchestrator boundary
- `BS-38` semantic Shadow recovery now rebuilds counter and registry continuity from durable day records after counter/registry corruption on the active Shadow runner rail
- `BS-49` is now closed on the bounded doctrine/name surface
  - active UI public names now expose `LockedOperator*` first, with `Light*` kept as explicit compatibility aliases
  - active protocol public names now expose `Live*` first, with `LiveLight*` kept as explicit compatibility aliases
  - monitoring runtime and technical payload builders now accept canonical `locked_operator_ui_runtime` / `live_projection` surfaces while preserving legacy aliases
  - canonical tests now exercise those new names directly
- the technical dashboard now renders an explicit `Build-10` section and `Build-10 Technical Supervision` navigation in HTML
- top-level canon docs now align with the governed runtime rail on Build-11 / Build-12 / Build-13
- secondary navigation docs and prompt-pack guidance now also carry explicit active-reading notes for the governed `COMPLETE` rail
- the fifth real hook/runtime slice is now also open on the active rail: `ENGINE_A_PRE_ENTRY_CONFIRMATION -> compiled bridge -> Engine A runtime -> bounded pre-scoring block`
- multiple BS slices on `execution_backbone`, `data_backbone`, and `shadow/protocols`

Still intentionally not opened:
- `local_ai_lab`
- `control_plane`
- global multihook executor
- new live hooks beyond the currently opened bounded slices `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, and `EXECUTION_NO_TRADE_FILTER`

Practical path toward IA Lab:
- use `src/local_replay_runtime` as the real entry rail
- carry evidence through governed export bundles into `src/backtest_artifact_import`
- continue into VPS `SHADOW` before asking for a separate `local_ai_lab` package

## Remaining Work By Priority

### Now

1. Restore stable documentation handoff discipline after corruption of tracker/memory files.
2. Continue bounded convergence on the real IA Lab entry rail `local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`.
3. Keep proof of closure attached to each slice.

### Next

1. the practical IA Lab entry rail now has a stable end-to-end proof; choose the next deliberate perimeter instead of more plumbing
2. choose the next real runtime perimeter after the hardened artifact rail, semantic Shadow recovery, doctrine/name convergence, and the fifth opened hook slice
   - remaining `shadow/protocols` backlog
   - or a non-engine deliberate hook/runtime slice
3. `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md` is now delivered
   - topology is now fixed as: `Local IA Lab` for calibration/backtest/proof, `VPS` for runtime consumption/execution
   - `src/calibration_loader/` is shared core, not duplicated
   - the runtime target remains `single active VPS`
   - a future `multi-VPS` concept is accepted only as a read-only fleet overview `health / runtime_mode / artifact_version / heartbeat / alert_state`
   - detailed diagnosis still happens by connecting to the selected VPS directly
   - no active multi-VPS control plane, orchestration, or failover loop should be opened from this alone
   - future bounded plan for that concept:
      - M0: doc/contract slice for fleet summary fields only (`vps_id`, `health_status`, `runtime_mode`, `artifact_version`, `heartbeat_age`, `alert_state`)
      - M1: read-only overview projection in monitoring/UI
      - M2: per-VPS drill-down entry point only; details still live on the selected VPS
      - never add remote execution or cross-VPS promotion in these slices
   - M0 is now closed in code:
     - `src/monitoring/contracts.py` exposes `FleetNodeProjection` and `FleetOverviewProjection`
     - the slice is contract-only/read-only with unique `vps_id` validation and `active_vps_id` validation
     - proof:
       - `rtk pytest tests/test_monitoring/test_monitoring_contracts.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_technical_dashboard.py -q`
       - `73 passed`
   - threshold-consumer inventory is now done in `docs/production_deployment_plan/11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md`
   - shared calibration contracts/loaders are now done in `src/calibration_loader/`
   - continued hardening of the real IA Lab rail remains the preferred code work until a new bounded perimeter is explicitly chosen
   - latest closed slice on that rail: corrupted LOCAL_REPLAY resume metadata and chunk-session files now back up to `.corrupted` and fail closed explicitly in `src/local_replay_runtime/replay_orchestrator.py`
   - latest closed slice after that: `src/backtest_artifact_import/export_dir_bridge.py` now backs up and rejects corrupted governed export sidecars across the real export bundle (`replay_run_manifest.json`, `feature_bridge.json`, `parity_diagnostics.json`, `replay_metrics.json`, `replay_dtr.jsonl`)
   - the bridge now validates `parity_diagnostics`, `replay_metrics`, and `replay_dtr` against typed contracts instead of generic JSON parsing
   - latest closed slice after that: the same bridge now rejects semantically contradictory exports even when every sidecar is JSON-valid
     - `review_export.md` provenance fields must stay aligned with manifest / metrics / parity sidecars
     - `feature_bridge.dataset_id` must match `replay_run_manifest.dataset_manifest_id`
     - `feature_bridge.feature_set_version` must match `replay_run_manifest.feature_set_version`
     - `feature_bridge.transform_set_version` must match `replay_run_manifest.transform_set_version`
     - `feature_bridge.pairs` / `feature_bridge.engines` must match manifest `tested_pairs` / `engine_scope`
     - `parity_diagnostics.dataset_id` must match `replay_run_manifest.dataset_manifest_id`
     - `replay_metrics.total_records` must match the real `replay_dtr` count
     - `pair_aggregates` / `engine_aggregates` must sum to `total_records`
     - `replay_metrics` and `replay_dtr` must stay within manifest `tested_pairs` / `engine_scope`
     - `replay_dtr.runtime_mode` must stay `local_replay`
     - `replay_dtr` timestamps must stay within the manifest clock range
     - `replay_metrics` must remain exactly recomputable from the exported `DTRRecord` set
4. keep the `engine_c / engine_d` structural asymmetry in the deliberate backlog
   - current code truth: `engine_c` and `engine_d` are functionally valid on the canonical `engine -> scoring -> risk` rail
   - current package truth: they are materially less factorized than `engine_a` and `engine_b`
   - if opened, treat this as an auditability/readability extraction slice, not as a runtime-rescue rewrite

### Later

1. Third real hook opening after the current governance rail is sufficiently justified
2. Additional remaining `BS-*` items not yet verified closed
3. Documentation realignment if the external corpus is patched again
4. Engine C / D factorization parity plan
   - likely Engine C extraction targets: structure resolver, continuation evaluator, fake-breakout filter, cost-feasibility checker, conviction builder, invalidation mapper, signal reporter
   - likely Engine D extraction targets: history scorer, reformation validator, marginal-edge evaluator, concentration blocker, cost-feasibility checker, conviction builder, invalidation mapper, signal reporter
   - invariant: preserve current runtime behavior and canonical contracts while improving auditability parity with `engine_a` / `engine_b`

## Verified BS Register

### Closed

- `BS-34` timestamp default `0.0` removed from open runtime rails
- `BS-36` rollout sequence corrected to `complete -> micro_live -> live`
- `BS-37` `check_all_gates` includes micro-live gate
- `BS-42` source-scoped divergence thresholds
- `BS-45` shadow ledger distinguishes accepted vs counted slot state
- `BS-47` no silent `now or time.time()` fallback in shadow counter
- `BS-48` shadow counter state frozen / rebuilt instead of mutated in place
- `BS-50` execution terminal state retention bounded
- `BS-51` typed dust/tolerance reconciliation policies
- `BS-53` typed adverse-selection delay policy
- `BS-54` dead backpressure action removed
- `BS-55` deterministic priority dispatch ordering
- `BS-56` exchange staleness blocks in shadow
- `BS-57` reverse skew no longer masked by signed delta semantics
- `BS-58` contradiction retention bounded
- `BS-59` deterministic replacement intent ids
- `BS-60` zero-division no longer silently returns zero
- `BS-61` explicit Decimal -> float64 loss boundary
- `BS-62` DTR crash protection
- `BS-65` fail-safe shadow registries
- `BS-66` no HTTP in execution hot path
- `BS-46` FD leak checks now enforce a suite-level absolute ceiling in addition to local delta tolerance
- `BS-52` explicit Build-14 typed contract checks in `live_light_runtime`
- `BS-41` shadow import / slot session-date consistency
- `BS-68` shadow session registry rollback on persist failure
- `BS-44` explicit freshness policy required at `portfolio_orchestrator` boundary
- `BS-67` DTRStore lookup helpers moved off full-list scans via append-only secondary indexes
- `BS-40` real Ed25519 artifact verification with real trust-store keys and built-in verifier on the governed import rail
- `BS-38` semantic Shadow recovery now rebuilds counter/registry continuity from durable day records after corruption on the active runner rail
- `BS-49` canonical `LockedOperator*` / `Live*` public surfaces now lead, with historical `Light*` / `LiveLight*` names kept only as explicit compatibility aliases
- `BS-87` active engine runtimes now require explicit `EmergencyCircuitBreaker` injection and no longer keep a permissive `None` path in constructor signatures
- `BS-85` engine C no longer crashes on implicit `next(...)`
- `BS-92` manual pair suspension now has an explicit audited path via `suspend_manual()` and no longer relies on ad hoc `SuspensionDecision(reason=MANUAL)` construction
- `BS-89` negative or zero REST bootstrap gaps now fail closed instead of silently triggering gap fill
- `BS-88` phantom detection now requires a positive expected-cost baseline and no longer misfires or overclaims when `expected_cost <= 0`
- `BS-86` active engine runtime inputs now reject Unix-second timestamps and enforce millisecond-scale `timestamp_ms`
- `BS-90` REST resync now reserves quota atomically at `record_call()` time and no longer ignores a post-check rate-limit failure
- `BS-93` pair-health suspension no longer hides a universal `0.3` threshold default on the health-based path
- `BS-91` rate-limit pruning now runs in-place on a deque and no longer reallocates a full list on each window trim
- `BS-80` beta governance no longer accepts a universal fallback `0.8`; active mappings are explicit, timestamped, and stale-beta mappings fail closed on the risk rail
- `BS-81` drawdown `REDUCE_EXPOSURE` is already enforced on the active risk runtime rail and no longer remains purely advisory
- `BS-83` unknown portfolio clusters now fail closed as mapping errors instead of being masked as `remaining=0.0`
- `BS-82` Build-8 portfolio selection now rejects unknown cluster mappings before allocation instead of silently capping them to `0`
- `BS-78` Engine A and Engine B now share the same governed market-physics penalty weights for `fragility`, `toxicity`, and `micro_friction`
- `BS-77` Engine B no longer defaults missing `false_breakout_score` to optimistic `0.0`; the governed default is now neutral `0.5`
- `BS-84` websocket reconnect now closes the stale client before replacing the endpoint entry
- `BS-35` hook runtime-open governance is now centralized: `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`, and `EXECUTION_NO_TRADE_FILTER` are declared runtime-open from a single canonical source of truth consumed by all hook modules
### Partial

- none on the currently remapped bounded backlog
### Open Or Unverified

- `BS-39` closed previously, but must remain watched after future shadow slot edits
- `BS-64` closed previously, but must remain watched after future venue-cache edits
- `BS-79` closed by deleting dead abstraction; watch for accidental reintroduction

### Audit-Remapped / Explicit Perimeter Change Required

- `BS-43`
  - mapped by `docs/ia lab vps v5.3/angle mor audit calude sonets .docx`
  - current code surface: `src/interface_contracts/atomic_io.py`
  - audit snapshot is stale: current `atomic_write_json()` no longer uses `default=str`
  - treat as closed by current code state
- `BS-46`
  - mapped by `docs/ia lab vps v5.3/angle mor audit calude sonets .docx`
  - current code surface: `src/smoke_bootstrap_recovery/state_sanity_checker.py`
  - audit snapshot was valid on remap, but current code now combines the local delta tolerance with a suite-level absolute FD ceiling
  - treat as closed by current code state
- `BS-63`
  - mapped by `docs/ia lab vps v5.3/angle mor audit calude sonets .docx`
  - current code surface: `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - audit snapshot is stale: current code no longer re-serializes every record on each flush
  - treat as effectively closed by the already-verified `BS-62` fix set
- `BS-67`
  - mapped by `docs/ia lab vps v5.3/angle mor audit calude sonets .docx`
  - current code surface: `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - audit snapshot was valid on remap, but current code now uses append-only secondary indexes
  - treat as closed by current code state

Current evidence:
- the Sonnet audit docx recovers the missing mapping
- 2026-04-08 code cross-check confirms `BS-43`, `BS-46`, `BS-63`, and `BS-67` are now all corrected relative to the older audit snapshots
- targeted supporting proof:
  - `rtk pytest tests/test_interface_contracts/test_atomic_io.py tests/test_meta_minimal/test_bs62_dtr_crash_protection_regression.py tests/test_smoke_bootstrap_recovery/test_state_sanity.py -k "not test_dag_clean_passes" -q`
  - `41 passed`
  - `rtk pytest tests/test_meta_minimal/test_meta_minimal.py tests/test_meta_minimal/test_bs62_dtr_crash_protection_regression.py tests/test_meta_minimal/test_bs67_dtr_store_index_regression.py tests/test_regression_alignment.py -k "TestTracePersistenceLayer or TestDTRFlushToDisk or bs62 or bs67" -q`
  - `21 passed`
  - `rtk pytest tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py -k "fd_leak or resource_release_checker" -q`
  - `5 passed`

Rule:
- do not call these ids `unmapped` anymore
- do not treat them as `shadow/protocols` items
- all four remapped ids are now closed unless the current code regresses

## Current Session Resume Point

If a new session starts from this tracker, resume here unless a higher-severity blocker appears:

1. Start from the real IA Lab entry rail `local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`
2. The concrete `export_dir -> ArtifactUploadRequest / ArtifactImportRequest` builder is now closed, launcher-side ad hoc import builders are removed, the dashboard no longer builds `ArtifactExportBundle` locally, the Shadow runner now consumes the upload-derived import rail, and `BS-40` is now closed on the bounded artifact-signature surface
3. `BS-38`, `BS-44`, `BS-49`, `BS-77`, `BS-78`, `BS-81`, `BS-82`, `BS-83`, `BS-84`, `BS-86`, `BS-88`, `BS-89`, `BS-90`, `BS-91`, `BS-92`, and `BS-93` are now closed on their bounded active surfaces; choose the next deliberate runtime perimeter instead of reopening compatibility cleanup by habit
4. the second real hook/runtime slice is now open on the active rail:
   - `src/protocols/engine_b_sweep_validation_bridge.py`
   - `src/protocols/engine_b_hooks.py`
   - `src/engines/engine_b/engine_b_runtime.py`
   - `src/scoring_backbone/scoring_runtime.py`
   - active behavior is still bounded: one typed Engine B hook, fail-open bridge semantics, and no global multihook executor
5. Reuse the `BS-41` proof set if slot/session-date semantics are touched again
6. Reuse the Sonnet-audit remap: `BS-43`, `BS-46`, `BS-63`, and `BS-67` are all corrected in current code
7. If the next deliberate perimeter is `engine_c / engine_d`, start from structure/readability parity, not from a claim that C/D are runtime-incomplete
8. The first bounded readability slices on that perimeter are now closed on `engine_c` and `engine_d`
   - `engine_c_runner.py` now delegates structure resolution and signal-math stages to helper modules
   - `engine_d_runner.py` now delegates context resolution and signal-math stages to helper modules
   - no thresholds, reason codes, or runtime contracts were changed
   - the second bounded readability slice is now also closed on `engine_c` and `engine_d`, covering cost / conviction / invalidation helpers
   - the third bounded readability slice is now also closed on `engine_c` and `engine_d`, covering final output payload assembly
   - no further bounded readability slice is currently justified on that perimeter without a broader refactor goal
9. Update tracker + working memory

## Latest Closure Proof

Latest bounded eighth real hook/runtime opening proof:

- `src/interface_contracts/artifact_contracts.py`
  - `RUNTIME_OPEN_HOOK_IDS` now governs eight active bounded slices: `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/portfolio_hooks.py`
  - now exposes a real bounded executor surface for `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT` instead of a permanent `NotImplementedError` skeleton
- `src/protocols/portfolio_relative_rank_adjustment_bridge.py`
  - now provides the compiled-plan fail-open bridge for `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`
- `src/portfolio_minimal/portfolio_orchestrator.py`
  - now accepts a typed relative-rank hook and reapplies deterministic reranking before `resolve_selection`
- `src/monitoring/technical_dashboard_backend.py`, `src/monitoring/observability.py`, `src/ui/technical_dashboard_view.py`, and `src/protocols/execution_runtime_dashboard.py`
  - Build-10 monitoring now projects the full eight-hook compiled bridge set through a typed `runtime_hook_bridges` surface instead of exposing only the execution no-trade bridge
  - the technical dashboard now renders a dedicated `Artifact Hooks` section and observability exports per-hook bridge status/configured/binding/loaded/artifact-count metrics
- targeted proof:
  - `rtk pytest tests/test_portfolio_minimal/test_portfolio_minimal.py tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_portfolio_relative_rank_hook.py tests/test_protocols/test_portfolio_relative_rank_adjustment_bridge.py -q`
  - `102 passed`

Latest bounded seventh real hook/runtime opening proof:

- `src/interface_contracts/artifact_contracts.py`
  - `RUNTIME_OPEN_HOOK_IDS` now governs seven active bounded slices: `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/scoring_hooks.py`
  - now exposes a real bounded executor surface for `SCORING_SOFT_PENALTY_LAYER` instead of a permanent `NotImplementedError` skeleton
- `src/protocols/scoring_soft_penalty_layer_bridge.py`
  - now provides the compiled-plan fail-open bridge for `SCORING_SOFT_PENALTY_LAYER`
- `src/scoring_backbone/scoring_runtime.py`
  - now accepts a typed soft-penalty hook and applies bounded `raw_score_multiplier / raw_score_add / raw_score_cap` adjustments before `calculate_raw_score`
- targeted proof:
  - `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_scoring_soft_penalty_hook.py tests/test_protocols/test_scoring_soft_penalty_layer_bridge.py -q`
  - `26 passed`

Latest bounded sixth real hook/runtime opening proof:

- `src/interface_contracts/artifact_contracts.py`
  - `RUNTIME_OPEN_HOOK_IDS` now governs six active bounded slices: `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/risk_hooks.py`
  - now exposes a real bounded executor surface for `RISK_MICRO_FRICTION_PRECHECK` instead of a permanent `NotImplementedError` skeleton
- `src/protocols/risk_micro_friction_precheck_bridge.py`
  - now provides the compiled-plan fail-open bridge for `RISK_MICRO_FRICTION_PRECHECK`
- `src/risk_backbone/risk_runtime.py`
  - now accepts a typed micro-friction precheck hook and can reject before the severe-pressure fallback without bypassing the canonical Build-4 runtime chain
- targeted proof:
  - `rtk pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_risk_micro_friction_hook.py tests/test_protocols/test_risk_micro_friction_precheck_bridge.py -q`
  - `36 passed`

Latest bounded fifth real hook/runtime opening proof:

- `src/interface_contracts/artifact_contracts.py`
  - `RUNTIME_OPEN_HOOK_IDS` now governs five active bounded slices: `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/engine_a_hooks.py`
  - now exposes a real bounded executor surface for `ENGINE_A_PRE_ENTRY_CONFIRMATION` instead of a permanent `NotImplementedError` skeleton
- `src/protocols/engine_a_pre_entry_confirmation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_A_PRE_ENTRY_CONFIRMATION`
- `src/engines/engine_a/engine_a_runtime.py`
  - now accepts a typed pre-entry validation hook and can block before scoring without bypassing the canonical runtime chain
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_a_pre_entry_hook.py tests/test_protocols/test_engine_a_pre_entry_confirmation_bridge.py tests/test_engines/test_engine_a/test_engine_a_runtime.py -q --basetemp=build/pytest-engine-a-pre-entry-hook`
  - `26 passed`

Latest bounded fourth real hook/runtime opening proof:

- `src/interface_contracts/artifact_contracts.py`
  - `RUNTIME_OPEN_HOOK_IDS` now governs four active bounded slices: `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/engine_c_hooks.py`
  - now exposes a real bounded executor surface for `ENGINE_C_VOID_VALIDATION` instead of a permanent `NotImplementedError` skeleton
- `src/protocols/engine_c_void_validation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_C_VOID_VALIDATION`
- `src/engines/engine_c/engine_c_runtime.py`
  - now accepts a typed void-validation hook and can block before scoring without bypassing the canonical runtime chain
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_c_void_hook.py tests/test_protocols/test_engine_c_void_validation_bridge.py tests/test_engines/test_engine_c/test_engine_c_runtime.py -q --basetemp=build/pytest-engine-c-void-hook`
  - `24 passed`

Latest bounded third real hook/runtime opening proof:

- `src/interface_contracts/artifact_contracts.py`
  - `RUNTIME_OPEN_HOOK_IDS` now governs three active bounded slices: `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/engine_d_hooks.py`
  - now exposes a real bounded executor surface for `ENGINE_D_REENTRY_VALIDATION` instead of a permanent `NotImplementedError` skeleton
- `src/protocols/engine_d_reentry_validation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_D_REENTRY_VALIDATION`
- `src/engines/engine_d/engine_d_runtime.py`
  - now accepts a typed re-entry validation hook and can block before scoring without bypassing the canonical runtime chain
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_d_reentry_hook.py tests/test_protocols/test_engine_d_reentry_validation_bridge.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q --basetemp=build/pytest-engine-d-reentry-hook`
  - `24 passed`

Latest bounded `engine_d` factorization pass-3 proof:

- `src/engines/engine_d/output_payload_builder_d.py`
  - now carries the bounded final `EngineDOutput` payload assembly extracted from the runner
- `src/engines/engine_d/engine_d_runner.py`
  - now delegates final output-payload construction to the helper while preserving the same thresholds, reason codes, and output contract
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py -q --basetemp=build/pytest-engine-d-final-assembly`
  - `26 passed`

Latest bounded `engine_c` factorization pass-3 proof:

- `src/engines/engine_c/output_payload_builder_c.py`
  - now carries the bounded final `EngineCOutput` payload assembly extracted from the runner
- `src/engines/engine_c/engine_c_runner.py`
  - now delegates final output-payload construction to the helper while preserving the same thresholds, reason codes, and output contract
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-c-final-assembly`
  - `21 passed`

Latest bounded `engine_d` factorization pass-2 proof:

- `src/engines/engine_d/cost_feasibility_d.py`
  - now carries the bounded economic-feasibility calculations extracted from the runner
- `src/engines/engine_d/conviction_builder_d.py`
  - now carries the bounded conviction/tier computation extracted from the runner
- `src/engines/engine_d/invalidation_mapper_d.py`
  - now carries the bounded stop/target/risk-multiple mapping extracted from the runner
- `src/engines/engine_d/engine_d_runner.py`
  - now delegates cost, conviction, and invalidation stages to helper modules while preserving the same thresholds, reason codes, and output contract
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py -q --basetemp=build/pytest-engine-d-factorization-pass2`
  - `26 passed`

Latest bounded `engine_c` factorization pass-2 proof:

- `src/engines/engine_c/cost_feasibility_c.py`
  - now carries the bounded economic-feasibility calculations extracted from the runner
- `src/engines/engine_c/conviction_builder_c.py`
  - now carries the bounded conviction/tier computation extracted from the runner
- `src/engines/engine_c/invalidation_mapper_c.py`
  - now carries the bounded stop/target/risk-multiple mapping extracted from the runner
- `src/engines/engine_c/engine_c_runner.py`
  - now delegates cost, conviction, and invalidation stages to helper modules while preserving the same thresholds, reason codes, and output contract
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-c-factorization-pass2`
  - `21 passed`

Latest bounded `engine_d` factorization proof:

- `src/engines/engine_d/context_resolver_d.py`
  - now carries the bounded context-resolution and Engine-A-overlap logic extracted from the runner
- `src/engines/engine_d/signal_math_d.py`
  - now carries the bounded history/context/reformation/marginal-value scoring math extracted from the runner
- `src/engines/engine_d/engine_d_runner.py`
  - now delegates those pure calculations to helper modules while preserving the same thresholds, reason codes, and output contract
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-d-factorization`
  - `21 passed`

Latest bounded `engine_c` factorization proof:

- `src/engines/engine_c/structure_resolver_c.py`
  - now carries the bounded structure-resolution and Engine-A-overlap context logic extracted from the runner
- `src/engines/engine_c/signal_math_c.py`
  - now carries the bounded breakout/context/continuation/fake-breakout scoring math extracted from the runner
- `src/engines/engine_c/engine_c_runner.py`
  - now delegates those pure calculations to helper modules while preserving the same thresholds, reason codes, and output contract
- targeted proof:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-c-factorization`
  - `21 passed`

Latest bounded second real hook/runtime opening proof:

- `src/protocols/engine_b_sweep_validation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_B_SWEEP_VALIDATION`
- `src/protocols/engine_b_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/engines/engine_b/engine_b_runtime.py`
  - now accepts a typed sweep-validation hook and can block or adjust score before scoring
- `src/scoring_backbone/scoring_runtime.py`
  - now supports bounded raw-score multiplier/add/cap adjustments as an explicit contract surface
- targeted proof:
  - `rtk pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_b_sweep_hook.py tests/test_protocols/test_engine_b_sweep_validation_bridge.py -q`
  - `17 passed`
- coupled runtime proof:
  - `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q`
  - `21 passed`
- broader cross-check:
  - `rtk pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q`
  - `83 passed`
  - canonical `locked_operator_ui_runtime` and `live_projection` inputs are now accepted directly
  - legacy `light_ui_runtime` and `live_light_projection` remain supported as compatibility aliases
- `src/protocols/enums.py`, `src/protocols/errors.py`, `src/protocols/contracts.py`, `src/protocols/live_light_dashboard.py`, `src/protocols/live_light_runtime.py`, `src/protocols/__init__.py`
  - canonical `Live*` exports now lead the public Build-13 surface
  - historical `LiveLight*` names remain as explicit compatibility aliases
- coupled proof:
  - `rtk pytest tests/test_ui/test_light_ui_runtime.py tests/test_ui/test_operator_actions.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py tests/test_integration_alignment.py -q`
  - `177 passed`
- canonical alias proof:
  - `rtk grep -n "LockedOperatorUiRuntime|LockedOperatorDashboardView|LiveInput = LiveLightInput|LiveRunState = LiveLightRunState|LiveProjection = LiveLightProjection|build_live_input_from_micro_live = build_live_light_input_from_micro_live|build_live_projection = build_live_light_projection" src/ui src/monitoring src/protocols`
  - confirms public canonical names now exist in code while historical names are explicit aliases

Latest bounded locked operator UI state fail-safe proof:

- `src/ui/light_ui_runtime.py`
  - persisted locked-operator UI state no longer resets silently on corrupted JSON or invalid non-object roots
  - corrupted state files are backed up to `.corrupted`
  - recovered state now carries an explicit `last_error` marker in the persisted runtime state and operator projection
- `src/monitoring/contracts.py`
  - `OperatorRuntimeProjection` now exposes `last_error` as a typed monitoring field
- `src/ui/ui_light_locked.py` and `src/ui/technical_dashboard_view.py`
  - Build-10 `Operator Events` cards now surface operator-runtime state corruption explicitly instead of hiding it behind the last nominal event message
- targeted proof:
  - `rtk pytest tests/test_ui/test_light_ui_runtime.py tests/test_ui/test_light_dashboard.py tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py -q`
  - `84 passed`

Latest bounded LOCAL_REPLAY state fail-safe proof:

- `src/local_replay_runtime/replay_state_store.py`
  - corrupted persisted session state is now backed up to `.corrupted` and recovered with a typed `last_error`
- `src/local_replay_runtime/runtime_evidence.py`
  - corrupted persisted runtime evidence is now backed up to `.corrupted` and recovered with a typed `last_error`
  - `build_state()` now exposes the recorder snapshot for audit/test verification
- targeted proof:
  - `pytest tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_contracts.py tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py -q --basetemp=build/pytest-local-replay-state`
  - `44 passed`

Latest bounded `BS-38` closure proof:

- `src/protocols/shadow_day_counter.py`
  - `recover_from_records()` now rebuilds durable counter state from successful persisted `ShadowDayRecord`s
- `src/protocols/shadow_session_registry.py`
  - `recover_from_entries()` now rebuilds the append-only registry state from validated persisted entries
- `scripts/run_local_replay_shadow.py`
  - the runner now recovers semantic counter/registry continuity from durable day records after counter/registry corruption
  - recovered registry continuity uses explicit synthetic recovery metadata instead of silent invented provenance
- targeted proof:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py -q`
  - `53 passed`

Latest bounded `BS-87` closure proof:

- `src/engines/engine_a/engine_a_runtime.py`
  - `EngineARuntime` now requires an explicit `EmergencyCircuitBreaker`
  - the runtime no longer keeps a permissive `if breaker is not None` branch
- `src/engines/engine_b/engine_b_runtime.py`
  - `EngineBRuntime` now requires an explicit `EmergencyCircuitBreaker`
- `src/engines/engine_c/engine_c_runtime.py`
  - `EngineCRuntime` now requires an explicit `EmergencyCircuitBreaker`
- `src/engines/engine_d/engine_d_runtime.py`
  - `EngineDRuntime` now requires an explicit `EmergencyCircuitBreaker`
- runtime test proof:
  - engine runtime tests now import from canonical `engines.engine_*` packages instead of mixing `engine_*` and `engines.engine_*`
  - the C/D tripped-breaker tests now use local state dirs instead of fragile `tmp_path` temp roots
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src pytest tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-runtime`
  - `47 passed`

Latest bounded `BS-92` closure proof:

- `src/data_backbone/pair_health_scorer/suspension_decider.py`
  - `SuspensionReason.MANUAL` now has a dedicated audited constructor path via `suspend_manual()`
  - manual suspension now requires both `operator_id` and `reason_text`
  - `evaluate_suspension()` still cannot emit `MANUAL`, so the operator-only path stays explicit
- targeted proof:
  - `rtk pytest tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_pair_health_scorer.py -q`
  - `31 passed`

Latest bounded `BS-89` closure proof:

- `src/data_backbone/rest_bootstrap/gap_fill_controller.py`
  - `evaluate_gap_fill()` now rejects `gap_size <= 0.0` before rate-limit or size acceptance logic
  - negative and zero gaps now fail closed with an explicit inversion/clock-reversal message
  - positive gaps at the normal boundary still keep the original fill semantics
- targeted proof:
  - `rtk pytest tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py -q`
  - `8 passed`

Latest bounded `BS-88` closure proof:

- `src/scoring_backbone/penalty_aggregator/penalty_cap_guard.py`
  - phantom detection now requires `expected_cost > 0.0` before comparing economics
  - `expected_cost <= 0.0` no longer creates a false or meaningless phantom baseline
  - profitable positive-cost paths and ordinary capped paths keep their existing semantics
- targeted proof:
  - `rtk pytest tests/test_scoring_backbone/test_bs88_phantom_detection_expected_cost_regression.py -q`
  - `8 passed`

Latest bounded `BS-86` closure proof:

- `src/engines/engine_a/engine_a_runtime.py`, `src/engines/engine_b/engine_b_runtime.py`, `src/engines/engine_c/engine_c_runtime.py`, `src/engines/engine_d/engine_d_runtime.py`
  - all four runtime input contracts now enforce `timestamp_ms >= 1_000_000_000_000`
  - Unix-second timestamps are now rejected before any runtime clock resolution occurs
- `tests/test_engines/test_bs86_timestamp_ms_unit_constraint_regression.py`
  - the regression proof now uses canonical `engines.engine_*` imports, matching the active package layout
- targeted proof:
  - `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_bs86_timestamp_ms_unit_constraint_regression.py -q --basetemp=build/pytest-bs86`
  - `12 passed`

Latest bounded `BS-90` closure proof:

- `src/data_backbone/rest_bootstrap/runtime_bootstrap.py`
  - `resync()` now evaluates gap geometry first, then reserves quota atomically through `record_call()`
  - a failed `record_call()` now returns `RATE_LIMITED` immediately and no longer falls through to `fill_gap()`
- `tests/test_data_backbone/test_rest_bootstrap.py`
  - the data-backbone bootstrap tests now include a regression where `record_call()` fails after a fillable gap was validated
  - the regression proves that the provider is not called on that path
- targeted proof:
  - `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py -q`
  - `40 passed`

Latest bounded `BS-93` closure proof:

- `src/data_backbone/pair_health_scorer/suspension_decider.py`
  - `evaluate_suspension()` now requires an explicit `threshold` for health-based decisions
  - `hard_stale` and `consistency_failed` remain threshold-independent paths
  - `SuspensionDecision.threshold` is now semantically optional instead of silently carrying `0.0`
- `tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py`
  - the regression proof now verifies that the health-based path rejects omitted thresholds while the non-threshold suspension reasons stay usable
- targeted proof:
  - `rtk pytest tests/test_data_backbone/test_pair_health_scorer.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
  - `35 passed`

Latest bounded `BS-91` closure proof:

- `src/data_backbone/rest_bootstrap/rate_limit_guard.py`
  - `_call_times` now uses a deque instead of a list
  - `_prune()` now pops expired timestamps in place instead of reallocating a full filtered list each time
- `tests/test_data_backbone/test_rest_bootstrap.py`
  - the guard proof now checks that prune keeps the same internal container identity while clearing expired timestamps
- targeted proof:
  - `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
  - `45 passed`

Latest bounded `BS-81` closure proof:

- `src/risk_backbone/risk_runtime.py`
  - `DrawdownVerdict.REDUCE_EXPOSURE` is already translated into `RiskRuntimeAction.REDUCE_EXPOSURE`
  - drawdown state is propagated into reason details and explainability instead of remaining advisory-only
- targeted proof:
  - `rtk pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py tests/test_risk_backbone/test_loss_budgeter.py -q`
  - `54 passed`

Latest bounded `BS-83` closure proof:

- `src/scoring_backbone/ranking_router/portfolio_compatibility_checker.py`
  - unknown `cluster_id` now fails closed as an explicit mapping error before any `remaining=0.0` budget comparison
  - configured but exhausted clusters still keep the original budget-based rejection path
- `tests/test_scoring_backbone/test_ranking_router.py`
  - includes a regression proving that an unknown cluster is not masked as zero remaining capacity
- targeted proof:
  - `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
  - `41 passed`

Latest bounded `BS-82` closure proof:

- `src/portfolio_minimal/opportunity_selector/eligibility_filter.py`
  - unknown `cluster_id` now fails closed before Build-8 selection/allocation instead of flowing into a silent `remaining_cluster.get(..., 0.0)` reduction path
- `src/portfolio_minimal/opportunity_selector/selection_resolver.py`
  - explicit `REJECTED_UNKNOWN_CLUSTER` verdict is now emitted on the Build-8 rail
- `tests/test_portfolio_minimal/test_portfolio_minimal.py`
  - includes regressions proving unknown clusters are rejected at eligibility, selection, and orchestrator pipeline level
- targeted proof:
  - `rtk pytest tests/test_portfolio_minimal/test_portfolio_minimal.py tests/test_portfolio/test_canonical_portfolio.py -q`
  - `89 passed`
  - `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py -q`
  - `37 passed`

Latest bounded `BS-78` closure proof:

- `src/data_backbone/market_physics_math.py`
  - now exposes the shared governed market-physics penalty calibration for engine conviction builders
- `src/engines/engine_a/conviction_builder_a.py`
  - now sources `fragility`, `toxicity`, and `micro_friction` penalties from the shared physics calibration
- `src/engines/engine_b/conviction_builder_b.py`
  - no longer underweights the same physics penalties relative to Engine A
- `tests/test_engines/test_engine_b/test_engine_b.py`
  - includes a regression proving that the shared physics penalty weights match both Engine A and Engine B
- targeted proof:
  - `rtk pytest tests/test_data_backbone/test_market_physics_math.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_b/test_engine_b.py -q`
  - `164 passed`
  - `rtk pytest tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
  - `23 passed`

Latest bounded `BS-80` closure proof:

- `src/risk_backbone/btc_factor_guard/pair_beta_registry.py`
  - no longer exposes a universal fallback beta
  - explicit beta mappings now carry `as_of_ts` and `regime_tag`
  - freshness is now checked explicitly through registry TTL policy
- `src/risk_backbone/btc_factor_guard/portfolio_beta_calculator.py`
  - now requires an explicit beta for every pair instead of silently using `0.8`
- `src/risk_backbone/risk_runtime.py`
  - now rejects both missing and stale beta mappings on the active risk rail via explicit reason codes
- targeted proof:
  - `rtk pytest tests/test_risk_backbone/test_btc_factor_guard.py tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py -q`
  - `49 passed`
  - `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_scoring_backbone/test_ranking_router.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q`
  - `72 passed`
  - broader `tests/test_risk_backbone -q` remains noisy in this workspace because `test_circuit_breaker.py` hits a temp-directory permission issue unrelated to the beta slice

Latest bounded `BS-77` closure proof:

- `src/engines/engine_b/conviction_builder_b.py`
  - `false_breakout_score` now defaults to neutral `0.5` instead of optimistic `0.0`
- `src/engines/engine_b/engine_b_runner.py`
  - the same governed neutral default is now applied on the runner input surface
- `tests/test_engines/test_engine_b/test_engine_b.py`
  - includes regressions proving that implicit defaults now match explicit `false_breakout_score=0.5`
- targeted proof:
  - `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q --basetemp=build/pytest-engine-b-bs77`
  - `80 passed`

Latest bounded `BS-84` closure proof:

- `src/protocols/shadow_live_websocket.py`
  - `BinanceSpotLiveWebSocketAdapter.connect()` now closes any stale client already registered for the endpoint before replacing it
- `tests/test_protocols/test_shadow_live_websocket.py`
  - includes a reconnect regression proving that the old socket is closed and the new socket becomes the active endpoint client
- targeted proof:
  - `rtk pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`

Earlier bounded `BS-49` doctrine-convergence proof:

- `src/meta_learning/contracts.py`
  - `TradeLearningInput.profile` now defaults to `ProfileId.COMPLETE`
- `src/ui/operator_actions.py`
  - the locked operator UI no longer rejects `profile=COMPLETE`
  - explicit `LIGHT` remains available only as a compatibility input
- targeted proof:
  - `rtk pytest tests/test_meta_learning/test_contracts.py tests/test_meta_learning/test_governance_edge_cases.py tests/test_ui/test_operator_actions.py tests/test_ui/test_light_ui_runtime.py -q`
  - `59 passed`
- locked-view proof:
  - `rtk pytest tests/test_ui/test_light_dashboard.py tests/test_ui/test_light_ui_runtime.py tests/test_ui/test_ui_contracts.py -q`
  - `50 passed`
- broader Build-10 cross-check:
  - `rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py -q`
  - `55 passed`
- broader Build-10 runtime cross-check:
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py -q`
  - `62 passed`
- import/parsing sanity after wording cleanup:
  - `rtk pytest tests/test_ui/test_light_dashboard.py tests/test_monitoring/test_monitoring_runtime.py -q`
  - `13 passed`
- non-runtime top-level doc alignment proof:
  - `rtk grep -n "surface locale de compatibilité|Build-11 actif|labels historiques|profil gouverné courant|Light Shadow|Live-Light" docs/specs/V5_3_MASTER_FINAL_UNIQUE.md docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md docs/specs/V5_3_MASTER_FINAL_CANONICAL.md`
  - confirms the top-level matrices now align with the governed runtime rail read from current code
- non-runtime lower-level phase-spec alignment proof:
  - `rtk grep -n "profil=COMPLETE|runtime_mode=SHADOW|runtime_mode=MICRO_LIVE|runtime_mode=LIVE|rail gouverné courant|extension COMPLETE" docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
  - confirms the lower-level Build-11 / Build-12 / Build-13 / Build-14 phase specs now align with the governed runtime rail read from current code
- manifest/master rollup convergence proof:
  - `rtk grep -n 'profil=LIGHT' docs/specs/V5_3_MASTER_FINAL_UNIQUE.md docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md docs/specs/V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md src/manifest_registry/build_order_registry.py src/manifest_registry/module_inventory.py src/manifest_registry/version_registry.py`
  - only the deliberate `LOCAL_REPLAY` compatibility lines remain in the touched master docs
  - `rtk grep -n 'UI Light verrouillée' docs/specs/V5_3_MASTER_FINAL_UNIQUE.md docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md docs/specs/V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md src/manifest_registry/module_inventory.py src/manifest_registry/version_registry.py`
  - `0 matches`
  - `rtk pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_version_registry.py -q`
  - `84 passed`
- monitoring/dashboard COMPLETE coverage proof:
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_technical_dashboard.py -q`
  - `65 passed`
- runtime hook dashboard/monitoring closure proof:
  - `rtk pytest tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `104 passed`
- Build-10 dashboard rendering proof:
  - `rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `33 passed`
- broader Build-10 dashboard/runtime cross-check:
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_light_dashboard.py tests/test_ui/test_light_ui_runtime.py -q`
  - `50 passed`
- latest bounded secondary monitoring/ui wording proof:
  - `src/monitoring/contracts.py`
    - `LiveLightProjection` now documents the active Build-13 Live rail and keeps `Live-Light` only as historical wording
  - `src/monitoring/technical_dashboard_backend.py`
    - governed extensions detail now names `Live` first and marks `Live-Light` as historical
  - `tests/test_ui/test_light_dashboard.py`
    - test module wording now speaks about the locked Build-10 operator dashboard surface
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_light_dashboard.py tests/test_ui/test_technical_dashboard.py -q`
  - `71 passed`
- latest bounded secondary navigation-doc proof:
  - `docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md`
    - active-reading note now states the governed rail `COMPLETE -> SHADOW -> MICRO_LIVE -> LIVE`
  - `docs/specs/V5_3_INDEX_MAITRE_FINAL_CORPUS.md`
    - Build-10/11/12/13 entries now describe the governed rails and keep historical `Light` labels only as file-label context
  - `docs/specs/V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md`
    - local replay now explicitly documents `COMPLETE` as the active governed rail reading and keeps `LIGHT + LOCAL_REPLAY` as compatibility only
  - `docs/specs/V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`
    - Build-11/12/13 prompt sections now carry active-reading notes for `profile=COMPLETE`
  - grep proof:
    - `rtk grep -n 'Lecture active|historique|rail gouverne courant|protocole Live gouverne|UI operateur verrouillee|bypass des builds officiels Shadow / Micro-live / Live|valider le Shadow gouverne|micro-live gouverne|production Live gouvernee' docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md docs/specs/V5_3_INDEX_MAITRE_FINAL_CORPUS.md docs/specs/V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md docs/specs/V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`
    - positive matches confirm the new active-reading notes on the touched files
    - `rtk grep -n 'Light Shadow 30 jours|phase courant \\(Shadow / Micro-live / Live-Light|bypass des builds officiels Shadow / Micro-live / Live-Light|valider le Shadow Light|micro-live Light à taille|verdict GO / NO-GO vers Live-Light|production Live-Light' docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md docs/specs/V5_3_INDEX_MAITRE_FINAL_CORPUS.md docs/specs/V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md docs/specs/V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`
    - `0 matches`

Latest bounded `local_replay_runtime` convergence proof:

- `src/local_replay_runtime/replay_orchestrator.py`
  - `ReplayOrchestratorRequest.profile_scope` now defaults to `ProfileId.COMPLETE`
  - completed-export resume now rejects mismatched `run_id`, strategy metadata, `profile_scope`, `performance_mode`, and chunk identity
- `scripts/run_local_replay_export.py`
  - governed replay export now defaults to `--profile-scope complete`
  - explicit `LIGHT` remains available only through deliberate caller choice
  - resume mode now hydrates missing identifiers from persisted metadata but rejects explicit contradictions
- targeted proof:
  - `rtk pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `26 passed`

Latest bounded `backtest_artifact_import` handshake proof:

- `src/backtest_artifact_import/contracts.py`
  - `ArtifactUploadRequest` now requires an explicit `governance_reference_date`
- `src/backtest_artifact_import/upload_bridge.py`
  - upload dry-run conversion now forwards the request date unchanged instead of injecting `date.today()`
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py -q`
  - `48 passed`

Latest bounded `BS-40` closure proof:

- `src/backtest_artifact_import/signature_policy.py`
  - the default governed trust-store now ships real base64 Ed25519 public keys
  - the import rail now verifies signatures through a built-in pure-Python Ed25519 path
- `scripts/run_technical_dashboard.py`
  - the dashboard demo now uses the shared signed fixture envelope on the built-in verifier path
- `scripts/run_local_replay_shadow.py`
  - the Shadow demo rail now uses the same shared signed fixture envelope and no longer injects a local accept-all verifier
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_onboarding.py -q`
  - `68 passed`
- broader coupled proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `86 passed`

Latest bounded export-dir bridge proof:

- `src/backtest_artifact_import/export_dir_bridge.py`
  - governed export directories now materialize typed replay/import/upload contracts instead of runner-local reconstruction
  - the bridge preserves `artifact_schema_version`, `feature_set_version`, and `transform_set_version` from `replay_run_manifest`
  - lineage locks are derived from `recognized_feature_keys`; explicit empty recognition no longer falls back to raw unrecognized keys
- `scripts/run_local_replay_shadow.py`
  - export-driven imports now consume the shared bridge
  - the demo path now reuses the same shared feature-lock builder
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `24 passed`

Latest bounded export-dir semantic-consistency proof:

- `src/backtest_artifact_import/export_dir_bridge.py`
  - now rejects semantically contradictory governed exports even when the sidecars remain JSON-valid and schema-valid
  - review markdown provenance, feature bridge, parity, metrics, and DTR payloads are cross-checked against `ReplayRunManifest`
  - a real governed `export_dir` now also rejects sidecar refs that resolve outside the export directory itself
  - a real governed `export_dir` now also rejects multiple candidate files for the same governed sidecar label
 - `src/backtest_artifact_import/contracts.py`
   - governed upload dry-runs now fail-close before import conversion when `manifest.review_export_ref / feature_bridge_ref / parity_diagnostics_ref / replay_metrics_ref / replay_dtr_ref` diverge from the typed `payload_bundle`
   - typed governed payload bundles now also fail-close on duplicate refs instead of silently normalizing them away
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_artifact_exporter.py -q`
  - `104 passed`

Latest bounded shared replay-plan import-builder proof:

- `src/backtest_artifact_import/export_dir_bridge.py`
  - replay-plan consumers now share one governed `ReplayExecutionPlan + payload bundle -> ArtifactImportRequest` builder
- `scripts/run_local_replay_shadow.py`
  - the demo path no longer reconstructs `ArtifactImportRequest` locally
- `scripts/run_technical_dashboard.py`
  - the signed dashboard demo import/onboarding path now reuses the same shared builder
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `23 passed`
- broader coupled proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `83 passed`

Latest bounded shared replay-plan upload-builder proof:

- `src/backtest_artifact_import/export_dir_bridge.py`
  - replay-plan consumers can now materialize a governed `ArtifactUploadRequest` directly from `ReplayExecutionPlan + payload bundle`
- `scripts/run_technical_dashboard.py`
  - the dashboard demo now consumes that shared upload builder
  - the launcher now derives governed import from `upload_request -> import_request` and emits upload dry-run sidecars
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `14 passed`
- broader coupled proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `84 passed`

Latest bounded replay/evidence -> upload -> import -> shadow/ui proof:

- `src/backtest_artifact_import/export_dir_bridge.py`
  - shared replay/evidence builders now materialize `ArtifactExportBundle`, `ArtifactUploadRequest`, and upload-derived `ArtifactImportRequest`
- `scripts/run_local_replay_shadow.py`
  - the runner now consumes the upload-derived import rail and writes upload sidecars before Shadow
- `scripts/run_technical_dashboard.py`
  - the dashboard no longer builds `ArtifactExportBundle` locally
- targeted proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `26 passed`
- stable end-to-end rail proof:
  - `rtk pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `36 passed`
- broader coupled proof:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `86 passed`

Latest bounded `smoke_bootstrap_recovery` closure proof:

- `src/smoke_bootstrap_recovery/state_sanity_checker.py`
  - `check_fd_leak()` now accepts an optional absolute FD ceiling in addition to the local `+5` tolerance
- `src/smoke_bootstrap_recovery/__init__.py`
  - `run_build1_smoke()` now derives a suite-level FD ceiling from the initial process baseline and passes it to both recovery-time and sanity-time leak checks
- targeted proof:
  - `rtk pytest tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py -k "fd_leak or resource_release_checker" -q`
  - `5 passed`

Latest bounded `meta_minimal/dtr_core` closure proof:

- `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - `DTRStore` now maintains append-only secondary indexes for `pair`, `engine_id`, and `decision_state`
  - `get_by_pair()`, `get_by_engine()`, and `get_by_state()` no longer rescan the full `_records` list
- targeted proof:
  - `rtk pytest tests/test_meta_minimal/test_meta_minimal.py tests/test_meta_minimal/test_bs62_dtr_crash_protection_regression.py tests/test_meta_minimal/test_bs67_dtr_store_index_regression.py tests/test_regression_alignment.py -k "TestTracePersistenceLayer or TestDTRFlushToDisk or bs62 or bs67" -q`
  - `21 passed`

Latest bounded `shadow/protocols` closure proof:

- `src/protocols/shadow_session_registry.py`
  - `append_entries()` now builds a candidate list first and restores the exact prior in-memory list if `_persist()` fails
  - retry after a failed persist no longer trips a false `already recorded session_date` deadlock
- targeted proof:
  - `rtk pytest tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py tests/test_protocols/test_bs68_session_registry_rollback_regression.py -q`
  - `27 passed`
- coupled proof:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py tests/test_protocols/test_bs68_session_registry_rollback_regression.py -q`
  - `40 passed`

Previous coupled proof set still valid:

- `src/protocols/shadow_daily_orchestrator.py`
  - a slot is now rejected when `shadow_session_summary`, `shadow_session_registry`, and `replay_run_manifest` disagree on `session_date`
- `scripts/run_local_replay_shadow.py`
  - direct runner now derives the governed base session date from export metadata when available
  - explicit `session_date` is rejected when it disagrees with governed export metadata
  - the runner now publishes explicit TTL/drift import-governance inputs, so governed demo and export-driven imports no longer fall back to `needs_revision`
- `scripts/run_shadow_vps_service.py`
  - auto-exported `raw_input`, `websocket`, and `native_live_websocket` flows now pin `replay_run_manifest.timeframe_scope` to the source governed session date before slot discovery
  - VPS Shadow service progression no longer collapses onto replay timestamps like `2023-11-14` when the source slot was `2026-04-01`
- broader proof:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `21 passed`

## Known Documentation Risk

On 2026-04-07 both tracker and working-memory files were found physically filled with `0x00`.
This tracker has been reconstructed from verified code state and session proofs.
If either file becomes unreadable again:

1. stop runtime edits
2. reconstruct documentation state from code + tests
3. only then continue development

## Latest bounded `T1 / P0-1.A` proof

- `src/interface_contracts/binance_contracts.py`
  - now defines typed frozen read-only Binance contracts for credentials, server time, exchange info, account snapshot, and time-sync result
- `src/venue_adapters/binance_spot/credential_loader.py`
  - explicit stub loader for mapping/env/file inputs without leaking secret content in repr/logging surfaces
- `src/venue_adapters/binance_spot/time_sync.py`
  - resolves `THR-X01` through `calibration_loader` and computes bounded drift alerts without hardcoded source-code thresholds
- `src/venue_adapters/binance_spot/rest_client.py`
  - opens a strictly read-only async Binance client for `/api/v3/time`, `/api/v3/exchangeInfo`, and signed GET `/api/v3/account`
  - no POST/PUT/DELETE path exists in this tranche
- `config/binance_adapter.yml`
  - exists as the template config for base URL, timeout, recvWindow, and calibration binding
- targeted proof:
  - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_execution_backbone/test_venue_constraints_provider.py -q`
  - `15 passed`
- honest residual:
  - Binance Testnet account validation remains manual/human
  - sealed-secret ownership still belongs to `T2`

## Latest bounded `T2 / P0-4` proof

- `src/secrets_manager/{__init__,__main__,_dpapi,loader,sealer,cli}.py`
  - now provide a bounded sealed-secrets workflow for the current Windows/local environment
  - the current backend is `windows_dpapi_user` with an external `master.key` file used as required additional entropy
- `src/secrets_manager/README.md`
  - documents the local workflow `gen-key -> seal -> load/unseal`
- `src/venue_adapters/binance_spot/credential_loader.py`
  - can now load `.sealed.json` credential payloads through `secrets_manager`
- targeted proof:
  - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
  - `12 passed`
- honest residual:
  - `age` / `sops` are still absent
  - Linux/VPS portability is not solved by this bounded slice
  - treat this as a local/dev closure, not as the final cross-platform secret-management story

## Latest bounded `T3 / P0-1.B` proof

- `src/venue_adapters/binance_spot/ws_client.py`
  - now wraps the existing Build-2 websocket gateway in a bounded Binance depth-stream client
  - reconnect never silently resumes trading; it marks the stream `STALE` until an explicit resync snapshot is applied
- `src/venue_adapters/binance_spot/rest_client.py`
  - now also provides a typed REST depth snapshot and an explicit provider bridge for `snapshot REST -> WS deltas`
- `src/venue_adapters/binance_spot/orderbook_manager.py`
  - now enforces `snapshot -> deltas` ordering, sequence-gap detection, time-gap detection, and deterministic top-of-book replay
- `src/data_backbone/freshness_checker/venue_stream_freshness.py`
  - provides a bounded stream-freshness hook for silence/stale evaluation
- `src/protocols/shadow_live_websocket.py`
  - depth payloads now preserve `first_update_id / final_update_id` in addition to `last_update_id`
- targeted proof:
  - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - `19 passed`
- broader coupled proof:
  - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_execution_backbone/test_venue_constraints_provider.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - `33 passed`
- honest residual:
  - no live/testnet websocket validation yet
  - no 24h RAM-leak proof yet
  - the next bounded additions are now live/testnet validation and soak proof, not another missing local core primitive

## Latest bounded `T6 / P0-3` progress

- `src/execution_backbone/execution_runtime.py`
  - now accepts an optional `FeeAwareEdgeGateConfig`
  - when that config is injected, `submit_opportunity()` resolves `THR-E01` / `THR-E02` through `src/scoring_backbone/fee_aware_edge_gate.py`
  - trades whose expected edge does not clear the calibrated fee-aware threshold are now rejected explicitly before submit
- `src/protocols/execution_runtime_bootstrap.py`
  - `build_execution_runtime()` and `build_binance_execution_runtime()` now pass through an optional `FeeAwareEdgeGateConfig`
- `src/venue_adapters/binance_spot/time_sync.py` and `config/binance_adapter.yml`
  - `BinanceAdapterConfig` now carries an explicit `fee_aware_edge_gate_enabled` flag
  - the bounded Binance runtime builder can now derive a standard EDGE config from `calibration_root/calibration_version` when that flag is enabled
- `src/execution_backbone/order_decider/intent_builder.py` and `src/execution_backbone/order_decider/decision_reporter.py`
  - fee-aware gate blocks no longer live only in free-text `detail`
  - `NoTradeDecision.context`, `DecisionEvent.no_trade_reason`, and `DecisionEvent.context` now provide a structured audit/monitoring surface for future Local IA Lab / VPS dashboards
- `tests/test_execution_backbone/test_execution_runtime.py`
  - now proves both block and permit paths under a real signed EDGE calibration artifact
  - now also proves structured fee-aware context propagation into the reporter path
- `tests/test_execution_backbone/test_order_decider.py`
  - now proves structured no-trade context storage and logging
- `tests/test_protocols/test_execution_runtime_bootstrap.py`
  - now proves the bootstrap wiring path for the same bounded EDGE gate
- targeted proof:
  - `rtk pytest tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py tests/test_execution_backbone/test_order_decider.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
  - `58 passed`
- broader cross-check:
  - `rtk pytest tests/test_execution_backbone tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py -q`
  - `163 passed`
- honest residual:
  - no standard bootstrap path injects the EDGE config everywhere yet
  - no higher-level scoring/engine consumer is wired yet

## Latest planning anchor: Local IA Lab ingestion diagnostic

- `docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md`
  - now records the code-confirmed truth that the Lab already ingests:
    - historical snapshot batches
    - governed replay sidecars
    - post-trade `DTRRecord` evidence
    - strategy/review bundles
  - and also records the missing part explicitly:
    - there is still no raw live bidirectional VPS -> Lab snapshot stream

## Latest bounded Local IA Lab post-trade review slice

- `src/meta_minimal/meta_runtime.py`
  - now exposes `build_meta_runtime_result_from_records(...)`
  - governed replay `DTRRecord` exports can now rebuild canonical Build-9 reports without rerunning the full runtime chain
- `scripts/run_local_lab_post_trade_review.py`
  - now provides a bounded Local IA Lab entrypoint from governed `replay_dtr.json/.jsonl`
  - input can be scoped by `--pair` and `--engine-id`
  - output surfaces are now audit/dashboard-ready without HTML coupling:
    - `meta_runtime_result.json`
    - `meta_learning_review.bundle.json`
    - `meta_learning_review.md`
    - `meta_learning_projection.json`
    - `trade_loss_attribution.json`
- `src/meta_learning/trade_loss_attribution.py`
  - now provides a governed per-trade explanation layer for Local IA Lab
  - the current typed failure modes are `cost_drift`, `sterilization`, `edge_degraded`, `trace_coverage`, and `unclassified_loss`
  - each losing trade now carries `preventive_action`, `confidence`, `evidence`, and optional `recommended_threshold_ids`
- `scripts/run_local_lab_analysis_bundle.py`
  - now propagates the new loss-attribution sidecar into `local_lab_analysis_summary.json`
  - now also emits `walk_forward_review.template.json` and `walk_forward_review.summary.json`
  - optional approved `--walk-forward-review-path` can now flip `walk_forward_review_ready=true`
  - the human anti-leakage gate is now explicit in the Local IA Lab code path, not just in docs
- targeted proof:
  - `python -m pytest tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `12 passed`
- broader cross-check:
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `267 passed`
- honest residual:
  - this is still replay-side evidence ingestion, not a live VPS -> Lab stream
  - no automatic recalibration/promotion loop is introduced by this slice

## Standing slice doctrine

- each new core slice must now be checked for a future dashboard-facing output surface
- acceptable surfaces:
  - typed projection
  - monitoring summary
  - artifact sidecar
  - structured logs
  - metrics payload
- this is a design-time check, not an obligation to wire HTML/UI immediately on every slice
- target outcome: no important new runtime or Lab logic should become invisible to future Local IA Lab / VPS monitoring

## Latest Local IA Lab recalibration planning slice

- `local_lab_recalibration_plan.json` now exists on the same governed Lab bundle
- it aggregates `trade_loss_attribution.json` and optional scope readiness into a first bounded local recalibration verdict
- it can now tell the operator:
  - whether a local recalibration candidate is actually ready
  - which threshold ids are implicated
  - whether the right next move is recalibration, sterilization review, or better trace capture
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py -q`
  - `11 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `285 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `90 passed`

## Latest Local IA Lab dry-run bridge refinement

## Latest EDGE provenance refinement

- `edge_gate.input_summary.json` now carries Local IA Lab recalibration provenance when available
- the Local IA Lab bundle now computes the recalibration plan first, then emits the EDGE artifact with that provenance attached
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `10 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `285 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `92 passed`

## Latest packaging gate refinement

- `artifact_release_candidate.py` now consumes the Local IA Lab recalibration plan explicitly
- `shadow_candidate` no longer depends only on proof sidecars; it now also requires a coherent local recalibration plan
- current bounded rule:
  - `NO_LOSING_TRADES_TO_RECALIBRATE` is benign
  - other recalibration blockers remain blocking
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `15 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `96 passed`

## Latest Local IA Lab dry-run bridge refinement
- `artifact_source_summary.json` now exists as a stable sidecar for the real Local IA Lab source artifact
- the current dry-run transport packet still stays `review_packet`
- that transport packet now also carries:
  - the source artifact ref `edge_gate.yml`
  - the source summary ref `artifact_source_summary.json`
  - via `ArtifactPayloadRefBundle.supplementary_refs`
- the bridge now reports `semantic_status = transport_packet_with_source_artifact_refs`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `9 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `88 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `283 passed`

## Latest Local IA Lab release-gate projection

- the dry-run bridge now reports the packaging verdict explicitly instead of forcing downstream tooling to re-derive it from sidecars
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now carries:
  - `release_ready_for_shadow`
  - `release_artifact_proof_ready`
  - `release_artifact_proof_validation_reasons`
  - `release_recalibration_candidate_ready`
  - `release_recalibration_blocking_reasons`
  - `release_gate_status`
  - `release_gate_reasons`
- `scripts/run_local_lab_analysis_bundle.py` now forwards the same gate projection into `local_lab_analysis_summary.json`
- current bounded gate statuses:
  - `proof_and_recalibration_backed`
  - `proof_backed_no_recalibration_required`
  - `proof_gate_blocked`
  - `recalibration_gate_blocked`
  - `release_candidate_blocked`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `15 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `96 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`

## Latest Local IA Lab release-gate sidecar transport

- `artifact_release_gate_summary.json` now exists on the Local IA Lab bundle
- the dry-run bridge now requires `release_gate_summary_ref` and carries it through `ArtifactPayloadRefBundle.supplementary_refs`
- the ready dry-run packet now carries three Local IA Lab supplementary refs:
  - `edge_gate.yml`
  - `artifact_source_summary.json`
  - `artifact_release_gate_summary.json`
- the semantic projection now also reports:
  - `TRANSPORT_SUPPLEMENTARY_REFS_CARRY_RELEASE_GATE_SUMMARY`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `9 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `17 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `96 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`

## Latest Local IA Lab multi-scope release drill-down

- `artifact_release_candidate.json` now carries richer per-scope release rows with evidence refs and counts
- the top-level Local IA Lab summary now also projects:
  - `release_ready_scope_slugs`
  - `release_blocked_scope_slugs`
- this keeps the packaging verdict navigable for future dashboards and operator drill-down without inventing a per-scope import rail
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `10 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `17 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `96 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`

## Latest Local IA Lab per-scope release sidecars

- each multi-scope run now also emits `artifact_release_scope_summary.json` under `scopes/<slug>/`
- those scope sidecars carry:
  - the shared artifact path
  - the shared release-gate summary ref
  - the shared dry-run bridge ref
  - the scope proof/review refs and counts
- the top-level summary now also projects `release_scope_summary_count` and `release_scope_summary_paths`
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `10 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `17 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `96 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`

## Latest Local IA Lab scope-matrix packaging projection

- the scope matrix now distinguishes proof-ready vs release-ready scope counts
- each scope row can now carry packaging-side fields:
  - `release_ready`
  - `release_blocking_reasons`
  - `release_scope_summary_path`
- the top-level Local IA Lab summary now also exposes:
  - `release_scope_ready_count`
  - `release_scope_blocked_count`
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `12 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `19 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `98 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`

## Latest Local IA Lab promotion-readiness summary

- `artifact_promotion_readiness_summary.json` now exists as a top-level Local IA Lab sidecar
- it maps Local IA Lab packaging truth onto canonical shared-core vocabulary:
  - `ArtifactActivationStage`
  - `PromotionState`
  - `ReviewState`
- current bounded readiness labels:
  - `local_only`
  - `shadow_candidate_pending_dry_run`
  - `shadow_candidate_dry_run_ready`
- the top-level bundle summary now also projects:
  - `artifact_promotion_readiness_summary_path`
  - `promotion_readiness_status`
  - `promotion_activation_stage`
  - `promotion_normalized_state`
  - `promotion_review_state`
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `9 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `22 passed`
- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `101 passed`
- `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `290 passed`

## Latest Local IA Lab monitoring projection

- `local_lab_monitoring_projection.json` now exists as the compact future-monitoring sidecar for the Local IA Lab packaging rail
- `src/local_replay_runtime/local_lab_monitoring_projection.py` keeps this summary projection-only:
  - no UI coupling
  - no new runtime rail
  - no promotion behavior
- the top-level bundle summary now also carries:
  - `local_lab_monitoring_projection_path`
  - `monitoring_projection_status`
  - `monitoring_projection_detail`
- current bounded status truth:
  - `healthy` only when dry-run handoff is ready
  - `critical` only when core Local IA Lab outputs are incomplete
  - otherwise `warning/info`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py -q`
  - `12 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `22 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `101 passed`
- `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `293 passed`

## Latest Local IA Lab observability export

- `local_lab_observability_export.json` now exists as the standard metrics/text export over the Local IA Lab packaging rail
- `src/local_replay_runtime/local_lab_observability.py` builds it from the compact monitoring projection
- the bundle summary now also carries:
  - `local_lab_observability_export_path`
  - `local_lab_observability_sample_count`
- this remains descriptive only:
  - no UI coupling
  - no runtime mutation
  - no promotion semantics
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py -q`
  - `11 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `24 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `103 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `295 passed`

## Latest Local IA Lab monitoring backend payload

- `src/local_replay_runtime/local_lab_monitoring_backend.py` now exists as the thin adapter from the compact Local IA Lab monitoring projection plus the standard observability export into one typed backend payload
- `src/monitoring/contracts.py` now defines `LocalLabMonitoringBackendPayload`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_monitoring_backend_payload.json`
- the bundle summary now also carries:
  - `local_lab_monitoring_backend_payload_path`
  - `local_lab_monitoring_backend_status`
- this remains descriptive only:
  - no UI coupling
  - no new runtime rail
  - no promotion semantics
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `17 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_monitoring_contracts.py -q`
  - `397 passed`

## Latest Local IA Lab monitoring ingestion summary

- `src/monitoring/local_lab_ingestion.py` now exists as the monitoring-side adapter for the Local IA Lab backend payload plus observability export
- `src/monitoring/contracts.py` now defines `LocalLabMonitoringIngestionSummary`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_monitoring_ingestion_summary.json`
- the bundle summary now also carries:
  - `local_lab_monitoring_ingestion_summary_path`
  - `local_lab_monitoring_ingestion_ready`
- current checks remain bounded and descriptive:
  - `correlation_id/profile/runtime_mode/timestamp_ms` alignment
  - sample/text payload presence
- important invariant:
  - no UI coupling
  - no Build-10 runtime coupling
  - no new promotion semantics
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py -q`
  - `20 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `400 passed`

## Latest Local IA Lab monitoring bundle loader

- `src/monitoring/local_lab_bundle_loader.py` now exists as the file-based loader for the Local IA Lab monitoring trio
- `src/monitoring/__init__.py` now exports:
  - `LocalLabMonitoringBundle`
  - `load_local_lab_monitoring_bundle`
- current loader checks:
  - file presence
  - typed JSON validity
  - alignment of `correlation_id/profile/runtime_mode/timestamp_ms`
- important invariant:
  - this is still local, descriptive, future-backend plumbing only
  - no UI coupling
  - no new promotion semantics
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `10 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `402 passed`

## Latest Local IA Lab observability text export

- `src/monitoring/observability_io.py` now exists as the generic persisted-text writer for `ObservabilityExport`
- `src/monitoring/__init__.py` now exports `write_observability_text_payload`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_observability.prom`
- the bundle summary now also carries:
  - `local_lab_observability_text_path`
- important invariant:
  - still descriptive-only export plumbing
  - no UI coupling
  - no runtime or promotion semantics added
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `11 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `403 passed`

## Latest Local IA Lab research-priority scorer

- `src/local_replay_runtime/local_lab_research_priority.py` now exists as the first bounded research-model-style component in the Local IA Lab core
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_research_priority.json`
- the analysis summary now also carries:
  - `local_lab_research_priority_path`
  - `research_priority_status`
  - `research_priority_scope_count`
  - `research_priority_top_scope_slug`
  - `research_priority_top_score`
- compact research-priority fields also propagate into:
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - transparent weighted score only
  - local-only
  - no VPS mutation
  - no promotion semantics
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_research_priority.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `15 passed`
  - `python -m pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring -q`
  - `493 passed`

## Latest Local IA Lab loss-surrogate scorer

- `src/local_replay_runtime/local_lab_loss_surrogate.py` now exists as the first truly trained but still transparent Local IA Lab component
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_loss_surrogate_report.json`
- the analysis summary now also carries:
  - `local_lab_loss_surrogate_path`
  - `loss_surrogate_status`
  - `loss_surrogate_ready`
  - `loss_surrogate_scope_count`
  - `loss_surrogate_top_scope_slug`
  - `loss_surrogate_top_probability`
- compact loss-surrogate fields also propagate into:
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - transparent trained local-only model
  - no-lookahead decision-time inputs only
  - no VPS mutation
  - no promotion semantics
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_loss_surrogate.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `15 passed`
  - `python -m pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring -q`
  - `495 passed`

## Latest Local IA Lab surrogate-guided planning

- the trained Local IA Lab loss surrogate now also feeds:
  - `src/local_replay_runtime/local_lab_research_priority.py`
  - `src/local_replay_runtime/local_lab_recalibration_plan.py`
- current bounded behavior:
  - research ranking can now use surrogate risk as an advisory feature
  - the recalibration plan can now emit `replay_surrogate_high_risk_scope`
  - proof/release/promotion gates remain unchanged
- important invariant:
  - surrogate remains advisory only
  - no VPS mutation
  - no promotion semantics
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_research_priority.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `19 passed`
  - `python -m pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring -q`
  - `497 passed`

## Latest Local IA Lab replay candidate queue

- `src/local_replay_runtime/local_lab_replay_candidate_queue.py` now exists as the first bounded queue of next local replay/research steps
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_replay_candidate_queue.json`
- the analysis summary now also carries:
  - `local_lab_replay_candidate_queue_path`
  - `replay_candidate_queue_status`
  - `replay_candidate_count`
  - `replay_candidate_ready_count`
  - `replay_candidate_top_scope_slug`
- compact replay-queue fields also propagate into:
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - local-only workflow surface
  - no VPS mutation
  - no promotion semantics
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_replay_candidate_queue.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `15 passed`
  - `python -m pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring -q`
  - `499 passed`

## Latest Local IA Lab replay ticket index

- `src/local_replay_runtime/local_lab_replay_ticket_index.py` now exists as the governed ticket index over the Local IA Lab replay queue
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_replay_ticket_index.json`
- the analysis summary now also carries:
  - `local_lab_replay_ticket_index_path`
  - `replay_ticket_index_status`
  - `replay_ticket_count`
  - `replay_ticket_ready_count`
  - `replay_ticket_top_scope_slug`
- compact replay-ticket fields also propagate into:
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - local-only governed planning artifact
  - no VPS mutation
  - no promotion semantics
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_replay_ticket_index.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `15 passed`
  - `python -m pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring -q`
  - `501 passed`

## Latest Local IA Lab replay dispatch plan

- `src/local_replay_runtime/local_lab_replay_dispatch_plan.py` now exists as the local-only dispatch surface over governed replay tickets
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_replay_dispatch_plan.json`
- the analysis summary now also carries:
  - `local_lab_replay_dispatch_plan_path`
  - `replay_dispatch_plan_status`
  - `replay_dispatch_ready_count`
  - `replay_dispatch_blocked_count`
  - `replay_dispatch_top_ticket_id`
- compact replay-dispatch fields also propagate into:
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - local-only non-executing dispatch surface
  - no VPS mutation
  - no promotion semantics
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_replay_dispatch_plan.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `15 passed`
  - `python -m pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring -q`
  - `503 passed`

## Latest Local IA Lab workflow/monitoring manifests

- `src/local_replay_runtime/local_lab_replay_workflow_manifest.py` now exists and the Local IA Lab bundle now emits `local_lab_replay_workflow_manifest.json`
- `src/monitoring/local_lab_replay_workflow_loader.py` now exists as the file-based loader for that workflow bundle
- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now exists and the Local IA Lab bundle now emits `local_lab_monitoring_bundle_manifest.json`
- `src/monitoring/local_lab_bundle_loader.py` now resolves monitoring sidecars via the manifest instead of hardcoded filenames
- future-dashboard propagation is explicit for both manifest sidecars and their refs
- important invariant:
  - local-only discovery/ingestion surface
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority
- latest proofs:
  - targeted: `16 passed`
  - rail-specific Local IA Lab + monitoring cross-check: `162 passed`
  - note: the older full broad sweep over all `tests/test_local_replay_runtime` still includes unrelated Windows build-path cleanup noise in legacy replay/export tests outside this slice

## Latest Local IA Lab monitoring bundle discovery

- `src/monitoring/local_lab_bundle_discovery.py` now exists as the manifest-driven discovery layer over multiple Local IA Lab monitoring bundles
- it can now:
  - scan a root for `local_lab_monitoring_bundle_manifest.json`
  - order bundles by latest governed `timestamp_ms`
  - load the newest valid bundle through the existing loader
- important invariant:
  - local/backend only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority
- latest proofs:
  - targeted: `18 passed`
  - rail-specific Local IA Lab + monitoring cross-check: `164 passed`

## Latest Local IA Lab monitoring feed

- `src/monitoring/local_lab_monitoring_feed.py` now exists as the first compact feed over discovered Local IA Lab monitoring bundles
- it now summarizes:
  - latest bundle identity/status
  - ingestion-ready bundle count
  - bundle counts by backend status
- important invariant:
  - local/backend only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority
- latest proofs:
  - targeted: `20 passed`
  - rail-specific Local IA Lab + monitoring cross-check: `166 passed`

## Latest Local IA Lab calibration-methods core (`13-A`)

- `src/calibration_methods/bootstrap.py` now provides a shared stationary block bootstrap helper
- `src/calibration_methods/walkforward.py` now provides a shared purged walk-forward planner with embargo + label purging
- `src/calibration_methods/dsr.py` now provides a shared Deflated Sharpe Ratio computation helper
- the first consumer is already real:
  - `src/local_replay_runtime/edge_gate_calibration.py` now uses the shared stationary bootstrap helper
  - EDGE calibration notes now expose `bootstrap_block_length=...`
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_bootstrap.py tests/test_calibration_methods/test_walkforward.py tests/test_calibration_methods/test_dsr.py tests/test_local_replay_runtime/test_edge_gate_calibration.py -q`
  - `11 passed`
  - `rtk pytest tests/test_calibration_methods/test_bootstrap.py tests/test_calibration_methods/test_walkforward.py tests/test_calibration_methods/test_dsr.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py -q`
  - `30 passed`
- honest residual:
  - no generic calibration-method consumer beyond EDGE bootstrap yet
  - DSR and walk-forward helpers are ready for later Local IA Lab slices but are not yet wired into promotion gating

## Latest Local IA Lab calibration-methods review sidecar

- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now consumes the shared Local IA Lab math-core over real `DTRRecord` history
- it evaluates:
  - walk-forward geometry readiness
  - DSR readiness / pass / fail
- `src/local_replay_runtime/artifact_proof_summary_builder.py` now consumes this review and promotes DSR failure to explicit local proof blockers:
  - `LOCAL_LAB_DSR_REQUIRED`
  - `LOCAL_LAB_DSR_INVALID`
  - `LOCAL_LAB_WALK_FORWARD_PLAN_INVALID`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_calibration_methods_review.json` and propagates its status into:
  - summary
  - monitoring projection
  - monitoring backend payload
  - observability export
- important invariant:
  - still Local IA Lab only
  - no VPS/runtime promotion mutation
  - human walk-forward approval remains a separate hard gate
- latest proofs:
  - targeted proof rail: `25 passed`
  - monitoring/backend propagation: `18 passed`
  - calibration/proof cross-check: `37 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `314 passed`

## Latest Local IA Lab release/dry-run calibration-methods propagation

- `src/local_replay_runtime/artifact_release_candidate.py` now carries explicit calibration-methods state on the release verdict
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now carries the same truth into:
  - `LocalLabReleaseGateSummary`
  - `LocalLabArtifactUploadDryRunBridge`
- important invariant:
  - no VPS/runtime mutation
  - no UI coupling
  - dry-run handoff is more explicit, not more permissive
- latest proofs:
  - targeted release/dry-run rail: `20 passed`
  - wider `backtest_artifact_import + local_lab + monitoring`: `111 passed`

## Latest Local IA Lab monitoring feed calibration-methods propagation

- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now carries compact calibration-methods truth
- `src/monitoring/local_lab_bundle_discovery.py` now exposes it per discovered bundle
- `src/monitoring/local_lab_monitoring_feed.py` now counts ready/partial/blocked calibration-methods bundles
- important invariant:
  - backend/discovery only
  - no UI coupling
  - no VPS/runtime mutation
- latest proofs:
  - targeted monitoring/backend rail: `18 passed`
  - wider monitoring + local handoff cross-check: `203 passed`

## Latest Local IA Lab tail-risk review (`13-B`)

- `src/calibration_methods/pot_gpd.py` now exists as the bounded Local IA Lab POT-GPD helper
- `src/local_replay_runtime/local_lab_tail_risk_review.py` now emits strategy-level tail-risk evidence over governed replay/post-trade history
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_tail_risk_review.json`
- current breaker scope:
  - `THR-R01` daily
  - `THR-R02` weekly
  - `THR-R03` monthly
- compact truth now also propagates into:
  - summary
  - monitoring projection
  - monitoring backend payload
  - observability export
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet wired into release gating or dry-run import semantics
- latest proofs:
  - targeted tail-risk rail: `16 passed`
  - calibration/tail-risk cross-check: `32 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `317 passed`

## Latest Local IA Lab stationarity gate (`MI-9`)

- `src/calibration_methods/stationarity.py` now exists as the bounded dual ADF + KPSS helper
- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now adds explicit stationarity truth on top of walk-forward geometry + DSR
- the same truth now propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- current conservative semantics:
  - insufficient history remains `partial`
  - MI-9 failure blocks local proof
  - proof-side validation reasons now include `LOCAL_LAB_STATIONARITY_REQUIRED` / `LOCAL_LAB_STATIONARITY_INVALID`
- latest proofs:
  - targeted stationarity rail: `23 passed`
  - calibration/proof cross-check: `42 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `320 passed`

## Latest shared human hard-cap helper (`MI-7`)

- `src/calibration_methods/hard_cap_floor.py` now exists and is consumed by the current Local IA Lab EDGE + tail-risk + normalized-report rail
- semantic clarification now carried in code and sidecars:
  - `hard_cap_satisfied`
  - `hard_cap_binding`
- latest proofs:
  - targeted hard-cap rail: `16 passed`
  - calibration/local cross-check: `44 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `320 passed`

## Latest Local IA Lab multiple-testing review (`MI-12`)

- `src/calibration_methods/multiple_testing.py` now exists as the shared bounded MI-12 helper
- `src/local_replay_runtime/local_lab_multiple_testing_review.py` now exists as the Local IA Lab MI-12 sidecar
- current conservative semantics:
  - current Local IA Lab calibration outputs are interval-publication artifacts
  - the current MI-12 verdict is therefore explicit `not_required_interval_publication`
  - future hypothesis-test families can still consume the same shared Holm-Bonferroni helper
- propagation now reaches:
  - normalized calibration report
  - proof assessment
  - analysis summary
  - monitoring projection/backend/observability
  - monitoring bundle manifest/discovery/feed
- latest proofs:
  - targeted MI-12 rail: `22 passed`
  - broad `calibration_methods + local_replay_runtime + monitoring + backtest_artifact_import + meta_learning + meta_minimal`: `524 passed`

## Latest Local IA Lab execution review (`13-C` first slice)

- `src/calibration_methods/execution.py` now exists as the bounded EXECUTION helper rail for `THR-X01` / `THR-X02`
- `src/local_replay_runtime/local_lab_execution_review.py` now emits explicit Local IA Lab EXECUTION truth
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_execution_review.json`
- the same truth now propagates into:
  - summary
  - monitoring projection/backend/observability
  - monitoring bundle manifest/discovery/feed
- current conservative semantics:
  - missing execution telemetry remains explicit `partial`
  - no fake venue telemetry is inferred from replay exports
  - no VPS/runtime mutation
- latest proofs:
  - targeted execution rail: `23 passed`
  - broad `calibration_methods + local_replay_runtime + monitoring + backtest_artifact_import + meta_learning + meta_minimal`: `529 passed`

## Latest VPS -> local observability architecture anchor

- `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md` now records the correct split:
  - VPS = runtime + lightweight exporters + short retention
  - local PC = Prometheus + Grafana + detailed drill-down + long retention
- continuous export from VPS must stay compact:
  - heartbeat
  - runtime stage
  - queue/reconnect/stale/kill-switch state
  - expected vs realized cost
  - CPU/RAM/disk summaries
  - import/proof/promotion summaries
- detailed logs and heavy traces must stay on-demand, not always-on
- current code truth:
  - `ObservabilityExport` and typed backend payloads already exist
  - Local IA Lab already emits `.prom`
  - VPS contracts/export logic exist, but real process/system producers are still incomplete
- immediate next observability code order:
  1. `node_exporter` / scrape hookup on the VPS
  2. local Prometheus/Grafana hookup
  3. compressed incident-bundle retrieval
  4. only then richer UI work
- missing VPS code still explicitly open:
  - `src/regime_classifier/`
  - `src/alerting/telegram_alerter.py`
  - `src/execution_backbone/gatekeeper/gatekeeper.py`
  - `src/risk_backbone/info_stress_monitor.py`
  - `src/execution_backbone/spread_guard.py`
  - `src/execution_backbone/slippage_model.py`
- estimated total solution progress is now tracked as `~62%` overall:
  - strong foundations and Local IA Lab core
  - still material work left on VPS ops/risk/live proof/observability integration

## Latest VPS Shadow service observability slice

- real process/service observability is now coded on the real Shadow VPS rail:
  - `scripts/run_shadow_vps_service.py`
  - `src/monitoring/disk_monitor.py`
  - `src/monitoring/process_metrics.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
- new emitted artifacts:
  - `shadow_vps_service_monitoring_backend_payload.json`
  - `shadow_vps_service_observability_export.json`
  - `shadow_vps_service_observability.prom`
- slice status:
  - bounded
  - typed
  - audit-ready
  - no UI coupling
- latest proofs:
  - targeted: `9 passed`
  - surrounding service/monitoring cross-check: `19 passed`
- next observability order remains:
  1. `node_exporter` / scrape hookup
  2. local Prometheus/Grafana hookup
  3. compressed incident-bundle retrieval
  4. execution telemetry for `13-C EXECUTION`

## Latest VPS bounded log retrieval slice

- durable Shadow VPS event retrieval is now coded on the monitoring rail:
  - `src/monitoring/shadow_vps_service_log_retrieval.py`
  - `src/monitoring/contracts.py`
  - `scripts/run_shadow_vps_service.py`
- new typed retrieval surfaces:
  - `ShadowVpsServiceLogQuery`
  - `ShadowVpsServiceLogQueryResult`
  - `ShadowVpsServiceLogEventProjection`
- new real-service artifact:
  - `shadow_vps_service_recent_events.json`
- current slice truth:
  - bounded full-scan retrieval exists for durable JSONL drill-down
  - bounded tail summary exists for cheap continuous service-side export
  - no heavy always-on raw log bus was introduced
  - no UI coupling was introduced
- latest proofs:
  - targeted retrieval slice: `11 passed`
  - wider monitoring/service cross-check: `22 passed`
- next observability order now is:
  1. `node_exporter` deployment / scrape hookup
  2. local Prometheus/Grafana hookup
  3. compressed incident-bundle retrieval
  4. execution telemetry for `13-C EXECUTION`

## Latest VPS node_exporter textfile collector hookup

- real collector mirroring is now wired on the Shadow VPS service rail:
  - `src/monitoring/observability_io.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
  - `scripts/run_shadow_vps_service.py`
- new service option:
  - `--node-exporter-textfile-dir`
- new emitted collector artifact when configured:
  - `v53_shadow_vps_service.prom`
- current slice truth:
  - the service can now mirror the same compact `.prom` payload into a node_exporter textfile directory
  - this is still lightweight and typed
  - `node_exporter` deployment and local scrape wiring remain outside this code slice
- latest proofs:
  - targeted collector slice: `10 passed`
  - wider monitoring/service cross-check: `24 passed`

## Latest local Prometheus scrape bundle hookup

- per-VPS scrape handoff is now coded on the service rail:
  - `src/monitoring/shadow_vps_service_scrape_manifest.py`
  - `scripts/run_shadow_vps_service.py`
- local-PC aggregation is now coded too:
  - `src/monitoring/shadow_vps_scrape_discovery.py`
  - `scripts/run_local_prometheus_scrape_bundle.py`
- new artifacts now possible:
  - per VPS:
    - `shadow_vps_service_scrape_manifest.json`
    - `shadow_vps_service_prometheus_file_sd.json`
  - local aggregate:
    - `shadow_vps_scrape_discovery.json`
    - `shadow_vps_prometheus_file_sd.json`
- current slice truth:
  - service emits scrape handoff only when `--scrape-host` is explicit
  - local aggregation deduplicates latest target and produces Prometheus `file_sd`
  - still no UI coupling
- latest proofs:
  - targeted scrape-manifest/aggregate slice: `11 passed`
  - wider monitoring/service cross-check: `29 passed`

## Latest checked local Prometheus config generator

- local-PC Prometheus config generation is now coded:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- new local artifacts now possible:
  - `prometheus.local.generated.yml`
  - `prometheus.local.config.summary.json`
- current slice truth:
  - config generation consumes the aggregated `shadow_vps_prometheus_file_sd.json`
  - optional local node_exporter target can be included
  - it is still only a checked config generator, not a runtime launcher
- latest proofs:
  - targeted config slice: `8 passed`
  - wider monitoring/service cross-check: `32 passed`

## Latest local observability extension: Local IA Lab dashboard rail

- `Shadow VPS` local visualization is no longer the only Grafana target on the dev box:
  - `src/monitoring/local_lab_grafana_dashboard.py`
  - `scripts/run_local_lab_grafana_dashboard.py`
- current truth:
  - a detailed Local IA Lab Grafana dashboard is now generated from the actual `v53_local_lab_*` metric set
  - the dev metrics bridge now accepts either `.prom` or `observability_export.json -> text_payload`
  - the generated local Prometheus config can now scrape a dedicated Local IA Lab bridge via `--local-lab-target`
- current demo bundle:
  - `build/dev_dual_role_demo/local_lab_grafana_dashboard/v53_local_lab_grafana.dashboard.json`
  - `build/dev_dual_role_demo/local_lab_grafana_dashboard/v53_local_lab_grafana.summary.json`
  - `build/dev_dual_role_demo/local_prometheus_config_with_lab/prometheus.local.generated.yml`
- latest proofs:
  - targeted Local IA Lab monitoring/dashboard slice: `19 passed`

## Latest `13-C EXECUTION` depth slice: cumulative Shadow-service telemetry

- new code truth:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now owns the cumulative per-session archive and the bindable service-owned handoff artifact
  - `scripts/run_shadow_vps_service.py` now writes:
    - `shadow_vps_service_execution_telemetry.archive.json`
    - `shadow_vps_service_execution_telemetry.json`
  - `scripts/run_local_lab_analysis_bundle.py` now accepts either the legacy review-owned execution telemetry JSON or the new service-owned artifact JSON
- current rail truth:
  - websocket timing is now harvested from:
    - `websocket_stream.jsonl` when the service runs on injected websocket input
    - `live_websocket_snapshot_batch.json` when the service runs on native live capture
  - the archive is cumulative by `session_date`, so the service can finally build a meaningful multi-day `THR-X02` evidence chain
  - `THR-X01` is still optional and explicit through `--execution-time-sync-offsets-path`
- latest proofs:
  - targeted execution telemetry + bundle + service slice: `20 passed`

## Latest `13-C EXECUTION` depth slice: native live `THR-X01` probe handoff

- new truth:
  - `src/protocols/shadow_live_websocket.py` now supports a bounded passive server-time probe and writes `live_time_sync_offsets.json`
  - `scripts/run_shadow_vps_service.py` now prefers:
    - explicit `--execution-time-sync-offsets-path`
    - else the native live-capture `live_time_sync_offsets.json`
    - else honest `partial` for `THR-X01`
- audit propagation added:
  - `ShadowVpsServiceState.last_live_capture_time_sync_offsets_ref`
  - `ShadowVpsRuntimeEvidenceBundle.live_capture_time_sync_offsets_ref`
  - `ShadowVpsCampaignSummary.live_capture_time_sync_offsets_ref`
- latest proofs:
  - targeted live-capture/service/bundle slice: `26 passed`

## Latest `13-C EXECUTION` depth slice: service-owned `X04/X05` sample rail

- new truth:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now aggregates `spread_bps` and `slippage_bps` from service-owned evidence
  - `src/calibration_methods/execution.py` now contains `calibrate_spread_guard_threshold_bps(...)`
  - `LocalLabExecutionTelemetry` now carries spread/slippage sample families end-to-end
- deliberate limit of this slice:
  - no fake `THR-X05` model verdict yet
  - no fake `THR-X03` quota verdict yet
  - current review gating still stays on `X01/X02`
- latest proofs:
  - targeted `13-C` cross-check: `30 passed`

## Latest `13-C EXECUTION` depth slice: `X04` is now consumed by the review

- new truth:
  - `src/local_replay_runtime/local_lab_execution_review.py` now makes `THR-X04` a real review threshold
  - `THR-X04` requires:
    - bounded `spread_bps` telemetry
    - at least `30` observation days
    - successful `calibrate_spread_guard_threshold_bps(...)`
  - `scripts/run_local_lab_analysis_bundle.py` now surfaces the updated threshold counts through the existing summary fields automatically
- deliberate limit of this slice:
  - `X03` is still not marked ready without real quota telemetry
  - `X05` is still not marked ready without a real slippage model
  - no runtime-live mutation was introduced
- latest proofs:
  - targeted execution review/bundle slice: `17 passed`
  - execution/protocols/monitoring cross-check: `31 passed`

## Latest `13-C EXECUTION` depth slice: `X03/X05` are now explicit gaps in the review

- new truth:
  - `src/local_replay_runtime/local_lab_execution_review.py` now enumerates all bounded execution thresholds `X01..X05`
  - current honest review state is:
    - `X01` ready
    - `X02` ready
    - `X04` ready
    - `X03` partial because service quota telemetry is not produced yet
    - `X05` partial because the slippage model is not implemented yet
  - the bundle-level summary now shows `3` ready thresholds and `2` partial thresholds
- deliberate limit of this slice:
  - no fake runtime telemetry was invented for `X03`
  - no fake model was invented for `X05`
  - release gates still remain unchanged
- latest proofs:
  - targeted execution review/bundle slice: `17 passed`
  - execution/protocols/monitoring cross-check: `31 passed`

## Latest `13-C EXECUTION` depth slice: future `X05` size traces now exist

- new truth:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now harvests `candidate_sizes` and `final_sizes`
  - those series come from route hints already emitted by injected/live evidence
  - `LocalLabExecutionTelemetry` now carries these size traces end-to-end
- deliberate limit of this slice:
  - still no slippage model
  - still no green `X05` verdict
  - the slice only prepares future model inputs
- latest proofs:
  - targeted execution telemetry/review/bundle slice: `17 passed`
  - execution/protocols/monitoring cross-check: `31 passed`

## Latest `13-C EXECUTION` depth slice: `X03` quota telemetry is now service-owned evidence instead of an implicit gap

- new truth:
  - `src/protocols/shadow_live_websocket.py` now writes quota probe metadata beside `live_time_sync_offsets.json`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now preserves that metadata into the service-owned execution telemetry artifact
  - `src/local_replay_runtime/local_lab_execution_review.py` now distinguishes:
    - telemetry missing
    - quota cap missing
    - quota history `< 30d`
    - model not implemented
- deliberate limit of this slice:
  - `X03` still stays `partial`
  - no quota model and no green threshold were added
  - the slice is evidence-first and review-first only
- latest proofs:
  - targeted execution/protocol slice: `20 passed`
  - execution/protocols/monitoring cross-check: `32 passed`

## Latest `13-C EXECUTION` depth slice: `X03` and `X05` now have first bounded models

- new truth:
  - `src/calibration_methods/execution.py` now calibrates `X03` as a real throttle ratio from quota telemetry and official quota caps
  - the same module now calibrates `X05` as a first service-owned size/slippage model with a robust Huber fit on `sqrt(size)`
  - `src/local_replay_runtime/local_lab_execution_review.py` now marks `X03` and `X05` `ready` when the bounded fit succeeds on aligned 30d evidence
- deliberate limit of this slice:
  - `X05` is still the first bounded Lab model, not yet the final execution backbone implementation
  - no live runtime mutation or hidden fallback was introduced
- latest proofs:
  - targeted execution model slice: `21 passed`
  - execution/protocols/monitoring cross-check: `35 passed`

## Latest `13-C EXECUTION` depth slice: `X03/X05` now project into future runtime consumers

- new truth:
  - `local_lab_execution_runtime_projection.py` now emits a typed future-runtime handoff
  - the handoff covers only:
    - `rate_limiter` from `THR-X03`
    - `slippage_model` from `THR-X05`
  - proof assessment and release candidate now carry that projection state forward
- deliberate limit of this slice:
  - no live runtime consumer was created yet
  - this remains handoff evidence only
- latest proofs:
  - targeted projection/proof/release slice: `18 passed`
  - execution/protocols/monitoring cross-check: `46 passed`

## Latest `13-C EXECUTION` depth slice: canonical runtime consumers now exist

- new code truth:
  - `src/execution_backbone/rate_limiter.py` is the first bounded canonical consumer of `THR-X03`
  - `src/execution_backbone/slippage_model.py` is the first bounded canonical consumer of `THR-X05`
  - `src/execution_backbone/execution_runtime.py` now understands both, but only on explicit injection
- deliberate limit of this slice:
  - no bootstrap auto-activation yet
  - no live mutation by default
  - still no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused runtime-consumer slice: `30 passed`
  - broader execution/protocols/monitoring cross-check: `17 passed`

## Latest `13-C EXECUTION` depth slice: runtime projection bootstrap now exists

- new code truth:
  - `execution_runtime_projection_bridge.py` now loads the Lab-side runtime projection artifact fail-open
  - `execution_runtime_bootstrap.py` can now wire the new canonical `X03/X05` consumers from `execution_runtime_projection_path`
- deliberate limit of this slice:
  - still explicit opt-in only
  - still fail-open on missing/invalid/partial projection
  - still no hidden live activation
- latest proofs:
  - focused projection-bridge/bootstrap slice: `36 passed`
  - supporting execution/protocols cross-check: `14 passed`

## Latest `13-C EXECUTION` depth slice: runtime projection bridge now surfaces in Build-10

- new code truth:
  - `execution_runtime_dashboard.py` now projects the bounded runtime projection bridge into monitoring truth
  - `technical_dashboard_backend.py`, `technical_dashboard_view.py`, and `observability.py` now expose the new seam separately from `execution_no_trade_bridge`
- deliberate limit of this slice:
  - monitoring is descriptive only
  - no hidden runtime activation
  - no replacement of the older compiled no-trade bridge
- latest proofs:
  - focused protocol/backend/runtime/observability/UI slice: `91 passed`
  - supporting execution bridge/bootstrap cross-check: `36 passed`

## Latest `13-C EXECUTION` depth slice: technical dashboard launcher now auto-discovers the runtime projection bridge

- new code truth:
  - `run_technical_dashboard.py` now auto-loads `local_lab_execution_runtime_projection.json` from the demo output directory when present
  - the launcher also accepts an explicit `--execution-runtime-projection-path` for operator-side inspection
- deliberate limit of this slice:
  - launcher surface only
  - no runtime activation
  - no Shadow/Micro-live/Live bypass
- latest proofs:
  - focused launcher/ui/backend slice: `90 passed`
  - supporting runtime/bridge cross-check: `46 passed`

## Latest `13-C EXECUTION` depth slice: local replay shadow runner now surfaces the runtime projection bridge

- new code truth:
  - `run_local_replay_shadow.py` now auto-loads `local_lab_execution_runtime_projection.json` from its output directory when present
  - the same runner now accepts an explicit `--execution-runtime-projection-path`
  - baseline and candidate technical payloads now expose the bounded `execution_runtime_projection_bridge` seam for `THR-X03/X05`
- deliberate limit of this slice:
  - runner/operator surface only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused runner/dashboard slice: `95 passed`
  - supporting runtime/bridge cross-check: `36 passed`

## Latest `13-C EXECUTION` depth slice: Shadow orchestrator and VPS service now persist the runtime projection seam

- new code truth:
  - `run_shadow_daily_orchestrator.py` now accepts `--execution-runtime-projection-path` and persists the projection ref plus readiness counts in `shadow_daily_orchestrator.last_run.json`
  - `run_shadow_vps_service.py` now forwards the same seam and persists it in service state, runtime evidence bundle, campaign summary, and monitoring payloads
  - `shadow_vps_service_monitoring.py` now exports bounded observability metrics for the execution runtime projection status and consumer counts
- deliberate limit of this slice:
  - descriptive persistence only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Shadow orchestrator/service slice: `24 passed`
  - supporting runtime/dashboard cross-check: `108 passed`

## Latest `13-C EXECUTION` depth slice: Micro-live and Live-Light now carry the runtime projection seam

- new code truth:
  - `src/protocols/contracts.py` now carries `execution_runtime_projection_*` fields across the canonical Build-12 and Build-13 input/summary contracts
  - `src/protocols/micro_live_runtime.py` now derives the seam from the governed Shadow technical payload bridge
  - `src/protocols/live_light_runtime.py` now propagates the same seam from governed Micro-live summaries into Build-13 inputs and summaries
  - normalized Build-10 Micro-live and Live-Light projections now preserve the seam for downstream monitoring
- deliberate limit of this slice:
  - descriptive protocol propagation only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused protocol/dashboard slice: `82 passed`
  - supporting runner/service/dashboard cross-check: `88 passed`

## Latest `13-C EXECUTION` depth slice: Micro-live and Live dashboard cards now expose the runtime projection seam

- new code truth:
  - `micro_live_dashboard.py` now surfaces the execution runtime projection status and consumer counts inside the Build-12 guardrails detail
  - `live_light_dashboard.py` now surfaces the same seam inside the Build-13 readiness detail
- deliberate limit of this slice:
  - operator visibility only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused dashboard slice: `33 passed`
  - supporting protocol cross-check: `76 passed`

## Latest `13-C EXECUTION` depth slice: Shadow live startup config now carries the runtime projection seam

- new code truth:
  - `ShadowLiveWebSocketConfig` now includes `execution_runtime_projection_path_ref`
  - `run_shadow_vps_service.py` now resolves that governed config-owned path when the explicit CLI projection path is absent
  - explicit CLI still wins, preserving the opt-in startup/config doctrine
- deliberate limit of this slice:
  - startup/config propagation only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused service/live-config slice: `12 passed`
  - supporting monitoring/orchestrator cross-check: `18 passed`

## Latest `13-C EXECUTION` depth slice: Shadow service now preserves runtime projection provenance

- new code truth:
  - Shadow service state, runtime evidence bundle, campaign summary, and monitoring payloads now preserve `execution_runtime_projection_source`
  - the bounded Shadow VPS observability export now labels the existing projection-ready metric with `projection_source`
- deliberate limit of this slice:
  - provenance only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused provenance slice: `8 passed`
  - supporting service/orchestrator cross-check: `22 passed`

## Latest `13-C EXECUTION` depth slice: Shadow Grafana now renders the runtime projection seam

- new code truth:
  - the local Shadow Grafana dashboard now includes dedicated execution runtime projection panels for readiness, ready/partial/blocked consumer counts, and instant labels carrying `projection_status` plus `projection_source`
  - the generated Shadow dashboard bundle now exposes that seam directly in Grafana instead of leaving it only in Prometheus and the technical dashboard
- deliberate limit of this slice:
  - observability only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Grafana slice: `2 passed`

## Latest `13-C EXECUTION` depth slice: Shadow service now preserves runtime projection observability across late telemetry failure

- new code truth:
  - the Shadow service now persists the runtime evidence bundle ref plus the `execution_runtime_projection` seam into service state before writing the later execution telemetry sidecar
  - if that sidecar write fails, Build-10 monitoring and Prometheus still expose `exec_projection` from the runtime evidence bundle instead of regressing to `not_configured`
- deliberate limit of this slice:
  - observability/persistence hardening only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused failure-hardening slice: `4 passed`

## Latest `13-C EXECUTION` depth slice: Shadow demo runs now skip missing telemetry sidecars cleanly

- new code truth:
  - `scripts/run_shadow_vps_service.py` now backfills `last_run.export_dir_ref` from `auto_export_dir` when that governed export exists
  - if a run is genuinely `demo`/replay-only and still has no governed export, the execution telemetry sidecar is skipped explicitly instead of degrading the Shadow service
  - the service emits `execution_telemetry_skipped`, keeps `execution_telemetry_ref=""`, and still closes the Shadow day successfully
- deliberate limit of this slice:
  - honest skip semantics only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Shadow/monitoring slice: `10 passed`
  - supporting orchestrator/replay cross-check: `16 passed`

## Latest `13-C EXECUTION` depth slice: Shadow telemetry status is now projected into Build-10 and Grafana

- new code truth:
  - the Shadow service now persists explicit telemetry status in typed state/campaign objects
  - Build-10 monitoring now surfaces `execution_telemetry_status` and exposes `exec_telemetry=<status>` in the compact operator detail string
  - the bounded Prometheus export now emits `v53_shadow_vps_execution_telemetry_ready{telemetry_status=...}`
  - the local Shadow Grafana bundle now contains dedicated telemetry panels, bringing the write/skip seam into Grafana instead of leaving it only in JSON/events
- deliberate limit of this slice:
  - observability only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Shadow/monitoring slice: `10 passed`
  - focused Grafana slice: `2 passed`

## Latest `13-C EXECUTION` depth slice: canonical Build-10 Shadow cards now surface execution telemetry

- new code truth:
  - `ShadowProjection` now includes `execution_telemetry_ref` and `execution_telemetry_status`
  - `scripts/run_technical_dashboard.py` now maps those service-owned fields from the Shadow campaign summary into the canonical Build-10 payload when rendering from local runtime artifacts
  - `src/ui/technical_dashboard_view.py` now renders an explicit `Execution Telemetry` card inside `Build-11 Shadow`
- deliberate limit of this slice:
  - dashboard/normalization only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Build-10/UI/launcher slice: `74 passed`
  - supporting Shadow monitoring non-regression: `10 passed`

## Latest `13-C EXECUTION` depth slice: THR-X04 is now a governed runtime consumer

- new code truth:
  - `THR-X04` now lands as `spread_guard` in the canonical execution runtime
  - the Local IA Lab runtime projection now carries three consumers: `rate_limiter`, `spread_guard`, and `slippage_model`
  - the runtime projection bridge/bootstrap/runtime/Build-10/Shadow/Micro-live/Live-light rails all preserve that third consumer without hidden activation
  - operator truth now includes `spread_guard_model_loaded` beside the existing rate-limit and slippage bridge flags
- deliberate limit of this slice:
  - opt-in runtime seam only
  - no hidden live activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused THR-X04 runtime slice: `50 passed`
  - supporting rail cross-check: `210 passed`

## Latest `13-C EXECUTION` depth slice: Build-9 smoke now accepts runtime projection injection

- new code truth:
  - `scripts/run_build9_core_smoke.py` now exposes `--execution-runtime-projection-path`
  - the operated execution bootstrap smoke now proves that `build_binance_execution_runtime(...)` can load `THR-X03/X04/X05` through the governed projection seam
  - default smoke behavior remains unchanged when that path is absent
- deliberate limit of this slice:
  - operated startup/config seam only
  - no hidden live activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused operated-smoke slice: `40 passed`

## Latest `13-C EXECUTION` depth slice: the operated Shadow chain now preserves bridge-load truth

- new code truth:
  - `run_shadow_daily_orchestrator.py` now derives `execution_runtime_projection_*` readiness from the canonical bridge projection instead of trusting only the Lab artifact headline
  - the operated Shadow chain now persists `execution_runtime_projection_bridge_status` and the three model-load flags for `rate_limiter`, `spread_guard`, and `slippage_model`
  - `run_shadow_vps_service.py` plus Shadow monitoring/Prometheus now expose that truth end-to-end
  - the local Shadow Grafana bundle now renders dedicated bridge/model-load panels on top of those new metrics
- deliberate limit of this slice:
  - operated reporting seam only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused operated-bridge slice: `12 passed`
  - supporting Shadow rail cross-check: `26 passed`
  - focused local Shadow Grafana update: `2 passed`

## Latest `13-C EXECUTION` depth slice: Build-10 Shadow cards now expose operated bridge truth

- new code truth:
  - `ShadowProjection` now carries the service-owned `execution_runtime_projection` bridge/load truth
  - `run_technical_dashboard.py` now projects those fields from the Shadow campaign summary into the canonical Build-10 payload
  - `technical_dashboard_view.py` now renders an explicit `Execution Projection` card inside `Build-11 Shadow`
  - the dev dual-role technical dashboard artifacts were regenerated from the current local runtime artifacts
- deliberate limit of this slice:
  - dashboard/normalization only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Build-10 Shadow card slice: `74 passed`

## Latest `Build-14` bounded Opus entry-timing reader

- new code truth:
  - `src/complete_enablers/micro_edge_entry_timing_layer.py` now exists as the bounded Build-14 reader for the still-open Opus `entry timing` suggestion
  - the reader only uses existing Build-14 observation facts and stays on the governed enabler rail
  - `src/complete_enablers/limited_influence.py` now includes that reader in Shadow and post-Shadow bounded influence evaluation
- deliberate limit of this slice:
  - Build-14 enabler only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Build-14 entry-timing slice: `97 passed`

## Latest `Build-14` bounded Opus exit-governor reader

- new code truth:
  - `src/complete_enablers/micro_edge_exit_governor.py` now exists as the bounded Build-14 reader for the still-open Opus `exit governor` suggestion
  - the reader only uses existing Build-14 observation facts and stays on the governed enabler rail
  - `src/complete_enablers/limited_influence.py` now includes that reader in Shadow and post-Shadow bounded influence evaluation
- deliberate limit of this slice:
  - Build-14 enabler only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live
- latest proofs:
  - focused Build-14 exit-governor slice: `99 passed`

## Latest `regime_lite` typed core

- new code truth:
  - `src/regime_classifier/regime_lite.py` now exists with typed `CALM / STRESSED / EXTREME`
  - the first cut covers explicit thresholds, bounded downgrade hysteresis, EXTREME cooldown, and transition trace
  - `regime_classifier` is now registered in the manifest/DAG as a real package instead of a missing target path
- deliberate limit of this slice:
  - no hidden runtime activation
  - no direct engine wiring in this cut
  - no shortcut around Shadow/Micro-live/Live
- remaining T9 work:
  - calibration artifact wiring
  - runtime/risk hooks
  - replay proof on stress windows

## Latest first governed risk consumer for `regime_lite`

- new code truth:
  - `src/risk_backbone/regime_lite_entry_gate.py` now exists
  - `RiskRuntime` now accepts a typed opt-in `regime_precheck_hook`
  - the first bounded behavior only rejects new entries while `EXTREME` or while cooldown is still active
- deliberate limit of this slice:
  - opt-in only
  - fail-open by default
  - no exit-all wiring yet
  - no hidden activation
- latest proofs:
  - focused `regime_lite + risk runtime` slice: `120 passed`

## Latest `regime_lite` calibration loader seam

- new code truth:
  - `src/regime_classifier/regime_lite.py` now exposes `RegimeLiteCalibrationConfig` and `resolve_regime_lite_thresholds(...)`
  - the typed helper now loads signed `THR-RG01..04` artifacts through `calibration_loader`
  - only the documented regime thresholds are artifact-governed in this cut; secondary dimensions stay on bounded documented defaults
  - `calibration_loader` is now registered in the canonical manifest/build-order/dependency registry
- deliberate limit of this slice:
  - opt-in only
  - no silent fallback when artifact loading is explicitly requested
  - no hidden runtime activation
- latest proofs:
  - focused `regime_lite + manifest` slice: `128 passed`

## Latest governed `regime_lite` safing recommendation

- new code truth:
  - `src/risk_backbone/regime_lite_safing.py` now exists as the explicit `EXTREME -> safing recommendation` seam
  - cooldown-only states stay on `ENTRY_BLOCK_ONLY`
  - live `EXTREME` states now yield `HALT_RECOMMENDED` + `should_exit_all=True`
  - the helper can materialize a canonical `OperatorSafingRequest(action=set_halted)` without inventing a new halt dialect
- deliberate limit of this slice:
  - recommendation only
  - no automatic kill switch trip
  - no hidden activation
- latest proofs:
  - focused `regime_lite + safing` slice: `128 passed`

## Latest Build-10 `regime_lite` safing observability seam

- new code truth:
  - Build-10 monitoring now exposes a typed `RegimeLiteSafingProjection` under `ShadowProjection`
  - `run_technical_dashboard.py` now hydrates that seam from the Shadow service campaign summary when available
  - the Build-11 Shadow card deck now includes an explicit `Regime Safing` card
  - canonical observability exports `v53_shadow_regime_lite_safing_status`
- deliberate limit of this slice:
  - recommendation only
  - no auto-`set_halted`
  - no hidden activation
- latest proofs:
  - focused `Build-10 regime_lite observability` slice: `85 passed`

## Latest `regime_lite` protocol-summary propagation

- new code truth:
  - canonical protocol contracts now carry `RegimeLiteGovernanceSummary`
  - Shadow is the first governed producer when explicit typed regime inputs are supplied
  - Micro-live and Live-Light preserve that seam end-to-end without synthetic classification
- deliberate limit of this slice:
  - explicit producer only
  - recommendation only
  - no hidden activation
- latest proofs:
  - focused `protocol regime_lite propagation` slice: `142 passed`

## Latest operated `regime_lite` Shadow service propagation

- new code truth:
  - the daily orchestrator now copies `shadow_summary.regime_lite_governance` into `shadow_daily_orchestrator.last_run.json`
  - the real Shadow VPS service now preserves that seam in:
    - `ShadowVpsRuntimeEvidenceBundle`
    - `ShadowVpsCampaignSummary`
    - service monitoring payload/detail
    - Prometheus service export
  - the operated metrics now include:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
- deliberate limit of this slice:
  - no synthetic regime inference in the service
  - recommendation only
  - no auto-halt
  - no hidden activation
- latest proofs:
  - focused `orchestrator + service + monitoring regime_lite` slice: `13 passed`

## Latest explicit operated `regime_lite` producer

- new code truth:
  - `run_local_replay_shadow.py` now accepts explicit typed:
    - `--regime-lite-assessment-path`
    - `--regime-lite-safing-recommendation-path`
  - the daily orchestrator and the real Shadow VPS service forward that opt-in seam end-to-end
  - operated artifacts now carry real `regime_lite` governance truth when the seam is provided, instead of leaving it protocol-only
- deliberate limit of this slice:
  - explicit opt-in only
  - no synthetic classifier inputs
  - recommendation only
  - no hidden auto-halt
- latest proofs:
  - focused `local_replay_shadow -> orchestrator -> service regime_lite` slice: `8 passed`

## Latest governed `regime_lite` auto-discovery

- new code truth:
  - `run_local_replay_shadow.py` now auto-discovers `regime_lite_assessment.json` and `regime_lite_safing_recommendation.json` from its governed `output_dir`
  - the daily orchestrator can therefore consume the seam without extra CLI wiring when those sidecars are staged in `shadow_output_dir`
- deliberate limit of this slice:
  - explicit path still wins
  - typed sidecars only
  - no synthetic classifier inputs
  - no hidden activation
- latest proofs:
  - focused `regime_lite auto-discovery` slice: `2 passed`

## Latest local Shadow Grafana `regime_lite` coverage

- new code truth:
  - the local Shadow Grafana dashboard now includes dedicated panels for:
    - `Regime Lite Entries Blocked`
    - `Regime Lite Exit-All Recommended`
    - `Regime Lite Labels`
  - the dashboard is now wired against the bounded service metrics:
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
    - `v53_shadow_vps_regime_lite_safing_status`
  - the local Grafana summary test no longer depends on the broken Windows `tmp_path` fixture on this machine
- deliberate limit of this slice:
  - monitoring-only seam
  - no dashboard-side inference
  - no hidden activation
- latest proofs:
  - focused `local shadow grafana regime_lite` slice: `4 passed`

## Latest Shadow VPS `regime_lite` config-ref provenance

- new code truth:
  - `ShadowLiveWebSocketConfig` now accepts:
    - `regime_lite_assessment_path_ref`
    - `regime_lite_safing_recommendation_path_ref`
  - `run_shadow_vps_service.py` now resolves them with explicit CLI precedence and persists the selected refs/sources through the operated Shadow rail
- deliberate limit of this slice:
  - typed refs only
  - no synthetic classifier inputs
  - recommendation-only, no hidden auto-halt
- latest proofs:
  - focused `shadow_vps_service + monitoring regime_lite provenance` slice: `12 passed`

## Latest Shadow VPS Prometheus `regime_lite` provenance labels

- new code truth:
  - the `regime_lite` Prometheus metrics now carry:
    - `assessment_source`
    - `safing_source`
  - the monitoring detail string now also summarizes that provenance directly
- deliberate limit of this slice:
  - bounded labels only
  - no new dashboard-only seam
  - no runtime behavior change
- latest proofs:
  - focused `shadow monitoring provenance labels` slice: `2 passed`

## Latest Build-10 `regime_lite` provenance detail

- new code truth:
  - `run_technical_dashboard.py` now hydrates:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
    from the operated Shadow service campaign summary
  - the Build-11 Shadow `Regime Safing` card now renders those refs/sources directly in the canonical technical dashboard
- deliberate limit of this slice:
  - dashboard consumer only
  - recommendation only
  - no hidden activation
- latest proofs:
  - focused `Build-10 regime_lite provenance detail` slice: `37 passed`

## Latest Binance Shadow PowerShell bootstrap

- new code truth:
  - `Install-BinanceApiEnv.ps1` now installs Binance API env vars in process scope and optionally user scope
  - `Start-BinanceShadowLiveCampaign.ps1` now stages the governed `build11_live_websocket_campaign`, runs one bounded Shadow service cycle, and re-renders the canonical HTML dashboard
  - the user-scope Binance env is now installed on the current Windows machine
- deliberate limit of this slice:
  - Shadow only
  - no repo-side secret persistence
  - dashboard remains read-only
- latest proofs:
  - focused `PowerShell Binance bootstrap` slice: operator scripts exercised successfully

## Latest native Binance live connect diagnostic

- new code truth:
  - `shadow_live_websocket.py` now preserves the endpoint and the root socket error when a native live connect attempt fails
  - the previously observed `WinError 10013` was confirmed to be a Codex sandbox network artifact
  - the same bounded live campaign now succeeds outside the sandbox on the real Windows host
- deliberate limit of this slice:
  - diagnostics only
  - no retry-policy change
  - no hidden activation
- latest proofs:
  - focused `shadow live websocket diagnostics` slice: included in the `44 passed` targeted test run

## Latest successful Binance Shadow operated campaign

- new code truth:
  - the bounded PowerShell launcher now completes successfully on the real host and regenerates the canonical technical dashboard
  - current operated campaign truth includes:
    - `last_completed_session_date=2026-04-12`
    - `last_error=""`
    - `execution_telemetry_status=written`
    - authenticated user-data capture summary present
    - live capture pairs `BTCUSDT`, `ETHUSDT`
- deliberate limit of this slice:
  - Shadow only
  - no live order path
  - dashboard remains read-only

## Latest `daily_pnl_breaker` typed core and first governed runtime consumer

- new code truth:
  - `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py` now exists as the typed persistent `THR-R01` seam
  - it loads governed `THR-R01`, enforces the documented `2%` hard cap, persists same-day Shadow lock state, and can optionally trip the canonical circuit breaker
  - `src/risk_backbone/daily_pnl_breaker_entry_gate.py` now exists as the first bounded runtime consumer
  - `RiskRuntime` now accepts a typed opt-in `daily_pnl_precheck_hook`, so the Build-4 rail can reject new entries once the daily breaker has forced the session into Shadow
- deliberate limit of this slice:
  - opt-in only
  - fail-open by default
  - no hidden live activation
  - no automatic same-day reactivation
- latest proofs:
  - focused `daily_pnl_breaker + risk_runtime` slice: `34 passed`
  - focused `risk_runtime + engine A/B/C/D cross-check` slice: `42 passed`

## Latest `reconciliation_scheduler` bounded operated seam

- new code truth:
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now exists
  - the scheduler now loads governed `THR-I04`, enforces bounded interval limits, and exposes typed `boot_reconcile(...)` + `run_periodic_if_due(...)`
  - boot reconciliation now has a canonical blocking seam for unresolved divergences
  - periodic reconciliation now has a canonical due/not-due seam and can trip the existing circuit breaker on critical divergence
- deliberate limit of this slice:
  - no hidden background loop
  - explicit caller ownership of timing
  - no bypass of the existing reconciliation runtime
- latest proofs:
  - focused `reconciliation_scheduler + reconciliation_layer` slice: `35 passed`
  - focused `execution_runtime cross-check` slice: `28 passed`

## Latest `execution_runtime_bootstrap` operated boot caller for `THR-I04`

- new code truth:
  - `src/protocols/execution_runtime_bootstrap.py` now exposes typed bootstrap bundles:
    - `ExecutionRuntimeBootstrapBundle`
    - `build_execution_runtime_bootstrap_bundle(...)`
    - `build_binance_execution_runtime_bootstrap_bundle(...)`
  - the existing runtime bootstrap helpers stay backward-compatible and still return only `ExecutionRuntime`
  - the bundle now carries optional bounded `reconciliation_scheduler` + `reconciliation_boot_result`
  - stale-only first boot with zero divergences is now treated as initial baseline establishment instead of a false trading block
  - `scripts/run_build9_core_smoke.py` is now the first real operated caller of this seam and can also load governed `THR-I04` from an optional calibration root
- deliberate limit of this slice:
  - opt-in only
  - no hidden scheduler loop
  - no fake Shadow integration before a real runtime caller exists
- latest proofs:
  - focused `execution runtime bootstrap + Build-9 smoke + reconciliation scheduler` slice: `20 passed`
  - focused `execution runtime cross-check` slice: `48 passed`

## Latest standalone Build-9 smoke alignment

- new code truth:
  - `scripts/run_build9_core_smoke.py` now imports the canonical engine facades through `engines.engine_a` and `engines.engine_b`
  - the same script now passes the explicit Build-8 portfolio `freshness_policy` required by the current `OrchestratorConfig`
  - the standalone operated report now reaches Build-2..9 `PASS`, including engine chain, portfolio chain, and execution bootstrap
  - the remaining direct-run failure is outside this slice: Build-1 still reports pre-existing DAG violations
- deliberate limit of this slice:
  - no new launcher
  - no compatibility alias package
  - canonical facades and typed config only
- latest proofs:
  - focused `Build-9 smoke script + execution bootstrap` slice: `21 passed`
  - direct `python scripts/run_build9_core_smoke.py` now fails only on Build-1 DAG debt

## Latest Build-1 DAG debt reduction

- new code truth:
  - the canonical registries now register the real on-disk packages:
    - `calibration_methods`
    - `secrets_manager`
    - `sharia_compliance`
    - `venue_adapters`
  - build-order ownership is now explicit for those packages without changing the Build-1 count
  - the dependency registry now authorizes the non-cyclic imports already present on disk for the execution/risk/scoring/local-replay/protocol drift
  - the Build-1 DAG report has dropped from `47` errors to `27`
  - the remaining failures are now the real cycle + forward-edge debt, not missing-manifest noise
- deliberate limit of this slice:
  - no validator weakening
  - no cycle authorization
  - no fake Build-1 green
- latest proofs:
  - focused `manifest registry` slice: `83 passed`
  - direct `dag_validator` report: `27` errors
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator`

## Latest Build-1 local Lab monitoring untangle

- new code truth:
  - the Local IA Lab monitoring projection/backend/observability builders were relocated under `monitoring`
  - `run_local_lab_analysis_bundle.py` now feeds that seam with primitive facts instead of `local_replay_runtime` typed objects
  - the former `local_replay_runtime` monitoring builder modules were deleted, so no reverse-edge wrapper remains
  - Build-1 debt has dropped further from `27` to `23` blocking errors
- deliberate limit of this slice:
  - no change to release semantics
  - no validator weakening
  - no profile expansion; COMPLETE-only doctrine preserved
- latest proofs:
  - focused `Local Lab monitoring seam` slice: `23 passed`
  - direct `dag_validator` blocking errors: `23`
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator`

## Latest Build-1 replay/protocol untangle

- new code truth:
  - the replay workflow loader was moved out of `monitoring` into `local_replay_runtime`
  - injected websocket frame loading was lowered into `data_backbone.websocket_gateway`
  - the `local_replay_runtime -> protocols` execution telemetry edge is now gone
  - Build-1 debt has dropped again from `23` to `19` blocking errors
- deliberate limit of this slice:
  - no protocol API break
  - no validator weakening
  - no profile expansion; COMPLETE-only doctrine preserved
- latest proofs:
  - focused `replay/protocol seam` slice: `36 passed`
  - direct `dag_validator` blocking errors: `19`
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator`

## Latest Build-1 DAG closure

- new code truth:
  - `execution_backbone` no longer imports fee gating from `scoring_backbone`
  - `execution_backbone` no longer imports the circuit breaker from `risk_backbone`
  - the last two helpers are now owned canonically inside `execution_backbone`
  - `scoring_backbone.fee_aware_edge_gate` and `risk_backbone.emergency_kill_switch.circuit_breaker` stay available as compatibility surfaces
  - the dependency registry no longer needs the temporary upward allowances for `execution_backbone -> risk_backbone/scoring_backbone`
- deliberate limit of this slice:
  - no validator weakening
  - no runtime behavior expansion
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `execution/risk/scoring compatibility` slice: `168 passed`
  - focused `manifest/build-order/dependency/layer` slice: `96 passed`
  - direct `dag_validator` report: `0` blocking errors
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T12 `gatekeeper` canonical landing

- new code truth:
  - `src/execution_backbone/gatekeeper/gatekeeper.py` now exists as the Build-3 execution convergence wrapper
  - `ExecutionRuntime.submit_opportunity(...)` now calls `ExecutionGatekeeper.authorize(...)` instead of chaining the pre-submit guards inline
  - the gatekeeper returns typed `ExecutionPermit` / `ExecutionRefusal` plus audit-ready `gate_trace`
  - refusals now preserve the real `pair` and `engine_id`
  - `ExecutionSubmission` now carries `gate_trace`, and the same trace is emitted in structured logs
- deliberate limit of this slice:
  - no persisted `artifacts/gatekeeper/` store yet
  - no new runtime path outside the canonical execution rail
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `gatekeeper + execution runtime + runtime bootstrap` slice: `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T13 `info_stress_monitor` bounded risk landing

- new code truth:
  - `src/risk_backbone/info_stress_monitor.py` now exists
  - the current lite implementation classifies `NORMAL / ELEVATED / EXTREME` from five simple microstructure anomaly signals
  - `build_info_stress_entry_gate(...)` now exposes the monitor as a typed Build-4 precheck hook
  - `RiskRuntime` now accepts `info_stress_precheck_hook` and candidate-side indicator inputs for this seam
  - EXTREME now blocks new entries through an explicit cooldown when the hook is injected
- deliberate limit of this slice:
  - opt-in only
  - no late-stage auto-wiring yet
  - bounded lite seam only, not the full MAS layer
- latest proofs:
  - focused `info_stress_monitor + risk_runtime` slice: `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T13 `info_stress` protocol propagation

- new code truth:
  - `src/protocols/contracts.py` now defines `InfoStressGovernanceSummary`
  - `src/protocols/shadow_runtime.py` now projects optional `InfoStressAssessment` into `ShadowRunSummary.info_stress_governance`
  - `src/protocols/micro_live_runtime.py` now preserves that summary through `MicroLiveInput` and `MicroLiveRunSummary`
  - `src/protocols/live_light_runtime.py` now preserves the same summary through `LiveLightInput` and `LiveLightRunSummary`
  - `src/protocols/__init__.py` now exports the summary type as canonical protocol surface
- deliberate limit of this slice:
  - no operated launcher/service wiring yet
  - no monitoring/dashboard projection yet
  - assessment-only seam only
- latest proofs:
  - focused `protocol contracts + shadow + micro-live + live-light` slice: `147 passed`
  - focused `info_stress_monitor + risk_runtime` slice: `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T13 `info_stress` operated Shadow rail

- new code truth:
  - `run_local_replay_shadow.py` now forwards typed `InfoStressAssessment` into the governed Shadow run and auto-discovers `info_stress_assessment.json`
  - `run_shadow_daily_orchestrator.py` now projects `info_stress_governance` into the persisted `last_run` sidecar
  - `run_shadow_vps_service.py` now accepts `--info-stress-assessment-path`, resolves `live_websocket_config.info_stress_assessment_path_ref`, and persists ref/source with the assessment-only governance truth
  - `shadow_vps_service_monitoring.py` now exposes the operated seam in the monitoring payload and Prometheus export
- deliberate limit of this slice:
  - assessment-only seam only
  - no recommendation or auto-halt layer added
  - no dashboard-first expansion beyond the canonical monitoring payload/export
- latest proofs:
  - focused `runner + orchestrator + service + monitoring` slice: `39 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T12 `gatekeeper` persisted audit store

- new code truth:
  - `src/execution_backbone/gatekeeper/audit_logger.py` now exists as the append-only audit logger for canonical gatekeeper decisions
  - `src/execution_backbone/execution_runtime.py` now persists gatekeeper outcomes on the existing `submit_opportunity(...)` path when a logger is injected
  - `src/protocols/execution_runtime_bootstrap.py` now accepts `gatekeeper_audit_path`
  - `scripts/run_build9_core_smoke.py` now materializes a real `artifacts/gatekeeper/audit.jsonl` when `--gatekeeper-audit-path` is provided
- deliberate limit of this slice:
  - still no extra monitoring/dashboard surface for this audit store
  - no new runtime path outside Build-3
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `gatekeeper + execution_runtime + bootstrap + build9 smoke` slice: `51 passed`
  - direct `python scripts/run_build9_core_smoke.py --gatekeeper-audit-path build/build9_core_smoke_run/artifacts/gatekeeper/audit.jsonl`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T11 `log_rotation` bounded seam

- new code truth:
  - `src/monitoring/log_rotation.py` now exists as the bounded gzip + retention helper
  - `rotate_log_file(...)` rotates one operated log into a timestamped archive, truncates the live file, and prunes old archives
  - `monitoring.__init__` now exports the helper
- deliberate limit of this slice:
  - no Telegram integration yet
  - no background scheduler/daemon
  - no new package/profile semantics
- latest proofs:
  - focused `log_rotation + disk_monitor + execution audit slice`: `55 passed`

## Latest T11 bounded `telegram_alerter` adapter

- new code truth:
  - `src/alerting/{__init__,telegram_alerter}.py` now exists
  - the adapter stays bounded on canonical `AlertRecord`, supports severity filtering, and loads sealed config via `secrets_manager`
  - `manifest_registry` now registers `alerting` as a canonical Build-11 module
- deliberate limit of this slice:
  - no hidden `monitoring_runtime` integration yet
  - no daemon / retry loop / background sender
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `alerting + manifest + layer DAG` slice: `126 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T11 operated Telegram alert seam on Shadow VPS service

- new code truth:
  - `src/protocols/shadow_vps_service_telegram_alerting.py` now exists
  - `scripts/run_shadow_vps_service.py` can now load an explicit Telegram config and emit bounded alerts from the operated Build-11 rail
  - delivery attempts are audited via `telegram_alert_sent` / `telegram_alert_failed` service events
- deliberate limit of this slice:
  - no hidden Build-10 wiring
  - no background retry daemon
  - Telegram failures stay fail-open for service execution
- latest proofs:
  - focused `protocols + alerting + manifest layer` slice: `43 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T11 operated Telegram monitoring projection

- new code truth:
  - `ShadowVpsServiceState`, `ShadowVpsCampaignSummary`, and `ShadowVpsServiceMonitoringPayload` now carry the last Telegram delivery truth
  - `run_shadow_vps_service.py` now persists that truth during delivery attempts and rewrites the final summary + monitoring export after `service_stopped`
  - `shadow_vps_service_monitoring.py` now emits `v53_shadow_vps_telegram_alert_delivery_status`
- deliberate limit of this slice:
  - no Build-10 UI/dashboard projection yet
  - no retry daemon or historical aggregation
  - last-state only, service-backed
- latest proofs:
  - focused `telegram seam + monitoring` slice: `17 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest T11 Build-10 technical dashboard projection

- new code truth:
  - `run_technical_dashboard.py` now projects `telegram_alert_delivery_status / event_type / error` from Shadow campaign summary into `ShadowProjection`
  - `technical_dashboard_view.py` now renders a dedicated `Build-11 Shadow / Telegram Alerts` card
  - `build/build11_live_websocket_campaign/technical_dashboard/*` has been regenerated with the new seam visible in the canonical HTML surface
- deliberate limit of this slice:
  - no Grafana expansion
  - no new operated alerting logic
  - still last-state only, service-backed
- latest proofs:
  - focused `launcher + view + monitoring backend` slice: `77 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest local Grafana + Telegram config provenance slice:

- current code truth:
  - local Shadow Grafana now renders `Telegram Alerts` and `Telegram Alert Labels`
  - `ShadowLiveWebSocketConfig` now accepts Telegram config/key refs, and the Shadow service resolves them with CLI precedence preserved
  - Telegram config provenance is now persisted through service state, runtime evidence, campaign summary, monitoring payload, and Prometheus label `config_source`
- deliberate limit:
  - no Build-10 projection of Telegram config provenance yet
  - no retry daemon, no hidden network behavior
- latest proofs:
  - focused `local_grafana + monitoring + launcher` slice: `21 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest operated execution runtime bootstrap monitoring slice:

- current code truth:
  - `run_shadow_vps_service.py` now carries the bounded bootstrap reconcile truth through runtime evidence and campaign summary
  - `shadow_vps_service_monitoring.py` now exposes the seam in the canonical Shadow payload and Prometheus
  - `run_technical_dashboard.py` and `technical_dashboard_view.py` now render a Build-11 Shadow `Execution Bootstrap` card
- deliberate limit:
  - no new runtime activation
  - no daemon/retry loop
  - no order-submit path
- latest proofs:
  - focused `shadow monitoring + technical dashboard + launcher` slice: `56 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest Build-1 executable engineering guardrails baseline:

- current code truth:
  - `smoke_bootstrap_recovery` now executes a repo-wide engineering guardrail scan derived from `CODEX_PROMPT.md`
  - `scripts/run_engineering_guardrails.py` now produces an audit-ready JSON/TXT report and can refresh the accepted legacy baseline
  - `config/engineering_guardrails_baseline.json` freezes the current legacy debt so the foundation rail fails only on net-new regressions
- preserve the doctrine:
  - no repo-wide blind rewrite
  - no hidden downgrade of Build-1
  - hotspot queue remains explicit and auditable
- latest proofs:
  - repo-wide baseline scan: `826` Python files, `4363` accepted legacy violations
  - steady-state guardrail run: `new_violations=0`
  - focused Build-1 guardrail tests: `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest first operated hotspot reduction under executable guardrails:

- current code truth:
  - the first guarded runtime hotspot, `scripts/run_shadow_vps_service.py`, has been reduced without changing the Shadow service semantics
  - inline CLI `print()` output is gone, parser construction is decomposed into typed helpers, and the execution-telemetry bare `except` is now explicit
  - the script still declares its remaining debt honestly: file length and three large monoliths
- preserve the doctrine:
  - no repo-wide blind rewrite
  - no hidden service behavior changes
  - the guardrail baseline is re-mined after each meaningful hotspot reduction so fixed debt does not remain silently accepted
- latest proofs:
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`
  - repo-wide guardrail total reduced from `4363` to `4341`
  - `scripts/run_shadow_vps_service.py` reduced from `26` to `4` residual guardrail violations

Latest second operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_shadow_vps_service.py` no longer builds `ShadowVpsCampaignSummary` as one large inline constructor
  - campaign summary generation now flows through grouped typed field-builders for `core`, `live_capture`, `execution`, `regime_lite`, and `info_stress`
  - the helper split removes the prior `_write_campaign_summary(...)` guardrail breach without changing the persisted schema
- deliberate limit:
  - no service-loop behavior change
  - no summary schema drift
  - the next remaining hotspot stays explicit: `_write_runtime_evidence_bundle(...)`
- latest proofs:
  - repo-wide guardrail run: `total_violations=4340`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest third operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_shadow_vps_service.py` no longer builds `ShadowVpsRuntimeEvidenceBundle` as one large inline constructor
  - durable runtime evidence generation now flows through grouped typed builders for `input`, `execution`, `projection`, `regime_lite`, `info_stress`, and artifact refs
  - `_write_runtime_evidence_bundle(...)` is now under the executable guardrail threshold with no schema drift
- deliberate limit:
  - no service-loop behavior change
  - no durable artifact rename
  - the remaining hotspot on this file is now the main service loop plus file length
- latest proofs:
  - refreshed guardrail baseline, then steady-state run: `total_violations=4339`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest fourth operated hotspot reduction under executable guardrails:

- current code truth:
  - the Shadow VPS service public entrypoint is now reduced to startup + bounded main-loop + finalize/output orchestration
  - helper extraction kept the operated service semantics unchanged while clearing the last new guardrail violation on this hotspot
  - explicit remaining debt on the file is now only `FILE_TOO_LONG`
- deliberate limit:
  - no service-loop behavior change
  - no durable artifact/schema change
  - no monitoring contract drift
- latest proofs:
  - repo-wide guardrail run: `total_violations=4338`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest fifth operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_local_replay_shadow.py` no longer keeps the governed LOCAL_REPLAY -> SHADOW export flow inline in one long runner function
  - the operated runner now delegates import-context resolution, materialization, runtime-bundle assembly, day/session persistence, demo payload construction, and per-engine evaluations to typed helpers
  - explicit remaining debt on this hotspot is now only the file-length split; function-level debt is cleared
- deliberate limit:
  - no control-flow drift on the governed Shadow rail
  - no sidecar/schema rename
  - no change to the LOCAL_REPLAY / session-summary / runtime-evidence contracts
- latest proofs:
  - repo-wide guardrail run: `total_violations=4316`, `new_violations=0`
  - focused `local replay shadow runner` slice: `18 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest sixth operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_local_replay_shadow.py` is now reduced to a stable CLI/public facade
  - the governed runner internals are split into bounded support modules for recovery/models, per-engine Shadow evaluation, payload/projection building, import pipeline, and runtime/session materialization
  - all split files are now at `0` local guardrail violations, so the previous runner file-length debt is fully removed instead of merely relocated
- deliberate limit:
  - no control-flow drift on the LOCAL_REPLAY -> SHADOW operated rail
  - no sidecar/schema rename
  - no public API drift for `main`, `export_local_replay_shadow_run`, or `LocalReplayShadowArtifacts`
- latest proofs:
  - repo-wide guardrail run: `total_violations=4315`, `new_violations=0`
  - focused `local replay shadow runner` slice: `18 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest seventh operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_local_lab_analysis_bundle.py` now centralizes CLI artifact output through `_emit_local_lab_analysis_bundle_output(...)`
  - the Local IA Lab chained pipeline is unchanged, but the inline terminal `print()` debt is removed
  - explicit remaining debt on this hotspot is now narrowed to `FILE_TOO_LONG` and the still-monolithic `main(...)`
- deliberate limit:
  - no artifact/schema rename
  - no pipeline behavior change
  - no attempt yet to split the full `main(...)` monolith
- latest proofs:
  - repo-wide guardrail run: `total_violations=4287`, `new_violations=0`
  - focused `local_lab_analysis_bundle launcher` slice: `7 passed`
