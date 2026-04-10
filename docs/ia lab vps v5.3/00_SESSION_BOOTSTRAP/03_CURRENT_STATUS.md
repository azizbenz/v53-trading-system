# Current Status

This file records the current known status for restart and continuation.

## Status sources used

Primary sources used to reconstruct this status:
- `docs/audit chatgpt buisness/2026-04-01_BUILD_HANDOFF_STATUS.md`
- readable docs under `docs/specs/`
- readable docs under `docs/ia lab vps v5.3/`
- current code under `src/`
- current test surfaces under `tests/`

Not used as trusted sources:
- files that contradict the active code or the active canon without explicit proof
- old audits used as if they were canon

Operational recovery docs now readable again:
- `docs/ia lab vps v5.3/2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`
- `docs/ia lab vps v5.3/2026-04-05_V53_CORPUS_WORKING_MEMORY.md`

Usage rule:
- use them as session memory and restart guidance
- do not let them override `docs/specs` or verified code/tests

## Last known branch and worktree state

Current branch:
- `codex/full-shadow-abcd-migration-20260403`

Important worktree reality:
- the worktree is broad and dirty across many builds and modules
- this is wider than the ideal "one critical module / one build at a time" method
- future sessions must not assume that all modified files are already validated

## Build status from strict handoff

Validated earlier under strict runtime-complete rule:
- Build-2 had already been closed before the strict Build-3 -> Build-9 sequence
- Build-3 ALIGNED
- Build-4 ALIGNED
- Build-5 ALIGNED
- Build-6 ALIGNED
- Build-7 ALIGNED
- Build-8 ALIGNED
- Build-9 ALIGNED
- Build-9X ALIGNED on the audited perimeter of that handoff

Not yet revalidated in the strict restart pass:
- Build-10
- Build-11
- Build-12
- Build-13
- Build-14
- Build-15
- Build-16
- Build-17

## Strategic reality check

There is a major doctrine convergence problem:

- the master canon and several docs still present `LIGHT` / `COMPLETE`
- the governed runtime path for Build-11 -> Build-13 already opens in `COMPLETE` only
- many registries, tests, and compatibility surfaces still carry `LIGHT`

This is a tracked strategic problem because it breaks the normal chain:
- docs -> code -> tests -> runtime expectation

## Code-confirmed truth anchors

The following facts are directly confirmed by the current code and must be treated as stronger than tracker or memory wording:

- `src/interface_contracts/domain_types.py`
  - `ProfileId` still contains both `LIGHT` and `COMPLETE`
  - `RuntimeMode` is the real governed rail: `LOCAL_REPLAY -> SHADOW -> MICRO_LIVE -> LIVE`
- `src/protocols/contracts.py`
  - Build-11 Shadow requires `profile=COMPLETE` and `runtime_mode=SHADOW`
  - Build-12 Micro-live requires `profile=COMPLETE` and `runtime_mode=MICRO_LIVE`
  - Build-13 Live requires `profile=COMPLETE` and `runtime_mode=LIVE`
- `src/backtest_artifact_import/validators.py`
  - governed import must start at `SHADOW`
  - implicit promotion beyond Shadow is forbidden
  - governed import currently requires `source_profile=COMPLETE`
- `src/backtest_artifact_import/signature_policy.py`
  - the default trust-store now carries real base64 Ed25519 public keys
  - governed signature verification now has a built-in pure-Python Ed25519 path and remains fail-closed on malformed or untrusted envelopes
- `src/backtest_artifact_import/upload_bridge.py`
  - the upload dry-run bridge now requires an explicit `governance_reference_date` on `ArtifactUploadRequest`
  - no hidden wall-clock `date.today()` fallback remains in the upload -> import conversion
- `src/local_replay_runtime/replay_orchestrator.py`
  - Local replay remains a governed export/proof path
  - `ReplayOrchestratorRequest` now defaults `profile_scope=ProfileId.COMPLETE`
- `src/meta_learning/contracts.py`
  - Build-9X governed inputs now default `TradeLearningInput.profile` to `ProfileId.COMPLETE`
  - explicit `LIGHT` remains available only as a deliberate compatibility input
- `src/engines/engine_a/engine_a_runtime.py`, `src/engines/engine_b/engine_b_runtime.py`, `src/engines/engine_c/engine_c_runtime.py`, `src/engines/engine_d/engine_d_runtime.py`
  - active engine runtimes now require explicit `EmergencyCircuitBreaker` constructor injection
  - no permissive `None` branch remains before `is_trading_allowed()`
- `src/data_backbone/pair_health_scorer/suspension_decider.py`
  - manual pair suspension now has an explicit audited path through `suspend_manual()`
  - `operator_id` and `reason_text` are both mandatory for `MANUAL`
  - the generic `evaluate_suspension()` path still cannot emit `MANUAL`
- `src/data_backbone/rest_bootstrap/gap_fill_controller.py`
  - REST bootstrap gap fill now fails closed on `gap_size <= 0.0`
  - negative or zero gaps are rejected explicitly as inverted/clock-reversal input instead of silently filling
- `src/scoring_backbone/penalty_aggregator/penalty_cap_guard.py`
  - phantom detection now requires a positive `expected_cost` baseline
  - `expected_cost <= 0.0` no longer creates a meaningless phantom verdict path
- `src/engines/engine_a/engine_a_runtime.py`, `src/engines/engine_b/engine_b_runtime.py`, `src/engines/engine_c/engine_c_runtime.py`, `src/engines/engine_d/engine_d_runtime.py`
  - active engine runtime inputs now enforce millisecond-scale `timestamp_ms`
  - Unix-second timestamps are rejected at contract validation time instead of corrupting runtime clock resolution
- `src/data_backbone/rest_bootstrap/runtime_bootstrap.py`
  - the REST resync path now reserves quota atomically through `record_call()`
  - a post-check rate-limit failure can no longer fall through to `fill_gap()`
- `src/data_backbone/pair_health_scorer/suspension_decider.py`
  - the health-based suspension path now requires an explicit threshold
  - only `hard_stale` and `consistency_failed` remain threshold-free suspension reasons
- `src/data_backbone/rest_bootstrap/rate_limit_guard.py`
  - rate-limit call timestamps now live in a deque
  - prune now trims expired entries in place instead of rebuilding the container on every call
- `src/risk_backbone/risk_runtime.py`
  - drawdown `REDUCE_EXPOSURE` is already enforced as `RiskRuntimeAction.REDUCE_EXPOSURE`
  - drawdown state is propagated into reason details and explainability on the active risk rail
- `src/scoring_backbone/ranking_router/portfolio_compatibility_checker.py`
  - unknown cluster ids now fail closed as explicit mapping errors
  - exhausted configured clusters still use the budget-based rejection path
- `src/engines/engine_b/conviction_builder_b.py` and `src/engines/engine_b/engine_b_runner.py`
  - `false_breakout_score` now defaults to neutral `0.5`
  - missing false-breakout information no longer silently reads as “no false breakout detected”
- `src/protocols/shadow_live_websocket.py`
  - websocket reconnect now closes the stale endpoint client before replacement
  - reconnect no longer leaks an old native client under the same endpoint key
- `scripts/run_local_replay_export.py`
  - governed local replay export now defaults `--profile-scope complete`
  - explicit `LIGHT` remains available only when the caller selects it deliberately
- `src/local_replay_runtime/replay_state_store.py` and `src/local_replay_runtime/runtime_evidence.py`
  - persisted LOCAL_REPLAY session/evidence state no longer resets silently on corruption
  - corrupted persisted state is backed up to `.corrupted` and recovered with typed `last_error` markers
  - the replay evidence recorder now exposes `build_state()` so recovery can be audited directly
- `src/local_replay_runtime/replay_orchestrator.py`
  - resume metadata and multi-chunk session sidecars no longer fail with raw JSON/Pydantic exceptions
  - corrupted `replay_session_config.json`, `replay_run_manifest.json`, `replay_chunk_session.json`, `performance_mode_guard.json`, `run_consistency_guard.json`, and `replay_metrics.json` are now backed up to `.corrupted`
  - LOCAL_REPLAY resume fails closed explicitly after backup instead of silently rebuilding from partial metadata
