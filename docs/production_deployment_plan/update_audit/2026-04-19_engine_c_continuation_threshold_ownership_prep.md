## 1. Objective

Prepare local threshold ownership for Engine C continuation microstructure inputs without changing runtime behavior or claiming signed governance.

## 2. Docs Governants

- `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Engine C already had typed continuation score thresholds for `score_min` and `extension_pct_max`, but caller-provided continuation microstructure thresholds still lived as raw field defaults on `EngineCContinuationValidationInput` and `EngineCInput`.

## 4. Placement

This slice stays local to `src/engines/engine_c/` and does not introduce a signed resolver. It prepares the continuation caller-threshold seam so a future governed upstream resolver can target one explicit local ownership surface.

## 5. Files Changed

- `src/engines/engine_c/continuation_validator_c.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/__init__.py`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`

## 6. Claims Implemented

- Added explicit documented threshold ids:
  - `THR-C_OFI_MIN`
  - `THR-C_QUEUE_MIN`
  - `THR-C_VPIN_MAX`
- Added `EngineCContinuationCallerThresholds` as the single local ownership surface for caller-provided continuation microstructure thresholds.
- Added `ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE` with explicit `TO_CALIBRATE` status.
- Wired `EngineCContinuationValidationInput` defaults to the typed ownership surface.
- Wired `EngineCInput` continuation threshold defaults to the same typed ownership surface.
- Exported the new ownership seam through `engines.engine_c`.
- Added ownership tests for both validation-input defaults and runner-input defaults.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_c/continuation_validator_c.py src/engines/engine_c/engine_c_runner.py src/engines/engine_c/__init__.py tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py`
  - pass
- `rtk pytest -q tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py --basetemp=.test_tmp/pytest`
  - `42 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No signed resolver for Engine C continuation caller thresholds yet.
- No upstream adoption outside `engine_c`.
- No threshold id was invented for `kyle_lambda_max`; governance for that seam remains deferred.
- No semantic tightening of `vpin_max`; default remains `None`.

## 9. Risks / Open Questions

- The local ownership surface is ready, but the future signed resolver must respect the existing `None` semantics for `vpin_max` unless doctrine explicitly changes that behavior.
- `kyle_lambda_max` still lacks a documented THR id in the current target doctrine; that gap should be resolved at the governance layer, not guessed locally.

## 10. Completion Status

`PARTIAL`

This slice completes local ownership preparation only. It does not complete signed governance or broader input-assembly adoption.

## 11. Next Safe Step

Stay in Step 7 and prepare the next local Engine C threshold family that does not depend on a broader caller, or add an allowed upstream resolver only after the local ownership surfaces are explicitly closed.
