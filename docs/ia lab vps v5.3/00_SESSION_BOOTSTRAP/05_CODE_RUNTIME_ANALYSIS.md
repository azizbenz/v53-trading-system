# Code Runtime Analysis

This file is a code-based understanding of the real V5.3 runtime paths.

It is built from readable code in `src/`, not from memory.

## 1. Core trading chain actually implemented

The core Build-3 -> Build-9 flow is not one monolithic runtime.
It is a typed DAG of bounded runtimes and audit surfaces.

### Execution backbone

File:
- `src/execution_backbone/execution_runtime.py`

Role:
- receives validated execution opportunities
- builds execution intents
- applies execution guards and no-trade vetoes
- submits or replaces orders through an injected venue adapter
- processes venue events
- aggregates fills, latency, and costs
- reconciles orders, fills, and positions

Important reality:
- execution is adapter-driven but end-to-end executable
- default governed profile has already moved to `COMPLETE`

### Binance venue adapter foundation

Files:
- `src/venue_adapters/binance_spot/rest_client.py`
- `src/venue_adapters/binance_spot/time_sync.py`
- `src/venue_adapters/binance_spot/ws_client.py`
- `src/venue_adapters/binance_spot/orderbook_manager.py`
- `src/venue_adapters/binance_spot/order_translator.py`
- `src/venue_adapters/binance_spot/error_classifier.py`

Role:
- provide the bounded Binance Spot adapter rail for P0
- keep read-only market-data/bootstrap surfaces separated from later order-submission surfaces
- translate governed execution intents into typed venue requests

Important reality:
- `THR-X01` is now really consumed through `calibration_loader` on the adapter rail
- `THR-X02` now has a real order-book / websocket consumer with explicit stale/resync semantics
- signed `POST /api/v3/order`, signed `GET /api/v3/openOrders`, and signed `DELETE /api/v3/order` now exist in the REST client and are mock-tested locally
- `execution_adapter.py` now provides a bounded `ExecutionVenueAdapter` implementation on top of that REST client
- `user_data_events.py` now provides a bounded authenticated user-data event source and `executionReport` parser
- `user_data_ws_client.py` now provides a bounded authenticated websocket client for `userDataStream.subscribe.signature`
- `bootstrap.py` now provides a bounded builder from `BinanceAdapterConfig + credentials`, with optional injection of that websocket source
- `src/protocols/execution_runtime_bootstrap.py` now consumes that builder via `build_binance_execution_runtime(...)`
- `scripts/run_build9_core_smoke.py` now consumes that runtime bootstrap on a bounded local smoke path
- replace is now modeled explicitly as cancel + submit on this rail
- remote-state reconciliation now has a minimal live bridge through `openOrders + account snapshot`
- `poll_order_events()` now drains that bounded source when injected
- deterministic `clientOrderId` now uses `engine_id + intent_id`, because the governed repo contract carries `engine_id`, not `strategy_id`
- this is still a bounded foundation slice, not a full live execution adapter:
  - no real Testnet submit proof yet
  - live fills/rejections/cancellations are not yet flowing from Binance events into `ExecutionRuntime`

### Risk backbone

### Sharia compliance

Files:
- `src/sharia_compliance/contracts.py`
- `src/sharia_compliance/policy_loader.py`
- `src/sharia_compliance/asset_whitelist.py`
- `src/sharia_compliance/asset_blacklist.py`
- `src/sharia_compliance/stablecoin_policy.py`
- `src/sharia_compliance/trade_type_guard.py`
- `src/sharia_compliance/pair_screening.py`
- `src/sharia_compliance/pair_screening_registry.py`
- `src/sharia_compliance/pair_screening_audit.py`
- `src/sharia_compliance/purification_calculator.py`
- `src/sharia_compliance/policy_audit_logger.py`
- `src/sharia_compliance/account_features_audit.py`
- `src/sharia_compliance/sharia_alerts.py`
- `src/sharia_compliance/sharia_runtime.py`
- `src/venue_adapters/binance_spot/account_feature_provider.py`
- `scripts/run_sharia_account_audit.py`

Role:
- provide the bounded halal policy gate before any venue submit
- load a versioned spot-halal policy from YAML
- produce explicit permit/reject decisions plus append-only audit traces
- estimate purification for incidental revenue and stablecoin reserve exposure
- detect forbidden account-feature usage deterministically from weekly audit inputs

