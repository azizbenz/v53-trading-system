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
- `src/calibration_methods/bootstrap.py`, `src/calibration_methods/walkforward.py`, and `src/calibration_methods/dsr.py`
  - the first shared Local IA Lab calibration-methods core now exists in the repo
  - current truth: stationary bootstrap, purged walk-forward geometry, and DSR are now available as pure typed helpers
  - current truth: `edge_gate_calibration.py` already consumes the shared stationary bootstrap helper
  - honest residual: the new walk-forward and DSR helpers are not yet promoted into release/promotion gates; they remain local math primitives for the next slices
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

## Latest Local IA Lab observability text export

- `run_local_lab_analysis_bundle.py` now also emits `local_lab_observability.prom`
- this file is written through the generic helper `src/monitoring/observability_io.py`
- it remains descriptive only:
  - no UI coupling
  - no new runtime semantics
  - no VPS mutation
  - no promotion behavior
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `11 passed`
  - `rtk pytest tests/test_backtest_artifact_import tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `403 passed`

## Latest Local IA Lab research-priority scorer

- `src/local_replay_runtime/local_lab_research_priority.py` now exists as the first bounded research-model-style component in the Local IA Lab core
- `run_local_lab_analysis_bundle.py` now emits `local_lab_research_priority.json`
- the same bundle now also propagates compact research-priority fields into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- this scorer stays transparent and local-only:
  - no hidden training
  - no VPS runtime coupling
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

- `src/local_replay_runtime/local_lab_replay_workflow_manifest.py` now exists and `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_replay_workflow_manifest.json`
- `src/monitoring/local_lab_replay_workflow_loader.py` now exists as the file-based loader for that workflow bundle
- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now exists and `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_monitoring_bundle_manifest.json`
- `src/monitoring/local_lab_bundle_loader.py` now discovers monitoring sidecars through the manifest instead of hardcoded filenames
- compact future-dashboard refs now also propagate for:
  - `local_lab_replay_workflow_manifest.json`
  - `local_lab_monitoring_bundle_manifest.json`
- important invariant:
  - local-only discovery/monitoring surface
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_monitoring/test_local_lab_ingestion.py -q`
  - `16 passed`
  - `python -m pytest tests/test_monitoring tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_loss_surrogate.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_local_lab_replay_candidate_queue.py tests/test_local_replay_runtime/test_local_lab_replay_dispatch_plan.py tests/test_local_replay_runtime/test_local_lab_replay_ticket_index.py tests/test_local_replay_runtime/test_local_lab_replay_workflow_manifest.py tests/test_local_replay_runtime/test_local_lab_research_priority.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_meta_learning/test_local_lab_post_trade_review_launcher.py tests/test_meta_learning/test_trade_loss_attribution.py tests/test_meta_minimal/test_meta_runtime.py -q`
  - `162 passed`
  - note: the older full broad sweep over all `tests/test_local_replay_runtime` still has unrelated Windows build-path cleanup noise in legacy replay/export tests, outside this slice

## Latest Local IA Lab monitoring bundle discovery

- `src/monitoring/local_lab_bundle_discovery.py` now exists as the manifest-driven discovery layer over multiple Local IA Lab monitoring bundles
- current capabilities:
  - discover bundles by `local_lab_monitoring_bundle_manifest.json`
  - sort by latest governed `timestamp_ms`
  - load the newest valid bundle through the existing loader
- important invariant:
  - local/backend only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_monitoring/test_local_lab_ingestion.py -q`
  - `18 passed`
  - rail-specific Local IA Lab + monitoring cross-check:
  - `164 passed`

## Latest Local IA Lab monitoring feed

- `src/monitoring/local_lab_monitoring_feed.py` now exists as the first compact feed over discovered Local IA Lab monitoring bundles
- current capabilities:
  - summarize latest bundle identity/status
  - count ingestion-ready bundles
  - count bundles by backend status
- important invariant:
  - local/backend only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_lab_monitoring_feed.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_monitoring/test_local_lab_ingestion.py -q`
  - `20 passed`
  - rail-specific Local IA Lab + monitoring cross-check:
  - `166 passed`

## Latest Local IA Lab calibration-methods review sidecar

- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now exists as the first proof-side consumer of the shared Local IA Lab math-core:
  - purged walk-forward geometry from `src/calibration_methods/walkforward.py`
  - DSR from `src/calibration_methods/dsr.py`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_calibration_methods_review.json`
- the same truth now propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- current conservative semantics:
  - DSR below floor blocks Local IA Lab proof locally
  - insufficient history stays explicit as `partial`
  - walk-forward geometry remains distinct from human walk-forward approval
- latest proofs:
  - targeted proof rail: `25 passed`
  - monitoring/backend propagation: `18 passed`
  - calibration/proof cross-check: `37 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `314 passed`

## Latest Local IA Lab release/dry-run calibration-methods propagation

- the Local IA Lab release candidate now carries explicit calibration-methods state
- the same truth now propagates into:
  - `artifact_release_gate_summary.json`
  - `artifact_import_dry_run_bridge.json`
- important invariant:
  - still Local IA Lab only
  - still no VPS/runtime mutation
  - this is descriptive handoff truth, not a new promotion authority
- latest proofs:
  - targeted release/dry-run rail: `20 passed`
  - `backtest_artifact_import + local_lab + monitoring` cross-check: `111 passed`

## Latest Local IA Lab monitoring feed calibration-methods propagation

- the monitoring bundle manifest, discovery layer, and compact feed now also carry calibration-methods readiness
- future backend discovery can now count:
  - calibration-ready bundles
  - calibration-partial bundles
  - calibration-blocked bundles
- latest proofs:
  - targeted monitoring/backend rail: `18 passed`
  - monitoring + local handoff cross-check: `203 passed`

## Latest Local IA Lab tail-risk review (`13-B`)

- `src/calibration_methods/pot_gpd.py` now exists as the bounded Local IA Lab POT-GPD helper
- `src/local_replay_runtime/local_lab_tail_risk_review.py` now consumes governed `DTRRecord` history and emits strategy-level breaker evidence for:
  - `THR-R01` daily net-loss buckets
  - `THR-R02` weekly net-loss buckets
  - `THR-R03` monthly net-loss buckets
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_tail_risk_review.json`
- the same compact truth now also propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet wired into release or dry-run handoff semantics
- latest proofs:
  - targeted tail-risk rail: `16 passed`
  - calibration/tail-risk cross-check: `32 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `317 passed`

## Latest Local IA Lab stationarity gate (`MI-9`)

- `src/calibration_methods/stationarity.py` now exists as the bounded dual ADF + KPSS helper
- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now consumes it over executed replay returns
- current conservative truth:
  - insufficient history stays `partial`
  - MI-9 failure blocks the local calibration-methods review
  - proof-side blockers now include:
    - `LOCAL_LAB_STATIONARITY_REQUIRED`
    - `LOCAL_LAB_STATIONARITY_INVALID`
- compact truth now also propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still Local IA Lab only
  - no UI coupling
  - no VPS/runtime mutation
- latest proofs:
  - targeted stationarity rail: `23 passed`
  - calibration/proof cross-check: `42 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `320 passed`

## Latest shared human hard-cap helper (`MI-7`)

- `src/calibration_methods/hard_cap_floor.py` now exists as the shared Local IA Lab floor/cap publication helper
- current consumers:
  - `src/local_replay_runtime/edge_gate_calibration.py`
  - `src/local_replay_runtime/local_lab_tail_risk_review.py`
  - `src/local_replay_runtime/local_lab_calibration_normalized_report.py`
- current audit semantics:
  - `hard_cap_satisfied` now means the published value respects the human bound
  - `hard_cap_binding` now makes explicit when the human floor/cap actually clipped the raw candidate
- important invariant:
  - still Local IA Lab only
  - no UI coupling
  - no VPS/runtime mutation
- latest proofs:
  - targeted hard-cap rail: `16 passed`
  - calibration/local cross-check: `44 passed`
  - broad `local_replay_runtime + meta_learning + meta_minimal`: `320 passed`

## Latest Local IA Lab multiple-testing review (`MI-12`)

- `src/calibration_methods/multiple_testing.py` now exists as the bounded shared Holm-Bonferroni helper
- `src/local_replay_runtime/local_lab_multiple_testing_review.py` now exists as the Local IA Lab MI-12 sidecar
- current truth:
  - current EDGE and tail-risk publications are still interval-publication artifacts
  - the bounded MI-12 verdict is therefore explicit `not_required_interval_publication`
  - this removes fake `not_evaluated` semantics without inventing a false corrected p-value pass
- the same truth now propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `artifact_proof_assessment.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - monitoring bundle manifest/discovery/feed
- latest proofs:
  - targeted MI-12 rail: `22 passed`
  - broad `calibration_methods + local_replay_runtime + monitoring + backtest_artifact_import + meta_learning + meta_minimal`: `524 passed`

