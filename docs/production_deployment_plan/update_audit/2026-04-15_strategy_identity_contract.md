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