Important reality:
- `config/sharia/policy_v1.yml` now carries the active conservative spot-halal policy root
- `src/execution_backbone/execution_runtime.py` now calls `sharia_trade_authorizer.authorize_trade()` before any venue submit
- `NoTradeReason.SHARIA_BLOCKED` now exists on the execution runtime rail
- `purification_calculator.py` now resolves `THR-H03` through `calibration_loader` for stablecoin reserve estimates
- `account_features_audit.py` now resolves `THR-H02` through `calibration_loader` and scans deterministic forbidden endpoint/balance evidence
- `account_feature_provider.py` now gives the weekly audit a bounded Binance read-only provider path via whitelisted signed GET calls
- `run_sharia_account_audit.py` now gives the slice a bounded launcher path that writes a typed JSON report
- `run_sharia_pair_screening_audit.py` now gives the slice a bounded HC-4 launcher path for traded-pair screening checks against a versioned local registry
- `sharia_alerts.py` now projects audit findings into typed `AlertRecord` CRITICAL alerts
- `trade_type_guard.py` now enforces deterministic AAOIFI pair-screening from `opportunity.metadata["pair_screening"]`, with explicit fail-close reasons for invalid, missing, mismatched, or failed screening evidence
- this is still not the full T5 layer:
  - no real Testnet proof yet for the weekly audit launcher
  - no kill switch or external alert backend is wired from the emitted `AlertRecord`s yet
  - no live/external provider is wired yet to feed AAOIFI pair-screening snapshots automatically; the bounded local dataset registry now exists

### Risk backbone

File:
- `src/risk_backbone/risk_runtime.py`

Role:
- evaluates a candidate against gross cap, loss cap, beta cap, cluster cap, and drawdown state
- emits structured reason details and explainability
- computes market-physics style pressure scores through `data_backbone.market_physics_math`

Important reality:
- risk is not a boolean guard only
- it produces an action surface: `accept`, `reject`, `reduce_exposure`, `observe_only`
- drawdown `REDUCE_EXPOSURE` is already enforced on the active risk runtime rail, not left as advisory metadata only
- beta governance is now explicit and time-bounded on the active risk rail: no universal fallback beta, and stale pair-beta mappings fail closed before projection/cap acceptance
- Engine A and Engine B now share the same governed market-physics penalty weights for `fragility`, `toxicity`, and `micro_friction`; engine diversification remains in positive signal structure, not in tolerance to the same physical stress

### Data backbone pair-health control

File:
- `src/data_backbone/pair_health_scorer/suspension_decider.py`

Role:
- decides whether a pair must be suspended from health, hard staleness, or consistency failure
- exposes the explicit operator intervention path for emergency manual suspension

Important reality:
- `SuspensionReason.MANUAL` is now guarded by `suspend_manual()`, not by silent ad hoc model construction
- manual suspension requires both `operator_id` and `reason_text`, and both are embedded in the audit trail
- the generic `evaluate_suspension()` path still cannot emit `MANUAL`
- health-based suspension no longer hides a universal `threshold=0.3`; callers must now provide an explicit threshold for that path

### Data backbone REST bootstrap gap fill

File:
- `src/data_backbone/rest_bootstrap/gap_fill_controller.py`

Role:
- decides whether a historical market-data gap is small enough to be filled via REST
- keeps REST bootstrap as a bounded recovery path instead of a silent real-time substitute

Important reality:
- `evaluate_gap_fill()` now fails closed on `gap_size <= 0.0`
- negative or zero gaps are treated as inverted timestamps / clock reversal, not as fillable history
- the normal positive-gap boundary semantics remain unchanged
- the resync runtime now reserves quota atomically through `record_call()`, so a post-check rate-limit failure no longer falls through to `fill_gap()`
- the underlying rate-limit guard now prunes in place on a deque instead of reallocating a filtered list on each check

### Scoring backbone

File:
- `src/scoring_backbone/scoring_runtime.py`

Role:
- selects allowed features
- computes raw score
- applies score and size penalties
- evaluates hard blockers
- ranks candidates
- resolves selection
- emits explainability and economics projections

