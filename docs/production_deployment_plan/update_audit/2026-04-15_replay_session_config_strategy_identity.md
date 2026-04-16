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
