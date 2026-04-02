# V5.3 - BUILD-11 OPTION B LOCAL SHADOW CHAIN FIX AUDIT
## Date: 2026-04-03
## Status: ACTIVE

---

# 0. Object

This note freezes the targeted Build-11 correction wave executed after the
Option-B canonical realignment.

Goal:

- verify the real remaining Build-11 blockers on the current branch
- distinguish runtime-proof gaps from plain local code regressions
- fix only the local regression that broke the Shadow VPS chain

---

# 1. Regression found

After Option B, the current branch still contained a local runner drift in:

- `scripts/run_local_replay_shadow.py`

The runner still emitted `engine_c` and `engine_d` in three Build-11 surfaces:

- `component_assessments`
- dashboard engine metrics
- `active_engines`

This created a real local regression because the current contracts now enforce:

- Build-11 Shadow engines = `engine_a`, `engine_b`

Observed operational symptom:

- the Shadow VPS chain stopped before final sidecars were written
- service state degraded with:
  - `success_count=0`
  - `failure_count>0`
  - `last_error` containing
    `Build-11 Shadow engine assessment is out of scope`

---

# 2. Applied correction

The runner was corrected surgically in:

- `scripts/run_local_replay_shadow.py`

Applied changes:

- `component_assessments` now emit `engine_a`, `engine_b` only
- demo monitoring payload engine metrics now emit `engine_a`, `engine_b` only
- `active_engines` now stay at `engine_a`, `engine_b`

No doctrinal widening was introduced.

Build-11 remains:

- `A/B + Build-14`
- `30-day minimum`
- `shadow_report_ready` still required

---

# 3. Evidence after fix

Focused suites executed:

- `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - result: `7 passed`
- `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - result: `5 passed`
- `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_runtime_evidence.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - result: `7 passed`
- `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_shadow_runtime_evidence.py tests/test_protocols/test_shadow_report_builder.py tests/test_protocols/test_shadow_dashboard.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - result: `36 passed`

What this proves:

- the local replay runner now closes again
- the daily orchestrator closes again
- the long-running Shadow VPS launcher closes again
- the native websocket capture surface still passes in local simulated tests

---

# 4. Honest conclusion

This lot fixes a real local regression, but not the whole build.

Result:

- the local Build-11 chain is aligned again on the Option-B perimeter
- Build-11 still remains `STILL_PARTIAL`

Remaining honest blockers:

- no real target-environment `live_websocket` proof recorded in this lot
- no real 30-day production Shadow evidence recorded in this lot

Therefore:

- treat the local chain as repaired
- treat real runtime proof as the remaining frontier