Important reality:
- scoring is a full round on a candidate set, not a single scalar
- the output is an auditable `ScoringRoundResult` with per-candidate audits
- phantom-risk comparison now requires a positive `expected_cost` baseline in `penalty_cap_guard`
- `expected_cost <= 0.0` is treated as missing economics context rather than as a valid phantom trigger
- unknown portfolio clusters now fail closed as explicit mapping errors in `portfolio_compatibility_checker` instead of being masked as exhausted zero-capacity clusters
- Build-8 `portfolio_minimal` now mirrors that fail-close posture: unknown `cluster_id` is rejected at `eligibility_filter` / `selection_resolver` before allocation can silently cap it to `0`

### Engines A and B

Files:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_b/engine_b_runtime.py`

Role:
- run engine-specific signal logic
- emit canonical `SignalCandidate`
- pass through scoring
- pass through risk
- stop before Build-3 execution

Important reality:
- engines do not bypass scoring or risk
- Build-6 and Build-7 are wrappers around engine logic plus canonical downstream gates
- active engine runtimes now require explicit `EmergencyCircuitBreaker` injection at construction time
- the permissive `None` branch before `is_trading_allowed()` is now removed on A/B/C/D runtime-open rails
- active engine runtime inputs now also enforce millisecond-scale `timestamp_ms`, so Unix-second inputs are rejected at validation time
- Engine B now defaults missing `false_breakout_score` to neutral `0.5` on both conviction-builder and runner input surfaces instead of optimistic `0.0`
- Engine B now also exposes a bounded typed sweep-validation hook surface
- that hook can fail-open through a compiled-plan bridge, block before scoring, or apply bounded raw-score multiplier/add/cap adjustments before the normal scoring round

### Engines C and D

Files:
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_d/engine_d_runner.py`
- `src/engines/engine_d/engine_d_runtime.py`

Role:
- implement the canonical later-engine decision surfaces
- emit canonical `SignalCandidate`
- pass through scoring
- pass through risk
- stop before Build-3 execution

Important reality:
- `engine_c` and `engine_d` are not empty or bypass rails; they follow the same canonical runtime chain as `engine_a` / `engine_b`
- their packages are materially smaller than `engine_a` / `engine_b`, but their runners remain large and business-dense
- the asymmetry is mostly architectural: C/D keep more logic inline in runner files, whereas A/B extract more leaf modules
- the first bounded readability slices on this perimeter are now landed on both engines:
  - `structure_resolver_c.py` carries the structure/overlap context logic
  - `signal_math_c.py` carries the breakout/context/continuation/fake-breakout math
  - `context_resolver_d.py` carries the re-entry context/overlap logic
  - `signal_math_d.py` carries the history/context/reformation/marginal-value math
  - `cost_feasibility_c.py`, `conviction_builder_c.py`, and `invalidation_mapper_c.py` now also carry the bounded economic/conviction/invalidation logic for Engine C
  - `cost_feasibility_d.py`, `conviction_builder_d.py`, and `invalidation_mapper_d.py` now also carry the bounded economic/conviction/invalidation logic for Engine D
  - `output_payload_builder_c.py` now also carries the bounded final `EngineCOutput` payload assembly for Engine C
  - `output_payload_builder_d.py` now also carries the bounded final `EngineDOutput` payload assembly for Engine D
- treat this as a future auditability/readability parity topic, not as proof that C/D are mathematically or runtime incomplete
- this perimeter is now in a good stopping state after three bounded slices; only reopen it if a broader refactor objective is chosen

### Portfolio

Files:
- `src/portfolio_minimal/portfolio_orchestrator.py`
- `src/portfolio_minimal/opportunity_selector/candidate_pool_builder.py`

Role:
- build candidate pool
- resolve conflicts
- rank
- select
- size
- apply caps
- phantom-check
- report

Important reality:
- structural selection and economic viability are separated
- definitive rejection can happen after cap application and phantom checks
- freshness is now explicit in both `candidate_pool_builder` and `portfolio_orchestrator`
- `OrchestratorConfig` now requires an explicit `freshness_policy`, so the portfolio rail no longer hides `DISABLED` by omission

### Meta runtime

File:
- `src/meta_minimal/meta_runtime.py`

Role:
- converts each significant decision into a DTR
- persists DTRs
- derives CRA
- derives break-even reports
- derives prudent edge reports

