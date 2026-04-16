# 2026-04-16 — Corwin-Schultz spread

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/corwin_schultz_spread.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py`

## Claims Implemented

- Added canonical Corwin-Schultz high-low spread estimator on the last two ordered bars.
- Kept the implementation faithful to the doc23 abbreviated formula.
- Returned a frozen audit-ready record with `beta`, `gamma`, `alpha`, and provenance hash.
- Added deterministic tests for positive spread, negative-value clamp, and ordering validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/corwin_schultz_spread.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: integrate these diagnostics into governed consumers.
