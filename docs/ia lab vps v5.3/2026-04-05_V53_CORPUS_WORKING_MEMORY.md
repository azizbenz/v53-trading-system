# 2026-04-05 V5.3 Corpus Working Memory

## Role Of This File

This file is not a superior canon document.
It is the operational memory for the current repository work.

Use it to answer:
- what rail is active now
- what was just closed
- what remains open
- what must stay closed
- how the next session must start

## Current Active Rail

Active runtime rail:
- `LOCAL_REPLAY -> SHADOW -> MICRO_LIVE -> LIVE`

Governed import/promotion constraint:
- `source_profile=COMPLETE`

Current work mode:
- foundations first
- typed governance before implicit logic
- runtime safety before new platform opening
- no UI-first detours while canonical structural gaps remain

## Current Session Doctrine

Every session must begin with:

- `You are working on module X.`
- `Global invariants: [...]`
- `Modules Y and Z must connect to X via [...]`
- `Forbidden defaults: [...]`
- `After generation, verify explicitly: [...]`

The goal is to prevent context loss and local hallucination.

## Rails That Must Stay Closed

Do not open these rails unless explicitly promoted by a deliberate decision:

- `local_ai_lab`
- `control_plane`
- global multihook executor
- new hook families beyond the currently opened bounded slices `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`, and `EXECUTION_NO_TRADE_FILTER`
- cosmetic monitoring/UI expansions without a foundation reason

## Last Verified Closures

Previously closed before this doc reconstruction:

Latest closure added after the eighth bounded hook slice:

