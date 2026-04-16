# 2026-04-16 — Microstructure feature registry

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/feature_registry.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_feature_registry.py`

## Claims Implemented

- Added the canonical `MicrostructureFeatureSpec` contract with frozen Pydantic v2 semantics.
- Added isolated doc23 promotion ladder for microstructure features.
- Registered the full doc23 feature set before any calculator implementation.
- Added immutable lookup helpers and governed promotion-transition helper.
- Exported the registry through `data_backbone` without changing existing market-physics APIs.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/feature_registry.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_feature_registry.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_feature_registry.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed: `4 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: implement `realized_kernel_vol.py` as the first calculator upstream dependency from doc 23 order.
