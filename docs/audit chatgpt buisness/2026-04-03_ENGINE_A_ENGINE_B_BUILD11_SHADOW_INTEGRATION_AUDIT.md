# 2026-04-03 - Engine A/B Build-11 Shadow Integration Audit

## Scope

Close the Build-11 local Shadow runner gap where `engine_a` and `engine_b`
were still rendered with synthetic component verdicts and hard-coded
dashboard metrics, while `engine_c` and `engine_d` were already executed
through their real runtimes.

## Findings Frozen Before Fix

- `scripts/run_local_replay_shadow.py` defaulted `engine_a` and `engine_b`
  to `SHADOW_VALIDATED` when no runtime evidence existed.
- Candidate payload engine metrics for `engine_a` and `engine_b` were still
  hard-coded in the local Shadow runner.
- `engine_a` and `engine_b` were strong in isolation, but not yet proven
  honestly inside the Build-11 local Shadow chain.

## Applied Fix

### Runner

- Added real Build-11 local Shadow execution for:
  - `engine_a`
  - `engine_b`
- Reused the same governed scoring/risk runtime pattern already used for
  `engine_c` and `engine_d`.
- Added `breakout_warning` to the local Shadow penalty registry so the
  `engine_b` runtime path can remain canonical if that warning path appears.
- Extended `engine_shadow_evidence` to persist `engine_a`, `engine_b`,
  `engine_c`, `engine_d` in runtime order.
- Candidate payload monitoring metrics for `engine_a` and `engine_b` now read
  from runtime evidence instead of demo constants when evidence is available.

### Tests

- Updated `tests/test_protocols/test_local_replay_shadow_runner.py` to assert:
  - 4 engine evidence entries
  - accepted runtime status for `engine_a` and `engine_b`
  - real evidence summaries for `engine_a` and `engine_b`

## Evidence

### Targeted green surface

- `rtk pytest tests/test_engines/test_engine_a tests/test_engines/test_engine_b tests/test_protocols/test_local_replay_shadow_runner.py -q`
- Result: `132 passed`

### Broader Build-11 adjacent green surface

- `rtk pytest tests/test_engines/test_engine_a tests/test_engines/test_engine_b tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_shadow_day_counter.py tests/test_regression_alignment.py -q`
- Result: `217 passed`

### Runtime surface sanity

- `rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q`
- Result: `21 passed`

## Current Interpretation

- `engine_a` and `engine_b` remain healthy as standalone engines.
- The local Build-11 Shadow runner is now materially more honest: all four
  canonical engines `A/B/C/D` are executed before component verdicts and
  engine metrics are rendered.
- This still does **not** prove the real 30-day target-environment Shadow.
  It only closes the local Build-11 integration gap for `A/B`.