## Latest Local IA Lab execution review (`13-C` first slice)

- `src/calibration_methods/execution.py` now exists as the bounded EXECUTION helper rail
- `src/local_replay_runtime/local_lab_execution_review.py` now emits explicit Local IA Lab truth for:
  - `THR-X01`
  - `THR-X02`
- current conservative semantics:
  - missing execution telemetry stays explicit `partial`
  - the bundle never fabricates venue telemetry from replay exports
  - this slice does not alter the current EDGE proof/release rail
- compact truth now also propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - monitoring bundle manifest/discovery/feed
- latest proofs:
  - targeted execution rail: `23 passed`
  - broad `calibration_methods + local_replay_runtime + monitoring + backtest_artifact_import + meta_learning + meta_minimal`: `529 passed`

## Latest VPS -> local observability architecture reminder

- planning anchor:
  - `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md`
- preserve the intended split:
  - VPS = runtime + lightweight collection + short retention
  - local PC = Prometheus + Grafana + heavy monitoring / drill-down / long retention
- preserve the transport doctrine:
  - continuous = compact summaries and typed metrics
  - on-demand = detailed logs and deep traces
  - never = permanent raw full-stream export that can saturate the VPS
- current code truth:
  - `src/monitoring/contracts.py` already provides `ObservabilityExport`, `TechnicalDashboardPayload`, `HealthDashboardPayload`, and `LocalLabMonitoringBackendPayload`
  - Local IA Lab already emits `.prom`
  - VPS observability contracts/exporters exist, but the real process/system producers are still not fully wired on the live service path
- immediate observability next steps:
  1. `node_exporter` / scrape hookup on the VPS
  2. local Prometheus/Grafana hookup
  3. compressed incident-bundle retrieval for detailed drill-down
  4. richer UI only after the backend/export rail is stable
- explicit missing code still open:
  - `src/regime_classifier/`
  - `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py`
  - `src/alerting/telegram_alerter.py`
  - `src/execution_backbone/gatekeeper/gatekeeper.py`
  - `src/risk_backbone/info_stress_monitor.py`
  - `src/execution_backbone/spread_guard.py`
  - `src/execution_backbone/slippage_model.py`
- estimated total solution progress:
  - `~62%` overall
  - estimate only, not a measured KPI

## Latest VPS Shadow service observability slice

- landed on the real service path, not on the dashboard scripts:
  - `scripts/run_shadow_vps_service.py`
  - `src/monitoring/process_metrics.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
- the Shadow VPS service now emits:
  - `shadow_vps_service_monitoring_backend_payload.json`
  - `shadow_vps_service_observability_export.json`
  - `shadow_vps_service_observability.prom`
- and now includes:
  - real bounded process metrics
  - real bounded disk usage for the service volume
- preserve the invariant:
  - VPS remains lightweight
  - heavy monitoring stays local
  - the service exports compact summaries, not raw heavy streams
- latest proofs:
  - focused service observability slice: `9 passed`
  - wider monitoring + launcher cross-check: `19 passed`
- explicit residuals:
  - no `node_exporter` / Prometheus scrape hookup yet
  - no compressed incident-bundle pull path yet
  - `13-C EXECUTION` still needs real execution telemetry

## Latest VPS bounded log retrieval slice

- real bounded log retrieval is now coded on the canonical monitoring/service rail:
  - `src/monitoring/shadow_vps_service_log_retrieval.py`
  - `src/monitoring/contracts.py`
  - `scripts/run_shadow_vps_service.py`
- current scope:
  - bounded full-scan query over durable `shadow_vps_service.events.jsonl`
  - bounded recent-tail summary written by the real service loop
  - typed results for future local drill-down without creating a heavy always-on stream
- new governed output:
  - `shadow_vps_service_recent_events.json`
- preserve the doctrine:
  - continuous export stays compact
  - detailed retrieval stays on-demand
  - no UI coupling
- latest proofs:
  - targeted retrieval slice: `11 passed`
  - wider monitoring/service cross-check: `22 passed`
- next observability order:
  1. `node_exporter` deployment / scrape hookup
  2. local Prometheus/Grafana hookup
  3. compressed incident-bundle retrieval
  4. real execution telemetry for `13-C EXECUTION`

## Latest VPS node_exporter textfile collector hookup

- real Shadow VPS service-side collector mirroring is now coded:
  - `scripts/run_shadow_vps_service.py`
  - `src/monitoring/observability_io.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
- current scope:
  - optional `--node-exporter-textfile-dir`
  - mirrors the compact service `.prom` export into `v53_shadow_vps_service.prom`
  - keeps the same canonical metrics payload; no alternate metrics format
- preserve the doctrine:
  - exporter remains lightweight on the VPS
  - `node_exporter` deployment and local scraping remain separate next steps
  - no UI coupling
- latest proofs:
  - targeted collector slice: `10 passed`
  - wider monitoring/service cross-check: `24 passed`

## Latest local Prometheus scrape bundle hookup

- the observability rail now covers both sides:
  - per-VPS handoff from the real service rail:
    - `shadow_vps_service_scrape_manifest.json`
    - `shadow_vps_service_prometheus_file_sd.json`
  - local-PC aggregation:
    - `scripts/run_local_prometheus_scrape_bundle.py`
    - `shadow_vps_scrape_discovery.json`
    - `shadow_vps_prometheus_file_sd.json`
- current truth:
  - a real service run can now emit a typed scrape handoff when `--scrape-host` is provided
  - local PC can aggregate multiple pulled VPS manifests into one Prometheus `file_sd` bundle
  - aggregation de-duplicates by latest target
- preserve the doctrine:
  - compact typed handoff only from the VPS
  - heavy Prometheus/Grafana consumption stays local
  - no UI coupling
- latest proofs:
  - targeted scrape-manifest/aggregate slice: `11 passed`
  - wider monitoring/service cross-check: `29 passed`
- next observability order:
  1. actual `node_exporter` deployment / scrape validation
  2. Grafana dashboards on top of the stable payloads
  3. compressed incident-bundle retrieval
  4. real execution telemetry for `13-C EXECUTION`

## Latest checked local Prometheus config generator

- local-PC config generation is now coded:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- current artifacts:
  - `prometheus.local.generated.yml`
  - `prometheus.local.config.summary.json`
- current truth:
  - the generated config consumes the aggregated `shadow_vps_prometheus_file_sd.json`
  - optional local node_exporter target can be included for Unix-like local hosts
  - optional local windows_exporter target can be included for Windows local PCs
  - this is a checked generator only; it does not start Prometheus itself
- latest proofs:
  - targeted config slice: `8 passed`
  - wider monitoring/service cross-check: `32 passed`

## Latest Windows local Prometheus exporter support

- the local Prometheus config generator now supports Windows local PCs explicitly:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- current truth:
  - `--local-windows-exporter-target` can now be passed to materialize a `v53_local_windows` scrape job
  - `--local-node-exporter-target` is now clearly optional and Unix-like only
  - default config generation no longer assumes a local exporter implicitly
- latest proofs:
  - targeted Windows exporter config slice: `6 passed`

## Latest dual-role dev Prometheus HTTP bridge

- the local dual-role dev path now has a dev-only HTTP bridge for the current `.prom` payload:
  - `src/monitoring/local_prometheus_metrics_bridge.py`
  - `scripts/run_local_prometheus_metrics_bridge.py`
- current truth:
  - it serves the generated V5.3 `.prom` payload over `/metrics`
  - it exposes `/-/ready`
  - it writes `local_prometheus_metrics_bridge.summary.json`
  - it exists to make local Windows/dev visualization work before the real VPS `node_exporter` path is deployed
- latest proofs:
  - targeted dev bridge slice: `8 passed`

## Latest local Grafana dashboard bundle and bootstrap

- the local dual-role dev path now has a Grafana dashboard bundle and local bootstrap helpers:
  - `src/monitoring/local_grafana_dashboard.py`
  - `scripts/run_local_grafana_dashboard.py`
  - `src/monitoring/local_grafana_api.py`
  - `scripts/run_local_grafana_bootstrap.py`
- current truth:
  - the generated dashboard is constrained to the currently observed `v53_shadow_vps_*` metric set
  - the bundle writes both dashboard JSON and typed summary JSON
  - the local bootstrap can create the Prometheus datasource and import the dashboard through Grafana HTTP API
- latest proofs:
  - targeted dashboard/bootstrap slice: `13 passed`

## Latest Local IA Lab Grafana rail on the dual-role dev box

