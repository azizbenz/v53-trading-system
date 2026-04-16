# 2026-04-16 — Order flow imbalance

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/order_flow_imbalance.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_order_flow_imbalance.py`

## Claims Implemented

- Added the canonical Cont-Kukanov-Stoikov best-bid/best-ask event contribution.
- Added governed cumulative OFI windowing with default 200 and hard cap 2000.
- Returned an audit-ready frozen record with canonical provenance fields.
- Added deterministic tests for sign convention, cumulative windowing, fallback to available events, and invalid inputs.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/order_flow_imbalance.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_order_flow_imbalance.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_order_flow_imbalance.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `13 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `vpin.py`.