- `src/backtest_artifact_import/export_dir_bridge.py`
  - the governed export -> import bridge no longer swallows corrupted payload sidecars from a real export directory
  - corrupted governed sidecars are now backed up to `.corrupted` and rejected explicitly
  - strict sidecars now covered: `replay_run_manifest.json`, `feature_bridge.json`, `parity_diagnostics.json`, `replay_metrics.json`, `replay_dtr.jsonl`
  - payload validation now uses typed contracts where available: minimal parity diagnostics schema, `ReplayMetricsSummary`, and `DTRRecord`
  - the same bridge now also rejects semantically contradictory governed exports even when those sidecars are still JSON-valid
  - `review_export.md` provenance fields must stay aligned with manifest / metrics / parity sidecars
  - `feature_bridge.dataset_id` must match `replay_run_manifest.dataset_manifest_id`
  - `feature_bridge.feature_set_version` must match `replay_run_manifest.feature_set_version`
  - `feature_bridge.transform_set_version` must match `replay_run_manifest.transform_set_version`
  - `feature_bridge.pairs` / `feature_bridge.engines` must match manifest `tested_pairs` / `engine_scope`
  - `parity_diagnostics.dataset_id` must match `replay_run_manifest.dataset_manifest_id`
  - `replay_metrics.total_records` must match the real DTR count
  - `pair_aggregates` / `engine_aggregates` must sum to `total_records`
  - `replay_metrics` and `replay_dtr` must stay within manifest `tested_pairs` / `engine_scope`
  - `replay_dtr.runtime_mode` must stay `local_replay`
  - `replay_dtr` timestamps must stay within the manifest clock range
  - `replay_metrics` must remain exactly recomputable from the exported `DTRRecord` set
  - a real governed `export_dir` now also rejects sidecar refs that resolve outside the export directory itself
  - a real governed `export_dir` now also rejects multiple candidate files for the same governed sidecar label
  - current nuance: symbolic non-file refs remain accepted only on the non-export-dir demo path used by the shadow runner
- `src/calibration_loader/contracts.py` and `src/calibration_loader/loader.py`
  - a shared-core dynamic threshold calibration layer now exists in the repo
  - it supports signed calibration artifact parsing, version-scoped loading, duplicate `threshold_id` rejection, and explicit failures on missing / invalid / unsigned artifacts
  - current truth: it is not yet consumed by runtime modules; it is a prepared shared core, not a completed threshold migration
- `src/local_replay_runtime/edge_gate_calibration.py` and `src/scoring_backbone/fee_aware_edge_gate.py`
  - the first Local IA Lab EDGE calibration producer now exists in the repo
  - `THR-E01` and `THR-E02` can now be calibrated from replay `DTRRecord` evidence and exported as a shared `CalibrationArtifact`
  - `scripts/run_edge_gate_calibration.py` now provides the bounded Local IA Lab launcher for `replay_dtr.jsonl -> edge_gate.yml`
  - the same launcher now also accepts a governed `export_dir` and recovers replay provenance through `discover_local_replay_export(...)`
  - it now emits `edge_gate.input_summary.json` beside the YAML artifact for future dashboard / monitoring use
  - `scripts/run_local_replay_export.py` can now emit the same EDGE calibration artifact during governed export when `--emit-edge-calibration` is requested explicitly
  - the exact future consumer surface now also exists under `src/scoring_backbone/fee_aware_edge_gate.py`
  - current truth: the producer/helper slice is closed and the first runtime consumer now exists under `src/execution_backbone/execution_runtime.py`
  - current truth: the execution bootstrap path now exists under `src/protocols/execution_runtime_bootstrap.py`
  - current truth: the bounded Binance runtime rail can now enable the same gate explicitly through `BinanceAdapterConfig.fee_aware_edge_gate_enabled`
  - current truth: fee-aware no-trade decisions now also expose a structured audit surface through `NoTradeDecision.context` and `DecisionEvent.context`
  - honest residual: no higher-level scoring / engine consumer is wired yet
- `src/local_replay_runtime/historical_snapshot_loader.py`, `src/local_replay_runtime/replay_event_router.py`, `src/meta_learning/post_trade_diagnostic_engine.py`, `src/meta_learning/review_orchestrator.py`, and `src/backtest_artifact_import/export_dir_bridge.py`
  - the Local IA Lab already ingests historical snapshot batches, governed replay sidecars, post-trade `DTRRecord` evidence, and strategy/review bundles
  - current truth: the Lab already supports governed post-trade and replay analysis, but there is still no raw live bidirectional VPS -> Lab snapshot stream
  - planning anchor: `docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md`
- `src/meta_minimal/meta_runtime.py` and `scripts/run_local_lab_post_trade_review.py`
  - the Local IA Lab now has a bounded post-trade review entrypoint directly from governed `replay_dtr.json/.jsonl`
  - `build_meta_runtime_result_from_records(...)` rebuilds canonical Build-9 reports from exported DTR evidence
  - `run_local_lab_post_trade_review.py` now bootstraps `src/` itself on direct script execution, matching the other governed launchers
  - the same launcher can now also ingest a full governed `export_dir` directly through `discover_local_replay_export(...)`
  - when fed from `export_dir`, it derives `replay_dtr`, carries forward manifest/payload provenance, and defaults `total_opportunities` from the governed `ReplayRunManifest.record_count`
  - `run_local_lab_post_trade_review.py` now emits future-facing audit surfaces without UI coupling:
    - `meta_runtime_result.json`
    - `meta_learning_review.bundle.json`
    - `meta_learning_review.md`
    - `meta_learning_projection.json`
    - `trade_loss_attribution.json`
    - `governed_input_summary.json`
  - `trade_loss_attribution.json` is now the bounded per-trade answer to "why did this trade lose and what should prevent the next one"
  - the current failure modes are typed and explicit: `cost_drift`, `sterilization`, `edge_degraded`, `trace_coverage`, `unclassified_loss`
  - each losing trade now carries a governed preventive action, confidence, evidence, and optional threshold references for future calibration work
- `scripts/run_local_lab_analysis_bundle.py`
  - the Local IA Lab now has a bounded chained launcher for `export_dir -> post_trade_review -> edge_calibration`
  - one governed `export_dir` can now produce the post-trade review packet, the signed EDGE calibration artifact, and a single future-facing `local_lab_analysis_summary.json`
  - that chained summary now also tracks the dedicated `trade_loss_attribution.json` sidecar as future dashboard input
  - it now also emits a governed `walk_forward_review.template.json` plus `walk_forward_review.summary.json`
  - it now also emits a canonical-but-conservative `artifact_proof_summary.json` plus `artifact_proof_assessment.json`
  - the assessment makes the current Local IA Lab proof state explicit:
    - dimensions already derivable from current evidence are computed and typed
    - missing causal/ablation proof dimensions stay fail-close instead of silently passing
  - `local_lab_analysis_summary.json` now carries:
    - `artifact_proof_summary_path`
    - `artifact_proof_assessment_path`
    - `artifact_proof_ready`
    - `artifact_proof_validation_reasons`
  - the walk-forward doctrine is now explicit in code:
    - the walk-forward computation can stay automated
    - but anti-leakage approval remains human-gated
    - without approved human review, `walk_forward_pass` stays false
  - the same launcher now also supports governed multi-scope analysis with `--all-scopes`
  - a single governed export can now emit `local_lab_scope_matrix.json` over the real `pair x engine` grid instead of forcing manual reruns scope by scope
  - each scope now materializes under `output-root/scopes/<pair>__<engine>/` with:
    - `post_trade_review/`
    - `artifact_ablation_study.json`
    - `artifact_proof_summary.json`
    - `artifact_proof_assessment.json`
  - the multi-scope path remains fail-close:
    - scope-level `total_opportunities` is recomputed from scope evidence, not inherited silently from the manifest-wide record count
    - `local_lab_scope_matrix.json` now exposes `artifact_ablation_ready`, `artifact_proof_ready`, and `artifact_proof_validation_reasons` per scope as future dashboard inputs
  - the same launcher now also emits `artifact_release_candidate.json`
  - this is the current packaging-side Local IA Lab verdict for the future VPS bridge:
    - `release_status`
    - `ready_for_shadow_import`
    - `blocking_reasons`
    - per-scope release projection when a scope matrix exists
  - the same launcher now also emits a bounded dry-run bridge over the existing governed import rail:
    - `artifact_import_dry_run_bridge.json`
    - `artifact_upload_request.dry_run.json`
    - `artifact_import_request.dry_run.json`
    - `artifact_import_decision.dry_run.json`
    - `artifact_upload_decision.dry_run.json`
  - this bridge now states the current source/transport duality explicitly:
    - source artifact = Local IA Lab calibration artifact (`edge_gate.yml`)
    - transport artifact = current governed replay-derived packet (`review_packet`)
    - ids and kinds are no longer silently conflated in the sidecar
  - this bridge is fail-close by construction:
    - it only materializes request/decision payloads when the Local IA Lab release candidate is already ready
    - it refuses hidden governance defaults for `training_end`, `governance_reference_date`, `artifact_class`, `artifact_scope`, lifecycle, and drift threshold
  - honest residual:
    - this is still a dry-run bridge over the current replay/import rail
    - final live packaging semantics for future calibration artifacts remain a later slice
  - this remains a Local IA Lab orchestration slice only; it does not change the VPS import/promotion rail
- dashboard/output doctrine for future slices
  - every new core slice must be checked for a future-facing output surface: typed projection, structured log, metrics payload, artifact sidecar, or monitoring summary
  - this does **not** mean immediate HTML/UI work on every slice
  - it means avoiding hidden logic that cannot later feed Local IA Lab or VPS dashboards
  - preferred order stays: core logic -> typed output/projection -> tests -> optional dashboard wiring later
- `src/venue_adapters/binance_spot/time_sync.py`
  - `THR-X01` is now really consumed through `calibration_loader` on the Binance adapter rail