Important reality:
- meta is not optional logging
- it is the audit spine for decision-path traceability and post-trade evidence

### Meta-learning governance

File:
- `src/meta_learning/contracts.py`

Role:
- captures governed learning inputs from Build-9 outputs
- keeps replay-only and no-implicit-promotion invariants on the Build-9X rail

Important reality:
- `TradeLearningInput` now defaults to `profile=ProfileId.COMPLETE`
- explicit `LIGHT` is still available only as a caller-selected compatibility input

## 2. Local AI Lab path in code

The Lab path is not a second trading system.
It is a governed proof and export path.

### Local replay orchestrator

File:
- `src/local_replay_runtime/replay_orchestrator.py`

Role:
- normalizes replay request and dataset slicing
- builds replay clock
- simulates shadow-compatible DTRs
- builds feature bridge and parity diagnostics payloads
- runs governed replay export
- persists session config and state
- supports chunking and resumable replay sessions

Important reality:
- Local replay is already shaped as an export and proof system
- it is not coded as a direct live runtime
- governed replay orchestration now defaults `profile_scope=ProfileId.COMPLETE`
- explicit `LIGHT` still exists only as a deliberate compatibility/testing override
- completed-export resume is now revalidated against persisted `replay_session_config.json` and `replay_run_manifest.json`
- the launcher can hydrate missing resume identifiers from persisted metadata, but explicit mismatches are rejected
- the Shadow runner now consumes a shared export-dir bridge instead of rebuilding governed import metadata ad hoc
- demo and export-driven Shadow imports now reuse the same feature-lock builder

## 3. Artifact governance path in code

Artifact import is tightly guarded.

### Controlled import

File:
- `src/backtest_artifact_import/validators.py`
- `src/backtest_artifact_import/export_dir_bridge.py`

Role:
- validates compatibility
- validates signature policy
- enforces runtime-governance rules
- enforces proof requirements
- validates feature lineage lock and transform whitelist lock

Important reality:
- import target must start at `SHADOW`
- implicit promotion beyond Shadow is forbidden
- artifact origin must be local
- governed import currently requires `source_profile=COMPLETE`
- the upload dry-run bridge no longer injects `date.today()` into import governance
- `ArtifactUploadRequest.governance_reference_date` is now explicit and forwarded unchanged into the import contract
- governed export directories now have a typed `export_dir -> ReplayExecutionPlan / ArtifactImportRequest / ArtifactUploadRequest` bridge
- that bridge preserves `artifact_schema_version`, `feature_set_version`, and `transform_set_version` from `replay_run_manifest`
- lineage locks are derived from `recognized_feature_keys` instead of falling back to unrecognized feature noise
- `replay_state_store.py` and `runtime_evidence.py` now also follow the hardened persistence rule used elsewhere on the governed rail: corruption is backed up to `.corrupted` and recovered with typed `last_error` markers instead of being swallowed silently
- the replay evidence recorder now exposes `build_state()` so its fail-safe recovery path is inspectable without reconstructing the runtime evidence contract indirectly
- active launcher consumers no longer rebuild `ArtifactImportRequest` locally
- `run_local_replay_shadow.py` and `run_technical_dashboard.py` now reuse the same shared `ReplayExecutionPlan + payload bundle -> ArtifactImportRequest` builder
- the governed signature policy now carries real base64 Ed25519 trust-store keys and a built-in pure-Python verifier
- `run_local_replay_shadow.py` and `run_technical_dashboard.py` now consume the same real signed fixture envelope on that built-in path instead of launcher-local accept-all verifier lambdas
- the technical dashboard is now also the first real launcher on this rail to consume a shared `ReplayExecutionPlan + payload bundle -> ArtifactUploadRequest` builder
- its governed import/onboarding demo path now flows through `upload_request -> import_request -> import validation -> onboarding`
- the shared rail now also exposes `ReplayExecutionPlan + local replay evidence -> ArtifactExportBundle`
- `run_technical_dashboard.py` and `run_local_replay_shadow.py` both consume that replay/evidence builder
- the Shadow runner now follows the same `upload_request -> import_request -> import validation -> Shadow` path instead of stopping at import-only state
- TTL governance on the upload-derived artifact bundle is anchored on `governance_reference_date`, not on historical replay timestamps

