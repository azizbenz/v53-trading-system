# 2026-04-16 — Kyle lambda

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_kyle_lambda.py`

## Claims Implemented

- Added a narrow rolling-OLS Kyle lambda estimator.
- Used Lee-Ready first, tick-rule fallback, and 1-minute interval aggregation before regression.
- Used default 1h rolling window with 4h hard cap.
- Marked non-positive or zero-variance estimates as stale instead of silently accepting them.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/kyle_lambda.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_kyle_lambda.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_kyle_lambda.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `27 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `amihud_illiquidity.py` or `roll_spread.py` for cost-feasibility seams.
