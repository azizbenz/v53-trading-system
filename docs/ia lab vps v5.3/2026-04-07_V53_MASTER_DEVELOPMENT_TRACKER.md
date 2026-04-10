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
