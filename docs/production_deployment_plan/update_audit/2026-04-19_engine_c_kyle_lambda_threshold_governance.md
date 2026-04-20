## 1. Objective

Govern the optional Engine C `continuation_kyle_lambda_max` seam without inventing a new canonical `THR-C_*` id or changing continuation runtime semantics.

## 2. Docs Governants

- `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Engine C already enforced `kyle_lambda_max` locally in `continuation_validator_c.py`, but the upstream signed continuation-threshold resolver only governed:

- `THR-C_OFI_MIN`
- `THR-C_QUEUE_MIN`
- `THR-C_VPIN_MAX`

That left `continuation_kyle_lambda_max` outside the governed calibration path even though doc 30 requires a governed artifact when this seam is supplied.

## 4. Placement

The slice stays on the existing continuation threshold seam:

- local ownership remains in `src/engines/engine_c/continuation_validator_c.py`
- upstream governed resolution remains in `src/scoring_backbone/engine_c_continuation_thresholds.py`

No new Engine C caller or orchestration surface was created.

## 5. Files Changed

- `src/engines/engine_c/continuation_validator_c.py`
- `src/scoring_backbone/engine_c_continuation_thresholds.py`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py`
- `tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py`

## 6. Claims Implemented

- Added explicit local ownership metadata `kyle_lambda_max_threshold_id` on `EngineCContinuationCallerThresholds`.
- Kept `kyle_lambda_max_threshold_id` optional and defaulted to `None` because the doctrine does not freeze a canonical `THR-C_*` id for this seam yet.
- Extended `EngineCContinuationThresholdResolverConfig` with optional `kyle_lambda_max_threshold_id`.
- Extended `EngineCContinuationThresholdResolution` to carry optional `kyle_lambda_max`.
- Extended `to_engine_c_input_updates()` to emit `continuation_kyle_lambda_max` only when a governed threshold id is actually supplied.
- Added an explicit sanity cap seam `kyle_lambda_max_hard_cap` with policy-governed explanation, not a claimed doctrinal final cap.
- Preserved current Engine C behavior when no governed kyle-lambda threshold is supplied.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_c/continuation_validator_c.py src/scoring_backbone/engine_c_continuation_thresholds.py tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py --basetemp=.test_tmp/pytest`
  - `49 passed`
- `rtk pytest -q tests/test_engines/test_engine_c --basetemp=.test_tmp/pytest`
  - `95 passed`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_c_continuation_thresholds.py --basetemp=.test_tmp/pytest`
  - `5 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No broader caller outside `engine_c` adopts `build_engine_c_continuation_threshold_updates(...)` yet.
- No canonical doctrinal `THR-C_*` id was introduced for `continuation_kyle_lambda_max`.
- No change was made to `continuation_vpin_max` default semantics; it remains optional.
- No broader Engine C assembly/orchestration surface was created.

## 9. Risks / Open Questions

- The optional `kyle_lambda_max` governed path now exists, but the threshold-id convention for this seam remains caller-specified rather than canonically frozen.
- The `kyle_lambda_max_hard_cap` is intentionally only a generous sanity cap. If doctrine later fixes a canonical threshold family and cap, this resolver should be tightened to that source of truth.

## 10. Completion Status

`PARTIAL`

The local ownership seam and upstream governed resolver now cover optional `continuation_kyle_lambda_max`, but broader caller adoption outside `engine_c` is still absent and no canonical `THR-C_*` id is claimed.

## 11. Next Safe Step

Either:

- continue Step 7 on the next local Engine C threshold family that does not depend on a broader caller, or
- stop and wait for a real Engine C input owner outside `engine_c` before adopting the updated continuation resolver.
