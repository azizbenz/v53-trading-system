# Wave 5 Test Coverage Evidence

This file records test evidence relevant to scoring, risk, sizing, portfolio, cockpit semantics, and side safety.

## Test files found

Scoring:
- `tests/test_scoring_backbone/test_raw_score_builder.py`
- `tests/test_scoring_backbone/test_penalty_aggregator.py`
- `tests/test_scoring_backbone/test_break_even_filter.py`
- `tests/test_scoring_backbone/test_fee_aware_edge_gate.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_scoring_backbone/test_scoring_integration.py`

Risk:
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_risk_backbone/test_risk_integration.py`
- `tests/test_risk_backbone/test_daily_pnl_breaker.py`
- `tests/test_risk_backbone/test_exposure_budgeter.py`

Portfolio:
- `tests/test_portfolio_minimal/test_allocation_router_minimal.py`
- `tests/test_portfolio_minimal/test_vol_target_sizing.py`
- `tests/test_portfolio_minimal/test_opportunity_selector_minimal.py`
- `tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py`

Cockpit:
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_economic_sterilization.py`
- `tests/cockpit/test_state_engine_why.py`
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_system_flow.py`
- `tests/cockpit/test_cockpit_server_routes.py`

Complete enablers / ML / regime:
- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
- other complete-enabler tests in the requested suite

Engines:
- `tests/test_engines/test_engine_c/...`
- `tests/test_engines/test_engine_d/...`
- broader engine suite in the requested test band

## Exact assertions already inspected

Representative inspected assertions:
- replay semantics:
  - `assert replay.expected_ce_label == "Expected CE net"`
  - `assert "not realized profitability" in replay.expected_ce_caveat`
  - `assert replay.exec_rate_total == 0.25`
  - `assert replay.exec_rate_label == "Exec rate (executed / total records)"`
  - `assert replay.economics_display_state == "partial_replay"`
  - `assert replay.cost_model_completeness_status == "PARTIAL_NO_FEE_NO_IMPACT"`
- cockpit routes:
  - trading page contains `Expected CE net`
  - trading page contains `Exec rate (executed / total records)`
- feature bridge:
  - artifact-present-only is not runtime active
  - research-only features stay gray / non-runtime
- ML governance:
  - `assert result.signal.reason_codes == ("ML_DIRECT_OVERRIDE_FORBIDDEN",)`
  - `assert result.engine_side == Side.SELL`
- engine C / D:
  - `assert result.signal_candidate.side == Side.BUY`
  - `assert candidate.carriage_statuses == ("local_math_only", "shared_scoring_physics_partial")`
- portfolio:
  - oversized trades are reduced, not pre-rejected
  - phantom trades are sterilized explicitly

## Missing or partial test areas

- no inspected test proves a measured small-capital exclusion artifact
- no inspected test proves a true executed-only realized net-return rail
- no inspected test proves a true replay/shadow/live net-equity max drawdown rail
- no inspected test proves runtime score/risk consumption of Wave 3 cost-completeness statuses
- no inspected test proves Kelly/fractional Kelly sizing because no such seam was found

## Validation commands

Requested commands to run:
- `python -m py_compile src/scoring_backbone/*.py`
- `python -m py_compile src/risk_backbone/*.py`
- `python -m py_compile src/portfolio_backbone/*.py`
- `python -m py_compile src/portfolio_minimal/*.py`
- `python -m py_compile src/complete_enablers/*.py`
- `python -m pytest -q tests/test_scoring_backbone --tb=short --disable-warnings`
- `python -m pytest -q tests/test_risk_backbone --tb=short --disable-warnings`
- `python -m pytest -q tests/test_portfolio_backbone --tb=short --disable-warnings`
- `python -m pytest -q tests/test_portfolio_minimal --tb=short --disable-warnings`
- `python -m pytest -q tests/test_complete_enablers --tb=short --disable-warnings`
- `python -m pytest -q tests/test_engines --tb=short --disable-warnings`
- `python -m pytest -q tests/cockpit --tb=short --disable-warnings`

Execution results:
- syntax:
  - wildcard form failed under PowerShell / Python argument handling with `Invalid argument: 'src\\...\\*.py'`
  - rerun with explicit file expansion succeeded for:
    - `src/scoring_backbone/*.py`
    - `src/risk_backbone/*.py`
    - `src/portfolio_minimal/*.py`
    - `src/complete_enablers/*.py`
  - `src/portfolio_backbone/` path not present
- `tests/test_scoring_backbone`
  - result: `189 passed`, `4 errors`
  - failure mode: `PermissionError [WinError 5]` in `tests/test_scoring_backbone/test_fee_aware_edge_gate.py` fixture writing under `build\\pytest-fee-aware-edge-gate\\...`
- `tests/test_risk_backbone`
  - result before session-finish crash: `162 passed`, `24 errors`, `2 additional session-finish permission failures`
  - failure modes:
    - `PermissionError [WinError 5]` in `tests/test_risk_backbone/test_circuit_breaker.py`
    - `PermissionError [WinError 5]` in `tests/test_risk_backbone/test_daily_pnl_breaker.py`
    - `PermissionError [WinError 5]` in `tests/test_risk_backbone/test_daily_pnl_breaker_entry_gate.py`
    - `PermissionError [WinError 5]` during pytest session cleanup of `.test_tmp\\pytest_wave5_risk`
- `tests/test_portfolio_backbone`
  - path missing
- `tests/test_portfolio_minimal`
  - result: `100 passed`
- `tests/test_complete_enablers`
  - result: `64 passed`
- `tests/test_engines`
  - result: `448 passed`
- `tests/cockpit`
  - result: `66 passed`

Exact command band executed:
- `python -m pytest -q tests\\test_scoring_backbone --tb=short --disable-warnings --basetemp=.test_tmp\\pytest_wave5_scoring`
- `python -m pytest -q tests\\test_risk_backbone --tb=short --disable-warnings --basetemp=.test_tmp\\pytest_wave5_risk`
- `python -m pytest -q tests\\test_portfolio_minimal --tb=short --disable-warnings --basetemp=.test_tmp\\pytest_wave5_portfolio_minimal`
- `python -m pytest -q tests\\test_complete_enablers --tb=short --disable-warnings --basetemp=.test_tmp\\pytest_wave5_complete_enablers`
- `python -m pytest -q tests\\test_engines --tb=short --disable-warnings --basetemp=.test_tmp\\pytest_wave5_engines`
- `python -m pytest -q tests\\cockpit --tb=short --disable-warnings --basetemp=.test_tmp\\pytest_wave5_cockpit`

Environment failures:
- pre-existing permission restrictions on some `build\\...` fixture directories
- pytest cleanup permission failure on `.test_tmp\\pytest_wave5_risk`

Evidence interpretation:
- the core Wave 5 logic seams inspected in portfolio, engines, cockpit, and complete-enablers are backed by passing test bands
- broad scoring and risk suites are only partially runnable in this environment because of permission-bound fixture paths, not because the inspected Wave 5 docs changed source logic