- `src/venue_adapters/binance_spot/ws_client.py` and `src/venue_adapters/binance_spot/orderbook_manager.py`
  - `THR-X02` now has a real consumer on the Binance adapter rail with explicit stale/resync behavior
  - honest residual: live/testnet websocket validation and long-run soak proof remain open
- `src/venue_adapters/binance_spot/order_translator.py`, `src/venue_adapters/binance_spot/error_classifier.py`, and `src/venue_adapters/binance_spot/rest_client.py`
  - the bounded `T4` foundation slice now exists on the Binance adapter rail
  - typed order translation now exists for `ExecutionIntent -> BinanceOrderRequest`
  - signed `POST /api/v3/order`, signed `GET /api/v3/openOrders`, and signed `DELETE /api/v3/order` now exist under mock-tested REST surfaces
  - deterministic `clientOrderId` now uses `engine_id + intent_id`, matching the governed repo contract
- `src/venue_adapters/binance_spot/execution_adapter.py` now provides a bounded `ExecutionVenueAdapter` implementation over that REST surface
  - replace is now modeled as cancel + submit on the adapter rail
  - remote-state reconciliation now has a minimal live bridge through `openOrders + account snapshot`
  - `src/venue_adapters/binance_spot/user_data_events.py` now exposes a bounded authenticated user-data event source plus `executionReport` parser
  - `poll_order_events()` now drains that bounded source when injected
  - `src/venue_adapters/binance_spot/user_data_ws_client.py` now provides a bounded websocket client for `userDataStream.subscribe.signature`
  - `src/venue_adapters/binance_spot/bootstrap.py` now provides a bounded builder from `BinanceAdapterConfig + credentials`
  - `src/protocols/execution_runtime_bootstrap.py` now consumes that builder via `build_binance_execution_runtime(...)`
  - `scripts/run_build9_core_smoke.py` now consumes that runtime bootstrap on a bounded local smoke path
  - honest residual: no real Testnet submit proof yet
- `src/sharia_compliance/contracts.py`, `policy_loader.py`, `asset_whitelist.py`, `asset_blacklist.py`, `stablecoin_policy.py`, `trade_type_guard.py`, `pair_screening.py`, `pair_screening_registry.py`, `pair_screening_audit.py`, `purification_calculator.py`, `policy_audit_logger.py`, `account_features_audit.py`, and `sharia_runtime.py`
  - bounded halal-compliance slice now covers veto before submit, deterministic AAOIFI pair-screening via metadata, a versioned local registry plus HC-4 traded-pair audit, purification math, and deterministic weekly account-feature audit
  - `src/venue_adapters/binance_spot/account_feature_provider.py` and `scripts/run_sharia_account_audit.py` now land a bounded Binance read-only provider plus weekly audit launcher path
  - `src/sharia_compliance/sharia_alerts.py` now turns audit findings into typed `AlertRecord` CRITICAL alerts
  - `config/sharia/policy_v1.yml` now carries the active conservative spot-halal policy root
  - `src/execution_backbone/execution_runtime.py` now calls `sharia_trade_authorizer.authorize_trade()` before any venue submit
  - honest residual: no real Testnet proof yet for the weekly audit launcher, no kill switch or external alert backend from the emitted `AlertRecord`s, and no live/external provider yet for AAOIFI pair-screening snapshots
- `scripts/run_complete_dashboard.py` and `src/ui/complete_dashboard_view.py`
  - Build-17 Complete local dashboard now supports a governed pair-scope selection over the canonical 12 COMPLETE pairs
  - the launcher accepts repeatable `--pair` selectors and a governed `--pair-count`
  - the selected scope now propagates consistently to HTML, payload JSON, view JSON, and supplement JSON
  - proof:
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py -q`
    - `6 passed`
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py -q`
    - `67 passed`
- `src/ui/technical_dashboard_html.py` and `scripts/run_complete_dashboard.py`
  - Build-17 Complete local HTML now exposes a clickable `Governed Complete Pair Selection` assistant
  - the panel provides canonical pair checkboxes, a `first N` helper, and a copyable PowerShell relaunch command
  - invariant kept: the page does not silently mutate the active payload in-browser; rescoping still requires governed launcher relaunch
  - proof:
    - `rtk pytest tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_complete_dashboard_launcher.py -q`
    - `8 passed`
    - `rtk pytest tests/test_ui/test_complete_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_monitoring/test_monitoring_backend.py -q`
    - `69 passed`
- `src/interface_contracts/artifact_contracts.py`
  - the canonical `RUNTIME_OPEN_HOOK_IDS` set now contains `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/engine_a_hooks.py` and `src/protocols/engine_a_pre_entry_confirmation_bridge.py`
  - `ENGINE_A_PRE_ENTRY_CONFIRMATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/engine_b_hooks.py` and `src/protocols/engine_b_sweep_validation_bridge.py`
  - `ENGINE_B_SWEEP_VALIDATION` now has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/engine_c_hooks.py` and `src/protocols/engine_c_void_validation_bridge.py`
  - `ENGINE_C_VOID_VALIDATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/engine_d_hooks.py` and `src/protocols/engine_d_reentry_validation_bridge.py`
  - `ENGINE_D_REENTRY_VALIDATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/risk_hooks.py` and `src/protocols/risk_micro_friction_precheck_bridge.py`
  - `RISK_MICRO_FRICTION_PRECHECK` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/scoring_hooks.py` and `src/protocols/scoring_soft_penalty_layer_bridge.py`
  - `SCORING_SOFT_PENALTY_LAYER` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/portfolio_hooks.py` and `src/protocols/portfolio_relative_rank_adjustment_bridge.py`
  - `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
  - it no longer remains a permanent `NotImplementedError` skeleton
- `src/protocols/execution_no_trade_hook.py`
  - `EXECUTION_NO_TRADE_FILTER` remains the other active bounded runtime-open hook executor surface
- `src/protocols/execution_runtime_dashboard.py`
  - the dashboard/monitoring rail now has a shared `build_runtime_hook_bridge_projections(...)` helper that projects the full eight-hook compiled bridge set
- `src/engines/engine_b/engine_b_runtime.py` and `src/scoring_backbone/scoring_runtime.py`
  - Engine B now accepts a typed sweep-validation hook and can block or apply bounded raw-score multiplier/add/cap adjustments before scoring
  - scoring now supports those bounded score adjustments explicitly instead of forcing hook effects through ad hoc penalty paths
- `src/engines/engine_a/engine_a_runtime.py`
  - Engine A now accepts a typed pre-entry validation hook and can block before scoring without bypassing the canonical runtime chain
- `src/engines/engine_d/engine_d_runtime.py`
  - Engine D now accepts a typed re-entry validation hook and can block before scoring without bypassing the canonical runtime chain
- `src/engines/engine_c/engine_c_runtime.py`
  - Engine C now accepts a typed void-validation hook and can block before scoring without bypassing the canonical runtime chain
- `src/protocols/portfolio_hooks.py`
  - unopened portfolio hook rail also remains a typed skeleton with `RUNTIME_OPEN = False`
- `src/protocols/live_light_runtime.py`
  - `BS-52` is closed: Build-14 influence now revalidates against explicit canonical contract classes
- `src/protocols/shadow_daily_orchestrator.py`
  - `BS-41` is closed: governed slot metadata sources must agree on `session_date`
- `scripts/run_local_replay_shadow.py`
  - `BS-41` is closed: direct shadow runner now resolves the base session date from governed export metadata when available
  - explicit import TTL/drift governance is now provided, so the governed runner no longer falls into `needs_revision` by omission
- `scripts/run_shadow_vps_service.py`
  - auto-exported `raw_input`, `websocket`, and `native_live_websocket` flows now pin `replay_run_manifest.timeframe_scope` to the source governed day before slot discovery
  - service/runtime evidence now advances on governed source days instead of replay timestamp dates
- `src/ui/operator_actions.py`
  - the locked operator surface no longer rejects `profile=COMPLETE`
  - explicit `LIGHT` remains accepted as a compatibility surface
- `src/ui/ui_light_locked.py`
  - the Build-10 locked view no longer hardcodes `Light` wording when rendering a `COMPLETE` payload
  - profile/state cards are now profile-aware on the active governed surface
- `src/ui/light_ui_runtime.py`, `src/ui/ui_light_locked.py`, `src/ui/technical_dashboard_view.py`, and `src/monitoring/contracts.py`
  - persisted locked-operator UI state no longer resets silently on corruption
  - corrupted state is backed up to `.corrupted` and surfaced as `operator_runtime.last_error`
  - Build-10 `Operator Events` cards now show the corruption marker instead of hiding it behind the last nominal operator event
- `src/ui/technical_dashboard_view.py` and `src/ui/technical_dashboard_html.py`
  - the technical dashboard now exposes an explicit `Build-10` section in the typed view and in the rendered HTML
  - the panel navigation now labels the top supervision surface as `Build-10 Technical Supervision`