- Build-10 monitoring now projects the full eight-hook compiled bridge set through a typed `runtime_hook_bridges` surface instead of exposing only `execution_no_trade_bridge`
- `src/protocols/execution_runtime_dashboard.py` now exposes a shared `build_runtime_hook_bridge_projections(...)` helper used by the dashboard and Shadow demo payload builders
- `src/ui/technical_dashboard_view.py` now renders a dedicated `Artifact Hooks` section
- `src/monitoring/observability.py` now emits per-hook bridge metrics `v53_runtime_hook_bridge_*`
- proof:
  - `rtk pytest tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `104 passed`
- feature dictionary / transform whitelist / lineage lock
- runtime error policy on open execution hook bridge
- compiled hook plan `load_error` typing
- risk runtime position and loss-budget release mechanics
- explicit runtime timestamp policy
- circuit breaker gating on engine runtimes
- scoring hot-path hardening
- beta mapping fail-closed behavior
- beta governance no longer accepts universal fallback values and now requires timestamped mappings on the active risk rail
- drawdown / peak-equity normalization
- artifact proof quantitative floors
- TTL / drift governance at import layer
- A/B calibration governance slices
- hook module skeletons

Closed during the latest verified slices:
- `BS-44` explicit orchestrator freshness policy
- `BS-42` source-scoped divergence thresholds
- `BS-45` shadow slot consumption semantics
- `BS-47` explicit `now` handling in shadow day counter
- `BS-48` immutable shadow counter state transitions
- `BS-50` bounded retention of terminal execution state
- `BS-51` typed reconciliation policy for fills and positions
- `BS-53` typed adverse-selection delay policy
- `BS-54` removal of dead backpressure action
- `BS-55` deterministic dispatcher ordering
- `BS-56` shadow stale exchange data blocks
- `BS-57` reverse skew correctly detected
- `BS-58` bounded contradiction retention
- `BS-59` deterministic replacement intent ids
- `BS-60` explicit zero-division failure semantics
- `BS-61` explicit Decimal -> float64 loss boundaries
- `BS-52` explicit typed Build-14 contract checks in `live_light_runtime`
- `BS-41` governed shadow slot/session-date consistency
- `BS-68` shadow session registry rollback on persist failure
- local replay governed entry-rail convergence
  - `ReplayOrchestratorRequest` now defaults to `ProfileId.COMPLETE`
  - `run_local_replay_export.py` now defaults governed export launches to `--profile-scope complete`
  - explicit `LIGHT` remains available only as a deliberate compatibility override
- local replay resume-governance convergence
  - completed-export resume now revalidates the request against persisted `replay_session_config.json` and `replay_run_manifest.json`
  - `run_local_replay_export.py` hydrates missing resume identifiers from persisted metadata instead of silently drifting on CLI defaults
  - explicit contradictory resume metadata is now rejected
- local replay state/evidence fail-safe convergence
  - `replay_state_store.py` and `runtime_evidence.py` no longer swallow corrupted persisted JSON silently
  - both stores now back up corrupted state to `.corrupted` and rebuild with typed `last_error` markers
  - the replay evidence recorder now also exposes `build_state()` so the recovery state can be audited directly
- upload/import governance-reference convergence
  - `ArtifactUploadRequest` now carries an explicit `governance_reference_date`
  - `build_import_request_from_upload_request()` now forwards that date unchanged
  - the upload/import handshake no longer injects `date.today()` as hidden governance state
- export-dir -> typed import/upload builder convergence
  - `src/backtest_artifact_import/export_dir_bridge.py` now materializes typed `ReplayExecutionPlan`, `ArtifactImportRequest`, and `ArtifactUploadRequest` directly from governed export directories
  - the bridge preserves `artifact_schema_version`, `feature_set_version`, and `transform_set_version` from `replay_run_manifest`
  - feature lineage / transform locks are now derived from `recognized_feature_keys` only, with explicit empty recognition no longer falling back to raw unrecognized `feature_keys`
  - timeframe-qualified keys like `sweep_score_1m` are now mapped to canonical sweep lineage instead of being silently dropped
  - `run_local_replay_shadow.py` now reuses the shared feature-lock builder on the demo path as well
- replay-plan -> typed import builder convergence
  - `src/backtest_artifact_import/export_dir_bridge.py` now exposes a shared `ReplayExecutionPlan + payload bundle -> ArtifactImportRequest` builder
  - `run_local_replay_shadow.py` and `run_technical_dashboard.py` now reuse that builder instead of reconstructing governed imports locally
  - the technical dashboard keeps its governed onboarding propagation, but its signed import path now relies on the same built-in Ed25519 verification surface as the Shadow demo rail
- replay-plan -> typed upload builder convergence
  - `src/backtest_artifact_import/export_dir_bridge.py` now also exposes a shared `ReplayExecutionPlan + payload bundle -> ArtifactUploadRequest` builder
  - `run_technical_dashboard.py` is now the first real launcher on the active rail to consume the upload contract directly
  - the dashboard demo now emits upload dry-run sidecars and derives governed import from `upload_request -> import_request`
- replay/evidence -> typed artifact bundle/upload convergence
  - `src/backtest_artifact_import/export_dir_bridge.py` now also exposes a shared `ReplayExecutionPlan + replay evidence -> ArtifactExportBundle` builder
  - `run_technical_dashboard.py` no longer builds its `ArtifactExportBundle` locally
  - `run_local_replay_shadow.py` now consumes the same replay/evidence -> upload -> import chain and emits upload dry-run sidecars before Shadow
  - TTL governance on the upload-derived artifact bundle now stays anchored on `governance_reference_date`, not replay-history timestamps
- bounded `T4` Binance order-path foundation closure
  - `src/venue_adapters/binance_spot/order_translator.py` now translates `ExecutionIntent` into a typed Binance order request
  - `src/venue_adapters/binance_spot/error_classifier.py` now classifies bounded Binance order API failures
  - `src/venue_adapters/binance_spot/rest_client.py` now supports signed `POST /api/v3/order`, signed `GET /api/v3/openOrders`, and signed `DELETE /api/v3/order`
  - `src/venue_adapters/binance_spot/execution_adapter.py` now implements the bounded `ExecutionVenueAdapter` contract over that REST surface
  - `src/venue_adapters/binance_spot/user_data_events.py` now exposes a bounded authenticated user-data event source plus `executionReport` parser
  - `src/venue_adapters/binance_spot/user_data_ws_client.py` now exposes a bounded authenticated websocket client for `userDataStream.subscribe.signature`
  - `src/venue_adapters/binance_spot/bootstrap.py` now builds the adapter from `BinanceAdapterConfig + credentials`, with optional injection of that websocket source
  - `src/protocols/execution_runtime_bootstrap.py` now consumes that builder via `build_binance_execution_runtime(...)`
  - `scripts/run_build9_core_smoke.py` now consumes that runtime bootstrap on a bounded local smoke path
  - replace is now modeled explicitly as cancel + submit on the adapter rail
  - remote reconciliation now has a minimal live bridge through `openOrders + account snapshot`
  - `poll_order_events()` now drains an injected bounded user-data source when present
  - a bounded `socket -> payloads -> event source -> execution adapter` path now exists locally
  - deterministic `clientOrderId` now uses `engine_id + intent_id`, because `ExecutionIntent` carries `engine_id` in the real repo contract
  - proof:
    - `rtk pytest tests/test_venue_adapters/test_binance_spot tests/test_execution_backbone tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
    - `193 passed`
  - honest residual:
    - no real Testnet submit proof yet
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
- bounded Build-17 Complete pair-scope selection is now real and test-backed
  - the launcher accepts explicit `--pair ...` selectors or governed `--pair-count N`
  - selection stays inside the canonical 12 COMPLETE pairs
  - the chosen scope is now visible in HTML and persisted sidecars (`payload`, `view`, `supplement`)
  - latest proof:
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py -q` -> `6 passed`
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py -q` -> `67 passed`
- bounded Build-17 Complete pair-scope assistant is now clickable locally
  - the HTML now renders a governed selection panel with 12 canonical pair checkboxes, `first N` helper, and a copyable PowerShell relaunch command
  - the page still does not fake a runtime rescope in-browser; it makes relaunch explicit and keeps payload truth intact
  - latest proof:
    - `rtk pytest tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_complete_dashboard_launcher.py -q` -> `8 passed`
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_monitoring/test_monitoring_backend.py -q` -> `69 passed`
- bounded `13-A / T6-prep` Local IA Lab EDGE slice is now closed on producer/helper scope
  - `src/local_replay_runtime/edge_gate_calibration.py` now calibrates `THR-E01` / `THR-E02` from replay `DTRRecord` evidence
  - the report publishes conservative values only (upper bootstrap CI bound + human floor)
  - `build_edge_gate_calibration_artifact(...)` now emits a shared `CalibrationArtifact`
  - `scripts/run_edge_gate_calibration.py` now turns governed `replay_dtr.jsonl` evidence into a signed `edge_gate.yml`
  - the same launcher now also accepts a governed `--export-dir` and emits `edge_gate.input_summary.json` as a future-facing audit/dashboard sidecar
  - `scripts/run_local_replay_export.py` can now emit that EDGE artifact directly during the governed export flow
  - `src/scoring_backbone/fee_aware_edge_gate.py` now exists as the exact future consumer surface, resolved via `calibration_loader`
  - latest proof:
    - `rtk pytest tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q` -> `19 passed`
    - `rtk pytest tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_artifact_exporter.py tests/test_scoring_backbone/test_scoring_runtime.py -q` -> `23 passed`
- `BS-40` bounded crypto closure on the governed artifact rail
  - `src/backtest_artifact_import/signature_policy.py` now ships real base64 Ed25519 trust-store public keys and a built-in pure-Python verifier
  - `run_technical_dashboard.py` and `run_local_replay_shadow.py` now use a shared real signed fixture envelope instead of local accept-all verifier lambdas
  - the active rail stays fail-closed on malformed signatures, unknown keys, revoked keys, and payload-hash mismatch
- `BS-87` bounded engine-runtime safety closure
  - `src/engines/engine_a/engine_a_runtime.py`, `src/engines/engine_b/engine_b_runtime.py`, `src/engines/engine_c/engine_c_runtime.py`, and `src/engines/engine_d/engine_d_runtime.py` now require an explicit `EmergencyCircuitBreaker`
  - the active engine runtimes no longer keep a permissive `None` branch before `is_trading_allowed()`
  - touched engine-runtime tests now import from canonical `engines.engine_*` packages and assert constructor rejection when `circuit_breaker=None`
- bounded `BS-49` code convergence on active profile defaults
  - `TradeLearningInput.profile` now defaults to `ProfileId.COMPLETE`
  - the locked operator UI now accepts governed `COMPLETE` requests while preserving explicit `LIGHT` compatibility
  - the Build-10 locked dashboard projection is now profile-aware and no longer hardcodes `Light` wording on `COMPLETE` payloads
  - active Build-10 source wording now consistently speaks about a locked operator UI rather than a locked Light UI
  - the technical dashboard now shows an explicit `Build-10` section in the typed view and rendered HTML
- bounded locked operator UI state fail-safe convergence
  - `src/ui/light_ui_runtime.py` no longer swallows persisted-state corruption silently
  - corrupted locked-operator UI state is now backed up to `.corrupted` and rebuilt with an explicit `last_error` marker
  - `OperatorRuntimeProjection.last_error` is now projected through Build-10 monitoring, and the `Operator Events` cards in the locked operator UI and technical dashboard now surface that state corruption explicitly
- bounded `BS-49` doctrine convergence on top-level specs
  - `V5_3_MASTER_FINAL_UNIQUE.md`, `V5_3_MASTER_FINAL_CANONICAL.md`, `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`, and `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md` now read Build-11/12/13 as governed `COMPLETE` rails
  - historical labels `Shadow intégral`, `Micro-live Light`, and `Live-Light` are now explicitly treated as historical/documentary wording in the top-level canon
- bounded `BS-49` doctrine convergence on lower-level phase specs
  - `V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`, `V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`, `V5_3_BUILD13_SPEC_LIVE_LIGHT.md`, and `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md` now start with active-reading notes
  - their canonical phase-state bullets now read Build-11/12/13 with governed `profil=COMPLETE`
  - Build-14 now speaks about the current governed rail vs the wider `extension COMPLETE` rollout instead of treating current runtime `COMPLETE` as not yet active
- bounded `BS-49` convergence on Build-10 detailed spec, deep master rollups, and manifest-registry descriptions
  - `V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md` now speaks about a locked operator UI while preserving the historical `Light UI` label
  - the deep Build-10/11/12/13 recap sections in `V5_3_MASTER_FINAL_UNIQUE.md` and `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md` now read the canonical runtime states as `COMPLETE`
  - `manifest_registry` descriptions now preserve historical stage names but describe the active runtime rail as `COMPLETE`
- bounded `BS-49` convergence on monitoring/dashboard test coverage
  - Build-10 backend, runtime, and technical dashboard tests now assert governed `ProfileId.COMPLETE` paths directly
  - the test proof is no longer limited to historical `LIGHT` compatibility scenarios
- bounded `BS-49` convergence on secondary monitoring/ui wording
  - `src/monitoring/contracts.py` now documents Build-13 as the active Live rail and keeps `Live-Light` as historical wording
  - `src/monitoring/technical_dashboard_backend.py` now names `Live` first in governed extensions detail and marks `Live-Light` as historical
  - the remaining residue was concentrated in historical file/class names and secondary docs, not in active Build-10 supervision wording
- bounded `BS-49` convergence on secondary navigation docs
  - `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md`, `V5_3_INDEX_MAITRE_FINAL_CORPUS.md`, `V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md`, and the Build-11/12/13 section of `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md` now carry active-reading notes for the governed `COMPLETE` rail
  - this reduces the risk that a new session reopens `LIGHT` as the active rollout just by reading orientation docs
- bounded `BS-38` semantic Shadow recovery closure
  - `shadow_day_counter.py` now rebuilds durable counter state from validated persisted day records
  - `shadow_session_registry.py` now rebuilds durable registry continuity from validated persisted entries
  - `run_local_replay_shadow.py` now restores counted-day continuity from durable day records after counter/registry corruption
- bounded final `BS-49` closure on active public surfaces
  - `ui` now exposes canonical `LockedOperator*` names first and keeps `Light*` as explicit compatibility aliases
  - `monitoring` now exposes canonical `LiveProjection` and `live` / `live_status` accessors while preserving legacy fields for compatibility
  - `protocols` now exposes canonical `Live*` names first and keeps `LiveLight*` as explicit compatibility aliases
  - canonical tests now exercise those new names directly on the active Build-10 / Build-13 rails
- bounded `BS-92` manual suspension audit closure
  - `src/data_backbone/pair_health_scorer/suspension_decider.py` now exposes `suspend_manual()` as the only explicit `MANUAL` suspension path
  - manual suspension now requires both `operator_id` and `reason_text`
  - `evaluate_suspension()` still cannot emit `MANUAL`, preserving the explicit audited operator path
- bounded `BS-89` REST gap-fill fail-close closure
  - `src/data_backbone/rest_bootstrap/gap_fill_controller.py` now rejects `gap_size <= 0.0` before any fill path
  - negative or zero gaps now fail closed with an explicit inversion message instead of silently filling
- bounded `BS-88` phantom-cost baseline closure
  - `src/scoring_backbone/penalty_aggregator/penalty_cap_guard.py` now requires `expected_cost > 0.0` before entering the phantom-risk comparison
  - `expected_cost <= 0.0` is now treated as an absent economic baseline instead of a phantom verdict trigger
- bounded `BS-86` engine timestamp-unit closure
  - all four `EngineXRuntimeInput` contracts now require millisecond-scale `timestamp_ms >= 1_000_000_000_000`
  - the dedicated regression proof now uses canonical `engines.engine_*` imports instead of stale top-level package names
- bounded `BS-90` REST quota TOCTOU closure
  - `src/data_backbone/rest_bootstrap/runtime_bootstrap.py` now consumes rate-limit quota atomically through `record_call()` on the resync path
  - a failed `record_call()` no longer falls through to `fill_gap()`
- bounded `BS-93` explicit pair-health threshold closure
  - `src/data_backbone/pair_health_scorer/suspension_decider.py` no longer hides a universal `threshold=0.3` default on the health-based path
  - only `hard_stale` and `consistency_failed` remain threshold-free suspension reasons
- bounded `BS-91` rate-limit prune allocation closure
  - `src/data_backbone/rest_bootstrap/rate_limit_guard.py` now keeps call timestamps in a deque
  - prune now runs in place instead of rebuilding a filtered list every time
- bounded `BS-81` drawdown enforcement closure
  - `src/risk_backbone/risk_runtime.py` already converts `DrawdownVerdict.REDUCE_EXPOSURE` into `RiskRuntimeAction.REDUCE_EXPOSURE`
  - drawdown state is therefore enforced on the active risk rail, not left as advisory-only metadata
- bounded `BS-83` explicit unknown-cluster closure
  - `src/scoring_backbone/ranking_router/portfolio_compatibility_checker.py` now distinguishes unknown cluster mapping from exhausted configured cluster capacity
  - unknown clusters fail closed as mapping errors instead of looking like `remaining=0.0`
- bounded `BS-82` Build-8 unknown-cluster alignment closure
  - `src/portfolio_minimal/opportunity_selector/eligibility_filter.py` now rejects unknown cluster mappings before selection
  - `src/portfolio_minimal/opportunity_selector/selection_resolver.py` now emits `REJECTED_UNKNOWN_CLUSTER` instead of letting allocation silently cap to zero
- bounded `BS-80` explicit beta-governance closure
- bounded `BS-35` hook-governance closure via a single canonical `runtime-open` hook-id source of truth
  - `src/interface_contracts/artifact_contracts.py` now defines the single canonical `RUNTIME_OPEN_HOOK_IDS` set
  - that source now governs eight active bounded slices: `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`, and `EXECUTION_NO_TRADE_FILTER`
  - `src/protocols/*_hooks.py` now derive `RUNTIME_OPEN` from that single canonical source
- bounded eighth real hook/runtime opening on the active rail
  - `src/protocols/portfolio_relative_rank_adjustment_bridge.py` now provides the compiled-plan fail-open bridge for `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`
  - `src/protocols/portfolio_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/portfolio_minimal/portfolio_orchestrator.py` now accepts a typed relative-rank hook and reapplies deterministic reranking before `resolve_selection`
- bounded seventh real hook/runtime opening on the active rail
  - `src/protocols/scoring_soft_penalty_layer_bridge.py` now provides the compiled-plan fail-open bridge for `SCORING_SOFT_PENALTY_LAYER`
  - `src/protocols/scoring_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/scoring_backbone/scoring_runtime.py` now accepts a typed soft-penalty hook and applies bounded `raw_score_multiplier / raw_score_add / raw_score_cap` adjustments before `calculate_raw_score`
- bounded sixth real hook/runtime opening on the active rail
  - `src/protocols/risk_micro_friction_precheck_bridge.py` now provides the compiled-plan fail-open bridge for `RISK_MICRO_FRICTION_PRECHECK`
  - `src/protocols/risk_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/risk_backbone/risk_runtime.py` now accepts a typed micro-friction precheck hook and can reject before the severe-pressure fallback path
- bounded fifth real hook/runtime opening on the active rail
  - `src/protocols/engine_a_pre_entry_confirmation_bridge.py` now provides the compiled-plan fail-open bridge for `ENGINE_A_PRE_ENTRY_CONFIRMATION`
  - `src/protocols/engine_a_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/engines/engine_a/engine_a_runtime.py` now accepts a typed pre-entry validation hook and can block before scoring
- bounded fourth real hook/runtime opening on the active rail
  - `src/protocols/engine_c_void_validation_bridge.py` now provides the compiled-plan fail-open bridge for `ENGINE_C_VOID_VALIDATION`
  - `src/protocols/engine_c_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/engines/engine_c/engine_c_runtime.py` now accepts a typed void-validation hook and can block before scoring
- bounded second real hook/runtime opening on the active rail
  - `src/protocols/engine_b_sweep_validation_bridge.py` now provides the compiled-plan fail-open bridge for `ENGINE_B_SWEEP_VALIDATION`
  - `src/protocols/engine_b_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/engines/engine_b/engine_b_runtime.py` now accepts a typed sweep-validation hook and can block or adjust score before scoring
  - `src/scoring_backbone/scoring_runtime.py` now supports bounded raw-score multiplier/add/cap adjustments instead of forcing hook effects through ad hoc penalty hacks
- bounded third real hook/runtime opening on the active rail
  - `src/protocols/engine_d_reentry_validation_bridge.py` now provides the compiled-plan fail-open bridge for `ENGINE_D_REENTRY_VALIDATION`
  - `src/protocols/engine_d_hooks.py` now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
  - `src/engines/engine_d/engine_d_runtime.py` now accepts a typed re-entry validation hook and can block before scoring
- bounded `BS-78` engine A/B physics-penalty symmetry closure
  - `src/data_backbone/market_physics_math.py` now carries the shared governed conviction penalty weights for `fragility`, `toxicity`, and `micro_friction`
  - `src/engines/engine_b/conviction_builder_b.py` no longer underweights the same physics stress inputs relative to `engine_a`
- bounded `BS-77` Engine B neutral false-breakout default closure
  - `src/engines/engine_b/conviction_builder_b.py` and `src/engines/engine_b/engine_b_runner.py` now default `false_breakout_score` to neutral `0.5`
  - missing false-breakout information no longer silently reads as “no false breakout detected”
- bounded `BS-84` websocket reconnect cleanup closure
  - `src/protocols/shadow_live_websocket.py` now closes stale endpoint clients before replacing them on reconnect
  - reconnect no longer leaves the old native websocket client unclosed in memory
- local runner import-governance alignment
  - `run_local_replay_shadow.py` now supplies explicit lifecycle/drift governance to governed imports
  - `test_local_replay_shadow_runner.py` is green again under the current import contract
- VPS auto-export session-date pinning
  - `run_shadow_vps_service.py` now pins auto-exported `replay_run_manifest.timeframe_scope` to the source governed day for `raw_input`, `websocket`, and `native_live_websocket`
  - service progression now advances on `2026-04-01 -> 2026-04-02` instead of collapsing to replay timestamp dates

## Current Remaining Work

Immediate next slice:
- toward IA Lab, continue on the real rail `local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`
- the concrete `export_dir -> ArtifactUploadRequest / ArtifactImportRequest` builder is now closed
- launcher-side ad hoc import builders are now also closed
- first launcher-side upload adoption is now closed on the dashboard demo path
- the Shadow runner now consumes the same upload rail, so the practical IA Lab entry rail has a stable end-to-end proof
- the second real hook/runtime slice is now also open and verified on the active rail
- the next move can now be a deliberate perimeter decision instead of more plumbing or compatibility cleanup by habit
- do not invent `src/local_ai_lab` while the real entry rail is still being hardened
- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md` is now delivered
- the working ownership is now:
  - `Local IA Lab` = calibration / backtest / replay / proof / human signature
  - `VPS` = runtime consumption / Shadow / Micro-live / Live
  - `src/calibration_loader/` = shared core
- accepted future concept:
  - `multi-VPS` is allowed only as a read-only fleet overview of `health / runtime_mode / artifact_version / heartbeat / alert_state`
  - full detail still requires connecting to VPS `X`
  - no active orchestration or failover loop is implied
- remembered next safe order for that future concept:
  - M0 = doc/contract fields only
  - M1 = monitoring/UI read-only overview
  - M2 = per-VPS drill-down entry point
  - never remote-control or auto-promote across VPS instances
- M0 is now closed:
  - `src/monitoring/contracts.py` now defines `FleetNodeProjection` and `FleetOverviewProjection`
  - the slice stays read-only and synthetic; no backend/UI binding yet
  - proof: `rtk pytest tests/test_monitoring/test_monitoring_contracts.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_technical_dashboard.py -q` -> `73 passed`
- current safe code work remains:
  - threshold-consumer inventory from `11_...` is already done in `11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md`
  - shared calibration contract/loader prep is now done in `src/calibration_loader/` with typed missing/invalid/unsigned failures
  - continued hardening of the verified IA Lab entry rail already present in code
- latest LOCAL_REPLAY hardening slice now closed:
  - `src/local_replay_runtime/replay_orchestrator.py` backs up corrupted resume metadata / chunk session sidecars to `.corrupted`
  - resume now fails closed explicitly on corrupted `replay_session_config.json`, `replay_run_manifest.json`, `replay_chunk_session.json`, and resume sidecars
  - proof: `pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py -q --basetemp=build/pytest-local-replay-resume-proof` -> `20 passed`
- latest export->import hardening slice now closed:
  - `src/backtest_artifact_import/export_dir_bridge.py` backs up corrupted governed sidecars to `.corrupted`
  - strict sidecars covered now: `replay_run_manifest.json`, `feature_bridge.json`, `parity_diagnostics.json`, `replay_metrics.json`, `replay_dtr.jsonl`
  - symbolic non-file refs on the demo shadow path remain allowed as non-export-dir metadata
  - `parity_diagnostics`, `replay_metrics`, and `replay_dtr` now validate against typed contracts on the real `export_dir` path
  - proof: `pytest tests/test_local_replay_runtime/test_shadow_execution_simulator.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py -q --basetemp=build/pytest-export-import-bridge-proof-3` -> `79 passed`
- latest export->import semantic-consistency slice now closed:
  - `src/backtest_artifact_import/export_dir_bridge.py` now rejects semantically contradictory exports even when the sidecars remain JSON-valid
  - `review_export.md` provenance must stay aligned with manifest / metrics / parity sidecars
  - `feature_bridge.dataset_id` must match `replay_run_manifest.dataset_manifest_id`
  - `feature_bridge.feature_set_version` must match `replay_run_manifest.feature_set_version`
  - `feature_bridge.transform_set_version` must match `replay_run_manifest.transform_set_version`
  - `feature_bridge.pairs` / `feature_bridge.engines` must match manifest `tested_pairs` / `engine_scope`
  - `parity_diagnostics.dataset_id` must match `replay_run_manifest.dataset_manifest_id`
  - `replay_metrics.total_records` must match the real DTR count
  - `pair_aggregates` / `engine_aggregates` must sum to `total_records`
  - `replay_metrics` and `replay_dtr` must stay inside manifest `tested_pairs` / `engine_scope`
  - `replay_dtr.runtime_mode` must stay `local_replay`
  - `replay_dtr` timestamps must stay within the manifest clock range
  - `replay_metrics` must remain exactly recomputable from the exported DTR set
  - proof: `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_artifact_exporter.py -q` -> `92 passed`
- latest proof after `feature_bridge` + `review_export` alignment: the same command now returns `98 passed`
- the same governed export-dir path now also rejects sidecar refs that resolve outside the export directory itself
- the same governed export-dir path now also rejects multiple candidate files for the same governed sidecar label

Next after that:
- inspect the remaining open `shadow/protocols` backlog if the next IA Lab-bound slice lands back on that rail
- no further `BS-49` cleanup is required unless a new regression reintroduces `LIGHT` as the active governed rail
- no further artifact-plumbing micro-slice is required unless the IA Lab entry rail regresses
- top-level canon, lower-level Build-11/12/13/14 phase specs, detailed Build-10 docs, manifest-registry descriptions, and active public runtime names are now aligned with the governed rail
- if the next perimeter is `engine_c / engine_d`, treat it as a bounded factorization/auditability slice only
  - current code truth: C/D are already valid canonical runtimes
  - current package truth: they are more monolithic than A/B and should not be described as empty or non-canonical
- the first bounded readability slices on that perimeter are now closed on both `engine_c` and `engine_d`
  - `engine_c` now extracts structure resolution and signal-math calculations into helper modules
  - `engine_d` now extracts context resolution and signal-math calculations into helper modules
- the second bounded readability slices are now also closed on both `engine_c` and `engine_d`
  - `engine_c` now also extracts cost-feasibility, conviction, and invalidation calculations into helper modules
  - `engine_d` now also extracts cost-feasibility, conviction, and invalidation calculations into helper modules
- the third bounded readability slices are now also closed on both `engine_c` and `engine_d`
  - `engine_c` now also extracts final `EngineCOutput` payload assembly into `output_payload_builder_c.py`
  - `engine_d` now also extracts final `EngineDOutput` payload assembly into `output_payload_builder_d.py`
- this parity/readability track is now in a good stopping state; do not reopen it without a broader refactor goal

Open governance / safety backlog still relevant:
- remaining unverified `BS-*` items from the master tracker
- continued proof discipline for every closure
- keep watch on previously closed items that can regress after nearby edits
- deliberate readability backlog still relevant:
  - possible further Engine C extractions after the already-landed second slice: signal reporter / final output assembly only if more parity value is still justified
  - possible further Engine D extractions after the already-landed second slice: signal reporter / final output assembly only if more parity value is still justified

Audit-remapped ids recovered from the Sonnet audit docx:
- `BS-43`
  - maps to `src/interface_contracts/atomic_io.py`
  - the audited `default=str` path is no longer present
  - treat as already corrected in current code
- `BS-46`
  - maps to `src/smoke_bootstrap_recovery/state_sanity_checker.py`
  - current smoke path now enforces both the local delta tolerance and a suite-level absolute FD ceiling
  - treat as closed in current code
- `BS-63`
  - maps to `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - the audited full re-serialization path is no longer present
  - treat as effectively closed by the `BS-62` fix set
- `BS-67`
  - maps to `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - current lookup helpers now read append-only secondary indexes maintained at persist time
  - treat as closed in current code

Current rule:
- do not call these ids `unmapped` anymore
- do not reopen `BS-43`, `BS-46`, `BS-63`, or `BS-67` unless code regresses

## Multi-Session Rules

To avoid hallucination across sessions:

1. Read this file first.
2. Read `2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`.
3. Do not trust memory-only claims.
4. Do not mark an item closed without proof.
5. Keep slices bounded to one module or one naturally coupled rail.
6. Update both files after each real closure.
7. If documentation is corrupted, rebuild docs from verified code/tests before continuing runtime edits.

## Forbidden Assumptions

Do not assume:
- that a BS item is closed because it was discussed
- that a hook is runtime-open because its module exists
- that a trust-store is real because a policy object exists
- that `LIGHT` is the active rollout rail
- that a broader canon patch exists unless it is explicitly present on disk

## Verification Habit

For each slice:
- run targeted tests for the touched rail
- run broader cross-check tests when the rail is safety-critical
- record the exact result in the final session summary
- then update tracker and working memory

## Latest Cross-Check Proof

Latest verified cross-check on the bounded `backtest_artifact_import` handshake slice:

- `rtk pytest tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py -q`
- `48 passed`

Latest verified cross-check on the bounded export-dir bridge slice:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `24 passed`

Latest verified cross-check on the bounded export-dir + upload-contract semantic-consistency slice:

- `src/backtest_artifact_import/export_dir_bridge.py` now rejects contradictory provenance, refs outside `export_dir`, and multiple candidate files for the same governed sidecar label
- `src/backtest_artifact_import/contracts.py` now rejects governed `ArtifactUploadRequest` objects whose manifest payload refs diverge from the typed `payload_bundle`
- typed `ArtifactPayloadRefBundle` instances now also reject duplicate refs instead of silently normalizing them away
- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_artifact_exporter.py -q`
- `104 passed`

Latest verified cross-check on the bounded shared replay-plan import-builder slice:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `23 passed`

Latest verified broader cross-check on the replay/import/signature/onboarding rail:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `83 passed`

Latest verified bounded `BS-92` closure proof:

- `rtk pytest tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_pair_health_scorer.py -q`
- `31 passed`

Latest verified bounded `BS-89` closure proof:

- `rtk pytest tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py -q`
- `8 passed`

Latest verified bounded `BS-88` closure proof:

- `rtk pytest tests/test_scoring_backbone/test_bs88_phantom_detection_expected_cost_regression.py -q`
- `8 passed`

Latest verified bounded `BS-86` closure proof:

- `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_bs86_timestamp_ms_unit_constraint_regression.py -q --basetemp=build/pytest-bs86`
- `12 passed`

Latest verified bounded `BS-90` closure proof:

- `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py -q`
- `40 passed`

Latest verified bounded `BS-93` closure proof:

- `rtk pytest tests/test_data_backbone/test_pair_health_scorer.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
- `35 passed`

Latest verified bounded `BS-91` closure proof:

- `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
- `45 passed`

Latest verified bounded `BS-81` closure proof:

- `rtk pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py tests/test_risk_backbone/test_loss_budgeter.py -q`
- `54 passed`

Latest verified bounded `BS-83` closure proof:

- `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
- `41 passed`

Latest verified bounded `BS-82` closure proof:

- `rtk pytest tests/test_portfolio_minimal/test_portfolio_minimal.py tests/test_portfolio/test_canonical_portfolio.py -q`
- `89 passed`
- `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py -q`
- `37 passed`

Latest verified bounded `BS-80` closure proof:

- `rtk pytest tests/test_risk_backbone/test_btc_factor_guard.py tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py -q`
- `49 passed`
- `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_scoring_backbone/test_ranking_router.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q`
- `72 passed`

Latest verified bounded `BS-35` closure proof:

- `rtk pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_b_sweep_hook.py tests/test_protocols/test_engine_b_sweep_validation_bridge.py -q`
- `17 passed`

Latest verified bounded second real hook/runtime opening proof:

- `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q`
- `21 passed`
- `rtk pytest tests/test_protocols/test_artifact_action_composer.py tests/test_protocols/test_compiled_hook_plan_loader.py tests/test_protocols/test_compiled_artifact_registry_store.py -q`
- `14 passed`
- `rtk pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q`
- `83 passed`

Latest verified bounded `BS-78` closure proof:

- `rtk pytest tests/test_data_backbone/test_market_physics_math.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_b/test_engine_b.py -q`
- `164 passed`
- `rtk pytest tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
- `23 passed`

Latest verified bounded `BS-77` closure proof:

- `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q --basetemp=build/pytest-engine-b-bs77`
- `80 passed`

Latest verified bounded `BS-84` closure proof:

- `rtk pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
- `11 passed`

Latest verified cross-check on the bounded shared replay-plan upload-builder slice:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `14 passed`

Latest verified broader cross-check on the upload/import/signature/onboarding rail:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `84 passed`

Latest verified bounded replay/evidence -> upload -> import -> shadow/ui proof:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `26 passed`

Latest verified stable end-to-end IA Lab entry-rail proof:

- `rtk pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `36 passed`

Latest verified broader cross-check on the upload/import/signature/onboarding/shadow rail:

- `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `86 passed`

Earlier verified bounded `BS-49` doctrine-convergence proof:

- `rtk pytest tests/test_meta_learning/test_contracts.py tests/test_meta_learning/test_governance_edge_cases.py tests/test_ui/test_operator_actions.py tests/test_ui/test_light_ui_runtime.py -q`
- `59 passed`

Latest verified broader Build-10 cross-check after the bounded `BS-49` slice:

- `rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py -q`
- `55 passed`

Latest verified locked-view proof after the bounded `BS-49` projection slice:

- `rtk pytest tests/test_ui/test_light_dashboard.py tests/test_ui/test_light_ui_runtime.py tests/test_ui/test_ui_contracts.py -q`
- `50 passed`

Latest verified broader Build-10 runtime cross-check after the locked-view slice:

- `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py -q`
- `62 passed`

Latest verified import/parsing sanity after the Build-10 wording cleanup:

- `rtk pytest tests/test_ui/test_light_dashboard.py tests/test_monitoring/test_monitoring_runtime.py -q`
- `13 passed`

Latest verified Build-10 dashboard rendering proof:

- `rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py -q`
- `33 passed`

Latest verified broader Build-10 dashboard/runtime cross-check:

- `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_light_dashboard.py tests/test_ui/test_light_ui_runtime.py -q`
- `50 passed`

Latest verified non-runtime proof after the top-level BS-49 doc slice:

- `rtk grep -n "surface locale de compatibilité|Build-11 actif|labels historiques|profil gouverné courant|Light Shadow|Live-Light" docs/specs/V5_3_MASTER_FINAL_UNIQUE.md docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md docs/specs/V5_3_MASTER_FINAL_CANONICAL.md`
- confirms the master matrices now read the governed rollout rail consistently with current code

Latest verified non-runtime proof after the lower-level BS-49 phase-spec slice:

- `rtk grep -n "profil=COMPLETE|runtime_mode=SHADOW|runtime_mode=MICRO_LIVE|runtime_mode=LIVE|rail gouverné courant|extension COMPLETE" docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
- confirms the lower-level Build-11 / Build-12 / Build-13 / Build-14 phase specs now read the governed runtime rail consistently with current code

Latest verified manifest/master rollup proof after the bounded BS-49 convergence slice:

- `rtk grep -n 'profil=LIGHT' docs/specs/V5_3_MASTER_FINAL_UNIQUE.md docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md docs/specs/V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md src/manifest_registry/build_order_registry.py src/manifest_registry/module_inventory.py src/manifest_registry/version_registry.py`
- only the deliberate `LOCAL_REPLAY` compatibility lines remain in the touched master docs
- `rtk grep -n 'UI Light verrouillée' docs/specs/V5_3_MASTER_FINAL_UNIQUE.md docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md docs/specs/V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md src/manifest_registry/module_inventory.py src/manifest_registry/version_registry.py`
- `0 matches`
- `rtk pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_version_registry.py -q`
- `84 passed`

Latest verified monitoring/dashboard COMPLETE coverage proof:

- `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_technical_dashboard.py -q`
- `65 passed`

Latest verified bounded `BS-49` final-closure proof:

- `rtk pytest tests/test_ui/test_light_ui_runtime.py tests/test_ui/test_operator_actions.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py tests/test_integration_alignment.py -q`
- `177 passed`
- `rtk grep -n "LockedOperatorUiRuntime|LockedOperatorDashboardView|LiveInput = LiveLightInput|LiveRunState = LiveLightRunState|LiveProjection = LiveLightProjection|build_live_input_from_micro_live = build_live_light_input_from_micro_live|build_live_projection = build_live_light_projection" src/ui src/monitoring src/protocols`
- confirms canonical public names now lead while legacy names remain explicit compatibility aliases

Latest verified bounded `BS-38` semantic-recovery proof:

- `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py -q`
- `53 passed`

Latest verified cross-check on the bounded `local_replay_runtime` IA Lab entry rail:

- `rtk pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `26 passed`

Latest verified cross-check on the bounded `smoke_bootstrap_recovery` slice:

- `rtk pytest tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py -k "fd_leak or resource_release_checker" -q`
- `5 passed`

Latest verified cross-check on the bounded `meta_minimal/dtr_core` slice:

- `rtk pytest tests/test_meta_minimal/test_meta_minimal.py tests/test_meta_minimal/test_bs62_dtr_crash_protection_regression.py tests/test_meta_minimal/test_bs67_dtr_store_index_regression.py tests/test_regression_alignment.py -k "TestTracePersistenceLayer or TestDTRFlushToDisk or bs62 or bs67" -q`
- `21 passed`

Latest verified cross-check on the active `shadow/protocols` rail:

- `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
- `21 passed`
- `rtk pytest tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py tests/test_protocols/test_bs68_session_registry_rollback_regression.py -q`
- `27 passed`
- `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py tests/test_protocols/test_bs68_session_registry_rollback_regression.py -q`
- `40 passed`

Latest verified cross-check on the bounded active engine-runtime safety rail:

- `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src pytest tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-runtime`
- `47 passed`

## Reconstruction Note

On 2026-04-07 this file was found corrupted and physically filled with `0x00`.
It has been reconstructed from verified repo state and recent session proofs.
Treat it as the current operational baseline from this point forward.

Latest verified cross-check on `T1 / P0-1.A`:

- `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_execution_backbone/test_venue_constraints_provider.py -q`
- `15 passed`

Current meaning:
- `src/venue_adapters/binance_spot/` now exists on the real repo
- `THR-X01` is no longer a pure future target; it is consumed by `time_sync.py`
- `T1` is closed on code + local tests
- manual Binance Testnet validation remains pending human execution
- next core tranche is `T2` or `T3`, not more UI work

Latest verified cross-check on `T2 / P0-4`:

- `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
- `12 passed`

Current meaning:
- `src/secrets_manager/` now exists on the real repo
- current backend is a bounded Windows DPAPI implementation using external `master.key` entropy
- `credential_loader.py` now accepts sealed credential files
- Linux/VPS secret portability remains open; do not oversell this slice as final production crypto
- next core tranche is `T3`, not UI

Latest bounded `T6 / P0-3` memory:

- Local IA Lab producer side is real:
  - `THR-E01` / `THR-E02` calibration from replay `DTRRecord`
  - signed `edge_gate.yml`
  - optional emission from `run_local_replay_export.py`
- first runtime consumer is now real too:
  - `src/execution_backbone/execution_runtime.py` can enforce the fee-aware gate when a `FeeAwareEdgeGateConfig` is injected
- bootstrap pass-through is now real too:
  - `src/protocols/execution_runtime_bootstrap.py` can pass the same config into both direct and Binance execution runtime builders
- explicit bounded runtime enablement is now real too:
  - `BinanceAdapterConfig.fee_aware_edge_gate_enabled` can activate the same EDGE gate on the real Binance runtime rail using `calibration_root/calibration_version`
- future dashboard-facing output is now real too:
  - `src/execution_backbone/order_decider/intent_builder.py` adds `NoTradeDecision.context`
  - `src/execution_backbone/order_decider/decision_reporter.py` adds `DecisionEvent.no_trade_reason` and `DecisionEvent.context`
  - fee-aware gate blocks are no longer only string details
- honest residual:
  - no ubiquitous bootstrap wiring yet
  - no higher-level scoring/engine wiring yet
- latest proofs:
  - `rtk pytest tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py tests/test_execution_backbone/test_order_decider.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
  - `58 passed`
  - `rtk pytest tests/test_execution_backbone tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py -q`
  - `163 passed`

Latest planning anchor:

- `docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md`
  - Local IA Lab already ingests historical snapshots, governed replay sidecars, post-trade DTR evidence, and strategy/review bundles
  - there is still no raw live bidirectional VPS -> Lab snapshot stream

Latest bounded Local IA Lab post-trade review memory:

- `src/meta_minimal/meta_runtime.py` now exposes `build_meta_runtime_result_from_records(...)`
- `scripts/run_local_lab_post_trade_review.py` now provides a governed Local IA Lab entrypoint from exported `replay_dtr.json/.jsonl`
- the same launcher now also accepts a governed `--export-dir` and recovers manifest/payload provenance through `discover_local_replay_export(...)`
- the new slice emits future-facing non-UI outputs by default:
  - `meta_runtime_result.json`
  - `meta_learning_review.bundle.json`
  - `meta_learning_review.md`
  - `meta_learning_projection.json`
  - `trade_loss_attribution.json`
  - `governed_input_summary.json`
- `scripts/run_local_lab_analysis_bundle.py` now chains one governed `export_dir` into:
  - post-trade review
  - EDGE calibration
  - a single non-UI summary `local_lab_analysis_summary.json`
- `trade_loss_attribution.json` is now the bounded per-trade explanation/suggestion surface:
  - why the trade lost
  - what should prevent the next loss
  - with typed failure modes (`cost_drift / sterilization / edge_degraded / trace_coverage / unclassified_loss`)
  - and future-facing recommendation fields (`preventive_action / confidence / recommended_threshold_ids`)
- `walk_forward_review.template.json` and `walk_forward_review.summary.json` now exist on the same Local IA Lab chain
  - the template is emitted automatically
  - the approval remains human
  - without approved human review, `walk_forward_pass` remains false by construction
- `artifact_proof_summary.json` and `artifact_proof_assessment.json` now also exist on the same Local IA Lab chain
  - the proof summary is canonical `ArtifactProofSummary`
  - the assessment makes the fail-close state explicit when ablation or causal proof dimensions are still missing
  - `artifact_proof_ready` is now a typed bundle outcome rather than an implicit absence
- `local_lab_scope_matrix.json` now also exists on the same Local IA Lab chain when `--all-scopes` is requested
  - `src/local_replay_runtime/local_lab_scope_matrix.py` now provides the typed `pair x engine` matrix surface
  - a single governed export can now be expanded into per-scope reviews under `output-root/scopes/<pair>__<engine>/`
  - each scope now carries:
    - `post_trade_review/`
    - `artifact_ablation_study.json`
    - `artifact_proof_summary.json`
    - `artifact_proof_assessment.json`
  - the matrix exposes future-dashboard-ready fields per scope:
    - `artifact_ablation_ready`
    - `artifact_proof_ready`
    - `artifact_proof_validation_reasons`
  - the multi-scope path stays fail-close:
    - scope coverage now uses scope-level `total_opportunities`
    - walk-forward approval stays human-gated
    - aligned baseline evidence remains mandatory for `ready`
- `artifact_release_candidate.json` now also exists on the same Local IA Lab chain
  - `src/local_replay_runtime/artifact_release_candidate.py` now provides the packaging-side verdict before any VPS import request is built
  - it exposes:
    - `release_status`
    - `ready_for_shadow_import`
    - `blocking_reasons`
    - `release_scopes` when a multi-scope matrix exists
  - this is still a Local Lab sidecar, not yet the governed VPS import payload itself
- `artifact_import_dry_run_bridge.json` now also exists on the same Local IA Lab chain
  - `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now provides the bounded dry-run bridge from `artifact_release_candidate.json` to the existing governed import rail
  - the same chain can now also emit:
    - `artifact_upload_request.dry_run.json`
    - `artifact_import_request.dry_run.json`
    - `artifact_import_decision.dry_run.json`
    - `artifact_upload_decision.dry_run.json`
  - the bridge remains fail-close:
    - release candidate must already be ready
    - governance metadata must be explicit
    - no hidden defaults for governance date, training end, artifact class/scope, lifecycle, or drift threshold
  - the bridge now also exposes the current semantic split explicitly:
    - source artifact id/kind belongs to the Local IA Lab calibration artifact
    - transport artifact id/kind belongs to the current replay-derived governed `review_packet`
  - honest residual:
    - this is still a dry-run/proof-packet bridge over the current replay/import rail
    - final live packaging semantics remain a later slice
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py tests/test_meta_minimal/test_meta_runtime.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
  - `32 passed`
  - `python -m pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `282 passed`
  - `python -m pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `87 passed`
- honest residual:
  - still no live VPS -> Lab streaming loop
  - still no automatic recalibration/promotion loop
  - next core Local IA Lab step: refine the new dry-run bridge toward the final live packaging semantics, especially around final `artifact_id / artifact_kind`
  - next calibration slice after that: consume `trade_loss_attribution.json` plus scope verdicts in the local recalibration loop instead of keeping them only as review sidecars

New standing implementation rule:

- for each new code brick, explicitly check whether it needs a future dashboard-facing output
- acceptable outputs include:
  - typed projection model
  - structured monitoring summary
  - artifact sidecar
  - structured logs
  - metrics payload
- do not force immediate UI wiring
- do not leave important new logic without an audit/monitoring surface if that surface will be needed later

Latest verified cross-check on the bounded `T3 / P0-1.B` core:

- `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_shadow_live_websocket.py -q`
- `19 passed`

Current meaning:
- `THR-X02` is no longer a pure future target
- the websocket/orderbook core exists with explicit stale/resync semantics
- the explicit REST depth snapshot provider now also exists
- this is not yet the full live/testnet closure of `T3`
- next bounded addition on this rail is live/testnet validation and soak proof, or we can switch to `T4`

Latest Local IA Lab recalibration reminder:

- `trade_loss_attribution.json` should no longer be treated as a dead-end report
- the current bounded continuation is `local_lab_recalibration_plan.json`
- preserve this split:
  - post-trade explanation
  - local recalibration planning
  - replay/backtest proof
  - only then governed artifact export toward the VPS rail

Latest EDGE producer reminder:

- if a future slice touches `edge_gate.input_summary.json`, preserve the provenance link back to `local_lab_recalibration_plan.json`
- this link is now part of the Local IA Lab audit story and future dashboard story

Latest packaging reminder:

- do not let `artifact_release_candidate.py` drift back to a proof-only gate
- current truth:
  - a release candidate needs a Local IA Lab recalibration plan path
  - only `NO_LOSING_TRADES_TO_RECALIBRATE` is currently treated as benign
  - other recalibration blockers must keep the candidate local-only

Latest Local IA Lab -> VPS dry-run semantics reminder:

- keep the existing governed import rail
- do not invent a new artifact kind for this slice
- current truthful model:
  - source artifact = Local IA Lab calibration artifact `edge_gate.yml`
  - transport artifact = replay-derived governed `review_packet`
- the bridge now makes this explicit with:
  - `artifact_source_summary.json`
  - `semantic_status = transport_packet_with_source_artifact_refs`
  - `ArtifactPayloadRefBundle.supplementary_refs` carrying both source refs
- preserve fail-close behavior if a future slice touches this perimeter

Latest release-gate projection reminder:

- the dry-run bridge now also mirrors the packaging verdict explicitly
- preserve these fields if a future slice touches the handoff:
  - `release_ready_for_shadow`
  - `release_artifact_proof_ready`
  - `release_artifact_proof_validation_reasons`
  - `release_recalibration_candidate_ready`
  - `release_recalibration_blocking_reasons`
  - `release_gate_status`
  - `release_gate_reasons`
- current doctrine:
  - future tooling should read the explicit release-gate projection
  - it should not re-derive or truncate proof blockers from separate sidecars

Latest release-gate sidecar reminder:

- `artifact_release_gate_summary.json` now exists and is part of the Local IA Lab handoff perimeter
- preserve this dry-run packet shape:
  - `edge_gate.yml`
  - `artifact_source_summary.json`
  - `artifact_release_gate_summary.json`
  - all carried through `supplementary_refs`
- the ready dry-run path now exposes `bridge_transport_payload_ref_count = 8`
- preserve fail-close behavior if `release_gate_summary_ref` is missing

Latest multi-scope packaging reminder:

- `artifact_release_candidate.json` is now the first per-scope packaging drill-down surface, not just a top-level boolean verdict
- preserve these per-scope fields:
  - `review_bundle_path`
  - `trade_loss_attribution_path`
  - `artifact_proof_summary_path`
  - `artifact_proof_assessment_path`
  - `executed_records`
  - `losing_trade_count`
- the top-level bundle summary now also exposes `release_ready_scope_slugs` and `release_blocked_scope_slugs`
- this remains descriptive packaging truth, not a new per-scope VPS import protocol

Latest per-scope release-sidecar reminder:

- multi-scope runs now also emit `artifact_release_scope_summary.json` for each scope
- preserve the linkage from each scope summary to:
  - shared artifact path
  - shared release-gate summary
  - shared dry-run bridge
  - scope-local proof/review refs
- keep this as a drill-down surface for future dashboards, not as a separate transport rail

Latest scope-matrix packaging reminder:

- `local_lab_scope_matrix.json` is no longer proof-only
- preserve its packaging-side additions:
  - `release_ready_scope_count`
  - `release_blocked_scope_count`
  - per-scope `release_ready`
  - per-scope `release_blocking_reasons`
  - per-scope `release_scope_summary_path`
- the matrix should remain aligned with `artifact_release_candidate.json`, not drift into a separate packaging truth

Latest promotion-readiness reminder:

- `artifact_promotion_readiness_summary.json` now exists as the top-level future-dashboard/operator summary
- preserve its canonical shared-core vocabulary:
  - `activation_stage`
  - `normalized_promotion_state`
  - `review_state`
- preserve its bounded local labels:
  - `local_only`
  - `shadow_candidate_pending_dry_run`
  - `shadow_candidate_dry_run_ready`
- this summary must remain descriptive only, never a source of automatic promotion behavior

Latest Local IA Lab monitoring reminder:

- `local_lab_monitoring_projection.json` now exists as the compact future-monitoring sidecar over the same Local IA Lab bundle
- preserve its role:
  - summarize core readiness
  - summarize packaging / dry-run bridge truth
  - summarize scope/release counts
  - point downstream tooling to the detailed sidecars
- preserve its bounded status mapping:
  - `healthy` only when dry-run handoff is ready
  - `critical` only when core Local IA Lab outputs are incomplete
  - otherwise `warning/info`
- keep it descriptive only
  - no UI coupling requirement
  - no promotion semantics
  - no second source of truth separate from release candidate / dry-run bridge / promotion-readiness sidecars

Latest Local IA Lab observability reminder:

- `local_lab_observability_export.json` now exists on the same bundle
- preserve its role:
  - standard metrics/text export over the Local IA Lab packaging truth
  - downstream-friendly for future monitoring ingestion
  - not a replacement for the detailed sidecars
- keep it descriptive only:
  - no UI behavior
  - no VPS mutation
  - no promotion semantics

Latest Local IA Lab backend payload reminder:

- `local_lab_monitoring_backend_payload.json` now exists on the same bundle
- preserve its role:
  - typed backend-facing future-dashboard payload
  - built from `local_lab_monitoring_projection.json` plus `local_lab_observability_export.json`
  - summarize status/counts/refs without replacing the detailed sidecars
- keep it descriptive only:
  - no UI behavior
  - no new runtime rail
  - no VPS mutation
  - no promotion semantics

Latest Local IA Lab ingestion summary reminder:

- `local_lab_monitoring_ingestion_summary.json` now exists on the same bundle
- preserve its role:
  - first monitoring-side ingestion verdict over the Local IA Lab backend payload plus observability export
  - verify alignment and non-empty export surfaces before future backend ingestion
  - not replace the detailed sidecars or the backend payload
- keep it descriptive only:
  - no UI behavior
  - no Build-10 runtime coupling
  - no VPS mutation
  - no promotion semantics

Latest Local IA Lab bundle loader reminder:

- `monitoring.local_lab_bundle_loader.load_local_lab_monitoring_bundle(...)` now exists
- preserve its role:
  - reload the Local IA Lab monitoring trio from one output directory
  - validate typed JSON plus alignment of `correlation_id/profile/runtime_mode/timestamp_ms`
  - support future backend ingestion without coupling to the launcher process
- keep it descriptive only:
  - no UI behavior
  - no Build-10 runtime coupling
  - no VPS mutation
  - no promotion semantics

Latest Local IA Lab observability text export reminder:

- `local_lab_observability.prom` now exists alongside the JSON observability export
- preserve its role:
  - exact text export of the standard `ObservabilityExport`
  - scrape-friendly future backend artifact
  - not a replacement for the JSON sidecars
- keep it descriptive only:
  - no UI behavior
  - no runtime semantics
  - no VPS mutation
  - no promotion semantics

Latest Local IA Lab research-priority reminder:

- `local_lab_research_priority.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - transparent weighted ranking of which `pair x engine` scope should get the next bounded research cycle
  - driven by governed loss attribution plus scope/proof/release truth
  - future-monitoring-ready, but not a runtime controller
- preserve its limits:
  - not a trained production model
  - not a promotion authority
  - not a VPS mutation surface
  - not a substitute for the detailed sidecars

Latest Local IA Lab loss-surrogate reminder:

- `local_lab_loss_surrogate_report.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - first truly trained but still transparent Local IA Lab model
  - use decision-time / no-lookahead features only
  - estimate modeled loss pressure by scope without replacing detailed attribution
  - future-monitoring-ready, but not a runtime controller
- preserve its limits:
  - not a VPS/runtime model
  - not a promotion authority
  - not a substitute for proof/recalibration/release gates
  - not a replacement for `trade_loss_attribution.json`

Latest Local IA Lab surrogate-guided planning reminder:

- the trained loss surrogate now also feeds:
  - `local_lab_research_priority`
  - `local_lab_recalibration_plan`
- preserve its role:
  - advisory signal for which scope deserves the next bounded replay/research cycle
  - possible trigger for `replay_surrogate_high_risk_scope`
  - never sufficient by itself for publication/promotion/import
- preserve its limits:
  - no VPS/runtime mutation
  - no promotion authority
  - no bypass of proof/release gates

Latest Local IA Lab replay candidate queue reminder:

- `local_lab_replay_candidate_queue.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - bounded queue of the next local replay/research scopes
  - derived from `research_priority + recalibration_plan + surrogate-guided truth`
  - expose ready vs blocked local work for future monitoring
- preserve its limits:
  - not a runtime scheduler
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab replay ticket index reminder:

- `local_lab_replay_ticket_index.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - governed ticket index built from the replay candidate queue
  - reuse the canonical `LocalReplayRequest` contract for future automation
  - keep blocked tickets explicit instead of silently inventing runnable work
- preserve its limits:
  - not an execution surface
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab replay dispatch plan reminder:

- `local_lab_replay_dispatch_plan.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - local-only dispatch truth over governed replay tickets
  - separate ready local work from blocked local work
  - prepare future automation without executing anything
- preserve its limits:
  - not an execution surface
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab workflow/monitoring manifest reminder:

- `local_lab_replay_workflow_manifest.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - bind together replay candidate queue + replay ticket index + replay dispatch plan
  - give future automation/monitoring one discovery file instead of hardcoded workflow filenames
  - stay audit-ready and local-only
- preserve its limits:
  - not an execution surface
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab monitoring bundle manifest reminder:

- `local_lab_monitoring_bundle_manifest.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - bind together backend payload + observability export + ingestion summary
  - optionally point to the replay workflow manifest
  - let future backend/Prometheus/dashboard ingestion discover monitoring sidecars through one manifest
- preserve its limits:
  - not UI by itself
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab monitoring bundle discovery reminder:

- `src/monitoring/local_lab_bundle_discovery.py` now exists over the same monitoring bundle manifests
- preserve its role:
  - scan a root for Local IA Lab monitoring bundle manifests
  - sort bundles by latest governed timestamp
  - load the newest valid monitoring bundle through the manifest-first loader
- preserve its limits:
  - backend/discovery only
  - not UI by itself
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab monitoring feed reminder:

- `src/monitoring/local_lab_monitoring_feed.py` now exists over discovered monitoring bundles
- preserve its role:
  - summarize latest bundle truth plus compact counts by backend status/ingestion readiness
  - prepare a small multi-bundle backend surface before any dashboard work
- preserve its limits:
  - backend/summary only
  - not UI by itself
  - not a VPS mutation surface
  - not a promotion authority

Latest Local IA Lab calibration-methods core reminder:

- `src/calibration_methods/` now exists with:
  - `bootstrap.py`
  - `walkforward.py`
  - `dsr.py`
- preserve its role:
  - first shared Local IA Lab math-core helpers for stationary bootstrap, purged walk-forward, and DSR
  - keep these helpers local-only and audit-ready
  - let later Lab slices consume them explicitly instead of cloning math ad hoc
- preserve its current truth:
  - `edge_gate_calibration.py` already consumes the shared stationary bootstrap helper
  - walk-forward human approval remains a separate hard gate
  - DSR is available locally but not yet wired into promotion/release logic

Latest Local IA Lab calibration-methods review reminder:

- `local_lab_calibration_methods_review.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - consume shared walk-forward geometry and DSR helpers over governed `DTRRecord` history
  - make calibration-method evidence explicit on the Local IA Lab proof rail
  - propagate compact future-dashboard/backend truth without touching UI
- preserve its current truth:
  - DSR below floor now blocks Local IA Lab proof locally
  - insufficient history remains explicit as `partial`, never silent
  - human walk-forward approval still remains a separate hard gate
- preserve its limits:
  - not a VPS/runtime gate by itself
  - not a promotion authority by itself
  - not a substitute for `walk_forward_review.summary.json`

Latest Local IA Lab release/dry-run calibration-methods reminder:

- the release candidate and dry-run bridge now also carry explicit calibration-methods state
- preserve its role:
  - make the handoff say whether it is calibration-methods-backed
  - keep proof-backed vs calibration-backed truth readable in sidecars
- preserve its limits:
  - not a new promotion authority
  - not a VPS/runtime mutation surface
  - not a substitute for the proof gate itself

Latest Local IA Lab monitoring feed calibration-methods reminder:

- the monitoring bundle manifest, discovery layer, and compact feed now also carry calibration-methods readiness
- preserve its role:
  - let future backend/Prometheus/dashboard ingestion see calibration-ready vs partial vs blocked bundles cheaply
  - keep multi-bundle discovery manifest-first instead of opening every sidecar eagerly
- preserve its limits:
  - backend/discovery only
  - not UI by itself
  - not a VPS mutation surface

Latest Local IA Lab tail-risk review reminder:

- `local_lab_tail_risk_review.json` now exists on the same Local IA Lab bundle
- preserve its role:
  - consume governed `DTRRecord` history into bounded strategy-level tail-risk evidence
  - review `THR-R01` daily, `THR-R02` weekly, and `THR-R03` monthly breaker candidates locally
  - expose compact future-dashboard/backend truth without touching UI
- preserve its current truth:
  - powered by `src/calibration_methods/pot_gpd.py`
  - method stays explicit as bounded `pot_gpd_mom_bootstrap_v1`
  - partial on no positive-loss periods or insufficient exceedances
  - blocked on invalid fit or excessive bootstrap dispersion
- preserve its limits:
  - not a VPS/runtime gate by itself
  - not release semantics by itself
  - not a promotion authority

Latest Local IA Lab stationarity gate reminder:

- `src/calibration_methods/stationarity.py` now exists as the bounded MI-9 helper
- preserve its role:
  - run dual ADF + KPSS checks over local replay-return history
  - make stationarity explicit on the Local IA Lab proof rail before any future artifact handoff
  - propagate compact future-dashboard/backend truth without touching UI
- preserve its current truth:
  - insufficient history remains explicit as `partial`
  - stationarity failure now blocks the local calibration-methods review
  - proof-side validation can now emit `LOCAL_LAB_STATIONARITY_REQUIRED` / `LOCAL_LAB_STATIONARITY_INVALID`
- preserve its limits:
  - Local IA Lab only
  - not a VPS/runtime mutation surface
  - not a new promotion authority by itself

Latest shared human hard-cap helper reminder:

- `src/calibration_methods/hard_cap_floor.py` now exists
- preserve its role:
  - centralize conservative publication against human floors/caps
  - stop duplicating ad hoc `max/min` semantics across Local IA Lab calibration slices
  - expose both `hard_cap_satisfied` and `hard_cap_binding` in sidecars
- preserve its current consumers:
  - `edge_gate_calibration`
  - `local_lab_tail_risk_review`
  - `local_lab_calibration_normalized_report`
- preserve its limits:
  - Local IA Lab only
  - not a UI surface by itself
  - not a VPS/runtime mutation surface

Latest Local IA Lab multiple-testing review reminder:

- `src/calibration_methods/multiple_testing.py` now exists as the bounded MI-12 helper
- `src/local_replay_runtime/local_lab_multiple_testing_review.py` now exists as the Local IA Lab MI-12 sidecar
- current truth:
  - current calibration publications remain interval-publication artifacts
  - MI-12 is therefore explicit `not_required_interval_publication`, not `not_evaluated`
- the same truth now propagates into proof/summary/monitoring sidecars
- preserve its limits:
  - Local IA Lab only
  - not a UI surface by itself
  - not a VPS/runtime mutation surface

Latest Local IA Lab execution review reminder:

- `src/calibration_methods/execution.py` now exists as the bounded EXECUTION helper rail
- `src/local_replay_runtime/local_lab_execution_review.py` now exists as the Local IA Lab EXECUTION sidecar
- preserve its role:
  - review `THR-X01` and `THR-X02` locally when real execution telemetry is available
  - expose compact future-dashboard/backend truth without touching UI
  - keep `13-C EXECUTION` started on the Lab side before any runtime mutation
- preserve its current truth:
  - missing execution telemetry remains explicit `partial`
  - no replay export sidecar is silently reused as venue telemetry
  - no proof/release gating change yet
- preserve its limits:
  - Local IA Lab only
  - not a UI surface by itself
  - not a VPS/runtime mutation surface

Latest VPS -> local observability architecture reminder:

- planning anchor:
  - `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md`
- preserve the split:
  - VPS collects and exports lightweight summaries
  - local PC hosts Prometheus/Grafana and detailed drill-down
- preserve the transport doctrine:
  - continuous = compact typed metrics / summaries
  - on-demand = detailed logs / incident bundles / deep traces
  - do not create a heavy always-on raw-stream VPS -> local bus
- preserve the implementation order:
  - real VPS process metrics first
  - real VPS `.prom` export second
  - local Prometheus/Grafana hookup third
  - richer UI only later
- current explicit missing VPS code still open:
  - `src/regime_classifier/`
  - `src/alerting/telegram_alerter.py`
  - `src/execution_backbone/gatekeeper/gatekeeper.py`
  - `src/risk_backbone/info_stress_monitor.py`
  - `src/execution_backbone/spread_guard.py`
  - `src/execution_backbone/slippage_model.py`
- keep the current total progress estimate in mind:
  - `~62%` overall
  - use it as planning orientation only, not as a hard KPI

Latest VPS Shadow service observability slice:

- current code truth:
  - `scripts/run_shadow_vps_service.py` now writes a typed backend payload and a real `.prom` file
  - `src/monitoring/disk_monitor.py` now provides bounded disk usage sampling for the service volume
  - `src/monitoring/process_metrics.py` samples bounded real process metrics without forcing a new dependency install
  - `src/monitoring/shadow_vps_service_monitoring.py` projects real service state into compact observability truth
- new files emitted by the real service loop:
  - `shadow_vps_service_monitoring_backend_payload.json`
  - `shadow_vps_service_observability_export.json`
  - `shadow_vps_service_observability.prom`
- preserve the doctrine:
  - lightweight VPS exporters only
  - heavy Prometheus/Grafana/drill-down stays local
  - no raw continuous heavy stream export
- latest proofs:
  - targeted slice: `9 passed`
  - wider monitoring/service cross-check: `19 passed`
- next steps stay unchanged in order:
  - `node_exporter` and scrape hookup
  - local Prometheus/Grafana hookup
  - compressed incident-bundle retrieval
  - real execution telemetry for `13-C EXECUTION`

Latest VPS bounded log retrieval slice:

- current code truth:
  - `src/monitoring/shadow_vps_service_log_retrieval.py` now provides bounded retrieval over durable `shadow_vps_service.events.jsonl`
  - `src/monitoring/contracts.py` now defines typed query/result/event projections for this rail
  - `scripts/run_shadow_vps_service.py` now emits `shadow_vps_service_recent_events.json`
- preserve the doctrine:
  - continuous export stays compact via a bounded recent-tail summary
  - deeper log inspection stays on-demand via typed bounded full-scan query
  - no heavy always-on raw stream was introduced
- latest proofs:
  - targeted slice: `11 passed`
  - wider monitoring/service cross-check: `22 passed`
- next observability steps now are:
  - `node_exporter` deployment / scrape hookup
  - local Prometheus/Grafana hookup
  - compressed incident-bundle retrieval
  - real execution telemetry for `13-C EXECUTION`

Latest VPS node_exporter textfile collector hookup:

- current code truth:
  - `src/monitoring/observability_io.py` now supports writing the compact observability text payload into a node_exporter textfile collector directory
  - `scripts/run_shadow_vps_service.py` now accepts `--node-exporter-textfile-dir`
  - when configured, the real service loop mirrors `v53_shadow_vps_service.prom`
- preserve the doctrine:
  - still lightweight on the VPS
  - still the same compact `.prom` payload
  - deployment/scrape remains a separate ops step
- latest proofs:
  - targeted collector slice: `10 passed`
  - wider monitoring/service cross-check: `24 passed`

Latest local Prometheus scrape bundle hookup:

- current code truth:
  - `src/monitoring/shadow_vps_service_scrape_manifest.py` now projects a typed per-VPS scrape handoff
  - `scripts/run_shadow_vps_service.py` can now emit that handoff when `--scrape-host` is supplied
  - `src/monitoring/shadow_vps_scrape_discovery.py` now discovers pulled/copied VPS scrape manifests on the local PC
  - `scripts/run_local_prometheus_scrape_bundle.py` now writes an aggregated Prometheus `file_sd` bundle
- preserve the doctrine:
  - VPS emits compact typed handoff only
  - local PC performs aggregation and future Prometheus/Grafana consumption
  - still no UI coupling
- latest proofs:
  - targeted scrape-manifest/aggregate slice: `11 passed`
  - wider monitoring/service cross-check: `29 passed`

Latest checked local Prometheus config generator:

- current code truth:
  - `src/monitoring/local_prometheus_config.py` now renders a checked local Prometheus config over the aggregated `shadow_vps_prometheus_file_sd.json`
  - `scripts/run_local_prometheus_config.py` now writes both YAML config and typed summary JSON
- preserve the doctrine:
  - local-PC side only
  - still no UI coupling
  - still no direct VPS runtime mutation
- latest proofs:
  - targeted config slice: `8 passed`
  - wider monitoring/service cross-check: `32 passed`

Latest Local IA Lab Grafana rail:

- current code truth:
  - `src/monitoring/local_lab_grafana_dashboard.py` now builds a detailed Grafana dashboard over the observed `v53_local_lab_*` metric surface
  - `scripts/run_local_lab_grafana_dashboard.py` writes both the dashboard import JSON and typed summary JSON
  - `src/monitoring/local_prometheus_metrics_bridge.py` now accepts `observability_export.json` as a dev bridge source in addition to raw `.prom`
  - `src/monitoring/local_prometheus_config.py` now supports a dedicated Local IA Lab scrape target via `--local-lab-target`
- current demo truth:
  - Local IA Lab dashboard UID: `v53-local-lab`
  - Local IA Lab dashboard panel count: `16`
  - observed Local IA Lab metric count in the demo summary: `44`
  - generated demo config with Local IA Lab target:
    - `build/dev_dual_role_demo/local_prometheus_config_with_lab/prometheus.local.generated.yml`
- preserve the doctrine:
  - Local IA Lab stays local-only
  - no new VPS runtime coupling
  - no fake panels beyond the currently observed metric inventory
- latest proofs:
  - targeted Local IA Lab monitoring/dashboard slice: `19 passed`

Latest `13-C EXECUTION` Shadow-service telemetry producer:

- current code truth:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now materializes a service-owned execution telemetry artifact bindable to a Local IA Lab review correlation
  - `scripts/run_shadow_vps_service.py` now writes a cumulative archive plus current sidecar:
    - `shadow_vps_service_execution_telemetry.archive.json`
    - `shadow_vps_service_execution_telemetry.json`
  - `scripts/run_local_lab_analysis_bundle.py` now accepts that service-owned artifact directly on `--execution-telemetry-path`
- current telemetry truth:
  - `THR-X02` can now come from real Shadow-service websocket timing evidence
  - websocket evidence is cumulative by `session_date`
  - native live capture uses accepted-event timing only and carries the explicit caution `THR-X02_ACCEPTED_EVENTS_ONLY`
  - `THR-X01` stays explicit/optional via `--execution-time-sync-offsets-path`
- latest proofs:
  - targeted execution telemetry + bundle + service slice: `20 passed`

Latest `13-C EXECUTION` native live `THR-X01` fallback:

- current code truth:
  - `src/protocols/shadow_live_websocket.py` now writes `live_time_sync_offsets.json` when `time_sync_probe_enabled=true`
  - `scripts/run_shadow_vps_service.py` now auto-reuses that service-owned sidecar for `THR-X01` when no explicit offsets path is passed
  - the ref is propagated in state/runtime/campaign summaries through `*_time_sync_offsets_ref`
- preserve the doctrine:
  - passive only
  - bounded and optional by config
  - no fake readiness when the probe is absent or fails
- latest proofs:
  - targeted live-capture/service/bundle slice: `26 passed`

Latest `13-C EXECUTION` service-owned `THR-X04/X05` samples:

- current code truth:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now collects `spread_bps` and `slippage_bps` from injected/live service evidence
  - `src/calibration_methods/execution.py` now adds a bounded `THR-X04` calibrator based on observed spread samples
  - `LocalLabExecutionTelemetry` now carries spread/slippage sample families end-to-end
- preserve the doctrine:
  - `THR-X05` still not marked modeled/ready
  - `THR-X03` still not marked ready without true runtime quota telemetry
  - this slice is evidence-first, not fake gating
- latest proofs:
  - targeted `13-C` cross-check: `30 passed`

Latest `13-C EXECUTION` `THR-X04` review activation:

- current code truth:
  - `src/local_replay_runtime/local_lab_execution_review.py` now consumes `THR-X04` as a real Local IA Lab threshold
  - readiness requires:
    - non-empty `spread_bps`
    - `spread_observation_days >= 30`
    - successful bounded lognormal calibration
  - the execution review threshold set is now:
    - `THR-X01`
    - `THR-X02`
    - `THR-X04`
- preserve the doctrine:
  - `THR-X03` still has no ready verdict without quota telemetry
  - `THR-X05` still has no ready verdict without a true slippage model
  - this slice remains review-side only
- latest proofs:
  - targeted execution review/bundle slice: `17 passed`
  - broader execution/protocols/monitoring cross-check: `31 passed`

Latest `13-C EXECUTION` explicit `THR-X03/X05` review gaps:

- current code truth:
  - `src/local_replay_runtime/local_lab_execution_review.py` now exposes the full bounded execution threshold set `THR-X01..THR-X05`
  - current review outcome is intentionally honest:
    - `THR-X01`, `THR-X02`, `THR-X04` can be `ready`
    - `THR-X03` stays `partial` with `THR-X03_SERVICE_RATE_LIMIT_TELEMETRY_MISSING`
    - `THR-X05` stays `partial` until a real slippage model exists
  - bundle summaries now report `execution_ready_threshold_count=3` and `execution_partial_threshold_count=2`
- preserve the doctrine:
  - no fake quota producer
  - no fake slippage model
  - no release-gate shortcut
- latest proofs:
  - targeted execution review/bundle slice: `17 passed`
  - broader execution/protocols/monitoring cross-check: `31 passed`

Latest `13-C EXECUTION` future `THR-X05` size traces:

- current code truth:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now also exports `candidate_sizes` and `final_sizes`
  - the review-side contract carries those traces end-to-end
  - route-hint size evidence is now ready for a later bounded `X05` model slice
- preserve the doctrine:
  - no fake slippage model yet
  - no fake ready verdict yet
  - this remains pure evidence preparation
- latest proofs:
  - targeted execution telemetry/review/bundle slice: `17 passed`
  - broader execution/protocols/monitoring cross-check: `31 passed`

Latest `13-C EXECUTION` `THR-X03` quota telemetry continuity:

- current code truth:
  - `src/protocols/shadow_live_websocket.py` now writes bounded quota probe metadata in `live_time_sync_offsets.json`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now propagates that metadata into the service-owned execution telemetry artifact
  - `src/local_replay_runtime/local_lab_execution_review.py` now makes `THR-X03` explicitly partial for four honest reasons:
    - telemetry missing
    - quota cap missing
    - history `< 30d`
    - model not implemented
- preserve the doctrine:
  - `THR-X03` still has no ready verdict
  - this slice adds evidence plumbing and clearer review semantics only
  - no release-gate shortcut was introduced
- latest proofs:
  - targeted execution/protocol slice: `20 passed`
  - broader execution/protocols/monitoring cross-check: `32 passed`

Latest `13-C EXECUTION` bounded `THR-X03/X05` models:

- current code truth:
  - `src/calibration_methods/execution.py` now calibrates:
    - `THR-X03` as a bounded throttle ratio from observed quota usage and official quota caps
    - `THR-X05` as a first bounded robust size/slippage model on service-owned telemetry
  - `src/local_replay_runtime/local_lab_execution_review.py` now marks `THR-X03` and `THR-X05` `ready` when aligned 30d evidence exists
  - the good-path Local IA Lab execution review can therefore become fully `ready` on service-owned execution evidence
- preserve the doctrine:
  - `THR-X05` remains a first bounded Lab model only
  - no live mutation and no opaque ML were introduced
- latest proofs:
  - targeted execution model slice: `21 passed`
  - broader execution/protocols/monitoring cross-check: `35 passed`

Latest `13-C EXECUTION` runtime consumer projection:

- current code truth:
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py` now projects:
    - `THR-X03 -> rate_limiter`
    - `THR-X05 -> slippage_model`
  - `src/local_replay_runtime/artifact_proof_summary_builder.py` and `src/local_replay_runtime/artifact_release_candidate.py` now surface that projection as future runtime handoff evidence
  - `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_execution_runtime_projection.json`
- preserve the doctrine:
  - descriptive handoff only
  - no live runtime mutation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - targeted projection/proof/release slice: `18 passed`
  - broader execution/protocols/monitoring cross-check: `46 passed`

Latest `13-C EXECUTION` canonical runtime consumers:

- current code truth:
  - `src/execution_backbone/rate_limiter.py` now exists as the bounded runtime consumer for `THR-X03`
  - `src/execution_backbone/slippage_model.py` now exists as the bounded runtime consumer for `THR-X05`
  - `src/execution_backbone/execution_runtime.py` can consume both only when they are injected explicitly
- bounded behavior:
  - `THR-X05` augments `expected_cost` conservatively and leaves an audit trail in `ExecutionIntent.metadata`
  - `THR-X03` blocks only when explicit live metadata carries `rest_quota_ratio_current`
  - absent/invalid rate-limit telemetry still fails open
- preserve the doctrine:
  - no bootstrap auto-wire
  - no default live mutation
  - no gate bypass
- latest proofs:
  - focused runtime-consumer slice: `30 passed`
  - broader execution/protocols/monitoring cross-check: `17 passed`

Latest `13-C EXECUTION` runtime projection bootstrap:

- current code truth:
  - `src/protocols/execution_runtime_projection_bridge.py` now loads `local_lab_execution_runtime_projection.json` fail-open
  - `src/protocols/execution_runtime_bootstrap.py` now accepts `execution_runtime_projection_path`
  - the canonical runtime can now recover `THR-X03/X05` consumer models directly from the Lab artifact on explicit bootstrap
- preserve the doctrine:
  - no path means no activation
  - invalid/missing/partial projection still fails open
  - no gate bypass
- latest proofs:
  - focused projection-bridge/bootstrap slice: `36 passed`
  - supporting execution/protocols cross-check: `14 passed`

Latest `13-C EXECUTION` runtime projection monitoring surface:

- current code truth:
  - Build-10 monitoring now exposes the Local IA Lab `execution_runtime_projection_path` seam through a typed projection
  - the technical dashboard, UI cards, and observability export now distinguish:
    - the compiled `execution_no_trade_bridge`
    - the bounded runtime-consumer bridge for `THR-X03/X05`
- preserve the doctrine:
  - monitoring remains descriptive only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused protocol/backend/runtime/observability/UI slice: `91 passed`
  - supporting execution bridge/bootstrap cross-check: `36 passed`

Latest `13-C EXECUTION` technical dashboard launcher auto-discovery:

- current code truth:
  - `scripts/run_technical_dashboard.py` now auto-loads `local_lab_execution_runtime_projection.json` from the demo output directory when present
  - an explicit `--execution-runtime-projection-path` is also accepted for operator-side inspection
- preserve the doctrine:
  - launcher surface only
  - no runtime activation
  - no gate bypass
- latest proofs:
  - focused launcher/ui/backend slice: `90 passed`
  - supporting runtime/bridge cross-check: `46 passed`

Latest `13-C EXECUTION` local replay shadow runner runtime projection surface:

- current code truth:
  - `scripts/run_local_replay_shadow.py` now auto-loads `local_lab_execution_runtime_projection.json` from its output directory when present
  - the same runner also accepts an explicit `--execution-runtime-projection-path`
  - generated baseline and candidate technical payloads now expose the bounded `execution_runtime_projection_bridge` seam for `THR-X03/X05`
- preserve the doctrine:
  - runner/operator surface only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused runner/dashboard slice: `95 passed`
  - supporting runtime/bridge cross-check: `36 passed`

Latest `13-C EXECUTION` Shadow orchestrator and VPS service runtime projection persistence:

- current code truth:
  - `scripts/run_shadow_daily_orchestrator.py` now accepts `--execution-runtime-projection-path` and persists the projection ref plus readiness counts in `shadow_daily_orchestrator.last_run.json`
  - `scripts/run_shadow_vps_service.py` now forwards the same seam and persists it in service state, runtime evidence bundle, campaign summary, and monitoring payloads
  - `src/monitoring/shadow_vps_service_monitoring.py` now emits bounded observability metrics for the projection seam
- preserve the doctrine:
  - descriptive persistence only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Shadow orchestrator/service slice: `24 passed`
  - supporting runtime/dashboard cross-check: `108 passed`

Latest `13-C EXECUTION` Micro-live and Live-Light runtime projection propagation:

- current code truth:
  - the canonical Build-12 and Build-13 protocol contracts now carry `execution_runtime_projection_ref/status/ready/counts`
  - Micro-live derives the seam from the governed Shadow technical payload bridge and preserves it through `run_micro_live_gate`
  - Live-Light inherits the same seam from governed Micro-live summaries and preserves it through `run_live_light_gate`
  - normalized Build-10 Micro-live and Live-Light projections now stay consistent with the same seam
- preserve the doctrine:
  - descriptive protocol propagation only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused protocol/dashboard slice: `82 passed`
  - supporting runner/service/dashboard cross-check: `88 passed`

Latest `13-C EXECUTION` Micro-live and Live dashboard operator visibility:

- current code truth:
  - Build-12 guardrails cards now surface `exec_proj` status and ready/partial/blocked consumer counts
  - Build-13 readiness cards now surface the same bounded seam from the canonical protocol chain
- preserve the doctrine:
  - operator visibility only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused dashboard slice: `33 passed`
  - supporting protocol cross-check: `76 passed`

Latest `13-C EXECUTION` Shadow live startup config propagation:

- current code truth:
  - `live_websocket_config.json` can now carry `execution_runtime_projection_path_ref`
  - the Shadow VPS service resolves that config-owned path when no explicit CLI projection path is supplied
  - explicit CLI still wins and the seam remains descriptive only
- preserve the doctrine:
  - startup/config propagation only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused service/live-config slice: `12 passed`
  - supporting monitoring/orchestrator cross-check: `18 passed`

Latest `13-C EXECUTION` Shadow service runtime projection provenance:

- current code truth:
  - Shadow service state, runtime bundle, campaign summary, and monitoring payloads now preserve `execution_runtime_projection_source`
  - current governed source values are `cli`, `live_websocket_config`, or `not_configured`
  - the existing bounded projection-ready metric now carries the same source label in observability
- preserve the doctrine:
  - provenance only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused provenance slice: `8 passed`
  - supporting service/orchestrator cross-check: `22 passed`

Latest `13-C EXECUTION` Shadow Grafana runtime projection observability:

- current code truth:
  - the local Shadow Grafana dashboard now renders dedicated panels for `execution_runtime_projection_ready`, ready/partial/blocked consumer counts, and an instant label table exposing `projection_status` plus `projection_source`
  - this makes the seam directly observable in Grafana, not only through Prometheus samples and the technical dashboard
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Grafana slice: `2 passed`

Latest `13-C EXECUTION` Shadow failure-hardening for runtime projection observability:

- current code truth:
  - once the runtime evidence bundle exists, the Shadow service now persists the `execution_runtime_projection` seam before attempting the later execution telemetry sidecar
  - if that later sidecar write fails, the monitoring payload and Prometheus export still surface `exec_projection=...` from the runtime evidence bundle instead of dropping back to `not_configured`
- preserve the doctrine:
  - observability hardening only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused failure-hardening slice: `4 passed`

Latest `13-C EXECUTION` Shadow demo telemetry skip semantics:

- current code truth:
  - the Shadow service now reuses `auto_export_dir` as `export_dir_ref` when a governed auto-export exists but the orchestrator payload omitted it
  - true demo/replay runs with no governed export now emit `execution_telemetry_skipped` instead of degrading the whole service over the missing telemetry sidecar
  - current dev dual-role Shadow artifacts therefore end `stopped` with `last_error=""`, `execution_telemetry_ref=""`, and `exec_projection=ready@cli`
- preserve the doctrine:
  - honest skip semantics only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Shadow/monitoring slice: `10 passed`
  - supporting orchestrator/replay cross-check: `16 passed`

Latest `13-C EXECUTION` Shadow telemetry monitoring/Grafana projection:

- current code truth:
  - the service now persists `last_execution_telemetry_status`
  - Build-10 monitoring now carries `execution_telemetry_status` and surfaces `exec_telemetry=<status>` in the compact payload detail
  - Prometheus now exposes `v53_shadow_vps_execution_telemetry_ready{telemetry_status=...}`
  - the local Shadow Grafana bundle now includes dedicated telemetry readiness/label panels
- current dev dual-role truth:
  - the refreshed demo payload is `exec_telemetry=skipped / exec_projection=ready@cli`
  - the refreshed demo `.prom` emits `v53_shadow_vps_execution_telemetry_ready{telemetry_status=\"skipped\"} 0.0`
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Shadow/monitoring slice: `10 passed`
  - focused Grafana slice: `2 passed`

Latest `13-C EXECUTION` canonical Build-10 Shadow telemetry card:

- current code truth:
  - the normalized `ShadowProjection` now carries `execution_telemetry_ref` plus `execution_telemetry_status`
  - the live-artifact technical dashboard loader now binds these fields from `shadow_vps_service.campaign_summary.json`
  - the `Build-11 Shadow` section of the technical dashboard now exposes an explicit `Execution Telemetry` card, so the seam is visible beyond Prometheus/local Grafana
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Build-10/UI/launcher slice: `74 passed`
  - supporting Shadow monitoring non-regression: `10 passed`

Latest `13-C EXECUTION` THR-X04 governed runtime consumer:

- current code truth:
  - `THR-X04` now lands as `spread_guard` in the canonical execution runtime
  - `local_lab_execution_runtime_projection` now emits three consumers instead of two: `rate_limiter`, `spread_guard`, `slippage_model`
  - `execution_runtime_projection_bridge` and `execution_runtime_bootstrap` now load the spread guard model in fail-open mode
  - Build-10/Prometheus/dashboard truth now exposes `spread_guard_model_loaded`
  - Shadow/Micro-live/Live-light preserve the new consumer counts through their normalized summaries
- preserve the doctrine:
  - opt-in only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused THR-X04 runtime slice: `50 passed`
  - supporting rail cross-check: `210 passed`

Latest `13-C EXECUTION` operated smoke seam:

- current code truth:
  - `scripts/run_build9_core_smoke.py` now accepts `--execution-runtime-projection-path`
  - the non-test execution bootstrap smoke can now load the governed runtime projection and verify the `rate_limiter + spread_guard + slippage_model` triplet on an operated launcher path
  - no default activation was added; absent projection still keeps the old smoke behavior
- preserve the doctrine:
  - explicit opt-in only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused operated-smoke slice: `40 passed`

Latest `13-C EXECUTION` operated Shadow bridge seam:

- current code truth:
  - the Shadow daily/orchestrator seam now derives `execution_runtime_projection_ready` from the canonical bridge inspection, not just the Lab artifact headline
  - the operated chain now preserves `execution_runtime_projection_bridge_status` plus the three model-load flags `rate_limiter`, `spread_guard`, and `slippage_model`
  - Shadow VPS runtime-evidence, campaign summary, monitoring payload, and Prometheus export now all carry this bridge truth
  - the local Shadow Grafana bundle now surfaces the same bridge-load truth with dedicated bridge/model-load panels
- preserve the doctrine:
  - no hidden runtime activation
  - no new launcher
  - no gate bypass
- latest proofs:
  - focused operated-bridge slice: `12 passed`
  - supporting Shadow rail cross-check: `26 passed`
  - focused local Shadow Grafana update: `2 passed`

Latest `13-C EXECUTION` Build-10 Shadow card seam:

- current code truth:
  - `ShadowProjection` now carries the service-owned `execution_runtime_projection` bridge/load truth from the operated Shadow chain
  - `run_technical_dashboard.py` now maps those fields from `shadow_vps_service.campaign_summary.json`
  - `technical_dashboard_view.py` now renders an explicit `Execution Projection` card inside `Build-11 Shadow`
  - the dev dual-role technical dashboard artifacts were regenerated against the current local runtime artifacts
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Build-10 Shadow card slice: `74 passed`

Latest `Build-14` bounded Opus entry-timing reader:

- current code truth:
  - `src/complete_enablers/micro_edge_entry_timing_layer.py` now exists as the bounded Build-14 reader for the still-open Opus `entry timing` suggestion
  - it consumes only existing Build-14 observation facts and stays on the governed enabler rail
  - `src/complete_enablers/limited_influence.py` now includes that reader in the canonical Shadow/post-Shadow bounded influence evaluation
- preserve the doctrine:
  - Build-14 enabler only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Build-14 entry-timing slice: `97 passed`

Latest `Build-14` bounded Opus exit-governor reader:

- current code truth:
  - `src/complete_enablers/micro_edge_exit_governor.py` now exists as the bounded Build-14 reader for the still-open Opus `exit governor` suggestion
  - it consumes only existing Build-14 observation facts and stays on the governed enabler rail
  - `src/complete_enablers/limited_influence.py` now includes that reader in the canonical Shadow/post-Shadow bounded influence evaluation
- preserve the doctrine:
  - Build-14 enabler only
  - no hidden runtime activation
  - no gate bypass
- latest proofs:
  - focused Build-14 exit-governor slice: `99 passed`

Latest `regime_lite` typed core:

- current code truth:
  - `src/regime_classifier/regime_lite.py` now exists
  - bounded first cut only:
    - typed `CALM / STRESSED / EXTREME`
    - explicit thresholds object
    - downgrade hysteresis
    - EXTREME cooldown
    - transition trace
  - `regime_classifier` is now present in the manifest/DAG instead of remaining an absent package path
- preserve the doctrine:
  - no hidden runtime activation
  - no direct engine wiring in this slice
  - no gate bypass
- remaining work:
  - calibration artifact loader
  - runtime/risk hooks
  - replay proof on the reference crisis windows

Latest first governed risk consumer for `regime_lite`:

- current code truth:
  - `src/risk_backbone/regime_lite_entry_gate.py` now exists
  - `RiskRuntime` now accepts a typed opt-in `regime_precheck_hook`
  - bounded first behavior: reject new entries while `EXTREME` or while the `EXTREME` cooldown is still active
- preserve the doctrine:
  - opt-in only
  - fail-open by default
  - no hidden live activation
  - no exit-all wiring yet
- latest proofs:
  - focused `regime_lite + risk runtime` slice: `120 passed`

Latest `regime_lite` calibration loader seam:

- current code truth:
  - `src/regime_classifier/regime_lite.py` now exposes `RegimeLiteCalibrationConfig` and `resolve_regime_lite_thresholds(...)`
  - the typed helper now loads signed `THR-RG01..04` artifacts through `calibration_loader`
  - only the documented regime thresholds are artifact-governed in this slice; the remaining classifier dimensions stay on bounded documented defaults
  - `calibration_loader` is now registered in the canonical manifest/build-order/dependency registry
- preserve the doctrine:
  - opt-in only
  - no silent fallback when the calibrated seam is requested
  - no hidden runtime activation
- latest proofs:
  - focused `regime_lite + manifest` slice: `128 passed`

Latest governed `regime_lite` safing recommendation:

- current code truth:
  - `src/risk_backbone/regime_lite_safing.py` now exists as the explicit `EXTREME -> safing recommendation` seam
  - cooldown-only states stay on `ENTRY_BLOCK_ONLY`
  - `EXTREME` states now yield `HALT_RECOMMENDED` + `should_exit_all=True`
  - the helper can materialize a canonical `OperatorSafingRequest(action=set_halted)` when explicitly requested
- preserve the doctrine:
  - recommendation only
  - no automatic kill switch trip
  - no hidden activation
- latest proofs:
  - focused `regime_lite + safing` slice: `128 passed`

Latest Build-10 `regime_lite` safing observability seam:

- current code truth:
  - Build-10 monitoring now exposes a typed `RegimeLiteSafingProjection` inside `ShadowProjection`
  - the technical dashboard launcher now hydrates it from the Shadow service campaign summary when that seam is emitted
  - `Build-11 Shadow` now shows a dedicated `Regime Safing` card
  - canonical observability now exports `v53_shadow_regime_lite_safing_status`
- preserve the doctrine:
  - recommendation only
  - no auto-`set_halted`
  - no hidden activation
- latest proofs:
  - focused `Build-10 regime_lite observability` slice: `85 passed`

Latest `regime_lite` protocol-summary propagation:

- current code truth:
  - `RegimeLiteGovernanceSummary` now exists in `src/protocols/contracts.py`
  - `run_shadow_validation(...)` can emit explicit governed regime truth when typed regime inputs are supplied
  - Micro-live and Live-Light now preserve that summary end-to-end without extra inference
- preserve the doctrine:
  - explicit producer only
  - recommendation only
  - no hidden activation
- latest proofs:
  - focused `protocol regime_lite propagation` slice: `142 passed`

Latest operated `regime_lite` service-summary propagation:

- current code truth:
  - `shadow_daily_orchestrator.last_run.json` now keeps flattened `regime_lite_governance` truth from the operated Shadow summary
  - `ShadowVpsRuntimeEvidenceBundle` and `ShadowVpsCampaignSummary` now preserve that seam through the real Shadow VPS service rail
  - service monitoring and Prometheus now expose:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
- preserve the doctrine:
  - copy operated Shadow truth only
  - recommendation only
  - no synthetic regime inference in the service
  - no hidden activation
- latest proofs:
  - focused `orchestrator + service + monitoring regime_lite` slice: `13 passed`

Latest explicit operated `regime_lite` producer:

- current code truth:
  - `run_local_replay_shadow.py` now accepts explicit typed `regime_lite` assessment/recommendation JSON inputs
  - the daily orchestrator and the real Shadow VPS service now forward that seam end-to-end
  - operated artifacts now carry real `regime_lite` governance truth when the seam is supplied
- preserve the doctrine:
  - explicit opt-in only
  - no synthetic classifier inputs
  - recommendation only
  - no hidden auto-halt
- latest proofs:
  - focused `local_replay_shadow -> orchestrator -> service regime_lite` slice: `8 passed`

Latest governed `regime_lite` auto-discovery:

- current code truth:
  - `run_local_replay_shadow.py` now auto-discovers `regime_lite_assessment.json` and `regime_lite_safing_recommendation.json` in its governed `output_dir`
  - the daily orchestrator can therefore consume the seam automatically when those sidecars are staged inside `shadow_output_dir`
- preserve the doctrine:
  - explicit path still wins
  - typed sidecars only
  - recommendation only
  - no hidden activation
- latest proofs:
  - focused `regime_lite auto-discovery` slice: `2 passed`

Latest local Shadow Grafana `regime_lite` coverage:

- current code truth:
  - the local Shadow Grafana dashboard now includes dedicated panels for entries blocked, exit-all recommended, and regime_lite labels
  - it reads only bounded service metrics:
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
    - `v53_shadow_vps_regime_lite_safing_status`
  - the local dashboard summary test is now stable on this Windows machine because it no longer depends on the broken `tmp_path` fixture
- preserve the doctrine:
  - monitoring-only seam
  - no dashboard-only inference
  - no hidden activation
- latest proofs:
  - focused `local shadow grafana regime_lite` slice: `4 passed`

Latest Shadow VPS `regime_lite` config-ref provenance:

- current code truth:
  - `ShadowLiveWebSocketConfig` now carries `regime_lite_assessment_path_ref` and `regime_lite_safing_recommendation_path_ref`
  - `run_shadow_vps_service.py` resolves those refs with explicit CLI precedence and persists the chosen refs/sources into state, runtime evidence bundle, campaign summary, and monitoring payload
- preserve the doctrine:
  - typed refs only
  - no synthetic inference
  - no hidden auto-halt
- latest proofs:
  - focused `shadow_vps_service + monitoring regime_lite provenance` slice: `12 passed`

Latest Shadow VPS Prometheus `regime_lite` provenance labels:

- current code truth:
  - the bounded `regime_lite` metrics now expose `assessment_source` and `safing_source`
  - the monitoring detail string also carries the same provenance summary
- preserve the doctrine:
  - bounded labels only
  - no dashboard-only seam
  - no runtime behavior change
- latest proofs:
  - focused `shadow monitoring provenance labels` slice: `2 passed`

Latest Build-10 `regime_lite` provenance detail:

- current code truth:
  - the canonical technical dashboard now preserves:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
    from the operated Shadow service campaign summary
  - the Build-11 Shadow `Regime Safing` card now renders those refs/sources directly
- preserve the doctrine:
  - dashboard consumer only
  - recommendation only
  - no hidden activation
- latest proofs:
  - focused `Build-10 regime_lite provenance detail` slice: `37 passed`

Latest Binance Shadow PowerShell bootstrap:

- current code truth:
  - `Install-BinanceApiEnv.ps1` now installs Binance API env vars in process scope and optionally user scope
  - `Start-BinanceShadowLiveCampaign.ps1` now stages the governed live campaign root, launches one bounded Shadow service cycle, and re-renders the canonical HTML dashboard
  - the user-scope Binance env is now installed on the current Windows machine
- preserve the doctrine:
  - Shadow only
  - no repo-side secret persistence
  - dashboard remains read-only
- latest proofs:
  - focused `PowerShell Binance bootstrap` slice: operator scripts exercised successfully

Latest native Binance live connect diagnostic:

- current code truth:
  - `shadow_live_websocket.py` now preserves endpoint + root cause when a native live connect attempt fails
  - the previously observed `WinError 10013` was confirmed to be a Codex sandbox network artifact
  - the same bounded live campaign succeeds outside the sandbox on the real Windows host
- preserve the doctrine:
  - diagnostics only
  - no retry-policy change
  - no hidden activation
- latest proofs:
  - focused `shadow live websocket diagnostics` slice: included in the `44 passed` targeted test run

Latest successful Binance Shadow operated campaign:

- current code truth:
  - the bounded PowerShell launcher now completes successfully on the real host and regenerates the canonical technical dashboard
  - current operated campaign truth includes:
    - `last_completed_session_date=2026-04-12`
    - `last_error=""`
    - `execution_telemetry_status=written`
    - authenticated user-data capture summary present
    - live capture pairs `BTCUSDT`, `ETHUSDT`
- preserve the doctrine:
  - Shadow only
  - no live order path
  - dashboard remains read-only

Latest `daily_pnl_breaker` typed core and first governed runtime consumer:

- current code truth:
  - `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py` now exists as the typed persistent `THR-R01` seam
  - it loads governed `THR-R01`, enforces the documented `2%` hard cap, persists same-day Shadow lock state, and can optionally trip the canonical circuit breaker
  - `src/risk_backbone/daily_pnl_breaker_entry_gate.py` now exists as the first bounded runtime consumer
  - `RiskRuntime` now accepts a typed opt-in `daily_pnl_precheck_hook`, so the Build-4 rail can reject new entries once the daily breaker has forced the session into Shadow
- preserve the doctrine:
  - opt-in only
  - fail-open by default
  - no hidden live activation
  - no automatic same-day reactivation
- latest proofs:
  - focused `daily_pnl_breaker + risk_runtime` slice: `34 passed`
  - focused `risk_runtime + engine A/B/C/D cross-check` slice: `42 passed`

Latest `reconciliation_scheduler` bounded operated seam:

- current code truth:
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now exists
  - the scheduler now loads governed `THR-I04`, enforces bounded interval limits, and exposes typed `boot_reconcile(...)` + `run_periodic_if_due(...)`
  - boot reconciliation now has a canonical blocking seam for unresolved divergences
  - periodic reconciliation now has a canonical due/not-due seam and can trip the existing circuit breaker on critical divergence
- preserve the doctrine:
  - no hidden background loop
  - explicit caller ownership of timing
  - no bypass of the existing reconciliation runtime
- latest proofs:
  - focused `reconciliation_scheduler + reconciliation_layer` slice: `35 passed`
  - focused `execution_runtime cross-check` slice: `28 passed`

Latest `execution_runtime_bootstrap` operated boot caller for `THR-I04`:

- current code truth:
  - `src/protocols/execution_runtime_bootstrap.py` now exposes typed bootstrap bundles:
    - `ExecutionRuntimeBootstrapBundle`
    - `build_execution_runtime_bootstrap_bundle(...)`
    - `build_binance_execution_runtime_bootstrap_bundle(...)`
  - the existing bootstrap helpers remain backward-compatible and still return only `ExecutionRuntime`
  - the bundle now carries optional bounded `reconciliation_scheduler` + `reconciliation_boot_result`
  - stale-only first boot with zero divergences is now treated as initial baseline establishment instead of a false trading block
  - `scripts/run_build9_core_smoke.py` is now the first real operated caller of this seam and can also load governed `THR-I04` from an optional calibration root
- preserve the doctrine:
  - opt-in only
  - no hidden scheduler loop
  - no fake Shadow integration before a real runtime caller exists
- latest proofs:
  - focused `execution runtime bootstrap + Build-9 smoke + reconciliation scheduler` slice: `20 passed`
  - focused `execution runtime cross-check` slice: `48 passed`

Latest standalone Build-9 smoke alignment:

- current code truth:
  - `scripts/run_build9_core_smoke.py` now imports the canonical engine facades through `engines.engine_a` and `engines.engine_b`
  - the same script now passes the explicit Build-8 portfolio `freshness_policy` required by the current `OrchestratorConfig`
  - the standalone operated report now reaches Build-2..9 `PASS`, including engine chain, portfolio chain, and execution bootstrap
  - the remaining direct-run failure is upstream of this slice: Build-1 still reports pre-existing DAG violations
- preserve the doctrine:
  - no new launcher
  - no alias package invented
  - canonical facades and typed config only
- latest proofs:
  - focused `Build-9 smoke script + execution bootstrap` slice: `21 passed`
  - direct `python scripts/run_build9_core_smoke.py` now fails only on Build-1 DAG debt

Latest Build-1 DAG debt reduction:

- current code truth:
  - the manifest/build registries now include the real on-disk packages:
    - `calibration_methods`
    - `secrets_manager`
    - `sharia_compliance`
    - `venue_adapters`
  - the dependency registry now authorizes the non-cyclic imports already present on disk for the execution/risk/scoring/local-replay/protocol drift
  - the Build-1 DAG report has been reduced from `47` errors to `27`
  - the remaining failures are now the real cycle + forward-edge debt, not missing-manifest noise
- preserve the doctrine:
  - no validator weakening
  - no cycle authorization
  - no fake Build-1 green
- latest proofs:
  - focused `manifest registry` slice: `83 passed`
  - direct `dag_validator` report: `27` errors
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator`

Latest Build-1 local Lab monitoring untangle:

- current code truth:
  - Local IA Lab monitoring builders now live under `monitoring`, not `local_replay_runtime`
  - the analysis bundle now passes primitive release/bridge/promotion facts into that seam
  - the old `local_replay_runtime` monitoring builder files were removed, not wrapped
  - Build-1 blocking DAG debt is now `23` real errors instead of `27`
- preserve the doctrine:
  - no validator weakening
  - no alias wrapper that preserves the cycle
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - focused `Local Lab monitoring seam` slice: `23 passed`
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator (23 error(s))`

Latest Build-1 replay/protocol untangle:

- current code truth:
  - replay workflow loading now lives with `local_replay_runtime`
  - injected websocket frame loading now lives in `data_backbone.websocket_gateway`
  - the `local_replay_runtime -> protocols` telemetry-loader seam is gone
  - Build-1 blocking DAG debt is now `19` real errors instead of `23`
- preserve the doctrine:
  - no validator weakening
  - no compatibility wrapper keeping the old seam alive
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - focused `replay/protocol seam` slice: `36 passed`
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator (19 error(s))`

Latest Build-1 DAG closure:

- current code truth:
  - `ExecutionRuntime` now uses `execution_backbone.fee_aware_edge_gate`
  - `ReconciliationScheduler` now uses `execution_backbone.emergency_circuit_breaker`
  - the scoring/risk paths remain compatibility entrypoints only
  - Build-1 `dag_validator` is now clean with `0` blocking errors
  - `scripts/run_build9_core_smoke.py` now passes Build-1 and Build-2..9 end to end
- preserve the doctrine:
  - no validator weakening
  - no fake green via registry-only exceptions
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `execution/risk/scoring compatibility` slice: `168 passed`
  - focused `manifest/build-order/dependency/layer` slice: `96 passed`
  - direct `dag_validator` report: `0` blocking errors
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest `gatekeeper` execution convergence:

- current code truth:
  - `src/execution_backbone/gatekeeper/gatekeeper.py` now exists as the canonical Build-3 convergence wrapper
  - `ExecutionRuntime.submit_opportunity(...)` now delegates the pre-submit decision chain to `ExecutionGatekeeper.authorize(...)`
  - the underlying execution guards remain unchanged; the gatekeeper only centralizes their outcome into typed `ExecutionPermit` / `ExecutionRefusal`
  - refusals now preserve the real `pair` and `engine_id`
  - `ExecutionSubmission` now carries `gate_trace`, and runtime logs emit the same trace
- preserve the doctrine:
  - no parallel execution rail
  - no guard removal
  - COMPLETE-only doctrine unchanged
  - persisted `artifacts/gatekeeper/` storage is still absent
- latest proofs:
  - focused `gatekeeper + execution runtime + runtime bootstrap` slice: `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest `info_stress_monitor` bounded risk seam:

- current code truth:
  - `src/risk_backbone/info_stress_monitor.py` now exists as the V37-3 lite detector
  - the current implementation classifies `NORMAL / ELEVATED / EXTREME` from five simple anomaly signals:
    - spread explosion
    - depth ratio collapse
    - cancellation spike
    - taker imbalance saturation
    - micro-vol divergence
  - `build_info_stress_entry_gate(...)` now exposes that detector as a typed Build-4 precheck hook
  - `RiskRuntime` now accepts the dedicated `info_stress_precheck_hook` plus candidate-side indicator fields
  - EXTREME now blocks new entries through a bounded cooldown when the hook is injected
- preserve the doctrine:
  - opt-in only
  - no late-stage auto-wiring yet
  - bounded lite seam only; not the full MAS layer
- latest proofs:
  - focused `info_stress_monitor + risk_runtime` slice: `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest `info_stress` protocol propagation:

- current code truth:
  - `src/protocols/contracts.py` now defines `InfoStressGovernanceSummary`
  - `run_shadow_validation(...)` now projects optional `InfoStressAssessment` into `shadow_summary.info_stress_governance`
  - `build_micro_live_input_from_shadow(...)` / `run_micro_live_gate(...)` preserve the same summary unchanged
  - `build_live_light_input_from_micro_live(...)` / `run_live_light_gate(...)` preserve it unchanged again
  - `src/protocols/__init__.py` now exports the summary type
- preserve the doctrine:
  - protocol-only propagation
  - no launcher/service wiring yet
  - no dashboard/observability work in this slice
  - assessment-only seam; no fake safing layer added
- latest proofs:
  - focused `protocol contracts + shadow + micro-live + live-light` slice: `147 passed`
  - focused `info_stress_monitor + risk_runtime` slice: `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest `info_stress` operated Shadow propagation:

- current code truth:
  - `run_local_replay_shadow.py` now accepts and auto-discovers `info_stress_assessment.json`
  - `run_shadow_daily_orchestrator.py` now persists `info_stress_governance_*` truth in `shadow_daily_orchestrator.last_run.json`
  - `run_shadow_vps_service.py` now resolves `info_stress_assessment` from CLI or `live_websocket_config`, then persists ref/source plus governance truth in state, runtime bundle, campaign summary, and monitoring payload
  - `shadow_vps_service_monitoring.py` now exports the assessment-only seam through:
    - `v53_shadow_vps_info_stress_status`
    - `v53_shadow_vps_info_stress_alert_count`
    - `v53_shadow_vps_info_stress_entries_blocked`
- preserve the doctrine:
  - assessment-only seam remains intact
  - no fake safing layer
  - no hidden activation on late-stage rails
- latest proofs:
  - focused `runner + orchestrator + service + monitoring` slice: `39 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest `gatekeeper` persisted audit store:

- current code truth:
  - `src/execution_backbone/gatekeeper/audit_logger.py` now exists as the append-only JSONL logger for canonical gatekeeper outcomes
  - `ExecutionRuntime.submit_opportunity(...)` now writes those audit records when configured with a `GatekeeperAuditLogger`
  - `execution_runtime_bootstrap.py` now accepts `gatekeeper_audit_path`
  - `run_build9_core_smoke.py` now accepts `--gatekeeper-audit-path` and can materialize `artifacts/gatekeeper/audit.jsonl`
- preserve the doctrine:
  - no new runtime path outside Build-3
  - no UI/monitoring-first expansion for this slice
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `gatekeeper + execution_runtime + bootstrap + build9 smoke` slice: `51 passed`
  - direct `python scripts/run_build9_core_smoke.py --gatekeeper-audit-path build/build9_core_smoke_run/artifacts/gatekeeper/audit.jsonl`: Build-1 `PASS`, Build-2..9 `PASS`

Latest `log_rotation` bounded monitoring seam:

- current code truth:
  - `src/monitoring/log_rotation.py` now exists as the bounded gzip + retention helper
  - `rotate_log_file(...)` rotates one operated log, truncates the active file, and prunes old `.gz` archives by retention window
  - `monitoring.__init__` now exports the helper
- preserve the doctrine:
  - bounded helper only, no daemon/scheduler
  - no Telegram integration yet
  - no new package/profile semantics
- latest proofs:
  - focused `log_rotation + disk_monitor + execution audit slice`: `55 passed`

Latest bounded `telegram_alerter` adapter:

- current code truth:
  - `src/alerting/{__init__,telegram_alerter}.py` now exists as the bounded external alert delivery package
  - it loads config from JSON/YAML or sealed mappings via `secrets_manager`, then sends canonical `AlertRecord` values through a bounded urllib adapter
  - `manifest_registry` now registers `alerting` as a canonical Build-11 module
- preserve the doctrine:
  - no hidden runtime integration yet
  - no daemon or retry loop
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `alerting + manifest + layer DAG` slice: `126 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest operated Telegram alert seam on Shadow VPS service:

- current code truth:
  - `src/protocols/shadow_vps_service_telegram_alerting.py` now projects selected service events into canonical `AlertRecord`
  - `scripts/run_shadow_vps_service.py` now accepts opt-in Telegram config/key paths and can emit bounded alerts from the operated Build-11 rail
  - each delivery attempt is audited in `shadow_vps_service.events.jsonl` as `telegram_alert_sent` or `telegram_alert_failed`
- preserve the doctrine:
  - no Build-10 forward dependency into `alerting`
  - no daemon or hidden retry loop
  - Telegram failures stay fail-open for the service
- latest proofs:
  - focused `protocols + alerting + manifest layer` slice: `43 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest operated Telegram monitoring projection:

- current code truth:
  - the Shadow service now persists the last Telegram delivery truth in state, campaign summary, and monitoring payload
  - the final `service_stopped` delivery result is no longer lost: summary and monitoring artifacts are rewritten after that event
  - Prometheus export now exposes `v53_shadow_vps_telegram_alert_delivery_status`
- preserve the doctrine:
  - no Build-10 dashboard-first expansion yet
  - no retry daemon or historical store
  - still service-backed last-state only
- latest proofs:
  - focused `telegram seam + monitoring` slice: `17 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest Build-10 technical dashboard projection of Telegram truth:

- current code truth:
  - the technical dashboard launcher now hydrates the last Shadow Telegram delivery truth from campaign summary
  - the Build-11 Shadow section now renders a dedicated `Telegram Alerts` card
  - the regenerated local `build11_live_websocket_campaign/technical_dashboard` artifact shows the same seam already present in monitoring/Prometheus
- preserve the doctrine:
  - projection only, no new sender logic
  - no Grafana work in this slice
  - last-state only, still service-backed
- latest proofs:
  - focused `launcher + view + monitoring backend` slice: `77 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest local Grafana + Telegram config provenance seam:

- current code truth:
  - the local Shadow Grafana bundle now includes two Telegram panels backed by `v53_shadow_vps_telegram_alert_delivery_status`
  - the operated Shadow service now accepts Telegram config/key refs from `live_websocket_config`, with CLI override preserved
  - Telegram config provenance is now carried through service state, runtime evidence, campaign summary, monitoring payload, and Prometheus
- preserve the doctrine:
  - projection-only Grafana slice
  - no hidden sender loop or retry daemon
  - operated precedence remains explicit and auditable
- latest proofs:
  - focused `local_grafana + monitoring + launcher` slice: `21 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest operated execution runtime bootstrap monitoring seam:

- current code truth:
  - the operated Shadow service now persists the bounded bootstrap reconcile truth through runtime evidence and campaign summary
  - canonical Shadow monitoring/Prometheus now exports this seam with explicit `status/source/gatekeeper_audit_source` plus reconcile counters
  - the Build-10 technical dashboard now exposes a dedicated `Execution Bootstrap` card in `Build-11 Shadow`
- preserve the doctrine:
  - no new runtime activation
  - no daemon/retry loop
  - no order-submit path
- latest proofs:
  - focused `shadow monitoring + technical dashboard + launcher` slice: `56 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest Build-1 executable engineering guardrails baseline:

- current code truth:
  - Build-1 now contains a repo-wide executable guardrail scan derived from `CODEX_PROMPT.md`
  - `scripts/run_engineering_guardrails.py` now emits audit-ready reports and refreshes `config/engineering_guardrails_baseline.json`
  - the baseline freezes current legacy debt, so only net-new guardrail regressions fail the foundation rail
- preserve the doctrine:
  - no repo-wide blind refactor
  - no weakening of Build-1
  - hotspot queue stays explicit for surgical follow-up
- latest proofs:
  - repo-wide baseline scan: `826` Python files, `4363` accepted legacy violations
  - normal guardrail run: `new_violations=0`
  - focused Build-1 guardrail tests: `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest first operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_shadow_vps_service.py` no longer carries inline `print()` calls, untyped loader helpers, or the previous bare `except` on the execution telemetry artifact path
  - parser construction is now decomposed into typed helper functions, while service output is centralized in `_build_service_output_lines(...)`
  - the remaining debt is now narrowed to `FILE_TOO_LONG` plus three large monoliths
- preserve the doctrine:
  - no semantic drift in the Shadow operated rail
  - no repo-wide rewrite
  - baseline is refreshed after the reduction so the fixed debt is no longer silently accepted
- latest proofs:
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`
  - repo-wide guardrail total reduced from `4363` to `4341`
  - `scripts/run_shadow_vps_service.py` reduced from `26` to `4` residual guardrail violations

Latest second operated hotspot reduction under executable guardrails:

- current code truth:
  - the Shadow service campaign summary is now built through grouped typed field-builders instead of one inline monolith
  - `_write_campaign_summary(...)` is now a thin wrapper over `core`, `live_capture`, `execution`, `regime_lite`, and `info_stress` builders
  - the decomposition keeps the exact persisted summary surface while removing the previous function-length breach
- preserve the doctrine:
  - no service-loop semantic drift
  - no artifact or schema rename
  - remaining runtime hotspot debt is still explicit
- latest proofs:
  - repo-wide guardrail run: `total_violations=4340`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest third operated hotspot reduction under executable guardrails:

- current code truth:
  - the Shadow service durable runtime bundle is now built through grouped typed field-builders instead of one inline monolith
  - `_write_runtime_evidence_bundle(...)` is now a thin wrapper over `input`, `execution`, `projection`, `regime_lite`, `info_stress`, and durable-artifact builders
  - the decomposition keeps the exact persisted runtime evidence surface while removing the previous function-length breach
- preserve the doctrine:
  - no service-loop semantic drift
  - no artifact or schema rename
  - remaining runtime hotspot debt is now narrowed further
- latest proofs:
  - refreshed guardrail baseline, then steady-state run: `total_violations=4339`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest fourth operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_shadow_vps_service.py` no longer keeps the full operated service loop inline in the public entrypoint
  - startup, loop, finalize, and output emission are now separated while preserving the same typed state/runtime-bundle/campaign-summary interfaces
  - the repo is back to `new_violations=0`; remaining explicit debt on this hotspot is now `FILE_TOO_LONG`
- preserve the doctrine:
  - no semantic drift in the Shadow operated rail
  - no artifact or schema rename
  - no broad rewrite outside the hotspot
- latest proofs:
  - repo-wide guardrail run: `total_violations=4338`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest fifth operated hotspot reduction under executable guardrails:

- current code truth:
  - the governed `scripts/run_local_replay_shadow.py` runner is now decomposed into typed helpers for import-context resolution, import materialization, runtime bundle assembly, session/day recording, demo payload construction, and per-engine evaluations
  - CLI artifact output no longer uses inline `print()` calls; typed annotations were restored on the remaining helper seams
  - file-local guardrail debt on this hotspot dropped from `22` to `1`; only `FILE_TOO_LONG` remains
- preserve the doctrine:
  - no schema rename
  - no hidden behavior change on the LOCAL_REPLAY -> SHADOW operated rail
  - no broad cleanup outside the hotspot
- latest proofs:
  - repo-wide guardrail run: `total_violations=4316`, `new_violations=0`
  - focused `local replay shadow runner` slice: `18 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest sixth operated hotspot reduction under executable guardrails:

- current code truth:
  - the governed `run_local_replay_shadow.py` runner is now a thin facade; its internals are split into bounded support modules for models/recovery, per-engine evaluations, payload/projection building, import materialization, and runtime/session persistence
  - the split preserves the same public entrypoints and the same governed sidecar outputs
  - all six resulting files now carry `0` local guardrail violations; the old file-length debt is fully removed
- preserve the doctrine:
  - no schema rename
  - no hidden behavior change on the LOCAL_REPLAY -> SHADOW operated rail
  - no broad cleanup outside the hotspot family
- latest proofs:
  - repo-wide guardrail run: `total_violations=4315`, `new_violations=0`
  - focused `local replay shadow runner` slice: `18 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest seventh operated hotspot reduction under executable guardrails:

- current code truth:
  - the Local IA Lab chained bundle script now emits its terminal summary through a bounded helper instead of inline `print()` calls
  - operator-facing output is preserved, but the CLI print debt on `scripts/run_local_lab_analysis_bundle.py` is removed
  - hotspot-local guardrail debt fell from `30` to `2`; only `FILE_TOO_LONG` and the giant `main(...)` remain
- preserve the doctrine:
  - no schema rename
  - no hidden behavior change in the Local IA Lab chain
  - no broad cleanup outside the hotspot
- latest proofs:
  - repo-wide guardrail run: `total_violations=4287`, `new_violations=0`
  - focused `local_lab_analysis_bundle launcher` slice: `7 passed`
