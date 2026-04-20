## Objective

Freeze operational governance around Engine D anti-revenge/reset thresholds `THR-X10` and `THR-X11` without changing Engine D trading semantics or inventing a new orchestration surface.

## Docs Governants

- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md`

## Current Code Seam

Current D code already had:

- the canonical coordination-threshold contract in `src/protocols/engine_coordination_rules.py`
- existing D consumption seams in:
  - `src/engines/engine_d/engine_d_runtime.py`
  - `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
  - `src/engines/engine_d/runtime_input_assembler_d.py`
  - `src/engines/engine_d/coordination_input_assembler_d.py`

What was missing was an upstream governed resolver for:

- `THR-X10` -> `d_reset_failsafe_ns`
- `THR-X11` -> `d_consecutive_stop_limit`

Doc 22 marks these thresholds as policy-governed, not calibration-artifact-governed. This slice preserves that distinction.

## Placement

The new upstream governance seam lands in:

- `src/scoring_backbone/engine_d_coordination_thresholds.py`

This placement is deliberate:

- it stays outside `engine_d`
- it does not introduce `engine_d -> calibration_loader`
- it does not create a second coordination rule engine
- it produces caller-owned updates that can be fed into the existing canonical `EngineCoordinationThresholds` contract

## Files Changed

- `src/scoring_backbone/engine_d_coordination_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `tests/test_scoring_backbone/test_engine_d_coordination_thresholds.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`

## Claims Implemented

1. Added a policy-governed upstream resolver for Engine D coordination thresholds.
2. Fixed canonical threshold ids in the resolver surface:
   - `THR-X10`
   - `THR-X11`
3. Enforced doc-22 defaults and hard caps:
   - `THR-X10`: default `24h`, hard cap `48h`
   - `THR-X11`: default `1`, hard cap `3`
4. Exposed caller-facing updates in current runtime units:
   - `d_reset_failsafe_ns`
   - `d_consecutive_stop_limit`
5. Proved that the existing Engine D runtime seam consumes the governed updates via the canonical `EngineCoordinationThresholds` contract.
6. Kept the slice policy-governed rather than pretending these thresholds are signed calibration artifacts.

## Tests and Proof

- `$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile src/scoring_backbone/engine_d_coordination_thresholds.py src/scoring_backbone/__init__.py tests/test_scoring_backbone/test_engine_d_coordination_thresholds.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_d_coordination_thresholds.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py --basetemp=.test_tmp/pytest`
  - `12 passed`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_d_coordination_thresholds.py tests/test_protocols/test_engine_coordination_rules.py --basetemp=.test_tmp/pytest`
  - `11 passed`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
  - `120 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - fails on the same pre-existing repo-global baseline:
    - cycle `execution_backbone -> venue_adapters -> execution_backbone`
    - unauthorized imports involving `engine_a`, `engine_b`, `engine_c`, `engine_d`, `execution_backbone`, and `protocols`

## Deferred / Not Done

- No broader runtime owner outside current D seams adopts the new policy resolver yet.
- No signed-calibration resolver was added for `THR-X10` / `THR-X11`, because doc 22 marks them as policy-governed.
- No change to `ce_min_D` / `delta_safe_D` governance in this slice.
- No broader orchestration surface was created.

## Risks / Open Questions

- Production adoption still depends on a real upstream caller passing the resolved updates into `EngineCoordinationThresholds`.
- Repo-global DAG/import-policy failures remain external blockers and keep repository-scope proof partial.
- If doctrine later moves `THR-X10` / `THR-X11` from policy-governed to signed-calibration-governed, this resolver will need to be migrated rather than silently reused as if equivalent.

## Completion Status

`PARTIAL`

This slice closes the upstream governance gap for `THR-X10` / `THR-X11` and proves compatibility with the current Engine D runtime seam. It remains `PARTIAL` because no broader caller outside the existing D package public seams adopts the resolver yet, and repo-global DAG proof remains red outside this slice.

## Next Safe Step

Adopt `build_engine_d_coordination_threshold_updates(...)` in the first truthful upstream owner that already constructs `EngineCoordinationThresholds` for Engine D, without creating a synthetic orchestrator. In parallel, keep `ce_min_D` / `delta_safe_D` governance explicit and separate.
