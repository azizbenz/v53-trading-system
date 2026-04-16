# 2026-04-16 — Hawkes intensity

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/hawkes_intensity.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_hawkes_intensity.py`

## Claims Implemented

- Added canonical univariate exponential-kernel Hawkes intensity evaluator.
- Kept the module honest: it evaluates intensity from pre-estimated `(mu, alpha, beta)` instead of pretending to do MLE.
- Returned a frozen audit-ready record with parameter-source provenance.
- Added deterministic tests for monotone intensity, ordering validation, and invalid evaluation time.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/hawkes_intensity.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_hawkes_intensity.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_hawkes_intensity.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: wire calibrated Hawkes parameters from the future estimation seam.