This is a strong code signal that the runtime doctrine already shifted away from old `LIGHT` rollout assumptions.

## 4. VPS runtime and supervision path in code

### Monitoring runtime

File:
- `src/monitoring/monitoring_runtime.py`

Role:
- collects monitoring snapshot
- builds alerts
- builds health dashboard payload
- builds technical dashboard payload
- builds observability export
- persists runtime guardrail state
- translates accepted operator UI safing actions into typed requests

Important reality:
- monitoring is not cosmetic
- it is part of the operator control surface and protocol wiring
- the public `ui` surface now exposes canonical `LockedOperator*` names first
- the public `monitoring` / `protocols` surfaces now expose canonical `Live*` names first
- legacy `Light*` / `LiveLight*` names remain only as explicit compatibility aliases
- the active operator action gate no longer rejects `profile=COMPLETE`; explicit `LIGHT` is preserved only as compatibility input
- the locked dashboard projection is now profile-aware and no longer emits stale `Light` wording when the payload is `COMPLETE`
- active Build-10 module wording now also uses `locked operator UI` instead of `locked Light UI` in source-level descriptions
- secondary monitoring wording now also presents Build-13 as the active Live rail and keeps `Live-Light` only as a historical label inside supervision text
- the technical dashboard now renders an explicit `Build-10` section in HTML instead of leaving Build-10 implicit behind generic `System`/`Portfolio` sections only
- persisted locked-operator UI state now follows the same fail-safe principle as the hardened Shadow/VPS stores: corruption is backed up to `.corrupted` and exposed as `operator_runtime.last_error` instead of being swallowed silently
- Build-10 operator supervision now surfaces that runtime-state corruption directly in the `Operator Events` cards of both the locked operator UI and the technical dashboard

### Open vs skeleton hook rails

Files:
- `src/protocols/execution_no_trade_hook.py`
- `src/protocols/risk_hooks.py`
- `src/protocols/scoring_hooks.py`
- `src/protocols/portfolio_hooks.py`
- `src/protocols/engine_a_hooks.py`
- `src/protocols/engine_b_hooks.py`
- `src/protocols/engine_c_hooks.py`
- `src/protocols/engine_d_hooks.py`

Role:
- define the bounded hook executor surface that is truly open
- keep all other hook families typed but intentionally unopened

Important reality:
- `EXECUTION_NO_TRADE_FILTER` has a real deterministic executor surface
- `ENGINE_A_PRE_ENTRY_CONFIRMATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- `ENGINE_B_SWEEP_VALIDATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- `ENGINE_C_VOID_VALIDATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- `ENGINE_D_REENTRY_VALIDATION` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- `RISK_MICRO_FRICTION_PRECHECK` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- `SCORING_SOFT_PENALTY_LAYER` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT` now also has a real bounded executor surface plus a compiled-plan fail-open bridge
- the hook-governance truth is now centralized in `interface_contracts.artifact_contracts.RUNTIME_OPEN_HOOK_IDS`; the only runtime-open hooks are `ENGINE_A_PRE_ENTRY_CONFIRMATION`, `ENGINE_B_SWEEP_VALIDATION`, `ENGINE_C_VOID_VALIDATION`, `ENGINE_D_REENTRY_VALIDATION`, `RISK_MICRO_FRICTION_PRECHECK`, `SCORING_SOFT_PENALTY_LAYER`, `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`, and `EXECUTION_NO_TRADE_FILTER`
- the other hook families remain typed skeletons with explicit `NotImplementedError` rails
- the repo is not running a global multihook executor
- monitoring no longer exposes only the execution no-trade compiled bridge; `technical_dashboard_backend` now carries a typed `runtime_hook_bridges` tuple for the whole open hook set
- the dashboard view now renders those hook bridges in a dedicated `Artifact Hooks` section, and observability exports per-hook bridge metrics for status/configuration/loading

### Protocol contracts

File:
- `src/protocols/contracts.py`

Role:
- defines the governed contracts for Build-11, Build-12, Build-13
- encodes truth sets, validation sets, component assessments, and runtime evidence
- validates import and runtime scope consistency

