# 2026-04-16 — Roll spread

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/roll_spread.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_roll_spread.py`

## Claims Implemented

- Added canonical Roll spread estimator from lag-one covariance of trade-price changes.
- Used the doc23 rule: `2 * sqrt(-Cov)` if covariance is negative, else `0`.
- Returned a frozen audit-ready record with covariance and provenance hash.
- Added deterministic tests for negative-covariance spread recovery, zero fallback, and ordering validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/roll_spread.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_roll_spread.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_roll_spread.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `33 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `corwin_schultz_spread.py` or `pin.py` for the next diagnostics seam.