- the local dual-role dev path now has a second dashboard rail for `Local IA Lab`, not only `Shadow VPS`:
  - `src/monitoring/local_lab_grafana_dashboard.py`
  - `scripts/run_local_lab_grafana_dashboard.py`
- current truth:
  - the new dashboard is generated from the real observed `v53_local_lab_*` metric inventory
  - the dev-only metrics bridge can now serve either a raw `.prom` file or a Local IA Lab observability export JSON with `text_payload`
  - the checked local Prometheus config can now include a dedicated `v53_local_lab` scrape job through `--local-lab-target`
  - current demo artifacts already exist under:
    - `build/dev_dual_role_demo/local_lab_grafana_dashboard/`
    - `build/dev_dual_role_demo/local_prometheus_config_with_lab/`
- current dashboard truth:
  - `uid = v53-local-lab`
  - `panel_count = 16`
  - `observed_metric_count = 44`
- latest proofs:
  - targeted Local IA Lab monitoring/dashboard slice: `19 passed`

## Latest `13-C EXECUTION` service-owned telemetry rail

- the Shadow VPS service now emits a typed execution telemetry handoff for Local IA Lab:
  - `shadow_vps_service_execution_telemetry.archive.json`
  - `shadow_vps_service_execution_telemetry.json`
- current truth:
  - the service cumulatively stores websocket timing evidence by `session_date`
  - `THR-X02` can now be fed from real service-owned websocket timing sources
  - the Local IA Lab bundle can now accept either:
    - a review-owned `LocalLabExecutionTelemetry`
    - or the new service-owned execution telemetry artifact, then bind it to the review `correlation_id`
  - `THR-X01` remains honest/optional via `--execution-time-sync-offsets-path`
  - service state now carries `last_execution_telemetry_ref`
  - `ShadowVpsServiceMonitoringPayload` now exposes `execution_telemetry_ref`
- latest proofs:
  - targeted execution telemetry + bundle + service slice: `20 passed`

## Latest `13-C EXECUTION` THR-X01 live-capture fallback

- native live capture can now materialize a bounded passive time-sync sidecar:
  - `live_time_sync_offsets.json`
- current truth:
  - the sidecar is emitted by `src/protocols/shadow_live_websocket.py` when `time_sync_probe_enabled=true`
  - `scripts/run_shadow_vps_service.py` now auto-consumes that sidecar for `THR-X01` if `--execution-time-sync-offsets-path` is absent
  - the ref is now visible in service/runtime handoff through:
    - `last_live_capture_time_sync_offsets_ref`
    - `live_capture_time_sync_offsets_ref`
  - replay/websocket-injected days remain honestly partial for `THR-X01`
- latest proofs:
  - targeted live-capture/service/bundle slice: `26 passed`

## Latest `13-C EXECUTION` THR-X04/X05 sample harvesting

- the service-owned execution telemetry artifact now also carries execution-surface samples:
  - `spread_bps`
  - `slippage_bps`
- current truth:
  - spreads are harvested from existing snapshot/depth evidence
  - slippage samples are harvested from existing route-hint metadata when present
  - `src/calibration_methods/execution.py` now exposes a shared bounded `THR-X04` calibrator
  - the execution review contract now carries the new sample families, but review gating is still intentionally limited to `THR-X01/X02` on this slice
- latest proofs:
  - targeted `13-C EXECUTION` cross-check: `30 passed`

## Latest `13-C EXECUTION` THR-X04 review consumption

- current truth:
  - `src/local_replay_runtime/local_lab_execution_review.py` now consumes `THR-X04` for real
  - `THR-X04` is `ready` only when:
    - `spread_bps` samples are present
    - `spread_observation_days >= 30`
    - the bounded lognormal calibrator succeeds
  - the Local IA Lab execution review now covers:
    - `THR-X01`
    - `THR-X02`
    - `THR-X04`
  - bundle-level counts changed accordingly from `2` to `3` execution thresholds
- preserve the doctrine:
  - `THR-X03` remains explicitly not-ready until real service quota telemetry exists
  - `THR-X05` remains explicitly not-ready until a real slippage model exists
- latest proofs:
  - targeted execution review/bundle slice: `17 passed`
  - broader execution/protocols/monitoring cross-check: `31 passed`

## Latest `13-C EXECUTION` explicit X03/X05 gap surfacing

- current truth:
  - the execution review no longer silently omits `THR-X03` and `THR-X05`
  - it now exposes the full bounded set:
    - `THR-X01`
    - `THR-X02`
    - `THR-X03`
    - `THR-X04`
    - `THR-X05`
  - the honest current outcome is:
    - `3` ready thresholds: `X01/X02/X04`
    - `2` partial thresholds: `X03/X05`
    - global execution review status: `partial`
- preserve the doctrine:
  - `X03` is partial because service quota telemetry is still missing
  - `X05` is partial because no real slippage model has been implemented yet
- latest proofs:
  - targeted execution review/bundle slice: `17 passed`
  - broader execution/protocols/monitoring cross-check: `31 passed`

## Latest `13-C EXECUTION` X05 input trace enrichment

- current truth:
  - the service-owned execution telemetry artifact now also carries:
    - `candidate_sizes`
    - `final_sizes`
  - those samples are extracted from existing route hints in injected/live evidence
  - the Local IA Lab review contract can now receive future `X05` size traces without inventing a slippage model
- preserve the doctrine:
  - this is evidence-only
  - `X05` remains partial until a real model exists
- latest proofs:
  - targeted execution telemetry/review/bundle slice: `17 passed`
  - broader execution/protocols/monitoring cross-check: `31 passed`

## Latest `13-C EXECUTION` `THR-X03` quota telemetry plumbing

- current truth:
  - the native live time-sync sidecar now also writes bounded quota probe metadata:
    - `rest_call_count`
    - `probe_duration_s`
    - `rest_quota_max_calls_per_minute`
    - `observed_calls_per_minute`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` now preserves those values into the service-owned execution telemetry artifact
  - `src/local_replay_runtime/local_lab_execution_review.py` now distinguishes honest `X03` partial states:
    - telemetry missing
    - quota cap missing
    - history `< 30d`
    - model not implemented
- preserve the doctrine:
  - `X03` is still not ready
  - this slice only removes silent ambiguity around why it is partial
- latest proofs:
  - targeted execution/protocol slice: `20 passed`
  - broader execution/protocols/monitoring cross-check: `32 passed`

## Latest `13-C EXECUTION` bounded `THR-X03/X05` models

- current truth:
  - `src/calibration_methods/execution.py` now contains a real bounded `THR-X03` throttle model:
    - calls/minute telemetry
    - quota cap telemetry
    - Little's-law burst margin
    - hard cap at `80%` of official quota
  - the same module now also contains a first bounded `THR-X05` slippage model:
    - Huber fit on `sqrt(size)`
    - service-owned `final_size` first, else `candidate_size`
    - validation floor `R² >= 0.30`
  - `src/local_replay_runtime/local_lab_execution_review.py` now marks `X03` and `X05` `ready` when aligned 30d evidence exists
- preserve the doctrine:
  - this is still Lab-side calibration/review only
  - no runtime live mutation and no opaque model were introduced
- latest proofs:
  - targeted execution model slice: `21 passed`
  - broader execution/protocols/monitoring cross-check: `35 passed`

## Latest `13-C EXECUTION` runtime handoff projection

- current truth:
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py` now emits a typed handoff artifact for:
    - `rate_limiter` from `THR-X03`
    - `slippage_model` from `THR-X05`
  - `artifact_proof_assessment` and `artifact_release_candidate` now surface that handoff state
  - `run_local_lab_analysis_bundle.py` writes `local_lab_execution_runtime_projection.json`
- preserve the doctrine:
  - still descriptive only
  - still no runtime live mutation
  - still no new promotion shortcut
- latest proofs:
  - targeted projection/proof/release slice: `18 passed`
  - broader execution/protocols/monitoring cross-check: `46 passed`

## Latest `13-C EXECUTION` canonical runtime consumers

- current truth:
  - `src/execution_backbone/rate_limiter.py` now exists as the first bounded canonical consumer of `THR-X03`
  - `src/execution_backbone/slippage_model.py` now exists as the first bounded canonical consumer of `THR-X05`
  - `src/execution_backbone/execution_runtime.py` can consume them only when the caller injects them explicitly
- bounded behavior:
  - `THR-X05` adds conservative slippage friction into `expected_cost` and carries audit metadata on the submitted intent
  - `THR-X03` blocks only when live metadata already exposes `rest_quota_ratio_current >= quota_ratio_ceiling`
  - absent/invalid `THR-X03` telemetry still fails open
- preserve the doctrine:
  - no bootstrap auto-wire yet
  - no live runtime mutation by default
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused runtime-consumer slice: `30 passed`
  - broader execution/protocols/monitoring cross-check: `17 passed`

