# 2026-04-16 — Queue pressure

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/queue_pressure.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_queue_pressure.py`

## Claims Implemented

- Added canonical top-k queue-pressure / book-imbalance feature.
- Used doc23 formula `I_t = (Qb - Qa) / (Qb + Qa)` with default `K=5`.
- Returned a frozen audit-ready record with provenance hash.
- Added deterministic tests for positive, zero, fallback-depth, and invalid-input cases.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/queue_pressure.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_queue_pressure.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_queue_pressure.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `27 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `amihud_illiquidity.py` or `roll_spread.py` for cost-feasibility seams.
