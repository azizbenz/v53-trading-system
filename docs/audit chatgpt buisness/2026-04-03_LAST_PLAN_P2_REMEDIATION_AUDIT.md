# V5.3 - LAST PLAN P2 REMEDIATION AUDIT
## Date: 2026-04-03
## Branch: codex/full-shadow-abcd-migration-20260403
## Status: FROZEN

---

# 0. Scope

Remediate the two remaining `P2` findings from:

- `docs/audit chatgpt buisness/2026-04-03_LAST_PLAN_EXECUTION_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-03_LAST_PLAN_P1_REMEDIATION_AUDIT.md`

This wave closes the remaining local reporting/demo gaps for the last Build-9X / Build-14 plan. It does not replace or shorten the real Build-11 runtime campaign.

---

# 1. Verdict

The two `P2` findings from the last execution audit are now **closed on the current branch**.

## Closed finding 1

`Build-11` Shadow reporting now captures `Build-14` at the reader level in addition to the family level.

What changed:

- `src/protocols/contracts.py` now exposes `ShadowBuild14ReaderContribution`
- `src/protocols/shadow_report_builder.py` now projects per-reader Build-14 metrics when `reader_projections` exist on the payload
- `src/protocols/shadow_day_counter.py` now aggregates those reader metrics into optional `build14_reader_contribution` entries in the persisted shadow report

Impact:

- the persisted Build-11 report is no longer limited to `build14_*` family aggregates only
- reader-level Build-14 facts are now available in the same audit-ready report artifact without changing promotion readiness logic
- `shadow_report_ready` still depends on the canonical family-level sections only, so the 30-day gate semantics stay unchanged

## Closed finding 2

The technical dashboard demo launcher no longer seeds Build-14 addendum inputs with fixed local constants.

What changed:

- `src/monitoring/build14_observation.py` now derives `Build14ObservationInput` from governed monitoring facts
- `scripts/run_technical_dashboard.py` now uses `derive_build14_observation_from_payload(...)`
- `scripts/run_local_replay_shadow.py` now uses the same shared derivation path through `derive_build14_observation_from_snapshot(...)`

Impact:

- the two local launchers now share one explicit derivation path for Build-14 observation facts
- the addendum readers are still deterministic in local/demo mode, but no longer depend on hidden hard-coded values
- this removes ambiguity while preserving the same rollout doctrine and avoiding any automatic live mutation

---

# 2. Proof

Focused green evidence:

- `rtk pytest tests/test_monitoring/test_build14_observation.py tests/test_protocols/test_shadow_report_builder.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_protocols/test_contracts.py tests/test_manifest_registry/test_runtime_surface.py -q`
  - `96 passed`
- `rtk pytest tests/test_monitoring tests/test_protocols/test_shadow_report_builder.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_contracts.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_manifest_registry/test_runtime_surface.py -q`
  - `172 passed`

Key test intent:

- `tests/test_monitoring/test_build14_observation.py`
  - proves the new Build-14 observation helper reacts to real monitoring stress and stays consistent between snapshot and payload derivation
- `tests/test_protocols/test_shadow_report_builder.py`
  - proves reader-level Build-14 metrics are now projected into the daily Shadow summary
- `tests/test_protocols/test_shadow_day_counter.py`
  - proves the 30-day report now persists optional reader-level Build-14 contributions without changing readiness semantics

---

# 3. Conclusion

The last Build-9X / Build-14 plan is now locally closed on the current branch:

- explicit Build-9X merge gates are operationalized
- Build-14 addendum readers exist
- Build-14 reader observability is visible across monitoring/UI
- the local Shadow report now carries reader-level Build-14 evidence
- the local dashboard/demo path now uses a governed shared derivation helper instead of hard-coded addendum constants

The next prod-safe step remains the same:

- continue the real Build-11 target-environment Shadow campaign day by day
- do not mistake local reporting closure for 30-day runtime closure