## Latest `13-C EXECUTION` runtime projection bootstrap

- current truth:
  - `src/protocols/execution_runtime_projection_bridge.py` now exists and loads `local_lab_execution_runtime_projection.json` fail-open
  - `src/protocols/execution_runtime_bootstrap.py` now accepts `execution_runtime_projection_path`
  - canonical runtime consumers `THR-X03/X05` can now be recovered from the Lab artifact by explicit bootstrap, not just manual injection
- preserve the doctrine:
  - no path -> no activation
  - invalid/missing/partial projection -> fail-open
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - projection-bridge/bootstrap focused slice: `36 passed`
  - supporting execution/protocols cross-check: `14 passed`

## Latest `13-C EXECUTION` runtime projection monitoring surface

- current truth:
  - Build-10 monitoring now exposes the new `execution_runtime_projection_path` seam as a typed technical dashboard and observability projection
  - the surface is separate from `execution_no_trade_bridge`, so compiled no-trade bindings and Lab-driven runtime consumers are no longer conflated
- preserve the doctrine:
  - monitoring remains descriptive only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - protocol/backend/runtime/observability/UI focused slice: `91 passed`
  - supporting execution bridge/bootstrap cross-check: `36 passed`

## Latest `13-C EXECUTION` technical dashboard launcher auto-discovers the runtime projection bridge

- current truth:
  - `scripts/run_technical_dashboard.py` now auto-discovers `local_lab_execution_runtime_projection.json` from its demo output directory when present
  - an explicit `--execution-runtime-projection-path` can also be provided for operator-side inspection
- preserve the doctrine:
  - launcher/operator surface only
  - no runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - launcher/ui/backend focused slice: `90 passed`
  - supporting runtime/bridge cross-check: `46 passed`

## Latest `13-C EXECUTION` local replay shadow runner now surfaces the runtime projection bridge

- current truth:
  - `scripts/run_local_replay_shadow.py` now auto-discovers `local_lab_execution_runtime_projection.json` from its output directory when present
  - the same runner also accepts an explicit `--execution-runtime-projection-path`
  - generated baseline and candidate technical payloads now expose the bounded `execution_runtime_projection_bridge` seam for `THR-X03/X05`
- preserve the doctrine:
  - runner/operator surface only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused runner/dashboard slice: `95 passed`
  - supporting runtime/bridge cross-check: `36 passed`

## Latest `13-C EXECUTION` Shadow orchestrator and VPS service now persist the runtime projection seam

- current truth:
  - `scripts/run_shadow_daily_orchestrator.py` now accepts `--execution-runtime-projection-path` and persists the projection ref plus readiness counts in `shadow_daily_orchestrator.last_run.json`
  - `scripts/run_shadow_vps_service.py` now forwards that seam and persists it in service state, runtime evidence bundle, campaign summary, and monitoring payloads
  - Shadow VPS observability now exposes the same seam through bounded projection metrics
- preserve the doctrine:
  - descriptive persistence only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused Shadow orchestrator/service slice: `24 passed`
  - supporting runtime/dashboard cross-check: `108 passed`

## Latest `13-C EXECUTION` Micro-live and Live-Light now carry the runtime projection seam

- current truth:
  - `MicroLiveInput`, `MicroLiveRunSummary`, `LiveLightInput`, and `LiveLightRunSummary` now carry the bounded `execution_runtime_projection_*` seam explicitly
  - Micro-live derives that seam from the governed Shadow technical payload bridge, then Live-Light inherits it from the governed Micro-live summary
  - normalized Build-10 monitoring projections for Micro-live and Live-Light now stay aligned with the same seam
- preserve the doctrine:
  - descriptive propagation only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused protocol/dashboard slice: `82 passed`
  - supporting runner/service/dashboard cross-check: `88 passed`

## Latest `13-C EXECUTION` Micro-live and Live dashboard cards now expose the runtime projection seam

- current truth:
  - Build-12 guardrails cards now show `exec_proj=<status>` plus ready/partial/blocked consumer counts
  - Build-13 readiness cards now show the same bounded seam, using the canonical protocol fields already propagated through Micro-live and Live-Light
- preserve the doctrine:
  - operator visibility only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused dashboard slice: `33 passed`
  - supporting protocol cross-check: `76 passed`

## Latest `13-C EXECUTION` Shadow live startup config can now carry the runtime projection seam

- current truth:
  - `live_websocket_config.json` can now carry `execution_runtime_projection_path_ref`
  - `run_shadow_vps_service.py` resolves that path at startup when no explicit CLI projection path is supplied
  - explicit CLI still overrides config, and the seam remains descriptive only
- preserve the doctrine:
  - startup/config propagation only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused service/live-config slice: `12 passed`
  - supporting monitoring/orchestrator cross-check: `18 passed`

## Latest `13-C EXECUTION` Shadow service now preserves runtime projection provenance

- current truth:
  - Shadow service state, runtime bundle, campaign summary, and monitoring payloads now preserve `execution_runtime_projection_source`
  - current governed values are `cli`, `live_websocket_config`, or `not_configured`
  - the observability export now carries the same source on the bounded projection-ready metric labels
- preserve the doctrine:
  - provenance only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused provenance slice: `8 passed`
  - supporting service/orchestrator cross-check: `22 passed`

## Latest `13-C EXECUTION` Shadow Grafana now renders the runtime projection seam

- current truth:
  - the local Shadow Grafana generator now renders dedicated panels for runtime projection readiness, ready/partial/blocked consumer counts, and the instant `projection_status / projection_source` label surface
  - this closes the remaining observability gap between Prometheus export and Grafana rendering for the `execution_runtime_projection` seam
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused Grafana slice: `2 passed`

## Latest `13-C EXECUTION` Shadow service now keeps runtime projection observability on late telemetry failure

- current truth:
  - once the runtime evidence bundle is written, the Shadow service now persists the `execution_runtime_projection` seam into state before attempting the later execution telemetry sidecar
  - if that later sidecar write fails, monitoring and Prometheus still expose the already-produced runtime projection seam instead of falling back to `not_configured`
- preserve the doctrine:
  - observability hardening only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused failure-hardening slice: `4 passed`

## Latest `13-C EXECUTION` Shadow demo runs now skip missing telemetry sidecars without degrading

- current truth:
  - the Shadow service now falls back to `auto_export_dir` when a governed auto-export exists but `last_run.export_dir_ref` is blank
  - for true demo/replay runs with no governed export, the service now records `execution_telemetry_skipped` instead of degrading the run
  - current dev dual-role Shadow artifacts therefore finish `status=stopped`, `last_error=""`, `execution_telemetry_ref=""`, while keeping `exec_projection=ready@cli`
- preserve the doctrine:
  - honest skip semantics only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused Shadow/monitoring slice: `10 passed`
  - supporting orchestrator/replay cross-check: `16 passed`

## Latest `13-C EXECUTION` Shadow telemetry write/skip status is now visible in monitoring and local Grafana

- current truth:
  - the Build-10 Shadow backend payload now carries `execution_telemetry_status`
  - the detail string now surfaces `exec_telemetry=<status>` alongside `exec_projection=...`
  - the Shadow Prometheus export now emits `v53_shadow_vps_execution_telemetry_ready{telemetry_status=...}`
  - the local Shadow Grafana bundle now renders dedicated telemetry readiness/label panels
- current dev dual-role demo:
  - `shadow_vps_service_monitoring_backend_payload.json` shows `exec_telemetry=skipped`
  - `shadow_vps_service_observability.prom` now carries `v53_shadow_vps_execution_telemetry_ready{telemetry_status="skipped"} 0.0`
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused Shadow/monitoring slice: `10 passed`
  - focused Grafana slice: `2 passed`

## Latest `13-C EXECUTION` Build-10 technical dashboard now exposes Shadow execution telemetry

- current truth:
  - the canonical `ShadowProjection` now carries `execution_telemetry_ref` and `execution_telemetry_status`
  - the live-artifact technical dashboard loader now projects these service-owned fields from `shadow_vps_service.campaign_summary.json`
  - the `Build-11 Shadow` section now renders an explicit `Execution Telemetry` card instead of leaving that seam only in Prometheus/local Grafana
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused Build-10/UI/launcher slice: `74 passed`
  - supporting Shadow monitoring non-regression: `10 passed`

## Latest `13-C EXECUTION` THR-X04 is now a governed runtime consumer

- current truth:
  - `THR-X04` no longer stops at Local IA Lab review; it is now projected as `spread_guard` beside `rate_limiter` and `slippage_model`
  - the projection bridge/bootstrap now load three opt-in execution consumers in fail-open mode
  - the canonical execution runtime blocks on the spread guard only when that model is explicitly present
  - Build-10/Prometheus/dashboard truth now exposes `spread_guard_model_loaded`
  - Shadow, Micro-live, and Live-light preserve the new consumer counts end-to-end
