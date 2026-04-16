# 2026-04-16 — Engine C continuation microstructure wiring

## Objective

Wire the canonical microstructure package into the first governed consumer seam for Engine C without rewriting the runtime rail.

## Docs Governants

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Current Code Seam

- `src/engines/engine_c/engine_c_runner.py` already owned Stage 2 continuation viability.
- `src/engines/engine_c/engine_c_runtime.py` already consumed only `EngineCOutput` and must remain compatible.
- `src/data_backbone/microstructure/*` now exists, but Engine C was not consuming any of its signals yet.

## Placement

- New pure validator seam in `src/engines/engine_c/continuation_validator_c.py`
- Additive fields on `EngineCInput`, `EngineCLogEntry`, and `EngineCOutput`
- Runner wiring only in `engine_c_runner.py`
- Runtime compatibility pass-through only in `engine_c_runtime.py`

## Files Changed

- `src/engines/engine_c/signal_math_c.py`
- `src/engines/engine_c/continuation_validator_c.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/__init__.py`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`

## Claims Implemented

- Added a pure `continuation_validator_c` seam that applies continuation maturity plus additive OFI / queue pressure / VPIN gates.
- Kept Engine C runtime architecture unchanged: the runtime still consumes `EngineCOutput`; no new profile, no new engine, no gate bypass.
- Made microstructure gating transitional and explicit:
  - OFI and queue pressure gate only when metrics are provided.
  - VPIN gate only when both `vpin` and `continuation_vpin_max` are provided.
  - If metrics are absent, the legacy continuation path remains active and auditable.
- Added audit fields to runner/runtime logs and outputs:
  - `cumulative_ofi`
  - `queue_pressure`
  - `vpin`
  - `kyle_lambda`
  - `microstructure_gate_applied`
- Added a new no-trade category `microstructure_unconfirmed` to separate structural continuation failure from microstructure confirmation failure.

## Tests and Proof

- `python -m py_compile src\engines\engine_c\signal_math_c.py src\engines\engine_c\continuation_validator_c.py src\engines\engine_c\engine_c_runner.py src\engines\engine_c\engine_c_runtime.py src\engines\engine_c\__init__.py tests\test_engines\test_engine_c\test_continuation_validator_c.py tests\test_engines\test_engine_c\test_engine_c.py tests\test_engines\test_engine_c\test_engine_c_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_data_backbone/microstructure/test_order_flow_imbalance.py tests/test_data_backbone/microstructure/test_queue_pressure.py tests/test_data_backbone/microstructure/test_vpin.py`
- `python scripts/run_engineering_guardrails.py`
- Proof executed:
  - `py_compile` passed
  - `Pytest: 36 passed`
  - `new_violations=0`

## Deferred / Not Done

- Engine C runtime does not compute OFI / queue pressure / VPIN itself yet; it consumes precomputed values through `EngineCInput`.
- `kyle_lambda` is surfaced in logs/output but not yet used as a hard gate because no governed threshold was introduced in this slice.
- No scoring-weight change was made; microstructure acts as a governed continuation gate, not a new scoring feature.

## Risks / Open Questions

- `THR-C_VPIN_MAX` remains `TBD_shadow_calibration`; the runner only applies the VPIN veto when the threshold is explicitly supplied.
- Upstream wiring from real order-book / trade streams into `EngineCInput` still needs a dedicated seam to avoid duplicate calculation paths.

## Completion Status

- `COMPLETE`

## Next Safe Step

- Wire a single upstream Engine C assembler that maps canonical microstructure records into `EngineCInput` without teaching the runtime to compute LOB features inline.