- `src/monitoring/technical_dashboard_backend.py`, `src/monitoring/observability.py`, and `src/ui/technical_dashboard_view.py`
  - Build-10 now projects and renders a dedicated `Artifact Hooks` supervision section for all eight runtime-open compiled hook bridges
  - observability now emits per-hook bridge metrics `v53_runtime_hook_bridge_status`, `configured`, `binding_present`, `loaded`, and `artifact_count`
- `src/monitoring/*.py` and `src/ui/*.py`
  - active Build-10 source wording now consistently describes a locked operator UI instead of a `Light UI`
  - secondary monitoring wording now also presents Build-13 as the active Live rail and keeps `Live-Light` as a historical label in supervision text
- `docs/specs/*` orientation docs
  - `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md`, `V5_3_INDEX_MAITRE_FINAL_CORPUS.md`, `V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md`, and the Build-11/12/13 prompts in `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md` now carry active-reading notes for the governed `COMPLETE` rail
  - these docs still preserve historical file labels where needed, but no longer orient a reader toward `LIGHT` as the active rollout on the touched lines
- `src/` directory inventory
  - there is no active `local_ai_lab` package in `src/`
  - there is no active `control_plane` package in `src/`

## Latest known critical rail work

Latest reported completed work on the active `shadow/protocols` rail:
- BS-47 in `src/protocols/shadow_day_counter.py`
  - no fallback `now or time.time()`
  - `now=0.0` remains an explicit timestamp
- BS-45 in:
  - `src/protocols/shadow_daily_orchestrator.py`
  - `scripts/run_shadow_daily_orchestrator.py`
  - `scripts/run_local_replay_shadow.py`
  - `src/protocols/shadow_session_registry.py`
  - accepted verdict is separated from final accounting
  - `shadow_day_recorded` is separated from the real shadow-day count
  - a non-counted slot is replayable
  - a counted slot remains consumed
  - slot resolution from `replay_run_manifest.timeframe_scope` handles ISO datetime
- BS-48 in `src/protocols/shadow_day_counter.py`
  - `ShadowCounterState` moved to frozen state transitions
  - transitions now go through validated reconstruction instead of in-place mutation
- BS-52 in `src/protocols/live_light_runtime.py`
  - Build-14 influence no longer uses module/name duck typing
  - validation now requires real `Build14InfluenceSignal` / `Build14InfluenceReport` classes
  - duck-typed impostors are blocked by regression coverage
- BS-41 in:
  - `src/protocols/shadow_daily_orchestrator.py`
  - `scripts/run_local_replay_shadow.py`
  - conflicting governed slot metadata is now rejected instead of silently selecting one date
  - the direct shadow runner now uses governed export metadata for its base session date
  - explicit `session_date` is rejected when it disagrees with governed export metadata
- BS-68 in:
  - `src/protocols/shadow_session_registry.py`
  - registry append now builds a candidate list first and restores the exact prior in-memory entries when `_persist()` fails
  - a failed persist no longer leaves ghost dates that deadlock retry with `already recorded session_date`
- adjacent import-governance alignment in:
  - `scripts/run_local_replay_shadow.py`
  - demo and export-driven imports now publish explicit lifecycle/drift governance fields
- auto-export slot-date alignment in:
  - `scripts/run_shadow_vps_service.py`
  - `raw_input`, `websocket`, and `native_live_websocket` auto-exports now keep their governed source date through daily slot discovery

Latest bounded work on the practical IA Lab entry rail:
- local replay/export profile convergence in:
  - `src/local_replay_runtime/replay_orchestrator.py`
  - `scripts/run_local_replay_export.py`
  - governed local replay exports now default to `COMPLETE`
  - explicit `LIGHT` is preserved only as a caller-selected compatibility override
  - this keeps the local replay entrypoint aligned with governed import, which already requires `source_profile=COMPLETE`
- local replay resume-governance convergence in:
  - `src/local_replay_runtime/replay_orchestrator.py`
  - `scripts/run_local_replay_export.py`
  - completed-export resume now revalidates `run_id`, strategy metadata, `profile_scope`, `performance_mode`, and chunk identity against persisted session/manifest metadata
  - the launcher now hydrates missing resume identifiers from persisted metadata, but rejects explicit contradictory resume inputs
- upload/import governance-reference convergence in:
  - `src/backtest_artifact_import/contracts.py`
  - `src/backtest_artifact_import/upload_bridge.py`
  - governed upload dry-run now requires an explicit `governance_reference_date`
  - the import bridge forwards the request date unchanged instead of injecting `date.today()`
- export-dir -> typed import/upload builder convergence in:
  - `src/backtest_artifact_import/export_dir_bridge.py`
  - `scripts/run_local_replay_shadow.py`
  - governed export directories now materialize typed `ReplayExecutionPlan`, `ArtifactImportRequest`, and `ArtifactUploadRequest` through a shared bridge instead of ad hoc runner reconstruction
  - the bridge preserves `artifact_schema_version`, `feature_set_version`, and `transform_set_version` from `replay_run_manifest`
  - feature lineage and transform locks are derived from `recognized_feature_keys` only; an explicit empty recognized set no longer falls back to unrecognized `feature_keys`
  - timeframe-qualified keys like `sweep_score_1m` now resolve to canonical sweep lineage instead of being silently dropped
  - the runner demo path now reuses the same shared feature-lock builder, so demo and export-dir imports stay on one governed contract surface
- replay-plan -> typed import builder convergence in:
  - `src/backtest_artifact_import/export_dir_bridge.py`
  - `scripts/run_local_replay_shadow.py`
  - `scripts/run_technical_dashboard.py`
  - launcher-local `ArtifactImportRequest` reconstruction is now removed from the active rail
  - both the Shadow runner demo path and the technical dashboard demo path now reuse a shared `ReplayExecutionPlan + payload bundle -> ArtifactImportRequest` builder
  - the technical dashboard keeps its signed/verified demo import and onboarding flow, but now rides the same governed builder as the Shadow rail
- replay-plan -> typed upload builder convergence in:
  - `src/backtest_artifact_import/export_dir_bridge.py`
  - `scripts/run_technical_dashboard.py`
  - the dashboard demo is now the first real launcher on this rail to consume a shared `ReplayExecutionPlan + payload bundle -> ArtifactUploadRequest` builder
  - the launcher now derives governed import from `upload_request -> import_request` instead of constructing import-only state directly
  - upload dry-run sidecars are now emitted alongside the existing dashboard payload/import/onboarding evidence
- replay/evidence -> typed artifact bundle/upload convergence in:
  - `src/backtest_artifact_import/export_dir_bridge.py`
  - `scripts/run_technical_dashboard.py`
  - `scripts/run_local_replay_shadow.py`
  - the shared rail now exposes `ReplayExecutionPlan + replay evidence -> ArtifactExportBundle -> ArtifactUploadRequest -> ArtifactImportRequest`
  - the dashboard no longer builds `ArtifactExportBundle` locally
  - the Shadow runner no longer stops at import-only state; it now consumes upload dry-run sidecars and validates the upload-derived import before Shadow
  - the shared builder keeps TTL governed on `governance_reference_date` rather than replay-history timestamps
- bounded `BS-40` closure on the governed artifact-signature rail in:
  - `src/backtest_artifact_import/signature_policy.py`
  - `scripts/run_technical_dashboard.py`
  - `scripts/run_local_replay_shadow.py`
  - real base64 Ed25519 trust-store keys now replace placeholder public keys
  - the governed import rail now verifies signatures through a built-in pure-Python Ed25519 path
  - the dashboard and Shadow runner now consume the same real signed fixture envelope instead of launcher-local accept-all verifier lambdas
- bounded `BS-87` closure on the active engine-runtime safety rail in:
  - `src/engines/engine_a/engine_a_runtime.py`
  - `src/engines/engine_b/engine_b_runtime.py`
  - `src/engines/engine_c/engine_c_runtime.py`
  - `src/engines/engine_d/engine_d_runtime.py`
  - active engine runtimes now require explicit `EmergencyCircuitBreaker` injection at construction time
  - touched engine-runtime tests now import from canonical `engines.engine_*` packages and explicitly reject `circuit_breaker=None`

Reported aligned test runs for that rail:
- `tests/test_protocols/test_shadow_day_counter.py`
- `tests/test_protocols/test_bs65_fail_safe_registries_regression.py`
- `tests/test_protocols/test_shadow_daily_orchestrator.py`
- `tests/test_protocols/test_shadow_daily_orchestrator_launcher.py`
- `tests/test_protocols/test_shadow_vps_service_launcher.py`
- `tests/test_protocols/test_live_light_runtime.py`
- `tests/test_integration_alignment.py::TestIntegrationBuild11Build13`
- `tests/test_regression_alignment.py::TestLiveLightShadowPrerequisite`
- `tests/test_protocols/test_shadow_daily_orchestrator.py`
- `tests/test_protocols/test_local_replay_shadow_runner.py::test_export_local_replay_shadow_run_rejects_session_date_mismatch_with_export_metadata`