- preserve the doctrine:
  - opt-in only
  - no hidden live activation
  - no Shadow/Micro-live/Live shortcut
- latest proofs:
  - focused THR-X04 runtime slice: `50 passed`
  - supporting rail cross-check: `210 passed`

## Latest `13-C EXECUTION` Build-9 core smoke now carries the execution projection seam

- current truth:
  - the first real non-test launcher that instantiates the execution runtime, [run_build9_core_smoke.py](/E:/claude%20%20v5.3/v53_trading_system/scripts/run_build9_core_smoke.py), now accepts `--execution-runtime-projection-path`
  - the operated smoke bootstrap can therefore prove loading of `rate_limiter + spread_guard + slippage_model` on a real launcher path
  - baseline smoke stays unchanged when no projection is provided
- preserve the doctrine:
  - explicit opt-in only
  - no hidden live activation
  - no gate shortcut
- latest proofs:
  - focused operated-smoke slice: `40 passed`

## Latest `13-C EXECUTION` operated Shadow chain now preserves bridge-load truth

- current truth:
  - the operated Shadow daily/orchestrator seam no longer trusts only the Local IA Lab projection headline; it now derives runtime-readiness from the canonical bridge inspection
  - the Shadow chain now persists `execution_runtime_projection_bridge_status` plus the three load flags `rate_limiter/spread_guard/slippage_model`
  - Shadow VPS runtime-evidence, campaign summary, monitoring payload, and Prometheus export all preserve that bridge truth
  - the local Shadow Grafana bundle now exposes the same bridge truth through dedicated bridge/model-load panels
- preserve the doctrine:
  - no hidden runtime activation
  - no new launcher
  - no gate shortcut
- latest proofs:
  - focused operated-bridge slice: `12 passed`
  - supporting Shadow rail cross-check: `26 passed`
  - focused local Shadow Grafana update: `2 passed`

## Latest `13-C EXECUTION` Build-10 Shadow cards now expose the operated projection bridge truth

- current truth:
  - the canonical `ShadowProjection` now carries the service-owned `execution_runtime_projection_*` bridge/load fields
  - the technical dashboard loader now maps those fields from `shadow_vps_service.campaign_summary.json`
  - `Build-11 Shadow` now renders an explicit `Execution Projection` card, distinct from `Execution Telemetry` and distinct from the top-level execution bridge card
  - the dev dual-role technical dashboard artifacts were regenerated
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no gate shortcut
- latest proofs:
  - focused Build-10 Shadow card slice: `74 passed`

## Latest `Build-14` bounded Opus entry-timing reader

- current truth:
  - `src/complete_enablers/micro_edge_entry_timing_layer.py` now exists as the bounded Build-14 reader for the still-open Opus `entry timing` suggestion
  - it remains a governed Build-14 enabler only; it does not open a new runtime rail and does not trade autonomously
  - `src/complete_enablers/limited_influence.py` now includes this reader in the canonical Build-14 Shadow/post-Shadow influence evaluation
- preserve the doctrine:
  - Build-14 enabler only
  - no hidden live activation
  - no gate shortcut
- latest proofs:
  - focused Build-14 entry-timing slice: `97 passed`

## Latest `Build-14` bounded Opus exit-governor reader

- current truth:
  - `src/complete_enablers/micro_edge_exit_governor.py` now exists as the bounded Build-14 reader for the still-open Opus `exit governor` suggestion
  - it remains a governed Build-14 enabler only; it does not open a new runtime rail and does not trade autonomously
  - `src/complete_enablers/limited_influence.py` now includes this reader in the canonical Build-14 Shadow/post-Shadow influence evaluation
- preserve the doctrine:
  - Build-14 enabler only
  - no hidden live activation
  - no gate shortcut
- latest proofs:
  - focused Build-14 exit-governor slice: `99 passed`

## Latest `regime_lite` typed core

- current code truth:
  - `src/regime_classifier/regime_lite.py` now exists
  - the first cut is intentionally bounded to a typed 3-state helper:
    - `CALM / STRESSED / EXTREME`
    - explicit thresholds object
    - downgrade hysteresis
    - EXTREME cooldown
    - transition trace with no silent state skip
  - `src/regime_classifier/` is now registered in the manifest/DAG as `regime_classifier`
- preserve the doctrine:
  - no hidden runtime activation
  - no direct engine wiring in this slice
  - no gate bypass
- remaining work stays explicit:
  - calibration artifact loading
  - runtime/risk hooks
  - replay proof on historical stress windows

## Latest first governed risk consumer for `regime_lite`

- current code truth:
  - `src/risk_backbone/regime_lite_entry_gate.py` now exists
  - `src/risk_backbone/risk_runtime.py` now exposes an opt-in typed `regime_precheck_hook`
  - the first bounded behavior only blocks new entries while `EXTREME` or while `EXTREME` cooldown is active
- preserve the doctrine:
  - opt-in only
  - fail-open by default
  - no hidden live activation
  - no exit-all wiring in this slice
- latest proofs:
  - focused `regime_lite + risk runtime` slice: `120 passed`

## Latest `regime_lite` calibration loader seam

- current truth:
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

## Latest governed `regime_lite` safing recommendation

- current truth:
  - `src/risk_backbone/regime_lite_safing.py` now exists as the explicit `EXTREME -> safing recommendation` seam
  - `ENTRY_BLOCK_ONLY` is used for cooldown-only states
  - `HALT_RECOMMENDED` + `should_exit_all=True` is used for live `EXTREME` states
  - the helper can materialize a canonical `OperatorSafingRequest(action=set_halted)` when the caller explicitly asks for it
- preserve the doctrine:
  - recommendation only
  - no automatic kill switch trip
  - no hidden activation
- latest proofs:
  - focused `regime_lite + safing` slice: `128 passed`

## Latest Build-10 `regime_lite` safing observability seam

- current truth:
  - `ShadowProjection` now carries a typed `regime_lite` safing projection in Build-10 monitoring
  - the technical dashboard loader now hydrates this seam from `shadow_vps_service.campaign_summary.json` when present
  - `Build-11 Shadow` now renders an explicit `Regime Safing` card
  - canonical observability now exports `v53_shadow_regime_lite_safing_status`
- preserve the doctrine:
  - recommendation only
  - no auto-`set_halted`
  - no hidden live activation
- latest proofs:
  - focused `Build-10 regime_lite observability` slice: `85 passed`

## Latest `regime_lite` governed protocol-summary propagation

- current truth:
  - `RegimeLiteGovernanceSummary` now exists in canonical protocol contracts
  - `run_shadow_validation(...)` can emit explicit governed regime truth when supplied with typed assessment/recommendation inputs
  - `build_micro_live_input_from_shadow(...)` and `build_live_light_input_from_micro_live(...)` now preserve that truth without extra inference
- preserve the doctrine:
  - explicit producer only
  - no fabricated classifier inputs
  - recommendation only
  - no hidden activation
- latest proofs:
  - focused `protocol regime_lite propagation` slice: `142 passed`

## Latest operated `regime_lite` service-summary propagation

- current truth:
  - `shadow_daily_orchestrator.last_run.json` now persists flattened `regime_lite_governance` truth from the operated `shadow_summary`
  - `ShadowVpsRuntimeEvidenceBundle` and `ShadowVpsCampaignSummary` now preserve that seam through the real Shadow VPS service rail
  - service monitoring now exposes the seam in payload/detail and Prometheus via:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
- preserve the doctrine:
  - copy operated Shadow truth only
  - no synthetic regime inference inside the service
  - recommendation only
  - no hidden auto-halt
- latest proofs:
  - focused `orchestrator + service + monitoring regime_lite` slice: `13 passed`

## Latest operated `regime_lite` Shadow producer seam

- current truth:
  - `run_local_replay_shadow.py` now accepts explicit typed `regime_lite` assessment/recommendation JSON inputs
  - the daily orchestrator and the real Shadow VPS service now forward that seam end-to-end
  - when the seam is supplied, the operated artifacts carry real `regime_lite_governance_status=ready` instead of staying protocol-only
- preserve the doctrine:
  - explicit opt-in only
  - no synthetic classifier inputs
  - recommendation only
  - no hidden auto-halt
- latest proofs:
  - focused `local_replay_shadow -> orchestrator -> service regime_lite` slice: `8 passed`

## Latest governed `regime_lite` auto-discovery seam

- current truth:
  - `run_local_replay_shadow.py` now auto-discovers `regime_lite_assessment.json` and `regime_lite_safing_recommendation.json` inside its governed `output_dir`
  - the daily orchestrator therefore picks up the same seam automatically when those sidecars are staged inside the governed `shadow_output_dir`
