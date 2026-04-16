# 2026-04-16 — Realized / effective spread

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/realized_effective_spread.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_realized_effective_spread.py`

## Claims Implemented

- Added canonical quoted/effective/realized spread diagnostics for live execution observations.
- Kept the formulas exactly at the diagnostic level from doc23.
- Returned a frozen audit-ready record carrying all three spread variants and provenance hash.
- Added deterministic tests for buy, sell, and crossed-book validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/realized_effective_spread.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_realized_effective_spread.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_realized_effective_spread.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: wire live execution observations from `execution_cost_meter` when ready.
