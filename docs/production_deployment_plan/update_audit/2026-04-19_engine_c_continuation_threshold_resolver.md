## 1. Objective

Add an allowed upstream signed-threshold resolver for the documented Engine C continuation caller thresholds without changing Engine C runtime semantics.

## 2. Docs Governants

- `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Engine C continuation threshold ownership is now explicit locally in `continuation_validator_c.py`, but there was still no upstream signed resolver equivalent to the A/B governance pattern.

## 4. Placement

The resolver lands in `src/scoring_backbone/` so `calibration_loader` remains upstream of `engine_c`. It returns additive updates targeted at caller-owned `EngineCInput` fields:

- `continuation_ofi_min`
- `continuation_queue_min`
- `continuation_vpin_max`

`continuation_kyle_lambda_max` remains out of scope because the current doctrine does not provide a canonical THR id for that seam.

## 5. Files Changed

- `src/scoring_backbone/engine_c_continuation_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py`

## 6. Claims Implemented

- Added `EngineCContinuationThresholdResolverConfig`.
- Added `EngineCContinuationThresholdResolution`.
- Added `resolve_engine_c_continuation_thresholds(...)`.
- Added `build_engine_c_continuation_threshold_updates(...)`.
- Enforced signed-resolution validation for:
  - `THR-C_OFI_MIN`
  - `THR-C_QUEUE_MIN`
  - `THR-C_VPIN_MAX`
- Enforced documented `THR-C_VPIN_MAX <= 0.5` via resolver hard cap.
- Kept OFI hard-cap treatment explicitly as a sanity cap because doctrinal OFI scale is not yet frozen.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/scoring_backbone/engine_c_continuation_thresholds.py src/scoring_backbone/__init__.py tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py src/engines/engine_c/continuation_validator_c.py src/engines/engine_c/engine_c_runner.py src/engines/engine_c/__init__.py tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py --basetemp=.test_tmp/pytest`
  - `45 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No broader caller outside `engine_c` adopts `build_engine_c_continuation_threshold_updates(...)` yet.
- No signed resolver for `continuation_kyle_lambda_max`.
- No claim that Engine C continuation thresholds are fully promoted; this slice only adds the upstream resolver seam.

## 9. Risks / Open Questions

- `THR-C_OFI_MIN` does not yet have a doctrinally frozen scale cap; the resolver uses a generous sanity cap rather than pretending the final OFI calibration scale is already settled.
- If doctrine later pins a canonical OFI scale or queue-threshold cap, this resolver should be tightened to match that source of truth.

## 10. Completion Status

`PARTIAL`

The upstream resolver exists and is tested, but broader caller adoption is still absent.

## 11. Next Safe Step

Either:

- continue Step 7 on the next local Engine C threshold family that can be closed without a broader caller, or
- stop and wait for a real Engine C input owner outside `engine_c` before adopting the new resolver.