Important note:
- those results were reported in-session and are consistent with the touched files
- latest targeted pass after `BS-52` was:
  - `rtk pytest tests/test_protocols/test_live_light_runtime.py tests/test_integration_alignment.py::TestIntegrationBuild11Build13 tests/test_regression_alignment.py::TestLiveLightShadowPrerequisite -q`
  - `47 passed`
- latest targeted pass after `BS-41` was:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_local_replay_shadow_runner.py::test_export_local_replay_shadow_run_rejects_session_date_mismatch_with_export_metadata -q`
  - `7 passed`
- latest broader cross-check after runner/service alignment was:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `21 passed`
- latest registry regression proof after `BS-68` verification was:
  - `rtk pytest tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py tests/test_protocols/test_bs68_session_registry_rollback_regression.py -q`
  - `27 passed`
- latest coupled registry/orchestrator/service proof after `BS-68` verification was:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py tests/test_protocols/test_bs68_session_registry_rollback_regression.py -q`
  - `40 passed`
- latest bounded local replay entry-rail proof was:
  - `rtk pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `26 passed`
- latest bounded upload/import handshake proof was:
  - `rtk pytest tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py -q`
  - `48 passed`
- latest bounded export-dir bridge proof was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `24 passed`
- latest bounded shared replay-plan import-builder proof was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `23 passed`
- latest broader replay/import/signature/onboarding cross-check was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `83 passed`
- latest bounded W3 semantic-consistency proof was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_artifact_exporter.py -q`
  - `104 passed`
- latest W3 hardening now also rejects governed `ArtifactUploadRequest` objects whose manifest payload refs diverge from the typed `payload_bundle`
- latest W3 hardening also rejects duplicate refs inside a governed `ArtifactPayloadRefBundle`, including duplicates introduced through `supplementary_refs`
- latest bounded shared replay-plan upload-builder proof was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `14 passed`
- latest broader upload/import/signature/onboarding cross-check was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `84 passed`
- latest bounded replay/evidence -> upload -> import -> shadow/ui proof was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `26 passed`
- latest stable end-to-end rail proof was:
  - `rtk pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `36 passed`
- latest broader upload/import/signature/onboarding/shadow cross-check was:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_signature_policy.py tests/test_backtest_artifact_import/test_validators.py tests/test_backtest_artifact_import/test_onboarding.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `86 passed`
- latest bounded active engine-runtime safety proof was:
  - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src pytest tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-runtime`
  - `47 passed`
- latest bounded manual-suspension audit proof was:
  - `rtk pytest tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_pair_health_scorer.py -q`
  - `31 passed`
- latest bounded REST gap-fill fail-close proof was:
  - `rtk pytest tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py -q`
  - `8 passed`
- latest bounded phantom-cost baseline proof was:
  - `rtk pytest tests/test_scoring_backbone/test_bs88_phantom_detection_expected_cost_regression.py -q`
  - `8 passed`
- latest bounded engine timestamp-unit proof was:
  - `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_bs86_timestamp_ms_unit_constraint_regression.py -q --basetemp=build/pytest-bs86`
  - `12 passed`
- latest bounded REST quota TOCTOU proof was:
  - `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py -q`
  - `40 passed`
- latest bounded explicit suspension-threshold proof was:
  - `rtk pytest tests/test_data_backbone/test_pair_health_scorer.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
  - `35 passed`
- latest bounded rate-limit prune-allocation proof was:
  - `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
  - `45 passed`
- latest bounded drawdown-enforcement proof was:
  - `rtk pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py tests/test_risk_backbone/test_loss_budgeter.py -q`
  - `54 passed`
- latest bounded unknown-cluster proof was:
  - `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
  - `41 passed`
- latest bounded Engine-B false-breakout-default proof was:
  - `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q --basetemp=build/pytest-engine-b-bs77`
  - `80 passed`
- latest bounded websocket reconnect-cleanup proof was:
  - `rtk pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`

## Known open decisions

### BS-38

`BS-38` is now closed on the bounded `shadow/protocols` recovery surface.

Current understanding:
- `src/protocols/shadow_day_counter.py`
  - semantic counter state can now be rebuilt from validated persisted `ShadowDayRecord`s
- `src/protocols/shadow_session_registry.py`
  - semantic registry continuity can now be rebuilt from validated persisted entries
- `scripts/run_local_replay_shadow.py`
  - the active Shadow runner now restores counted-day continuity from durable day records after counter/registry corruption
  - recovered registry continuity uses explicit synthetic recovery metadata instead of silent invented provenance
- proof:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_bs65_fail_safe_registries_regression.py -q`
  - `53 passed`

### BS-44

`BS-44` is now closed on the bounded `portfolio_minimal` surface.

Current understanding:
- `candidate_pool_builder` already required explicit freshness policy
- the real remaining gap was `OrchestratorConfig`, which still defaulted to `CANDIDATE_POOL_FRESHNESS_DISABLED`
- `src/portfolio_minimal/portfolio_orchestrator.py` now requires an explicit `freshness_policy` at the orchestrator boundary
- the smallest proof set is:
  - `rtk pytest tests/test_portfolio_minimal/test_portfolio_minimal.py tests/test_portfolio_minimal/test_candidate_pool_bs125_regression.py tests/test_portfolio/test_canonical_portfolio.py -q`
  - `93 passed`

### BS-49

`BS-49` is now closed on the bounded doctrine/name convergence surface.

Current understanding:
- the governed rail is now described consistently as `COMPLETE -> SHADOW -> MICRO_LIVE -> LIVE` across:
  - touched primary canon docs
  - touched secondary navigation docs
  - active Build-10 monitoring/dashboard wording
- `ui` now exposes canonical `LockedOperator*` names first
  - `LightDashboardView` and `LightUIRuntime*` remain only as explicit compatibility aliases
- `monitoring` now exposes canonical `LiveProjection` and `live` / `live_status` compatibility accessors
  - legacy `live_light` fields remain only for compatibility continuity
- `protocols` now exposes canonical `Live*` names first
  - `LiveLight*` remains only as explicit compatibility aliases
- canonical tests now exercise those new names directly on the active Build-10 / Build-13 rails

Proof:
- `rtk pytest tests/test_ui/test_light_ui_runtime.py tests/test_ui/test_operator_actions.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_html.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py tests/test_integration_alignment.py -q`
  - `177 passed`
- `rtk grep -n "LockedOperatorUiRuntime|LockedOperatorDashboardView|LiveInput = LiveLightInput|LiveRunState = LiveLightRunState|LiveProjection = LiveLightProjection|build_live_input_from_micro_live = build_live_light_input_from_micro_live|build_live_projection = build_live_light_projection" src/ui src/monitoring src/protocols`
  - confirms canonical public names now lead while historical names remain explicit compatibility aliases

### BS-92

`BS-92` is now closed on the bounded `data_backbone` manual-suspension surface.

Current understanding:
- `src/data_backbone/pair_health_scorer/suspension_decider.py`
  - `SuspensionReason.MANUAL` now goes through `suspend_manual()` instead of ad hoc `SuspensionDecision` construction
  - `operator_id` and `reason_text` are both mandatory and embedded in the audit message
  - `evaluate_suspension()` still cannot return `MANUAL`, which keeps the operator path explicit and auditable

Proof:
- `rtk pytest tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_pair_health_scorer.py -q`
  - `31 passed`

### BS-89

`BS-89` is now closed on the bounded `data_backbone` REST bootstrap gap-fill surface.

Current understanding:
- `src/data_backbone/rest_bootstrap/gap_fill_controller.py`
  - `evaluate_gap_fill()` now rejects `gap_size <= 0.0` before rate-limit or size acceptance logic
  - negative and zero gaps no longer reach the fill path
  - positive gaps at the configured boundary keep the original `>` semantics and still fill

Proof:
- `rtk pytest tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py -q`
  - `8 passed`

### BS-88

`BS-88` is now closed on the bounded `scoring_backbone` phantom-risk surface.

Current understanding:
- `src/scoring_backbone/penalty_aggregator/penalty_cap_guard.py`
  - `evaluate_penalty_cap()` now requires `expected_cost > 0.0` before computing `PHANTOM_RISK`
  - zero or negative `expected_cost` is treated as an absent cost baseline, not as a positive phantom signal
  - positive-cost unprofitable trades still trip `PHANTOM_RISK` as intended

Proof:
- `rtk pytest tests/test_scoring_backbone/test_bs88_phantom_detection_expected_cost_regression.py -q`
  - `8 passed`

### BS-86

`BS-86` is now closed on the bounded `engines` runtime-input timestamp surface.

Current understanding:
- `src/engines/engine_a/engine_a_runtime.py`, `src/engines/engine_b/engine_b_runtime.py`, `src/engines/engine_c/engine_c_runtime.py`, `src/engines/engine_d/engine_d_runtime.py`
  - all four runtime input contracts now enforce `timestamp_ms >= 1_000_000_000_000`
  - Unix-second timestamps are rejected before `_resolve_runtime_now` can misread them as millisecond input