Important reality:
- Build-11 Shadow requires `profile=COMPLETE` and `runtime_mode=SHADOW`
- Build-12 Micro-live requires `profile=COMPLETE` and `runtime_mode=MICRO_LIVE`
- Build-13 Live requires `profile=COMPLETE` and `runtime_mode=LIVE`

This is the clearest code anchor for the current runtime doctrine.

### Shadow runtime

File:
- `src/protocols/shadow_runtime.py`

Role:
- combines replay evidence and runtime evidence
- compares truth set vs validation set
- derives component assessments
- derives engine and portfolio judgments
- supports Shadow verdicting and 30-day gate reporting

Important reality:
- Shadow is coded as a real judgment layer, not a placeholder
- it expects all A/B/C/D engines and Build-14 components in the evaluation surface

### Shadow day counter

File:
- `src/protocols/shadow_day_counter.py`

Role:
- persists consecutive shadow day counts
- resets on gaps greater than 24h
- records daily audit summaries

Important reality:
- it now uses frozen state transitions
- it still carries both `LIGHT` and `COMPLETE`
- it now also supports semantic recovery from validated persisted `ShadowDayRecord`s after counter corruption

### Shadow session registry

File:
- `src/protocols/shadow_session_registry.py`

Role:
- persists the append-only list of recorded Shadow days
- provides resume continuity for orchestrator and VPS service consumers

Important reality:
- append failure now rolls back to the exact prior in-memory entry list
- retry after a failed persist no longer deadlocks on a ghost `session_date`
- registry continuity can now be rebuilt from validated persisted entries after registry corruption

### Shadow daily orchestrator

File:
- `src/protocols/shadow_daily_orchestrator.py`

Role:
- persists external daily Shadow run ledger
- resolves replay/export slots
- records counted vs non-counted slots
- keeps replayability separate from day consumption

Important reality:
- `accepted` and `shadow_day_recorded` are intentionally separated
- a non-counted slot can be replayed
- a counted slot remains consumed
- when multiple governed metadata files exist in one export directory, their `session_date` must agree
- slot/session-date mismatch is now treated as invalid governed metadata instead of a silent fallback

### Shadow VPS service

File:
- `src/protocols/shadow_vps_service.py`

Role:
- persists state for a long-running VPS Shadow service
- tracks loops, heartbeats, failures, session dates, evidence refs, reports, and campaign summaries
- supports dated raw inputs, websocket inputs, and native live websocket capture

Important reality:
- the VPS rail is not a vague future idea
- the repo contains a concrete persistent service surface for autonomous Shadow operations
- for `raw_input`, `websocket`, and `native_live_websocket` auto-exports, the service now pins `replay_run_manifest.timeframe_scope` to the source governed day before slot discovery
- this keeps autonomous VPS progression aligned with the source slot date instead of historical replay timestamps
- the native websocket adapter now closes stale endpoint clients on reconnect instead of leaking the previously registered socket

### Live-Light runtime

File:
- `src/protocols/live_light_runtime.py`

Role:
- enforces the minimal Build-13 Live-Light gate
- projects bounded post-Shadow Build-14 influence without opening autonomous Build-14 behavior
- derives the final small-execution or dry-run decision

Important reality:
- Build-14 influence now revalidates against explicit `Build14InfluenceSignal` / `Build14InfluenceReport` classes
- duck-typed objects that only spoof module/name are rejected
- this closed `BS-52` without widening the runtime perimeter

## 5. Real code doctrine vs stale doctrine

The codebase currently contains an important split-brain situation.

### Real in code

- governed Shadow / Micro-live / Live runtime opens on `COMPLETE`
- artifact import requires `source_profile=COMPLETE`
- execution defaults also moved to `COMPLETE`

### Still legacy or partially stale

- `ProfileId` still contains `LIGHT`
- `manifest_registry` still models `LIGHT` / `COMPLETE`
- many tests still exercise `LIGHT`
- `local_replay_runtime` still exposes `LIGHT`, but its governed orchestrator and export launcher now default to `COMPLETE`
- `shadow_day_counter` still tracks both `LIGHT` and `COMPLETE`
- some deeper tests and secondary docs still describe the old two-profile rollout, but the top-level canon, the Build-11/12/13/14 phase specs, the detailed Build-10 docs, the manifest-registry descriptions, and the active public runtime names are now aligned with the governed `COMPLETE` rail
- Build-10 monitoring/dashboard tests now also prove `COMPLETE` on the active backend/runtime/view path, and canonical `LockedOperator*` / `Live*` names are exercised directly on the active rail

