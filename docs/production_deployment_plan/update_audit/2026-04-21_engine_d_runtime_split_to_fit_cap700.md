# Engine D Runtime Split To Fit Cap700

## Objective

Close the `FILE_TOO_LONG` guardrail violation on `src/engines/engine_d/engine_d_runtime.py`
without changing Engine D runtime behavior, typed public models, refusal semantics, or DAG shape.

## Governing Constraints

- Keep `EngineDRuntimeStatus`, `EngineDRuntimeInput`, and `EngineDRuntimeResult`
  in `engine_d_runtime.py` as the canonical public runtime surface.
- Do not change runtime decision ordering.
- Do not introduce lazy-import bypasses or new dependency violations.
- Preserve full Engine D runtime test behavior.

## Files Changed

- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_result_builders.py`

## Implementation

The split is surgical:

- `engine_d_runtime.py` keeps:
  - runtime protocols
  - public runtime enums/models
  - `EngineDRuntime` orchestration methods
  - coordination evaluation / application
  - refusal finalization
- `engine_d_runtime_result_builders.py` now owns the runtime-result construction helpers:
  - `_build_runtime_result(...)`
  - `_build_hook_blocked_runtime_result(...)`
  - `_build_missing_scoring_audit_runtime_result(...)`
  - `_build_hard_blocked_runtime_result(...)`
  - `_build_selection_rejected_runtime_result(...)`
  - `_build_risk_runtime_result(...)`
  - `_build_accepted_runtime_result(...)`
  - `_build_circuit_breaker_blocked_result(...)`

The builder module imports the public runtime models only after they are defined in
`engine_d_runtime.py`, preserving compatibility and avoiding contract drift.

## Measured Result

- `src/engines/engine_d/engine_d_runtime.py`: `426` lines
- `src/engines/engine_d/engine_d_runtime_result_builders.py`: `344` lines

The original runtime file is now below the `700` line cap.

## Proof

### Syntax / imports

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_d/engine_d_runtime.py src/engines/engine_d/engine_d_runtime_result_builders.py` -> pass
- import smoke:
  - `from engines.engine_d.engine_d_runtime import EngineDRuntime` -> pass

### Engine D tests

- `rtk pytest -q tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py --basetemp=.test_tmp/pytest_engine_d_runtime_split2` -> `37 passed`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest_engine_d_runtime_full` -> `131 passed`

### Guardrails

- `python scripts/run_engineering_guardrails.py`
- result after this slice:
  - `new_violations=1`
  - `first_new_violation=tests/test_venue_adapters/test_binance_spot/test_credential_loader.py:40 MISSING_RETURN_ANNOTATION`

This confirms the `engine_d_runtime.py FILE_TOO_LONG` issue is no longer the first
remaining new guardrail violation.

### DAG

- `python scripts/run_dag_check.py` -> `VERDICT: PASS`

## Status

`COMPLETE`

This slice closed the requested `engine_d_runtime.py FILE_TOO_LONG` issue.

## Next Safe Step

The next visible new guardrail issue is outside Engine D runtime:

- `tests/test_venue_adapters/test_binance_spot/test_credential_loader.py:40`
  -> missing return annotation