- preserve the doctrine:
  - explicit path still wins
  - typed sidecars only
  - recommendation only
  - no hidden auto-halt
- latest proofs:
  - focused `regime_lite auto-discovery` slice: `2 passed`

## Latest local Shadow Grafana `regime_lite` panels

- current truth:
  - the local Shadow Grafana dashboard now includes dedicated panels for:
    - entries blocked
    - exit-all recommended
    - regime_lite labels
  - the dashboard reads only the bounded Prometheus service metrics:
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
    - `v53_shadow_vps_regime_lite_safing_status`
- preserve the doctrine:
  - monitoring-only seam
  - no dashboard-only JSON inference
  - no hidden activation
- latest proofs:
  - focused `local shadow grafana regime_lite` slice: `4 passed`

## Latest Shadow VPS `regime_lite` config-ref seam

- current truth:
  - `ShadowLiveWebSocketConfig` now supports:
    - `regime_lite_assessment_path_ref`
    - `regime_lite_safing_recommendation_path_ref`
  - `run_shadow_vps_service.py` resolves those refs with explicit CLI precedence, then persists the chosen refs/sources into:
    - service state
    - runtime evidence bundle
    - campaign summary
    - monitoring payload
- preserve the doctrine:
  - typed refs only
  - explicit path still wins
  - no synthetic regime inference
  - no hidden auto-halt
- latest proofs:
  - focused `shadow_vps_service + monitoring regime_lite provenance` slice: `12 passed`

## Latest Shadow VPS Prometheus `regime_lite` provenance labels

- current truth:
  - the bounded service metrics now expose:
    - `assessment_source`
    - `safing_source`
    labels for the `regime_lite` seam
  - the monitoring detail string also carries the same provenance summary
- preserve the doctrine:
  - bounded labels only
  - no dashboard-only seam
  - no runtime behavior change
- latest proofs:
  - focused `shadow monitoring provenance labels` slice: `2 passed`

## Latest Build-10 `regime_lite` provenance detail

- current truth:
  - the canonical technical dashboard now preserves and renders:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
    from the operated Shadow service campaign summary
  - the Build-11 Shadow `Regime Safing` card therefore keeps the governed ref/source seam visible instead of collapsing it to severity-only
- preserve the doctrine:
  - dashboard consumes operated artifact truth only
  - no dashboard-side inference
  - recommendation only
- latest proofs:
  - focused `Build-10 regime_lite provenance detail` slice: `37 passed`

## Latest Binance Shadow PowerShell bootstrap

- current truth:
  - `scripts/Install-BinanceApiEnv.ps1` now installs the Binance API env in process scope and, when requested, user scope
  - `scripts/Start-BinanceShadowLiveCampaign.ps1` now materializes the governed campaign root, launches one bounded Shadow service cycle, and re-renders the canonical HTML dashboard
  - user-scope Binance env is now installed on this Windows operator machine, so new terminals can reuse the same bootstrap without re-pasting secrets
- preserve the doctrine:
  - Shadow only
  - no secrets written into repo JSON
  - dashboard remains read-only
- latest proofs:
  - focused `PowerShell Binance bootstrap` slice: operator scripts exercised successfully

## Latest native Binance live connect diagnostic

- current truth:
  - the native live websocket capture path now preserves endpoint + root cause when connect fails
  - the previously observed `WinError 10013` was confirmed to be a Codex sandbox network artifact, not a host Windows firewall/policy issue
  - the same bounded PowerShell live campaign succeeds when launched outside the sandbox on the real host
- preserve the doctrine:
  - diagnostics only
  - no hidden retry or behavior change
- latest proofs:
  - focused `shadow live websocket diagnostics` slice: included in the `44 passed` targeted test run

## Latest successful Binance Shadow operated campaign

- current truth:
  - the bounded PowerShell launcher now succeeds on the real Windows host against native Binance streaming
  - current operated artifacts show:
    - `last_completed_session_date=2026-04-12`
    - `service_status=stopped`
    - `last_error=""`
    - `execution_telemetry_status=written`
    - `live_user_data_authenticated=true`
    - `live_capture_pair_scope=[BTCUSDT, ETHUSDT]`
  - the canonical Build-10 HTML dashboard has been regenerated from that successful operated campaign root
- preserve the doctrine:
  - Shadow only
  - no live order path
  - dashboard remains read-only

## Latest `daily_pnl_breaker` typed core and first governed runtime consumer

- current truth:
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

## Latest `reconciliation_scheduler` bounded operated seam

- current truth:
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now exists
  - the scheduler now loads governed `THR-I04`, enforces bounded interval limits, and exposes typed `boot_reconcile(...)` + `run_periodic_if_due(...)`
  - boot reconciliation now has an explicit blocking seam for unresolved divergences
  - periodic reconciliation now has an explicit due/not-due seam and can trip the canonical circuit breaker on critical divergence
- preserve the doctrine:
  - no hidden background loop in this slice
  - explicit caller ownership of timing
  - reuse the canonical `EmergencyCircuitBreaker`
  - no bypass of the existing reconciliation runtime
- latest proofs:
  - focused `reconciliation_scheduler + reconciliation_layer` slice: `35 passed`
  - focused `execution_runtime cross-check` slice: `28 passed`

## Latest `execution_runtime_bootstrap` operated boot caller for `THR-I04`

- current truth:
  - `src/protocols/execution_runtime_bootstrap.py` now exposes typed bootstrap bundles:
    - `ExecutionRuntimeBootstrapBundle`
    - `build_execution_runtime_bootstrap_bundle(...)`
    - `build_binance_execution_runtime_bootstrap_bundle(...)`
  - the existing bootstrap helpers remain backward-compatible and still return only `ExecutionRuntime`
  - the bundle now exposes optional bounded `reconciliation_scheduler` + `reconciliation_boot_result`
  - stale-only first boot with zero divergences is now treated as initial baseline establishment, not as a false trading block
  - `scripts/run_build9_core_smoke.py` is now the first real operated caller of this seam and can also load governed `THR-I04` from an optional calibration root
- preserve the doctrine:
  - opt-in only
  - no hidden loop
  - no fake Shadow/service integration before a real runtime caller exists
  - Build-9 smoke remains the first operated seam on this path
- latest proofs:
  - focused `execution runtime bootstrap + Build-9 smoke + reconciliation scheduler` slice: `20 passed`
  - focused `execution runtime cross-check` slice: `48 passed`

## Latest standalone Build-9 smoke alignment

- current truth:
  - `scripts/run_build9_core_smoke.py` now imports the canonical engine facades through `engines.engine_a` and `engines.engine_b`
  - the same script now passes the explicit Build-8 portfolio `freshness_policy` required by the current `OrchestratorConfig`
  - the standalone operated report now reaches:
    - Build-2..9 `PASS`
    - engine chain `PASS`
    - portfolio chain `PASS`
    - execution bootstrap `PASS`
  - the remaining direct-run failure is upstream of this slice: Build-1 still reports pre-existing DAG violations
- preserve the doctrine:
  - no new launcher
  - no fake alias package
  - canonical facades and typed config only
- latest proofs:
  - focused `Build-9 smoke script + execution bootstrap` slice: `21 passed`
  - direct `python scripts/run_build9_core_smoke.py` now fails only on Build-1 DAG debt

## Latest Build-1 DAG debt reduction

- current truth:
  - the canonical manifest/build registries now include the real on-disk packages:
    - `calibration_methods`
    - `secrets_manager`
    - `sharia_compliance`
    - `venue_adapters`
  - the dependency registry now authorizes the non-cyclic imports already present on disk for `execution_backbone`, `risk_backbone`, `scoring_backbone`, `local_replay_runtime`, `backtest_artifact_import`, `protocols`, and `venue_adapters`
  - the mixed Build-1 DAG report has been reduced from `47` errors to `27`
  - the remaining debt is now mostly real cycle/forward-edge debt, not missing-manifest drift
- preserve the doctrine:
  - no DAG validator weakening
  - no cycle authorization just to force Build-1 green
  - Build-1 module count remains unchanged
- latest proofs:
  - focused `manifest registry` slice: `83 passed`
  - direct `dag_validator` report: `27` errors
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator`

## Latest Build-1 monitoring seam reduction

- current truth:
  - Local IA Lab monitoring builders now live in `monitoring`, not `local_replay_runtime`
  - `run_local_lab_analysis_bundle.py` now passes primitive release/bridge/promotion facts into that monitoring seam
  - the old `local_replay_runtime` monitoring builder files were removed, not wrapped
  - the `local_replay_runtime -> monitoring` unauthorized imports are gone from the DAG report
  - Build-1 blocking debt is now `23` real errors:
    - `4` cycles
    - `19` unauthorized imports
- preserve the doctrine:
  - no fake alias package
  - no validator weakening
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - focused `Local Lab monitoring seam` slice: `23 passed`
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator (23 error(s))`

