# 09_MICROSTRUCTURE_MEASURES_A

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-16_microstructure_feature_registry.md
- docs/production_deployment_plan/update_audit/2026-04-16_order_flow_imbalance.md
- docs/production_deployment_plan/update_audit/2026-04-16_realized_kernel_vol.md
- docs/production_deployment_plan/update_audit/2026-04-16_vpin.md
- docs/production_deployment_plan/update_audit/2026-04-16_queue_pressure.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_microstructure_feature_registry.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_order_flow_imbalance.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_realized_kernel_vol.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_vpin.md

# 2026-04-16 — VPIN

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/vpin.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_vpin.py`

## Claims Implemented

- Added the canonical equal-volume VPIN estimator with bucket-level BVC.
- Enforced doc 29 caps for `THR-C_VPIN_BUCKETS` and `THR-C_VPIN_N_BUCKETS_WINDOW`.
- Kept toxicity-threshold policy out of the calculator because crypto `THR-C_VPIN_MAX` remains `TBD_shadow_calibration`.
- Added deterministic tests for bucket splitting, one-sided boundary case, unit-interval behavior, defaults, and invalid inputs.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/vpin.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_vpin.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_vpin.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `18 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `queue_pressure.py` or `kyle_lambda.py` according the next governed dependency.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_queue_pressure.md

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