- `tests/test_engines/test_bs86_timestamp_ms_unit_constraint_regression.py`
  - the dedicated regression proof now uses canonical `engines.engine_*` imports, matching the active package layout

Proof:
- `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_bs86_timestamp_ms_unit_constraint_regression.py -q --basetemp=build/pytest-bs86`
  - `12 passed`

### BS-90

`BS-90` is now closed on the bounded `data_backbone` REST resync quota surface.

Current understanding:
- `src/data_backbone/rest_bootstrap/runtime_bootstrap.py`
  - `resync()` now validates gap geometry first, then reserves quota atomically through `record_call()`
  - a failed `record_call()` now returns `RATE_LIMITED` and stops before `fill_gap()`
- `tests/test_data_backbone/test_rest_bootstrap.py`
  - includes a regression where `record_call()` fails after a fillable gap was validated
  - proves the provider is not called on that path

Proof:
- `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py -q`
  - `40 passed`

### BS-93

`BS-93` is now closed on the bounded `data_backbone` pair-health suspension surface.

Current understanding:
- `src/data_backbone/pair_health_scorer/suspension_decider.py`
  - `evaluate_suspension()` no longer hides a universal `threshold=0.3` default
  - health-based decisions now require an explicit threshold
  - `hard_stale` and `consistency_failed` remain threshold-free suspension reasons
- `tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py`
  - proves the health path rejects omitted thresholds
  - proves the non-threshold suspension reasons remain available

Proof:
- `rtk pytest tests/test_data_backbone/test_pair_health_scorer.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
  - `35 passed`

### BS-91

`BS-91` is now closed on the bounded `data_backbone` rate-limit pruning surface.

Current understanding:
- `src/data_backbone/rest_bootstrap/rate_limit_guard.py`
  - `_call_times` now uses a deque instead of a list
  - `_prune()` now trims expired timestamps in place instead of rebuilding a filtered list
- `tests/test_data_backbone/test_rest_bootstrap.py`
  - includes a regression that proves prune keeps the same internal container while expiring old calls

Proof:
- `rtk pytest tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_bs89_gap_fill_negative_gap_regression.py tests/test_data_backbone/test_bs92_manual_suspension_audit_regression.py tests/test_data_backbone/test_bs93_suspension_threshold_explicit_regression.py -q`
  - `45 passed`

### BS-81

`BS-81` is now treated as closed on the bounded active `risk_backbone` rail.

Current understanding:
- `src/risk_backbone/risk_runtime.py`
  - `DrawdownVerdict.REDUCE_EXPOSURE` is already translated into `RiskRuntimeAction.REDUCE_EXPOSURE`
  - the drawdown verdict is surfaced in reason details and explainability instead of staying advisory-only

Proof:
- `rtk pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py tests/test_risk_backbone/test_loss_budgeter.py -q`
  - `54 passed`

### BS-83

`BS-83` is now closed on the bounded `scoring_backbone` portfolio-compatibility surface.

Current understanding:
- `src/scoring_backbone/ranking_router/portfolio_compatibility_checker.py`
  - unknown cluster ids now fail closed as explicit mapping errors
  - the old `get(cluster_id, 0.0)` masking path is gone
  - configured but exhausted clusters still reject through the normal budget path

Proof:
- `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
  - `41 passed`

### BS-82

`BS-82` is now closed on the bounded `portfolio_minimal` Build-8 selection surface.

Current understanding:
- `src/portfolio_minimal/opportunity_selector/eligibility_filter.py`
  - unknown cluster ids now fail closed before selection instead of being treated as implicitly zero remaining capacity downstream
- `src/portfolio_minimal/opportunity_selector/selection_resolver.py`
  - the Build-8 rail now emits `REJECTED_UNKNOWN_CLUSTER` explicitly
- `src/portfolio_minimal/portfolio_orchestrator.py`
  - unknown-cluster candidates are rejected at selection and no longer reach the cap/phantom path as silent `final_size=0` artifacts

Proof:
- `rtk pytest tests/test_portfolio_minimal/test_portfolio_minimal.py tests/test_portfolio/test_canonical_portfolio.py -q`
  - `89 passed`
- `rtk pytest tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_scoring_runtime.py -q`
  - `37 passed`

### BS-80

`BS-80` is now closed on the bounded `risk_backbone` beta-governance surface.

Current understanding:
- `src/risk_backbone/btc_factor_guard/pair_beta_registry.py`
  - no longer exposes a universal fallback beta
  - explicit beta mappings now carry `as_of_ts` and `regime_tag`
- `src/risk_backbone/btc_factor_guard/portfolio_beta_calculator.py`
  - now requires an explicit beta for every pair instead of silently using `0.8`
- `src/risk_backbone/risk_runtime.py`
  - now rejects stale beta mappings in addition to missing ones on the active risk rail

Proof:
- `rtk pytest tests/test_risk_backbone/test_btc_factor_guard.py tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py -q`
  - `49 passed`
- `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_scoring_backbone/test_ranking_router.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q`
  - `72 passed`
- `tests/test_risk_backbone -q` remains noisy in this workspace because `test_circuit_breaker.py` hits a temp-directory permission error unrelated to the beta slice

### BS-35

`BS-35` is now closed on the bounded `protocols` hook-governance surface.

Current understanding:
- `src/interface_contracts/artifact_contracts.py`
  - now defines the single canonical `RUNTIME_OPEN_HOOK_IDS` set
  - that governed set now contains `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`, and `EXECUTION_NO_TRADE_FILTER`
- `src/protocols/*_hooks.py`
  - now derive `RUNTIME_OPEN` from that single canonical source instead of carrying duplicated booleans
- `tests/test_protocols/test_hook_module_skeletons.py`
  - now proves the runtime-open hook set is bounded and code-governed

Proof:
- `rtk pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_b_sweep_hook.py tests/test_protocols/test_engine_b_sweep_validation_bridge.py -q`
  - `17 passed`

### Second Real Hook Slice

The bounded second real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/engine_b_sweep_validation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_B_SWEEP_VALIDATION`
- `src/protocols/engine_b_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/engines/engine_b/engine_b_runtime.py`
  - now accepts a typed sweep-validation hook and can block or adjust score before scoring
- `src/scoring_backbone/scoring_runtime.py`
  - now supports bounded raw-score multiplier/add/cap adjustments as an explicit contract surface

Proof:
- `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q`
  - `21 passed`
- `rtk pytest tests/test_protocols/test_artifact_action_composer.py tests/test_protocols/test_compiled_hook_plan_loader.py tests/test_protocols/test_compiled_artifact_registry_store.py -q`
  - `14 passed`
- `rtk pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q`
  - `83 passed`

### Third Real Hook Slice

The bounded third real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/engine_d_reentry_validation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_D_REENTRY_VALIDATION`
- `src/protocols/engine_d_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/engines/engine_d/engine_d_runtime.py`
  - now accepts a typed re-entry validation hook and can block before scoring without bypassing the canonical runtime chain

Proof:
- `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_d_reentry_hook.py tests/test_protocols/test_engine_d_reentry_validation_bridge.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q --basetemp=build/pytest-engine-d-reentry-hook`
  - `24 passed`

### Fourth Real Hook Slice

The bounded fourth real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/engine_c_void_validation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_C_VOID_VALIDATION`
- `src/protocols/engine_c_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/engines/engine_c/engine_c_runtime.py`
  - now accepts a typed void-validation hook and can block before scoring without bypassing the canonical runtime chain

Proof:
- `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_c_void_hook.py tests/test_protocols/test_engine_c_void_validation_bridge.py tests/test_engines/test_engine_c/test_engine_c_runtime.py -q --basetemp=build/pytest-engine-c-void-hook`
  - `24 passed`

### Fifth Real Hook Slice

The bounded fifth real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/engine_a_pre_entry_confirmation_bridge.py`
  - now provides the compiled-plan fail-open bridge for `ENGINE_A_PRE_ENTRY_CONFIRMATION`
- `src/protocols/engine_a_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/engines/engine_a/engine_a_runtime.py`
  - now accepts a typed pre-entry validation hook and can block before scoring without bypassing the canonical runtime chain

Proof:
- `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_engine_a_pre_entry_hook.py tests/test_protocols/test_engine_a_pre_entry_confirmation_bridge.py tests/test_engines/test_engine_a/test_engine_a_runtime.py -q --basetemp=build/pytest-engine-a-pre-entry-hook`
  - `26 passed`

### Sixth Real Hook Slice

The bounded sixth real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/risk_micro_friction_precheck_bridge.py`
  - now provides the compiled-plan fail-open bridge for `RISK_MICRO_FRICTION_PRECHECK`
- `src/protocols/risk_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/risk_backbone/risk_runtime.py`
  - now accepts a typed micro-friction precheck hook and can reject before the severe-pressure fallback without bypassing the canonical Build-4 runtime chain

Proof:
- `rtk pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_risk_micro_friction_hook.py tests/test_protocols/test_risk_micro_friction_precheck_bridge.py -q`
  - `36 passed`

### Seventh Real Hook Slice

The bounded seventh real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/scoring_soft_penalty_layer_bridge.py`
  - now provides the compiled-plan fail-open bridge for `SCORING_SOFT_PENALTY_LAYER`
