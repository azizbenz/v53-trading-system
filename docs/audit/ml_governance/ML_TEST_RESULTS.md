# ML Test Results

## Logic test status

## Complete enablers
- Command:
  - `python -m pytest -q tests/test_complete_enablers/test_ml_confidence_enabler.py tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py tests/test_complete_enablers/test_regime_detector_runtime.py --tb=short --disable-warnings --basetemp=tmp_pytest_add2_complete_enablers`
- Result:
  - `21 passed`

## Scoring / risk targeted carriage
- Command:
  - `python -m pytest -q tests/test_scoring_backbone/test_scoring_runtime.py tests/test_risk_backbone/test_risk_runtime.py --tb=short --disable-warnings --basetemp=tmp_pytest_add2_scoring_risk_rerun`
- Logic result:
  - carriage assertions passed
- Environment failure:
  - one `PermissionError` on `build/pytest-risk-runtime-daily-breaker/...`

## Engine runtime targeted carriage
- Command:
  - `python -m pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py --tb=short --disable-warnings --basetemp=tmp_pytest_add2_engines_rerun3`
- Result:
  - `104 passed`

## Syntax validation
- Command:
  - `python -c "from pathlib import Path; ... compile(...)"` over modified files
- Result:
  - `PASS`

## Environment permission failures
- `python -m compileall src/scoring_backbone src/risk_backbone src/complete_enablers src/engines`
  - blocked by workspace `__pycache__` write permissions
- risk runtime suite fixture:
  - `build/pytest-risk-runtime-daily-breaker/...`
  - `PermissionError: [WinError 5] Access denied`

## Interpretation
- logic coverage for the carriage patch is green on targeted suites
- remaining failures observed during validation are environmental write-permission issues, not confirmed carriage logic regressions
