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