- `src/protocols/scoring_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/scoring_backbone/scoring_runtime.py`
  - now accepts a typed soft-penalty hook and applies bounded `raw_score_multiplier / raw_score_add / raw_score_cap` adjustments before `calculate_raw_score`

Proof:
- `rtk pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_scoring_soft_penalty_hook.py tests/test_protocols/test_scoring_soft_penalty_layer_bridge.py -q`
  - `26 passed`

### Eighth Real Hook Slice

The bounded eighth real hook/runtime slice is now open on the active rail.

Current understanding:
- `src/protocols/portfolio_relative_rank_adjustment_bridge.py`
  - now provides the compiled-plan fail-open bridge for `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`
- `src/protocols/portfolio_hooks.py`
  - now exposes a real bounded executor surface instead of a permanent `NotImplementedError` skeleton
- `src/portfolio_minimal/portfolio_orchestrator.py`
  - now accepts a typed relative-rank hook and reapplies deterministic reranking before `resolve_selection`

Proof:
- `rtk pytest tests/test_portfolio_minimal/test_portfolio_minimal.py tests/test_protocols/test_hook_module_skeletons.py tests/test_protocols/test_portfolio_relative_rank_hook.py tests/test_protocols/test_portfolio_relative_rank_adjustment_bridge.py -q`
  - `102 passed`

### BS-78

`BS-78` is now closed on the bounded `engine_a / engine_b` conviction-calibration surface.

Current understanding:
- `src/data_backbone/market_physics_math.py`
  - now defines the shared governed conviction penalty weights for `fragility`, `toxicity`, and `micro_friction`
- `src/engines/engine_a/conviction_builder_a.py`
  - continues to use the canonical physics penalty calibration through the shared constant
- `src/engines/engine_b/conviction_builder_b.py`
  - is now aligned on the same physics penalty weights instead of tolerating the same stress inputs more loosely than Engine A
- `tests/test_engines/test_engine_b/test_engine_b.py`
  - includes an explicit regression proving weight symmetry across the two engines

Proof:
- `rtk pytest tests/test_data_backbone/test_market_physics_math.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_b/test_engine_b.py -q`
  - `164 passed`
- `rtk pytest tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_integration.py -q`
  - `23 passed`

### BS-77

`BS-77` is now closed on the bounded `engine_b` conviction/runtime-default surface.

Current understanding:
- `src/engines/engine_b/conviction_builder_b.py`
  - `false_breakout_score` now defaults to neutral `0.5` instead of optimistic `0.0`
- `src/engines/engine_b/engine_b_runner.py`
  - the same governed default is now applied on the runner input contract
- `tests/test_engines/test_engine_b/test_engine_b.py`
  - includes regressions proving that implicit defaults now match explicit `false_breakout_score=0.5`

Proof:
- `$env:PYTHONPATH='E:\\claude  v5.3\\v53_trading_system\\src'; pytest tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py -q --basetemp=build/pytest-engine-b-bs77`
  - `80 passed`

### BS-84

`BS-84` is now closed on the bounded native websocket adapter surface.

Current understanding:
- `src/protocols/shadow_live_websocket.py`
  - `BinanceSpotLiveWebSocketAdapter.connect()` now closes any stale client already registered on the endpoint before replacement
  - reconnect no longer leaks the old client behind `_clients[endpoint]`
- `tests/test_protocols/test_shadow_live_websocket.py`
  - includes a reconnect regression proving stale-client cleanup on the adapter itself

Proof:
- `rtk pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`

### Audit-remapped ids previously treated as orphan

The Sonnet audit docx under `docs/ia lab vps v5.3/` remaps the previously orphan ids:

- `BS-43`
  - maps to `src/interface_contracts/atomic_io.py`
  - the audited `default=str` code path is no longer present
  - treat as already corrected in the current repo state
- `BS-46`
  - maps to `src/smoke_bootstrap_recovery/state_sanity_checker.py`
  - `check_fd_leak()` now combines the local delta tolerance with a suite-level absolute FD ceiling passed by `run_build1_smoke()`
  - treat as closed in the current repo state
- `BS-63`
  - maps to `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - the audited full re-serialization pattern is no longer present
  - treat as effectively closed by the already-landed `BS-62` fix set
- `BS-67`
  - maps to `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - the current store now maintains append-only secondary indexes for `pair`, `engine_id`, and `decision_state`
  - treat as closed in the current repo state

Current rule:
- do not call these ids `unmapped` anymore
- do not reopen `BS-46` unless the smoke suite regresses
- do not reopen `BS-67` unless the store regresses
- reuse `07_SONNET_AUDIT_BS_MAPPING.md` as the recovery proof for these ids

### Tracker repair

The historical tracker files in the parent directory were previously found zero-filled, but are now readable again and contain reconstructed content.

Current rule:
- use the parent tracker + working memory for continuity
- use this bootstrap folder as the stable session entry point and usage matrix
- if the tracker or working memory becomes unreadable again, fall back to this bootstrap folder and rebuild from code/tests

## Recommended next steps

1. use this bootstrap folder as the mandatory entry point for every new session
2. do not reopen `BS-43`, `BS-46`, `BS-63`, or `BS-67` unless the current code regresses
3. if the goal is to reach IA Lab safely, continue on the real rail `local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`
4. the practical IA Lab entry rail is now stable, and `BS-38`, `BS-44`, `BS-49`, `BS-77`, `BS-78`, `BS-80`, `BS-81`, `BS-82`, `BS-83`, `BS-84`, `BS-86`, `BS-88`, `BS-89`, `BS-90`, `BS-91`, `BS-92`, and `BS-93` are closed on their bounded active surfaces; the next deliberate perimeter is a new real runtime rail, not more compatibility cleanup
5. do not invent or open a new `src/local_ai_lab` package until the real rail requires it
6. `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md` is now the ownership source:
   - `Local IA Lab` owns calibration/backtest/replay/proof/signature
   - `VPS` owns runtime consumption/execution
   - `src/calibration_loader/` stays shared core
7. accepted future architecture note:
   - `multi-VPS` may exist as a read-only fleet overview with only `health / runtime_mode / artifact_version / heartbeat / alert_state`
   - deep diagnostics still require connecting to the selected VPS directly
   - no active multi-VPS control plane or failover loop is implied
   - safest future order: `M0 doc/contract -> M1 monitoring/UI overview -> M2 per-VPS drill-down`
   - `M0` is now closed in code on `src/monitoring/contracts.py` with targeted proof `73 passed`
8. after each bounded tranche, update this file before ending the session
9. if the next deliberate perimeter is `engine_c / engine_d`, treat it as a structure/auditability parity slice
   - current truth: C/D already implement the canonical runtime chain
   - current asymmetry: C/D concentrate more logic inline in runner files, while A/B are more factorized
   - expected work: extract bounded helper modules without changing runtime semantics
10. the first bounded slice on that perimeter is now closed on `engine_c`
   - `src/engines/engine_c/structure_resolver_c.py` and `src/engines/engine_c/signal_math_c.py` now hold pure helper logic extracted from the runner
   - targeted proof:
     - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-c-factorization`
     - `21 passed`
11. the matching first bounded slice is now also closed on `engine_d`
   - `src/engines/engine_d/context_resolver_d.py` and `src/engines/engine_d/signal_math_d.py` now hold pure helper logic extracted from the runner
   - targeted proof:
     - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-d-factorization`
     - `21 passed`
10. the second bounded slice is now also closed on `engine_c`
   - `src/engines/engine_c/cost_feasibility_c.py`, `src/engines/engine_c/conviction_builder_c.py`, and `src/engines/engine_c/invalidation_mapper_c.py` now hold pure helper logic extracted from the runner
   - targeted proof:
     - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-c-factorization-pass2`
     - `21 passed`
11. the matching second bounded slice is now also closed on `engine_d`
   - `src/engines/engine_d/cost_feasibility_d.py`, `src/engines/engine_d/conviction_builder_d.py`, and `src/engines/engine_d/invalidation_mapper_d.py` now hold pure helper logic extracted from the runner
   - targeted proof:
     - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py -q --basetemp=build/pytest-engine-d-factorization-pass2`
     - `26 passed`
12. the third bounded slice is now also closed on `engine_c`
   - `src/engines/engine_c/output_payload_builder_c.py` now holds pure final `EngineCOutput` payload assembly extracted from the runner
   - targeted proof:
     - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py -q --basetemp=build/pytest-engine-c-final-assembly`
     - `21 passed`
13. the matching third bounded slice is now also closed on `engine_d`
   - `src/engines/engine_d/output_payload_builder_d.py` now holds pure final `EngineDOutput` payload assembly extracted from the runner
   - targeted proof:
     - `PYTHONPATH=E:\\claude  v5.3\\v53_trading_system\\src;E:\\claude  v5.3\\v53_trading_system\\src\\engines pytest tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py -q --basetemp=build/pytest-engine-d-final-assembly`
     - `26 passed`
14. the `engine_c / engine_d` parity/readability track is now in a good stopping state; do not reopen it without a broader refactor goal
15. `T1 / P0-1.A` is now closed on code + local tests
   - `src/interface_contracts/binance_contracts.py` exists
   - `src/venue_adapters/binance_spot/{credential_loader,time_sync,rest_client}.py` exists
   - `config/binance_adapter.yml` exists
   - `THR-X01` is consumed by `time_sync.py` via `calibration_loader`
   - targeted proof:
     - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_execution_backbone/test_venue_constraints_provider.py -q`
     - `15 passed`
   - honest residual:
     - Binance Testnet validation remains manual/human
     - sealed secrets remain the next tranche `T2`
