# 2026-04-16 — Amihud illiquidity

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/amihud_illiquidity.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_amihud_illiquidity.py`

## Claims Implemented

- Added canonical rolling Amihud illiquidity estimator on close-price bars and dollar volume.
- Used the doc23 window semantics with 24h default and no embedded decision threshold.
- Returned a frozen audit-ready record with provenance hash.
- Added deterministic tests for manual parity, non-negativity, and input ordering.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/amihud_illiquidity.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_amihud_illiquidity.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_amihud_illiquidity.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `33 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `corwin_schultz_spread.py` or `pin.py` for the next diagnostics seam.
