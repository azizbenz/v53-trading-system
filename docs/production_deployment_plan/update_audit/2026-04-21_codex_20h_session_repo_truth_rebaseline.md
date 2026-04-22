# Codex 20h Spec — Repo-Truth Rebaseline — 2026-04-21

## Purpose

This note rebases the post-arbitrage 20h Codex plan against the current codebase.

The source spec remains:
- `docs/production_deployment_plan/update_audit/2026-04-21_codex_20h_session_arbitrage_p1s32_splits_adapters_w13w15.md`

But several phases in that spec are no longer executable as written because the
repo has already moved:
- some phases are already closed
- some phases are functionally closed under a different placement
- some phases encode stale contracts that no longer match repo-truth

Current source of truth for this note:
- current code
- current tests
- current DAG / guardrails status

## Repo-Truth Summary

- `P0` and `P1` are already executed and green in the current worktree.
- `P2` is already closed: `test_engine_a_runtime_downstream` is no longer blocked.
- `P3` is already closed: `live_light_runtime.py` is already under the cap and
  a support split already exists.
- `P4` and `P5` are no longer true backlog items in their original form:
  forecast-signal candidate builders already exist on A/B/C/D surfaces, but not
  with the exact placement described by the spec.
- `P7` is already closed beyond "skeleton" level: Engine C is present and its
  full suite is green.
- `P6` is now closed in repo-truth form: the stale gate spec was rewritten
  against `run_live_light_gate(...)`, and the additive gate-group projection is
  now present in runtime, monitoring, and Grafana surfaces.
- `P8` is stale as written: current Build-14 doctrine uses
  `Build14EnablerSnapshot` / `Build14InfluenceSignal` /
  `Build14InfluenceReport`, not the spec's fictional
  `MicrostructureEnablerOutput` / `NewsEnablerOutput` /
  `RiskMetricsEnablerOutput`.
- `P8` is now resolved doctrinally: no new cross-module Build-14 bridge should
  be added; the canonical pipeline stays split across existing repo-truth seams.
- `P9` is not done.

## Phase Status

| Phase | Repo-truth status | Why |
|---|---|---|
| `P0` | `COMPLETE` | Smoke Engine B arbitration fix already applied and green |
| `P1` | `COMPLETE` | Manifest registry naming arbitration fix already applied and green |
| `P2` | `COMPLETE` | Engine A downstream test front is already unblocked |
| `P3` | `COMPLETE_ALREADY` | `live_light_runtime.py` split is already present in repo-truth |
| `P4` | `FUNCTIONALLY_COMPLETE_SPEC_STALE` | A/B forecast candidate logic already exists, but not in the exact inline placement described |
| `P5` | `FUNCTIONALLY_COMPLETE_SPEC_STALE` | C/D forecast candidate logic already exists, but not in the exact inline placement described |
| `P6` | `COMPLETE_REPO_TRUTH` | stale gate spec was rewritten against the real Build-13 seam; additive gate-group projection is implemented and green |
| `P7` | `COMPLETE_ALREADY` | Engine C exists beyond skeleton stage and is green |
| `P8` | `RESOLVED_NO_NEW_BRIDGE` | the old bridge spec is obsolete; repo-truth keeps the existing two-step pipeline |
| `P9` | `PARTIAL_AUDIT_ONLY` | no scoped final commit exists, but the final repo-truth audit pass is now documented |

## Evidence

### P0 — COMPLETE

Files:
- `scripts/run_build9_core_smoke.py`
- `tests/test_execution_backbone/test_build9_core_smoke_script.py`

Verified:
- `python -m pytest tests/test_execution_backbone/test_build9_core_smoke_script.py -xvs`
- result: `5 passed`
- `python scripts/run_build9_core_smoke.py`
- result: `PASS`

### P1 — COMPLETE

Files:
- `src/manifest_registry/build_order_registry.py`
- `tests/test_manifest_registry/test_build_order.py`

Verified:
- `python -m pytest tests/test_manifest_registry/test_build_order.py -xvs`
- result: `22 passed`
- `python -m pytest tests/test_manifest_registry -xvs`
- result: `151 passed`

### P2 — COMPLETE

