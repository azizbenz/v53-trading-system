# 11_STRATEGY_IDENTITY_AND_REPLAY

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-15_strategy_identity_contract.md
- docs/production_deployment_plan/update_audit/2026-04-15_replay_manifest_strategy_identity.md
- docs/production_deployment_plan/update_audit/2026-04-15_replay_scope_identity.md
- docs/production_deployment_plan/update_audit/2026-04-15_replay_session_config_strategy_identity.md
- docs/production_deployment_plan/update_audit/2026-04-15_replay_session_state_strategy_identity.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_strategy_identity_contract.md

# 2026-04-15 Strategy Identity Contract

## Objective

Add the canonical typed `StrategyIdentity` contract as an upstream seam for future forecast adapters and aggregation logic, without forcing migration of existing `strategy_id: str` surfaces.

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§12.4`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) line about `strategy_identity.py`
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R21`, `R22`, `Bloc 10`

## Current Code Seam

- Existing repo truth: many replay/protocol manifests still carry plain `strategy_id: str`
- Forecast seam already exists in [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- Forbidden shortcut for this slice: no repo-wide refactor from string strategy ids to typed model in one pass

## Placement

- Target file: [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)
- Actual landing decision: add canonical typed model in `interface_contracts`, then let future slices resolve string ids progressively

## Files Changed

- [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)
- [__init__.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/__init__.py>)
- [test_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_interface_contracts/test_strategy_identity.py>)

## Claims Implemented

- Canonical frozen `StrategyIdentity` contract exists -> [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)
- Contract uses the doctrinal tuple `{engine_id, pair, regime_bucket, forecast_target_class, bet_structure, calibration_version}` -> [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)
- Deterministic `canonical_key` exists for stable aggregation/audit use -> [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)
- Additive helper `from_forecast_signal(...)` exists for future forecast adapters -> [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)

## Tests and Proof

- `python -m py_compile src/interface_contracts/strategy_identity.py src/interface_contracts/__init__.py tests/test_interface_contracts/test_strategy_identity.py` -> pass
- `python -m pytest tests/test_interface_contracts/test_strategy_identity.py tests/test_interface_contracts/test_forecast_contracts.py -q` -> `26 passed`
- `python -m pytest tests/test_interface_contracts/test_all_contracts.py tests/test_interface_contracts/test_strategy_identity.py tests/test_interface_contracts/test_forecast_contracts.py -q` -> `89 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`, `total_violations=3537`

## Deferred / Not Done

- Existing manifests and runtimes still use plain `strategy_id: str`
- No resolver from free-form legacy strategy strings to `StrategyIdentity` yet
- No integration yet with replay manifests or portfolio aggregation

## Risks / Open Questions

- `canonical_key` is deterministic, but it is not yet declared as the universal external `strategy_id`
- Any future migration from string ids must preserve existing artifact/replay compatibility

## Completion Status

`COMPLETE`

Reason:

`The contract exists, the broader interface proof is green, and guardrails report no new violations.`

## Next Safe Step

`Keep the slice contract-only until a governed resolver or consumer is ready; the next safe consumer is a replay/export or portfolio aggregation seam, not a blind repo-wide migration.`


---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_replay_manifest_strategy_identity.md

# 2026-04-15 Replay Manifest Strategy Identity

## Objective

Add `StrategyIdentity` as an optional governed replay/export consumer without breaking the canonical `strategy_id: str` manifest surface.

## Docs Gouvernants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§12.4`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) optional downstream seam after the enriched contract lands
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R21`, `R22`, `R23`, `R26`, `Bloc 10`

## Current Code Seam

- Repo truth before this slice: replay/export manifests only carried `strategy_id: str`
- `StrategyIdentity` already exists canonically in [strategy_identity.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/strategy_identity.py>)
- Replay manifests can be multi-engine and multi-pair, so `StrategyIdentity` cannot be inferred or attached blindly

## Placement

- Governed consumer: [replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_run_manifest.py>)
- Proof of export serialization: [artifact_exporter.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/artifact_exporter.py>) via targeted tests

## Files Changed

- [replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_run_manifest.py>)
- [test_replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_run_manifest.py>)
- [test_artifact_exporter.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_artifact_exporter.py>)

## Claims Implemented

- `ReplayRunManifest` now accepts `strategy_identity: StrategyIdentity | None` additively -> [replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_run_manifest.py>)
- Legacy `strategy_id: str` remains mandatory and unchanged -> [replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_run_manifest.py>)
- No blind inference is performed from `strategy_id` to `StrategyIdentity` -> [replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_run_manifest.py>)
- `strategy_identity` is only allowed when the replay manifest is single-engine and single-pair, and the typed tuple matches that governed scope -> [replay_run_manifest.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_run_manifest.py>)
- Exported replay manifests serialize the optional typed identity cleanly into JSON -> [test_artifact_exporter.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_artifact_exporter.py>)

## Tests and Proof

- `python -m py_compile src/local_replay_runtime/replay_run_manifest.py tests/test_local_replay_runtime/test_contracts.py tests/test_local_replay_runtime/test_replay_run_manifest.py tests/test_local_replay_runtime/test_artifact_exporter.py` -> pass
- `python -m pytest tests/test_interface_contracts/test_strategy_identity.py tests/test_local_replay_runtime/test_contracts.py::test_replay_run_manifest_accepts_canonical_local_replay_shape tests/test_local_replay_runtime/test_contracts.py::test_replay_run_manifest_rejects_non_local_runtime_and_duplicate_scope tests/test_local_replay_runtime/test_replay_run_manifest.py tests/test_local_replay_runtime/test_artifact_exporter.py -q` -> `13 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`, `total_violations=3536`

## Deferred / Not Done

- No repo-wide migration from `strategy_id: str` to `StrategyIdentity`
- No attempt to infer typed identity for multi-engine or multi-pair replay runs
- No propagation yet into `ReplaySessionConfig`, `ReplayOrchestratorRequest`, or runtime prompts

## Risks / Open Questions

- Multi-strategy replay scopes still require plain string identity today; a single `StrategyIdentity` is intentionally not expressive enough for those aggregates
- If a future slice needs typed identity across multi-scope replay, it should add a dedicated aggregate contract rather than overloading this optional field

## Completion Status

`COMPLETE`

## Next Safe Step

Use the same additive pattern only on a seam that is genuinely mono-strategy, or introduce a dedicated typed aggregate identity for multi-engine / multi-pair replay scope.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_replay_scope_identity.md

# 2026-04-15 Replay Scope Identity

## Objective

Introduce a typed aggregate replay identity for multi-engine / multi-pair LOCAL_REPLAY chunk sessions, without overloading `StrategyIdentity` or changing legacy `strategy_id: str` request and resume surfaces.

## Docs Gouvernants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§12.4` for the distinction between single-strategy identity and broader governed scope
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) notes that multi-engine grammar still uses simplified contracts and needs typed deepening
- [2026-04-15_replay_session_state_strategy_identity.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/update_audit/2026-04-15_replay_session_state_strategy_identity.md>) explicit stop point before multi-scope surfaces
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R21`, `R22`, `R23`, `R26`, `Bloc 10`

## Current Code Seam

- `StrategyIdentity` is valid only for mono-strategy seams
- `ReplayChunkSessionSummary` persists a genuinely aggregate replay session (`multi-chunk`, potentially multi-engine / multi-pair)
- Resume logic still compares legacy string fields and must remain compatible

## Placement

- New replay-specific contract: [replay_scope_identity.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_scope_identity.py>)
- Aggregate consumer: [replay_orchestrator_models.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_models.py>) via `ReplayChunkSessionSummary`
- Builder wiring: [replay_orchestrator_execution.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_execution.py>)

## Files Changed

- [replay_scope_identity.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_scope_identity.py>)
- [replay_orchestrator_models.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_models.py>)
- [replay_orchestrator_execution.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_execution.py>)
- [__init__.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/__init__.py>)
- [test_replay_scope_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_scope_identity.py>)
- [test_replay_orchestrator_scope_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_orchestrator_scope_identity.py>)

## Claims Implemented

- `ReplayScopeIdentity` exists as a replay-specific typed aggregate contract -> [replay_scope_identity.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_scope_identity.py>)
- The contract captures dataset, engine scope, pair scope, chunk selection, requested window, and effective time envelope without pretending to be a mono-strategy tuple -> [replay_scope_identity.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_scope_identity.py>)
- `ReplayChunkSessionSummary` now persists optional `replay_scope_identity` for aggregate chunk sessions -> [replay_orchestrator_models.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_models.py>)
- `orchestrate_local_replay_export(...)` computes and writes this typed aggregate identity into `replay_chunk_session.json` -> [replay_orchestrator_execution.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_execution.py>)
- Legacy request/resume matching remains based on existing string fields; no migration of those surfaces in this slice -> [replay_orchestrator_resume.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_orchestrator_resume.py>)

## Tests and Proof

- `python -m py_compile src/local_replay_runtime/replay_scope_identity.py src/local_replay_runtime/replay_orchestrator_models.py src/local_replay_runtime/replay_orchestrator_execution.py tests/test_local_replay_runtime/test_replay_scope_identity.py tests/test_local_replay_runtime/test_replay_orchestrator_scope_identity.py` -> pass
- `python -m pytest tests/test_local_replay_runtime/test_replay_scope_identity.py tests/test_local_replay_runtime/test_replay_orchestrator_scope_identity.py -q` -> pass
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No propagation into `ReplayOrchestratorRequest`
- No change to resume matching logic
- No change to mono-strategy `StrategyIdentity` semantics

## Risks / Open Questions

- If a future resume slice wants typed aggregate comparison, it should compare `ReplayScopeIdentity` only when both sides explicitly carry it and preserve legacy fallback
- If future aggregate replay spans multiple dataset ids, this contract should be extended deliberately instead of silently concatenating ids

## Completion Status

`COMPLETE`

## Next Safe Step

If we need typed replay aggregate comparison, the next safe seam is `replay_orchestrator_resume.py` and `replay_orchestrator_io.py`, using this new contract additively while preserving legacy resume checks.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_replay_session_config_strategy_identity.md

# 2026-04-15 Replay Session Config Strategy Identity

## Objective

Propagate the optional typed `StrategyIdentity` from the governed replay manifest into `ReplaySessionConfig`, while preserving canonical `strategy_id: str` compatibility and existing LOCAL_REPLAY builder semantics.

## Docs Gouvernants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§12.4`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) optional downstream replay consumer after the manifest seam
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R21`, `R22`, `R23`, `R26`, `Bloc 10`

## Current Code Seam

- `ReplayRunManifest` already carries optional `strategy_identity`
- `ReplaySessionConfig` remained string-only before this slice
- The session config is persisted to `replay_session_config.json` during orchestration, so this seam is audit-relevant

## Placement

- Governed consumer: [replay_session_config.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_session_config.py>)
- Focused tests: [test_replay_session_config_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_config_strategy_identity.py>)

## Files Changed

- [replay_session_config.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_session_config.py>)
- [test_replay_session_config_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_config_strategy_identity.py>)

## Claims Implemented

- `ReplaySessionConfig` now accepts `strategy_identity: StrategyIdentity | None` additively -> [replay_session_config.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_session_config.py>)
- `build_replay_session_config(...)` performs a strict pass-through from `ReplayRunManifest.strategy_identity` -> [replay_session_config.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_session_config.py>)
- Legacy manifests without typed identity remain valid and unchanged -> [test_replay_session_config_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_config_strategy_identity.py>)
- JSON serialization of the session config now preserves the optional typed identity for audit sidecars -> [test_replay_session_config_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_config_strategy_identity.py>)

## Tests and Proof

- `python -m py_compile src/local_replay_runtime/replay_session_config.py tests/test_local_replay_runtime/test_replay_session_config_strategy_identity.py` -> pass
- `python -m pytest tests/test_interface_contracts/test_strategy_identity.py tests/test_local_replay_runtime/test_replay_session_config_strategy_identity.py -q` -> pass
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No propagation yet into `ReplaySessionState`
- No change to `ReplayOrchestratorRequest`, `ReplayExecutionInput`, or resume matching logic
- No attempt to infer typed identity from plain legacy strings

## Risks / Open Questions

- Multi-engine / multi-pair replay still relies on plain `strategy_id`; this slice intentionally does not redefine aggregate identity
- If future resume logic needs typed identity validation, it should compare optional typed tuples only when both sides explicitly carry them

## Completion Status

`COMPLETE`

## Next Safe Step

Propagate the same additive field into the next persisted mono-strategy replay seam only if that seam already receives a governed `ReplaySessionConfig`; otherwise stop and design an aggregate identity contract first.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-15_replay_session_state_strategy_identity.md

# 2026-04-15 Replay Session State Strategy Identity

## Objective

Propagate the optional typed `StrategyIdentity` from `ReplaySessionConfig` into persisted `ReplaySessionState`, while preserving canonical `strategy_id: str` compatibility and current LOCAL_REPLAY state semantics.

## Docs Gouvernants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§12.4`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) additive downstream replay seam after session config
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R21`, `R22`, `R23`, `R26`, `Bloc 10`

## Current Code Seam

- `ReplaySessionConfig` already carries optional `strategy_identity`
- `ReplaySessionState` persisted only `strategy_id: str` before this slice
- The state store is written to `replay_session_state.json`, so it is an audit-visible persistence seam

## Placement

- Governed consumer: [replay_state_store.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_state_store.py>)
- Focused tests: [test_replay_session_state_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_state_strategy_identity.py>)

## Files Changed

- [replay_state_store.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_state_store.py>)
- [test_replay_session_state_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_state_strategy_identity.py>)

## Claims Implemented

- `ReplaySessionState` now accepts `strategy_identity: StrategyIdentity | None` additively -> [replay_state_store.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_state_store.py>)
- `ReplaySessionStateStore.initialize(...)` performs a strict pass-through from `ReplaySessionConfig.strategy_identity` -> [replay_state_store.py](</E:/claude  v5.3/v53_trading_system/src/local_replay_runtime/replay_state_store.py>)
- Persisted JSON state now carries the optional typed identity when explicitly present -> [test_replay_session_state_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_state_strategy_identity.py>)
- Legacy state remains compatible and serializes `strategy_identity: null` when absent -> [test_replay_session_state_strategy_identity.py](</E:/claude  v5.3/v53_trading_system/tests/test_local_replay_runtime/test_replay_session_state_strategy_identity.py>)

## Tests and Proof

- `python -m py_compile src/local_replay_runtime/replay_state_store.py tests/test_local_replay_runtime/test_replay_session_state_strategy_identity.py` -> pass
- `python -m pytest tests/test_interface_contracts/test_strategy_identity.py tests/test_local_replay_runtime/test_replay_session_state_strategy_identity.py -q` -> pass
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No change to resume matching logic
- No propagation yet into `ReplayOrchestratorRequest`, `ReplayChunkSessionSummary`, or aggregate replay identity
- No inference from legacy strings to typed identity

## Risks / Open Questions

- Resume validation still keys off `strategy_id`; if future logic wants typed identity parity, it should compare optional tuples only when both sides explicitly carry them
- Multi-strategy aggregate replay state still needs a separate aggregate identity contract, not overload of this optional field

## Completion Status

`COMPLETE`

## Next Safe Step

Stop before resume/request surfaces unless the next consumer is still genuinely mono-strategy; otherwise design an aggregate replay identity contract first.


