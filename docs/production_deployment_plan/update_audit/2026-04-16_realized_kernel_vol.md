# 2026-04-16 — Realized kernel volatility

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/realized_kernel_vol.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_realized_kernel_vol.py`

## Claims Implemented

- Added the canonical Parzen-kernel realized-kernel calculator.
- Enforced doc 21 / doc 29 caps for `THR-C_RK_BANDWIDTH_C` and `THR-C_RK_BUCKET_SIZE`.
- Returned an audit-ready frozen record with `value`, `window_used`, `n_events_used`, `method_version_hash`, `pair`, `computed_at_ns`, and `input_data_hash`.
- Added deterministic proof tests for Parzen shape, bandwidth rule, manual small-case parity, and cap validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/realized_kernel_vol.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_realized_kernel_vol.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_realized_kernel_vol.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `13 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `vpin.py` after keeping the current registry / realized-kernel / OFI test pack green.