## Latest Build-1 replay/protocol seam reduction

- current truth:
  - the replay workflow loader now lives under `local_replay_runtime`, not `monitoring`
  - injected websocket frame loading now lives under `data_backbone.websocket_gateway`
  - the `local_replay_runtime -> protocols` edge in the execution telemetry artifact path is gone
  - Build-1 blocking debt is now `19` real errors:
    - `3` cycles
    - `16` unauthorized imports
- preserve the doctrine:
  - no wrapper alias to preserve the old seam
  - no validator weakening
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - focused `replay/protocol seam` slice: `36 passed`
  - direct `python scripts/run_build9_core_smoke.py` still fails only on Build-1 `dag_validator (19 error(s))`

## Latest Build-1 DAG closure

- current code truth:
  - the last execution-layer upward edges are gone
  - `ExecutionRuntime` now consumes the canonical fee-aware edge helper from `execution_backbone`, not `scoring_backbone`
  - `ReconciliationScheduler` now consumes the canonical circuit breaker from `execution_backbone`, not `risk_backbone`
  - the former scoring/risk entrypoints remain as compatibility surfaces over the execution-owned implementations
  - the temporary dependency-registry allowances for `execution_backbone -> risk_backbone/scoring_backbone` were removed
  - Build-1 now passes with `0` blocking DAG errors
- preserve the doctrine:
  - no validator weakening
  - no fake green via broad registry exceptions
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - focused `execution/risk/scoring compatibility` slice: `168 passed`
  - focused `manifest/build-order/dependency/layer` slice: `96 passed`
  - direct `dag_validator` report: `0` blocking errors
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest `gatekeeper` canonical execution convergence

- current code truth:
  - `src/execution_backbone/gatekeeper/gatekeeper.py` now exists as the canonical Build-3 convergence wrapper
  - `ExecutionRuntime.submit_opportunity(...)` now routes its pre-submit decision chain through `ExecutionGatekeeper.authorize(...)`
  - the existing execution guards are still the real underlying checks; the gatekeeper only centralizes their decision into a typed `ExecutionPermit` / `ExecutionRefusal`
  - refusals now preserve the real `pair` and `engine_id`
  - `ExecutionSubmission` now carries `gate_trace`, and the same trace is emitted in structured runtime logs
- preserve the doctrine:
  - no parallel execution path
  - no guard removal
  - COMPLETE-only doctrine unchanged
  - persisted `artifacts/gatekeeper/` audit storage is still not implemented
- latest proofs:
  - focused `gatekeeper + execution runtime + execution runtime bootstrap` slice: `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest `info_stress_monitor` bounded risk seam

- current code truth:
  - `src/risk_backbone/info_stress_monitor.py` now exists as the bounded V37-3 detector
  - the first governed implementation classifies `NORMAL / ELEVATED / EXTREME` from five simple signals:
    - spread explosion
    - depth ratio collapse
    - cancellation spike
    - taker imbalance saturation
    - micro-vol divergence
  - `build_info_stress_entry_gate(...)` now exposes a typed `RiskInfoStressPrecheckHook`
  - `RiskRuntime` now accepts that dedicated hook and blocks entries during an EXTREME cooldown when the hook is injected explicitly
- preserve the doctrine:
  - opt-in only
  - no Shadow/Micro-live/Live auto-wiring yet
  - no full MAS/ML layer; bounded lite seam only
- latest proofs:
  - focused `info_stress_monitor + risk_runtime` slice: `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest `info_stress` late-stage protocol propagation

- current code truth:
  - `src/protocols/contracts.py` now defines `InfoStressGovernanceSummary`
  - `run_shadow_validation(...)` now accepts an optional `info_stress_assessment` and projects it into `shadow_summary.info_stress_governance`
  - `build_micro_live_input_from_shadow(...)` and `run_micro_live_gate(...)` now preserve that summary unchanged
  - `build_live_light_input_from_micro_live(...)` and `run_live_light_gate(...)` now preserve the same summary unchanged
- preserve the doctrine:
  - protocol propagation only
  - no launcher/service/config auto-wiring yet
  - no monitoring/dashboard work in this slice
  - assessment-only seam; no fake recommendation layer added
- latest proofs:
  - focused `protocol contracts + shadow + micro-live + live-light` slice: `147 passed`
  - focused `info_stress_monitor + risk_runtime` slice: `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest `info_stress` operated Shadow propagation

- current code truth:
  - `run_local_replay_shadow.py` now accepts and auto-discovers `info_stress_assessment.json`
  - `run_shadow_daily_orchestrator.py` now persists `info_stress_governance_status`, `level`, `alert_count`, `entries_blocked`, `entries_blocked_until_ts`, `reason_codes`, and `detail`
  - `run_shadow_vps_service.py` now resolves `info_stress_assessment` from CLI first, then `live_websocket_config.info_stress_assessment_path_ref`
  - the Shadow VPS service now persists `info_stress` ref/source into state, runtime bundle, campaign summary, monitoring payload, and observability export
  - monitoring now exposes the assessment-only seam via dedicated Prometheus samples
- preserve the doctrine:
  - assessment-only seam remains intact
  - no fake safing layer
  - no hidden Shadow/Micro-live/Live automation
- latest proofs:
  - focused `runner + orchestrator + service + monitoring` slice: `39 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest `gatekeeper` persisted audit store on the canonical execution rail

- current code truth:
  - `src/execution_backbone/gatekeeper/audit_logger.py` now exists as the append-only JSONL logger for canonical gatekeeper decisions
  - `ExecutionRuntime.submit_opportunity(...)` now writes gatekeeper audit records when a `GatekeeperAuditLogger` is injected
  - `execution_runtime_bootstrap.py` now accepts `gatekeeper_audit_path`
  - `run_build9_core_smoke.py` now accepts `--gatekeeper-audit-path` and can materialize `artifacts/gatekeeper/audit.jsonl`
- preserve the doctrine:
  - no new runtime path outside canonical Build-3
  - no dashboard-first expansion for this slice
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `gatekeeper + execution_runtime + bootstrap + build9 smoke` slice: `51 passed`
  - direct `python scripts/run_build9_core_smoke.py --gatekeeper-audit-path build/build9_core_smoke_run/artifacts/gatekeeper/audit.jsonl`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest `log_rotation` bounded monitoring seam

- current code truth:
  - `src/monitoring/log_rotation.py` now exists
  - `rotate_log_file(...)` performs timestamped gzip rotation plus retention pruning on one operated log file
  - `monitoring.__init__` now exports the rotation helper
- preserve the doctrine:
  - bounded helper only, no daemon or hidden scheduler
  - no Telegram wiring yet
  - no new package/profile semantics
- latest proofs:
  - focused `log_rotation + disk_monitor + execution audit slice`: `55 passed`

## Latest bounded `telegram_alerter` adapter

- current code truth:
  - `src/alerting/{__init__,telegram_alerter}.py` now exists as a bounded external alert delivery package
  - it accepts canonical `AlertRecord` values, applies severity filtering, formats bounded plain-text Telegram payloads, and can load sealed config via `secrets_manager`
  - `manifest_registry` now registers `alerting` as a canonical Build-11 module, so the package no longer sits outside the manifest
- preserve the doctrine:
  - no hidden integration into `monitoring_runtime` yet
  - no daemon or retry service
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - focused `alerting + manifest + layer DAG` slice: `126 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest operated Telegram alert seam on the Shadow VPS service

- current code truth:
  - `src/protocols/shadow_vps_service_telegram_alerting.py` now projects selected operated `ShadowVpsServiceEvent` values into canonical `AlertRecord`
  - `scripts/run_shadow_vps_service.py` now accepts optional Telegram config/key paths and sends opt-in alerts from the service rail
  - every successful or failed delivery is audited in `shadow_vps_service.events.jsonl` as `telegram_alert_sent` / `telegram_alert_failed`
- preserve the doctrine:
  - no Build-10 forward dependency into `alerting`
  - no hidden background sender
  - Telegram delivery failure stays fail-open for the service
- latest proofs:
  - focused `protocols + alerting + manifest layer` slice: `43 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest operated Telegram monitoring seam on the Shadow VPS service

- current code truth:
  - the service state, campaign summary, and monitoring payload now persist the last Telegram delivery truth as `telegram_alert_delivery_status / event_type / error`
  - `run_shadow_vps_service.py` now updates that truth on each bounded delivery attempt and rewrites the final summary + monitoring artifacts after `service_stopped`
  - Prometheus export now exposes `v53_shadow_vps_telegram_alert_delivery_status`
