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