16. `T2 / P0-4` is now closed on a bounded local/dev backend
   - `src/secrets_manager/{__init__,__main__,_dpapi,loader,sealer,cli}.py` exists
   - `src/secrets_manager/README.md` exists
   - `src/venue_adapters/binance_spot/credential_loader.py` now accepts `.sealed.json`
   - targeted proof:
     - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
     - `12 passed`
   - honest residual:
     - backend implemented today: Windows DPAPI + external `master.key`
     - `age` / `sops` / Linux VPS portability remain open
17. `T3 / P0-1.B` core is now coded and locally proved, but not yet fully closed as a live/testnet story
   - `src/venue_adapters/binance_spot/ws_client.py` exists
   - `src/venue_adapters/binance_spot/orderbook_manager.py` exists
   - `src/venue_adapters/binance_spot/rest_client.py` now also exposes typed REST depth snapshots and an explicit snapshot-provider bridge
   - `src/data_backbone/freshness_checker/venue_stream_freshness.py` exists
   - targeted proof:
     - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_shadow_live_websocket.py -q`
     - `19 passed`
   - broader coupled proof:
     - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_execution_backbone/test_venue_constraints_provider.py tests/test_protocols/test_shadow_live_websocket.py -q`
     - `33 passed`
   - honest residual:
     - live/testnet websocket validation pending
     - 24h RAM-leak proof pending
    - live/soak proof still to add

## Latest Local IA Lab recalibration planning

- `src/local_replay_runtime/local_lab_recalibration_plan.py` now converts governed loss evidence into a bounded local recalibration plan
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_recalibration_plan.json`
- this sidecar exposes:
  - `recommended_threshold_ids`
  - `calibration_candidate_ready`
  - `blocking_reasons`
  - typed actions such as `recalibrate_edge_gate`, `review_scope_sterilization`, and `improve_trace_capture`
- targeted proof:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py -q`
  - `11 passed`

## Latest Local IA Lab handoff semantics

## Latest EDGE provenance refinement

- `scripts/run_edge_gate_calibration.py` can now attach `local_lab_recalibration_plan.json` to `edge_gate.input_summary.json`
- `scripts/run_local_lab_analysis_bundle.py` now runs EDGE calibration after the recalibration plan is built, so the artifact producer carries that provenance
- targeted proof:
  - `rtk pytest tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `10 passed`

## Latest packaging gate refinement

- `artifact_release_candidate.py` now consumes `local_lab_recalibration_plan.json`
- a release candidate now needs a real plan path, not just proof sidecars
- current conservative semantics:
  - benign: `NO_LOSING_TRADES_TO_RECALIBRATE`
  - blocking: other recalibration blockers such as trace/evidence issues
- targeted proof:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `15 passed`

## Latest Local IA Lab handoff semantics
- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_source_summary.json`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now keeps the source/transport split explicit:
  - source artifact = Local IA Lab calibration artifact `edge_gate.yml`
  - transport artifact = replay-derived governed `review_packet`
- the dry-run transport packet now carries both source refs through `ArtifactPayloadRefBundle.supplementary_refs`
- `semantic_status` now reports `transport_packet_with_source_artifact_refs`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `9 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `88 passed`

## Latest Local IA Lab release-gate projection

- `artifact_upload_bridge_candidate.py` now mirrors the packaging verdict explicitly into the dry-run bridge:
  - `release_ready_for_shadow`
  - `release_artifact_proof_ready`
  - `release_artifact_proof_validation_reasons`
  - `release_recalibration_candidate_ready`
  - `release_recalibration_blocking_reasons`
  - `release_gate_status`
  - `release_gate_reasons`
- `local_lab_analysis_summary.json` now carries the same `bridge_release_gate_*` projection
- important invariant:
  - the bridge must expose the full proof blocker set
  - future tooling must not collapse this to a single truncated proof reason
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py -q`
  - `15 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py -q`
  - `96 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `287 passed`

## Latest Local IA Lab release-gate sidecar transport

- `run_local_lab_analysis_bundle.py` now emits `artifact_release_gate_summary.json`
- the dry-run bridge now requires and carries `release_gate_summary_ref`
- the transport packet supplementary refs now carry three Local IA Lab refs:
  - `edge_gate.yml`
  - `artifact_source_summary.json`
  - `artifact_release_gate_summary.json`
- `bridge_transport_payload_ref_count` is now `8` on the ready dry-run path
- semantic projection now also includes:
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

- `artifact_release_candidate.json` now preserves richer per-scope release rows:
  - `review_bundle_path`
  - `trade_loss_attribution_path`
  - `artifact_proof_summary_path`
  - `artifact_proof_assessment_path`
  - `executed_records`
  - `losing_trade_count`
- `local_lab_analysis_summary.json` now also exposes:
  - `release_ready_scope_slugs`
  - `release_blocked_scope_slugs`
- current use:
  - future dashboard drill-down can jump from the top-level release verdict to exact scope evidence
  - no new per-scope VPS import semantics are implied
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

- multi-scope analysis now emits `artifact_release_scope_summary.json` under each `scopes/<slug>/`
- each scope sidecar links:
  - shared artifact path
  - shared release-gate summary
  - shared dry-run bridge
  - scope-specific proof/review refs
- the top-level summary now also exposes:
  - `release_scope_summary_count`
  - `release_scope_summary_paths`
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

- `local_lab_scope_matrix.json` now carries packaging-side scope truth in addition to proof-side scope truth
- new matrix fields:
  - `release_ready_scope_count`
  - `release_blocked_scope_count`
- new per-scope fields:
  - `release_ready`
  - `release_blocking_reasons`
  - `release_scope_summary_path`
- `local_lab_analysis_summary.json` now also exposes:
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

- `run_local_lab_analysis_bundle.py` now emits `artifact_promotion_readiness_summary.json`
- this summary maps the current Local IA Lab packaging/dry-run truth to canonical shared-core vocabulary:
  - `activation_stage`
  - `normalized_promotion_state`
  - `review_state`
- bounded readiness statuses now exposed:
  - `local_only`
  - `shadow_candidate_pending_dry_run`
  - `shadow_candidate_dry_run_ready`
- top-level summary now also exposes:
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

- `run_local_lab_analysis_bundle.py` now also emits `local_lab_monitoring_projection.json`
- this is the compact future-dashboard summary over the current Local IA Lab packaging rail
- `local_lab_analysis_summary.json` now also projects:
  - `local_lab_monitoring_projection_path`
  - `monitoring_projection_status`
  - `monitoring_projection_detail`
- bounded status truth:
  - `healthy` only when the dry-run handoff is ready
  - `critical` only when core Local IA Lab outputs are incomplete
  - otherwise descriptive `warning/info`
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

- `run_local_lab_analysis_bundle.py` now also emits `local_lab_observability_export.json`
- this export is built from the compact Local IA Lab monitoring projection and uses the standard `ObservabilityExport` contract
- the top-level bundle summary now also projects:
  - `local_lab_observability_export_path`
  - `local_lab_observability_sample_count`
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

- `run_local_lab_analysis_bundle.py` now also emits `local_lab_monitoring_backend_payload.json`
- this payload is built from:
  - `local_lab_monitoring_projection.json`
  - `local_lab_observability_export.json`
- it is the first typed backend-facing future-dashboard payload for the Local IA Lab rail
- it stays descriptive only:
  - no UI coupling
  - no new runtime rail
  - no promotion behavior
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `17 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_monitoring_contracts.py -q`
  - `397 passed`

## Latest Local IA Lab monitoring ingestion summary

- `run_local_lab_analysis_bundle.py` now also emits `local_lab_monitoring_ingestion_summary.json`
- this summary is built from:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- it is the first monitoring-side ingestion verdict for the Local IA Lab bundle
- it remains descriptive only:
  - no UI coupling
  - no Build-10 runtime coupling
  - no VPS mutation
  - no promotion behavior
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py -q`
  - `20 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `400 passed`

## Latest Local IA Lab monitoring bundle loader

- `src/monitoring/local_lab_bundle_loader.py` now exists as the file-based loader for the Local IA Lab monitoring trio
- it loads and revalidates:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_ingestion_summary.json`
- it remains descriptive only:
  - no UI coupling
  - no Build-10 runtime coupling
  - no VPS mutation
  - no promotion behavior
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `10 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `402 passed`