## 6. What this means for future sessions

Do not ask "what does the doc say?" before asking:
- what do the runtime contracts enforce
- what do the import validators enforce
- what do the tests enforce

Practical rule:
- if a session touches runtime governance, start from `src/protocols/`, `src/backtest_artifact_import/`, `src/local_replay_runtime/`, and `src/monitoring/`
- if a session touches trading logic, start from engine runtime -> scoring -> risk -> portfolio -> meta

## 7. Minimum code reading set by rail

### Trading core rail

- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/scoring_backbone/scoring_runtime.py`
- `src/risk_backbone/risk_runtime.py`
- `src/portfolio_minimal/portfolio_orchestrator.py`
- `src/meta_minimal/meta_runtime.py`
- `src/execution_backbone/execution_runtime.py`

### Lab / VPS governance rail

- `src/local_replay_runtime/replay_orchestrator.py`
- `src/backtest_artifact_import/validators.py`
- `src/protocols/contracts.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_daily_orchestrator.py`
- `src/protocols/shadow_vps_service.py`
- `src/protocols/live_light_runtime.py`
- `src/monitoring/monitoring_runtime.py`

## 8. Bottom line

V5.3 is coded as:
- a shared typed core
- bounded runtime modules by build
- a local proof/export path
- a governed VPS import and Shadow path
- a persistent monitoring and operator layer

The most important risk is no longer "missing architecture".
It is doctrine drift between:
- current runtime code
- legacy profile/docs/test surfaces
- session memory quality

## 9. Binance Spot venue adapter (P0-1.A)

Files:
- `src/interface_contracts/binance_contracts.py`
- `src/venue_adapters/binance_spot/credential_loader.py`
- `src/venue_adapters/binance_spot/time_sync.py`
- `src/venue_adapters/binance_spot/rest_client.py`

Role:
- starts the real P0 production path without opening live order submission
- provides typed read-only Binance contracts and a read-only async REST surface
- binds the first dynamic execution threshold `THR-X01` to real code via `calibration_loader`

Important reality:
- the venue-adapter package is no longer hypothetical
- `time_sync.py` already consumes calibrated drift policy instead of a source-code hardcoded threshold
- `rest_client.py` is strictly read-only in this tranche: `/api/v3/time`, `/api/v3/exchangeInfo`, and signed GET `/api/v3/account`
- sealed secrets are not solved here; `credential_loader.py` is an explicit stub waiting for `T2`

## 10. Secrets manager (P0-4 bounded slice)

Files:
- `src/secrets_manager/__init__.py`
- `src/secrets_manager/__main__.py`
- `src/secrets_manager/_dpapi.py`
- `src/secrets_manager/loader.py`
- `src/secrets_manager/sealer.py`
- `src/secrets_manager/cli.py`

Role:
- seals plaintext secret files into a typed encrypted envelope
- keeps the current local/dev environment off plaintext-on-disk at runtime
- gives `venue_adapters/binance_spot/credential_loader.py` a real sealed-file path

Important reality:
- this is a bounded Windows/local backend, not the final cross-platform production story
- encryption currently relies on Windows DPAPI plus an external `master.key` file as additional entropy
- `age` / `sops` / Linux VPS portability remain open

## 11. Binance Spot websocket/orderbook core (P0-1.B bounded slice)

Files:
- `src/venue_adapters/binance_spot/ws_client.py`
- `src/venue_adapters/binance_spot/orderbook_manager.py`
- `src/data_backbone/freshness_checker/venue_stream_freshness.py`

Role:
- adds the first real websocket/orderbook core for Binance Spot without opening live trading
- enforces `snapshot -> deltas` sequencing and explicit stale/resync states
- keeps reconnect from silently resuming a stale order-book stream

Important reality:
- the core is now real in code, but the full live/testnet closure is not done yet
- `THR-X02` can now be consumed by code through `resolve_websocket_gap_threshold_s()`
- `shadow_live_websocket.py` now also preserves `first_update_id / final_update_id` on depth payloads
- `rest_client.py` now also exposes a typed REST depth snapshot and an explicit provider bridge for websocket bootstrap
