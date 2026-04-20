## 1. Objective

Govern and land `THR-D_MIN_GAP` on the existing public Engine D historical-entry seam, without inventing a new orchestrator and without moving the rule into `engine_coordination_rules`.

## 2. Docs Governants

- `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Before this slice:

- `THR-D_LOOKBACK` was governed and publicly adopted
- `THR-D_MIN_GAP` was still deferred
- the truthful landing seam already existed in:
  - `first_episode_resolver_d.py`
  - `runtime_input_assembler_d.py`
  - `engine_d_runtime_history_entry_mixin.py`
  - `engine_d_runtime.py`

No real broader caller outside `engine_d` was required to land the rule on the existing public Engine D historical-entry surface.

## 4. Placement

This slice keeps the rule on the current D historical-entry stack:

- local threshold ownership in `src/engines/engine_d/first_episode_resolver_d.py`
- upstream signed resolution in `src/scoring_backbone/engine_d_first_episode_thresholds.py`
- runtime-input inspection in `src/engines/engine_d/runtime_input_assembler_d.py`
- public adoption in `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- enforcement in `src/engines/engine_d/engine_d_runtime.py`

`THR-D_MIN_GAP` is intentionally not routed through `engine_coordination_rules`, because it is a D-local structural timing rule, not the shared coordination canon.

## 5. Files Changed

- `src/engines/engine_d/first_episode_resolver_d.py`
- `src/engines/engine_d/runtime_input_assembler_d.py`
- `src/engines/engine_d/engine_d_runtime_history_entry_mixin.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/__init__.py`
- `src/scoring_backbone/engine_d_first_episode_thresholds.py`
- `tests/test_engines/test_engine_d/test_first_episode_resolver_d.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`
- `tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py`

## 6. Claims Implemented

- Added local typed ownership for:
  - `THR-D_MIN_GAP`
- Extended `EngineDFirstEpisodeCallerThresholds` with:
  - `min_gap_ns`
  - `min_gap_threshold_id`
- Added explicit D-local gap inspection:
  - `FirstEpisodeGapInspectionD`
  - `inspect_first_episode_gap(...)`
- Added fail-closed behavior when `first_episode_ref.closed_at_ns` is missing:
  - `hard_block.d_first_episode_timestamp_missing`
- Added explicit gap-not-elapsed hard block:
  - `hard_block.d_min_gap_not_elapsed`
- Extended the upstream signed resolver to optionally resolve:
  - `THR-D_MIN_GAP`
- Added public runtime adoption:
  - `EngineDRuntime(first_episode_min_gap_ns=...)`
  - `evaluate_from_historical_state(...)` uses the governed gap when the caller does not override it
- Enforced the gap on the existing public Engine D historical-entry runtime path before coordination evaluation.

## 7. Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_d/first_episode_resolver_d.py src/engines/engine_d/runtime_input_assembler_d.py src/engines/engine_d/engine_d_runtime_history_entry_mixin.py src/engines/engine_d/engine_d_runtime.py src/engines/engine_d/__init__.py src/scoring_backbone/engine_d_first_episode_thresholds.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py`
  - pass
- `rtk pytest -q tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py tests/test_engines/test_engine_d/test_first_episode_resolver_d.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py --basetemp=.test_tmp/pytest`
  - `53 passed`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
  - `128 passed`
- `rtk pytest -q tests/test_scoring_backbone/test_engine_d_first_episode_thresholds.py --basetemp=.test_tmp/pytest`
  - `5 passed`
- `python scripts/run_engineering_guardrails.py`
  - repo-global run still reports `new_violations=3`, but the reported new violations are outside this slice:
    - `src/engines/engine_a/engine_a_runtime.py` `FILE_TOO_LONG`
    - `src/engines/engine_a/engine_a_runtime.py` `BARE_EXCEPT`
  - no touched D file is reported as a new guardrail violation after the runtime file was reduced below the max length
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline failure with 9 pre-existing violations outside this slice

## 8. Deferred / Not Done

- No broader caller outside `engine_d` adopts `build_engine_d_first_episode_threshold_updates(...)`.
- `THR-D_LOOKBACK` and `THR-D_MIN_GAP` share the same upstream resolver seam, but broader production caller adoption is still local to the current public Engine D runtime surface.
- No `structure_reformation_detector_d.py` module was created; the min-gap rule lands on the truthful existing historical-entry seam instead.

## 9. Risks / Open Questions

- The local/public adoption is real for Engine D, but broader caller adoption outside `engine_d` is still absent.
- Repo-global guardrail cleanliness cannot be claimed for this slice because unrelated new violations are present elsewhere in the dirty worktree.
- If doctrine later introduces a dedicated `structure_reformation_detector_d.py`, this min-gap inspection may need to move there, but only if that module becomes a real owner seam rather than a synthetic split.

## 10. Completion Status

`PARTIAL`

The `THR-D_MIN_GAP` seam is now governed and adopted on the existing public Engine D historical-entry runtime path, with targeted tests green. Status remains partial because broader caller adoption outside `engine_d` is still absent and repo-global guardrails are currently red due unrelated worktree changes outside this slice.

## 11. Next Safe Step

Wait for a truthful broader caller outside `engine_d` before pushing wider adoption, or move to another real open doctrinal slice that does not depend on inventing architecture.
