# Engine D Runner Split To Fit Cap700

## Objective

Close the `FILE_TOO_LONG` guardrail violation on `src/engines/engine_d/engine_d_runner.py`
without changing Engine D orchestration semantics, gate ordering, typed contracts, or
structured logs.

## Governing Constraints

- Keep `run_engine_d(...)` as the canonical orchestrator entrypoint.
- Do not change Engine D stage order or no-trade semantics.
- Do not introduce new engine surfaces or DAG violations.
- Preserve the existing `engine_d.__init__` import contract.

## Files Changed

- `src/engines/engine_d/engine_d_runner.py`
- `src/engines/engine_d/engine_d_runner_late_stages.py`

## Implementation

The split is surgical:

- `run_engine_d(...)` stays in `engine_d_runner.py`.
- Early gates remain in `engine_d_runner.py`:
  - guard
  - anti-revenge
  - history
  - reformation
  - marginal-value
- Late stages moved to `engine_d_runner_late_stages.py`:
  - `_evaluate_cost_stage(...)`
  - `_evaluate_conviction_stage(...)`
  - `_build_engine_d_emit_output(...)`

Backward-compatible re-export behavior was preserved by keeping
`EngineDDecision` and `EngineDInvalidation` imported in `engine_d_runner.py`,
because `src/engines/engine_d/__init__.py` still imports those names from that module.

## Measured Result

- `src/engines/engine_d/engine_d_runner.py`: `490` lines
- `src/engines/engine_d/engine_d_runner_late_stages.py`: `294` lines

The original runner dropped below the `700` line guardrail cap.

## Proof

### Syntax / imports

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_d/engine_d_runner.py src/engines/engine_d/engine_d_runner_late_stages.py` -> pass
- package import smoke:
  - `import engines.engine_d as m`
  - `hasattr(m, "run_engine_d") == True`

### Engine D tests

- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest_engine_d_runner_split` -> `131 passed`

### DAG

- `python scripts/run_dag_check.py` -> `VERDICT: PASS`

### Guardrails

- `python scripts/run_engineering_guardrails.py`
- result after this slice:
  - `new_violations=2`
  - `first_new_violation=src/engines/engine_d/engine_d_runtime.py:1 FILE_TOO_LONG`

This confirms the `engine_d_runner.py` size violation is no longer the first outstanding
new guardrail issue.

## Status

`COMPLETE`

This slice closed the requested `engine_d_runner.py FILE_TOO_LONG` issue.

## Deferred / Next Safe Step

The next safe follow-up is:

- `src/engines/engine_d/engine_d_runtime.py` -> `FILE_TOO_LONG`

That is now the first remaining new guardrail violation in the current worktree.