- preserve the doctrine:
  - still no Build-10/dashboard-first expansion
  - still no retry daemon or hidden sender loop
  - the seam remains last-state only, backed by operated service truth
- latest proofs:
  - focused `telegram seam + monitoring` slice: `17 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest Build-10 projection of the Shadow Telegram seam

- current code truth:
  - `run_technical_dashboard.py` now hydrates the last Telegram delivery truth from `shadow_vps_service.campaign_summary.json`
  - `technical_dashboard_view.py` now renders a dedicated `Telegram Alerts` card in `Build-11 Shadow`
  - the regenerated local Build-10 artifact for `build11_live_websocket_campaign` now shows the same operated Telegram seam already exposed in Prometheus
- preserve the doctrine:
  - projection only, no new alerting logic
  - no Grafana-first expansion
  - last-state only, still backed by service truth
- latest proofs:
  - focused `launcher + view + monitoring backend` slice: `77 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest local Grafana + operated Telegram config provenance seam

- current code truth:
  - the local Shadow Grafana bundle now contains `Telegram Alerts` and `Telegram Alert Labels`
  - the operated Shadow service now resolves Telegram config/key refs from `live_websocket_config` with CLI override preserved
  - service state, runtime evidence, campaign summary, monitoring payload, and Prometheus now persist the Telegram config provenance seam
- preserve the doctrine:
  - projection only on Grafana, no new alerting daemon
  - operated precedence remains `cli > live_websocket_config > not_configured`
  - still no hidden runtime activation
- latest proofs:
  - focused `local_grafana + monitoring + launcher` slice: `21 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest operated execution runtime bootstrap monitoring seam

- current code truth:
  - the operated Shadow service now persists bootstrap reconcile truth beyond `ref/status/source`: `executed`, `trading_blocked`, `circuit_breaker_tripped`, `recovery_action`, and `divergence_count`
  - canonical Shadow monitoring/Prometheus now exposes that seam through `v53_shadow_vps_execution_runtime_bootstrap_status`, `..._divergence_count`, and `..._trading_blocked`
  - the canonical Build-10 `Build-11 Shadow` section now renders a dedicated `Execution Bootstrap` card backed by the service campaign summary
- preserve the doctrine:
  - no new bootstrap runtime behavior
  - no daemon/retry path, no hidden order flow
  - Build-10 remains projection-only over service truth
- latest proofs:
  - focused `shadow monitoring + technical dashboard + launcher` slice: `56 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest Build-1 executable engineering guardrails baseline

- current code truth:
  - `smoke_bootstrap_recovery` now runs a real repo-wide engineering guardrail scan as part of Build-1 sanity, derived from `CODEX_PROMPT.md`
  - `scripts/run_engineering_guardrails.py` now writes `build/engineering_guardrails/engineering_guardrails.report.json` and `.summary.txt`
  - accepted legacy drift is frozen in `config/engineering_guardrails_baseline.json`, so Build-1 now blocks only net-new guardrail regressions instead of failing on the entire historical repo
- preserve the doctrine:
  - no repo-wide blind rewrite
  - no bypass of the Build-1 foundation rail
  - hotspots are surfaced explicitly for surgical follow-up
- latest proofs:
  - repo-wide baseline scan: `826` Python files, `4363` accepted legacy violations
  - normal guardrail run: `new_violations=0`
  - focused Build-1 guardrail suite: `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest first operated hotspot reduction under executable guardrails

- current code truth:
  - `scripts/run_shadow_vps_service.py` is no longer carrying untyped loader helpers, bare `print()` calls, or the previous bare `except Exception:` on the execution telemetry write path
  - parser construction is now decomposed into typed `_build_argument_parser(...)` and `_add_*_arguments(...)` helpers
  - the service final output is now emitted through a dedicated CLI-output helper instead of inline prints
- preserve the doctrine:
  - no service-loop semantic drift
  - no bypass of the operated Shadow rail
  - only the hotspot surface was reduced; the remaining large monoliths stay explicit and visible
- latest proofs:
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`
  - repo-wide guardrail total reduced from `4363` to `4341`
  - `scripts/run_shadow_vps_service.py` reduced from `26` to `4` residual guardrail violations

## Latest second operated hotspot reduction under executable guardrails

- current code truth:
  - `scripts/run_shadow_vps_service.py` now materializes `ShadowVpsCampaignSummary` through grouped field-builders instead of one monolithic inline constructor
  - `_write_campaign_summary(...)` is now a thin typed wrapper over `core`, `live_capture`, `execution`, `regime`, and `info_stress` builders
  - the helper decomposition keeps the exact summary schema and defaults while removing the previous function-length violation
- preserve the doctrine:
  - no service-loop semantic drift
  - no artifact/schema rename
  - remaining debt stays explicit: `FILE_TOO_LONG`, `_write_runtime_evidence_bundle(...)`, `run_shadow_vps_service(...)`
- latest proofs:
  - repo-wide guardrail run: `total_violations=4340`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

## Latest third operated hotspot reduction under executable guardrails

- current code truth:
  - `scripts/run_shadow_vps_service.py` now builds `ShadowVpsRuntimeEvidenceBundle` through grouped typed builders instead of one monolithic inline constructor
  - `_write_runtime_evidence_bundle(...)` is now a thin wrapper over `input`, `execution`, `projection`, `regime_lite`, `info_stress`, and artifact-ref builders
  - `last_run` conversions are centralized via typed helper functions, keeping the durable runtime schema unchanged
- preserve the doctrine:
  - no service-loop semantic drift
  - no artifact/schema rename
  - remaining debt on the file is now narrowed to `FILE_TOO_LONG` plus `run_shadow_vps_service(...)`
- latest proofs:
  - refreshed guardrail baseline, then steady-state run: `total_violations=4339`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest fourth operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_shadow_vps_service.py` public entrypoint is now a thin orchestrator over startup, main-loop, finalize, and output helpers
  - the remaining newly introduced builder overage was reduced with small extraction helpers, so the guardrail run is back to zero new debt
  - remaining explicit debt on this file is now only `FILE_TOO_LONG`
- preserve the doctrine:
  - no semantic drift in the Shadow operated rail
  - no artifact/schema rename
  - no monitoring field loss
- latest proofs:
  - repo-wide guardrail run: `total_violations=4338`, `new_violations=0`
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest fifth operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_local_replay_shadow.py` no longer keeps the governed LOCAL_REPLAY -> SHADOW export path inline inside one monolithic runner body
  - import-context, import materialization, runtime bundle, session-day recording, demo payload, and per-engine Shadow evaluations are now all routed through typed helpers
  - the file-local guardrail debt on this hotspot dropped from `22` to `1`; the only residue is now `FILE_TOO_LONG`
- preserve the doctrine:
  - no artifact/schema rename
  - no session-summary or evidence-contract drift
  - no hidden runtime behavior change on the governed Shadow rail
- latest proofs:
  - repo-wide guardrail run: `total_violations=4316`, `new_violations=0`
  - focused `local replay shadow runner` slice: `18 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest sixth operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_local_replay_shadow.py` is now only the CLI/public facade; the governed runner internals were split into bounded support modules for models/recovery, engines, payloads, import pipeline, and runtime/session pipeline
  - the split preserves the same public API (`main`, `export_local_replay_shadow_run`, `LocalReplayShadowArtifacts`) and the same governed sidecar/session artifacts
  - all newly split files are now at `0` local guardrail violations; the previous file-length debt on the original runner is fully removed
- preserve the doctrine:
  - no artifact/schema rename
  - no hidden runtime behavior change on the LOCAL_REPLAY -> SHADOW operated rail
  - no bypass of canonical Shadow governance
- latest proofs:
  - repo-wide guardrail run: `total_violations=4315`, `new_violations=0`
  - focused `local replay shadow runner` slice: `18 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`

Latest seventh operated hotspot reduction under executable guardrails:

- current code truth:
  - `scripts/run_local_lab_analysis_bundle.py` no longer emits inline CLI `print()` calls at the end of the Local IA Lab chain
  - operator output now flows through a single bounded `_emit_local_lab_analysis_bundle_output(...)` helper, preserving the same artifact refs and terminal surface
  - hotspot-local debt dropped from `30` to `2`; the remaining debt is only `FILE_TOO_LONG` plus the still-monolithic `main(...)`
- preserve the doctrine:
  - no Local IA Lab artifact/schema drift
  - no behavior change in the chained review/calibration/replay/monitoring pipeline
  - no UI-only diversion
- latest proofs:
  - repo-wide guardrail run: `total_violations=4287`, `new_violations=0`
  - focused `local_lab_analysis_bundle launcher` slice: `7 passed`
