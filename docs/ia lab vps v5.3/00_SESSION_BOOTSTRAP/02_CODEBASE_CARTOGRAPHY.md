# Codebase Cartography

This file is the practical map of the repo for new sessions.

## Top-level working surfaces

Code:
- `src/`

Tests:
- `tests/`

Canon:
- `docs/specs/`

Strict restart handoff:
- `docs/audit chatgpt buisness/`

Local AI Lab and VPS doctrine pack:
- `docs/ia lab vps v5.3/`

## Build map from the manifest

The manifest source is:
- `src/manifest_registry/module_inventory.py`

### Build-1

Contracts and structural safety:
- `src/interface_contracts/`
- `src/manifest_registry/`
- `src/dag_validator/`
- `src/contract_test_suite/`
- `src/smoke_bootstrap_recovery/`

Matching tests:
- `tests/test_interface_contracts/`
- `tests/test_manifest_registry/`
- `tests/test_dag_validator/`
- `tests/test_contract_test_suite/`
- `tests/test_smoke_bootstrap_recovery/`

### Build-2

Data backbone:
- `src/data_backbone/`

Matching tests:
- `tests/test_data_backbone/`

### Build-3

Execution backbone:
- `src/execution_backbone/`

Matching tests:
- `tests/test_execution_backbone/`

### Build-4

Risk backbone:
- `src/risk_backbone/`

Matching tests:
- `tests/test_risk_backbone/`

### Build-5

Scoring backbone:
- `src/scoring_backbone/`

Matching tests:
- `tests/test_scoring_backbone/`

### Build-6

Engine A:
- `src/engine_a/`
- `src/engines/engine_a/`

Matching tests:
- `tests/test_engines/test_engine_a/`

### Build-7

Engine B:
- `src/engine_b/`
- `src/engines/engine_b/`

Matching tests:
- `tests/test_engines/test_engine_b/`

### Build-8

Portfolio:
- `src/portfolio/`
- `src/portfolio_minimal/`

Matching tests:
- `tests/test_portfolio/`
- `tests/test_portfolio_minimal/`

### Build-9

Meta minimal:
- `src/meta/`
- `src/meta_minimal/`

Matching tests:
- `tests/test_meta/`
- `tests/test_meta_minimal/`

### Build-9X and Build-10 sidecars

Replay, import, learning, monitoring, UI:
- `src/local_replay_runtime/`
- `src/backtest_artifact_import/`
- `src/meta_learning/`
- `src/monitoring/`
- `src/ui/`

Matching tests:
- `tests/test_local_replay_runtime/`
- `tests/test_backtest_artifact_import/`
- `tests/test_meta_learning/`
- `tests/test_monitoring/`
- `tests/test_ui/`

### Build-11 to Build-13

Protocols:
- `src/protocols/`

Matching tests:
- `tests/test_protocols/`

Critical runtime files on the current rail:
- `src/protocols/contracts.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_daily_orchestrator.py`
- `src/protocols/shadow_session_registry.py`
- `src/protocols/micro_live_runtime.py`
- `src/protocols/live_light_runtime.py`
- `src/protocols/promotion_gates.py`

### Build-14 to Build-16

Complete enablers and engines C/D:
- `src/complete_enablers/`
- `src/engine_c/`
- `src/engine_d/`
- `src/engines/engine_c/`
- `src/engines/engine_d/`

Matching tests:
- `tests/test_complete_enablers/`
- `tests/test_engines/test_engine_c/`
- `tests/test_engines/test_engine_d/`

## Read order by critical slice

### If the session works on `shadow/protocols`

Read in this order:
- `src/interface_contracts/domain_types.py`
- `src/manifest_registry/module_inventory.py`
- `src/protocols/contracts.py`
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_daily_orchestrator.py`
- `src/protocols/shadow_session_registry.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/promotion_gates.py`
- `tests/test_protocols/`

### If the session works on `local replay / artifact governance`

Read in this order:
- `src/interface_contracts/`
- `src/local_replay_runtime/`
- `src/backtest_artifact_import/`
- `src/meta_learning/`
- matching tests in `tests/test_local_replay_runtime/`, `tests/test_backtest_artifact_import/`, `tests/test_meta_learning/`

### If the session works on `portfolio`

Read in this order:
- `src/portfolio_minimal/portfolio_orchestrator.py`
- `src/portfolio_minimal/opportunity_selector/`
- `src/risk_backbone/`
- `src/scoring_backbone/`
- matching tests in `tests/test_portfolio_minimal/` and `tests/test_portfolio/`

## Practical rule for new chats

Do not read the whole repo line by line before doing anything.

Do:
- read the architecture map first
- then read line by line the exact active critical slice
- then read its tests
- then compare with canon and handoff docs