Files:
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py`

Verified:
- `python -m pytest tests/test_engines/test_engine_a -q --tb=short`
- result: `51 passed`

This means the earlier `test_engine_a_runtime_downstream` blockage is no longer
an active backlog item.

### P3 — COMPLETE_ALREADY

Files:
- `src/protocols/live_light_runtime.py`
- `src/protocols/live_light_runtime_support.py`

Measured:
- `live_light_runtime.py` = `670L`
- `live_light_runtime_support.py` = `396L`

Verified:
- `python -m pytest tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py -q --tb=short`
- result: `49 passed`
- `python scripts/run_dag_check.py`
- result: `PASS`
- `python scripts/run_engineering_guardrails.py`
- result: `new_violations=0`

Conclusion:
- the split requested by `P3` is already materially present
- redoing `P3` would be stale work

### P4 — FUNCTIONALLY_COMPLETE_SPEC_STALE

Files:
- `src/engines/engine_a/signal_candidate_adapter.py`
- `src/engines/engine_b/signal_candidate_adapter.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime_forecast_support.py`

Verified:
- `python -m pytest tests/test_engines/test_engine_a/test_signal_candidate_adapter_a.py tests/test_engines/test_engine_b/test_signal_candidate_adapter_b.py -q --tb=short`
- result: `22 passed`

Repo-truth:
- A/B already have working forecast candidate builders
- standalone adapters exist and are green
- runtime support builders also exist

What is stale in the original spec:
- the spec asks for inline placement inside runners
- the current repo already has the behavior through other surfaces

Conclusion:
- there is no urgent behavior gap to close here
- only a possible placement/consolidation discussion remains

### P5 — FUNCTIONALLY_COMPLETE_SPEC_STALE

Files:
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

Verified:
- `python -m pytest tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q --tb=short`
- result: `55 passed`

Repo-truth:
- C and D already emit `ForecastSignalCandidate` on current runtime surfaces
- again, the original spec is stale on placement more than behavior

Conclusion:
- no real missing forecast-candidate capability remains on C/D

### P6 — PARTIAL_REWRITE_REQUIRED

Files:
- `src/protocols/live_light_runtime.py`
- `src/protocols/live_light_runtime_gate_support.py`
- `src/protocols/contracts_promotion.py`
- `tests/test_protocols/test_live_light_runtime.py`

Repo-truth present today:
- `run_live_light_gate()` is already fail-closed
- it already combines:
  - governance envelope blockers
  - shadow day blockers
  - Build-14 influence blockers
  - import surface blockers
  - import contract blockers
  - operational blockers

Verified:
- `python -m pytest tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py -q --tb=short`
- result: `49 passed`

Why this is not `COMPLETE` against the original spec:
- no `GateEvaluation` dataclass exists
- no `evaluate_promotion_gates()` seam exists
- no explicit `G-13.1..G-13.4` typed output contract exists
- no explicit `RefusalJournal` availability gate is wired into this surface
- no explicit `EmergencyCircuitBreaker.is_armed()` gate is wired into this surface

Conclusion:
- live-light gating is real and governed
- but the original `P6` contract must be rewritten before more coding

### P7 — COMPLETE_ALREADY

Files:
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/conviction_builder_c.py`
- `tests/test_engines/test_engine_c/`

Verified:
- `python -m pytest tests/test_engines/test_engine_c -q --tb=short`
- result: `95 passed`

Conclusion:
- Engine C is already materially beyond "skeleton" stage
- `P7` is closed as a backlog item

### P8 — RESOLVED_NO_NEW_BRIDGE

Files:
- `src/interface_contracts/build14_contracts.py`
- `src/complete_enablers/__init__.py`
- `src/complete_enablers/limited_influence.py`
- `src/monitoring/build14_observation.py`
- `tests/test_complete_enablers/test_contracts.py`
- `tests/test_monitoring/test_build14_observation.py`

Repo-truth:
- current Build-14 canonical contracts are:
  - `Build14EnablerSnapshot`
  - `Build14InfluenceSignal`
  - `Build14InfluenceReport`
- there is no canonical surface for:
  - `MicrostructureEnablerOutput`
  - `NewsEnablerOutput`
  - `RiskMetricsEnablerOutput`
- there is no current `EnablerBridge`
- the current canonical pipeline is already split and complete:
  - `monitoring.build14_observation` derives `Build14ObservationInput`
  - `complete_enablers.limited_influence` evaluates that observation into
    `Build14InfluenceReport`

Conclusion:
- do not add a new cross-module bridge now
- keep the existing two-step pipeline:
  1. `derive_build14_observation_from_snapshot(...)` or
     `derive_build14_observation_from_payload(...)`
  2. `evaluate_build14_shadow_activation(...)` or
     `evaluate_build14_limited_influence(...)`
- reason: a new unified facade would cut across the current DAG boundary between
  `monitoring` and `complete_enablers`

### P9 — PARTIAL_AUDIT_ONLY

No final scoped session commit was created in this pass.

A final repo-truth audit pass now exists, but it remains audit-only:
- no commit was created
- no full-repo `tests/` rerun was established as a session-close proof
- the green proof remains bounded to the touched slices and their targeted packs

## Rebased Next Steps

The original 20h spec should no longer be followed literally.

The safe repo-truth order is now:

1. Freeze `P0`, `P1`, `P2`, `P3`, `P4`, `P5`, `P7` as already closed or
   functionally closed.
2. Freeze `P6` as complete in repo-truth: keep `run_live_light_gate(...)` as
   the canonical fail-closed seam and keep the additive gate-group projection.
3. Freeze `P8` as resolved: no new bridge, current Build-14 two-step pipeline
   remains canonical.
4. Treat `P9` as an audit/closure item, not as a hidden coding backlog.
5. Open the next bounded coding slice only when a new real behavior gap is
   identified from current repo-truth rather than from the stale original spec.

## Suggested Current Gap

If work continues immediately, the remaining gap is no longer `P6`.

- the session close / commit decision under `P9`
- or a new bounded engineering slice opened from current repo-truth

`P6` and `P8` no longer block forward motion.

## Status

`PARTIAL`

Reason:
- the original 20h spec is no longer a literal execution checklist
- most early/mid phases are already closed
- the only remaining named original phase is now `P9`, and it remains audit-only
  until a deliberate commit/closure decision is taken
