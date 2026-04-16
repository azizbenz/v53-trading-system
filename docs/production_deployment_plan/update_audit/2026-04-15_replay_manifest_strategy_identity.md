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
