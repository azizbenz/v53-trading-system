# 2026-04-15 Forecast Contract + Engine A Adapter

## Objective

Create an auditable additive forecast contract seam, then wire the first real engine adapter on Engine A without replacing the canonical decision signal contract.

## Docs Governants

- [20_CARVER_NARANG_TALEB_INTEGRATION.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md>) `§3.1`
- [24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md](</E:/claude  v5.3/v53_trading_system/docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md>) `§3.3`, `§5`
- [CODEX_PROMPT.md](</E:/claude  v5.3/v53_trading_system/CODEX_PROMPT.md>) `R22`, `R23`, `R24`, `R26`

## Current Code Seam

- Canonical file today: [decision_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/decision_contracts.py>)
- First engine runtime consumer: [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- Forbidden shortcut for this slice: no canonical contract replacement, no invented `strategy_id`, no `side="flat"`

## Placement

- Target file: [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- First engine adapter landing: [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>) + [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)
- Actual landing decision: additive sibling contract plus optional runtime adapter, preserving `decision_contracts.SignalCandidate` as the package canon

## Files Changed

- [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- [__init__.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/__init__.py>)
- [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)
- [test_forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/tests/test_interface_contracts/test_forecast_contracts.py>)
- [test_engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a_runtime.py>)

## Claims Implemented

- Additive forecast enums + conditioning contract exist -> [forecast_contracts.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/forecast_contracts.py>)
- Package-level canonical `SignalCandidate` remains unchanged while `ForecastSignalCandidate` is exported separately -> [__init__.py](</E:/claude  v5.3/v53_trading_system/src/interface_contracts/__init__.py>)
- Engine A can emit `forecast_signal_candidate` only when `strategy_id` is explicitly provided -> [engine_a_runtime.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime.py>)
- Engine A forecast mapping uses only real data already present in the runtime seam -> [engine_a_runtime_support.py](</E:/claude  v5.3/v53_trading_system/src/engines/engine_a/engine_a_runtime_support.py>)

## Tests and Proof

- `python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py tests/test_engines/test_engine_a/test_engine_a_runtime.py src/interface_contracts/forecast_contracts.py` -> pass
- `python -m pytest tests/test_interface_contracts/test_all_contracts.py tests/test_interface_contracts/test_forecast_contracts.py tests/test_engines/test_engine_a/test_engine_a_runtime.py -q` -> `95 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`, `total_violations=3549`

## Deferred / Not Done

- Engine B adapter not wired yet
- No canonical `strategy_identity` contract yet
- No propagation yet into C/D, scoring, portfolio, or execution

## Risks / Open Questions

- `strategy_id` is currently an optional runtime seam, not yet a cross-repo canonical contract
- Future engines should reuse the same pattern rather than creating a second competing forecast canon

## Completion Status

`COMPLETE`

Reason:

`The additive contract seam exists, the first real engine adapter exists, proof commands are green, and no new guardrail violations were introduced.`

## Next Safe Step

`Replicate the same optional strategy_id -> forecast_signal_candidate pattern on Engine B, or formalize strategy identity before wider propagation.`
