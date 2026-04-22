# P6 Rewrite — Live-Light Gates Repo-Truth — 2026-04-21

## Purpose

Rewrite the stale `P6` gate spec against the current governed Build-13 seam.

This note replaces the old idea:
- add a new `GateEvaluation` dataclass
- add a new `evaluate_promotion_gates()` API
- wire four newly named gates into a fresh typed surface

That is not how the current repo works.

## Current Repo-Truth Seam

The active gate seam is:
- `protocols.live_light_runtime.run_live_light_gate(...)`

Current live-light behavior is already fail-closed and already governed through:
- governance envelope blockers
- shadow-day blockers
- micro-live blockers
- import surface blockers
- import contract blockers
- operational blockers
- Build-14 influence validation and bounded influence handling

Current code split:
- `src/protocols/live_light_runtime.py`
- `src/protocols/live_light_runtime_gate_support.py`
- `src/protocols/live_light_runtime_support.py`
- `src/protocols/contracts_promotion.py`

## What Exists Already

### Live-Light contract truth

`LiveLightInput` already carries the fields that the old `P6` wanted to gate:
- governance summaries
- import artifact and lineage
- observability readiness
- halt readiness
- execution / broker / exchange readiness
- operator safing request
- Build-14 live eligibility

See:
- `src/protocols/contracts_promotion.py`

### Fail-closed gate execution

`run_live_light_gate(...)` already aggregates blocking reasons from:
- `_governance_envelope_blocking_reasons(...)`
- `_shadow_day_gate_blocking_reasons(...)`
- `_evaluate_build14_influence(...)`
- `_evaluate_micro_live_gate(...)`
- `_import_surface_blocking_reasons(...)`
- `_import_contract_blocking_reasons(...)`
- `_operational_blocking_reasons(...)`

See:
- `src/protocols/live_light_runtime.py`

### Existing test proof

The current live-light runtime test suite already proves:
- governance summaries are preserved
- import contract mismatches block
- Build-14 typed influence is accepted or rejected correctly
- operator safing requests block
- observability / halt / execution readiness block
- model-constructed contradictions block

See:
- `tests/test_protocols/test_live_light_runtime.py`

## Why the Old P6 Is Stale

The old `P6` expected explicit typed gate outputs:
- `G-13.1`
- `G-13.2`
- `G-13.3`
- `G-13.4`
- returned as `GateEvaluation`

Current repo-truth does not use that seam.

The actual system is already enforcing the same family of constraints, but
through a blocking-reasons model inside `run_live_light_gate(...)`.

So the real task is not:
- add a second gate API

The real task is:
- map the existing blockers to stable canonical gate groups
- add missing proof only where current behavior does not yet make the intended
  gate group explicit enough

## Repo-Truth Gate Groups

The closest current mapping is:

### Gate Group A — Governance Envelope

Implemented through:
- `_governance_envelope_blocking_reasons(...)`

Current examples:
- profile must be `COMPLETE`
- runtime mode must be `LIVE`
- no profile fork
- no automatic complete promotion
- concrete artifact / lineage ids required

### Gate Group B — Promotion History / Rollout Integrity

Implemented through:
- `_shadow_day_gate_blocking_reasons(...)`
- `_evaluate_micro_live_gate(...)`
- `_rollout_temporal_blocking_reasons(...)`

Current examples:
- 30-day shadow prerequisite
- rendered component verdicts
- shadow report ready
- stable micro-live days

### Gate Group C — Import / Replay Integrity

Implemented through:
- `_import_surface_blocking_reasons(...)`
- `_import_contract_blocking_reasons(...)`

Current examples:
- accepted import status
- local exported source
- complete source profile
- lineage / whitelist / signature / atomicity guarantees

### Gate Group D — Operational Readiness

Implemented through:
- `_operational_blocking_reasons(...)`

Current examples:
- onboarding accepted
- review export ready
- observability ready
- halt ready
- execution / broker / exchange ready
- operator safing request blocks

### Gate Group E — Build-14 Governed Influence

Implemented through:
- `_evaluate_build14_influence(...)`
- `protocols.live_light_runtime_support._resolve_validated_build14_signal(...)`
- `complete_enablers.limited_influence`

Current examples:
- only typed `Build14InfluenceSignal` / `Build14InfluenceReport`
- correlation id must match
- live eligibility must be explicit
- review-only and soft-veto paths stay fail-closed

## What P6 Should Become

The repo-truth rewrite of `P6` should be:

1. Do **not** add a second top-level gate API.
2. Keep `run_live_light_gate(...)` as the canonical execution seam.
3. If more explicit gate reporting is needed, add a **small internal or output
   summary projection** derived from existing blockers instead of replacing the
   seam.
4. Add tests only for genuinely missing gate-group proofs.

## Safe Next Coding Slice

The safe next coding slice is:

- inspect whether the current runtime summary needs an explicit
  gate-group projection for observability / audit readability

Potential bounded enhancement:
- add a lightweight gate-group summary to `LiveLightRunSummary`
- without introducing a second independent promotion API

That slice is only justified if:
- current audit readability is insufficient
- and the added summary does not change gate behavior

## Status

`READY_FOR_BOUNDED_IMPLEMENTATION`

Meaning:
- repo-truth is now clear
- no speculative rewrite is needed
- the next implementation, if opened, must stay additive and must preserve the
  existing fail-closed seam

## 2026-04-21 Addendum — Bounded Projection Implemented

The bounded repo-truth slice described above is now implemented.

Applied change:
- add `LiveLightGateGroupSummary` to the Build-13 promotion contracts
- add `gate_groups` projection to `LiveLightRunSummary`
- derive the projection from existing blocker families inside
  `run_live_light_gate(...)`
- preserve the canonical fail-closed seam and verdict ordering

Files touched:
- `src/protocols/contracts_promotion.py`
- `src/protocols/__init__.py`
- `src/protocols/live_light_runtime.py`
- `tests/test_protocols/test_contracts.py`
- `tests/test_protocols/test_live_light_runtime.py`

Proof:
- `python -m pytest tests/test_protocols/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py -q --tb=short`
  - `80 passed`
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Repo-truth outcome:
- no second `GateEvaluation` API was introduced
- no Build-14 bridge was introduced
- audit readability is improved through additive output projection only

Status after this slice:
- `COMPLETE_REPO_TRUTH`

## 2026-04-21 Addendum 2 — Monitoring/Dashboard Projection

The additive `gate_groups` projection is now carried through the existing
monitoring/dashboard surface.

Applied change:
- add `LiveLightGateGroupProjection` to the Build-10 dashboard contracts
- project `LiveLightRunSummary.gate_groups` into `LiveLightProjection`
- expose one dedicated Build-13 dashboard card summarizing gate-group status
- export compact Prometheus metrics:
  - `v53_live_light_gate_group_status`
  - `v53_live_light_gate_group_reason_count`

Important boundary:
- no prose-heavy metric documentation was pushed into Prometheus itself
- no second promotion API was introduced
- no gate behavior changed

Proof:
- `python -m pytest tests/test_protocols/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py tests/test_monitoring/test_observability.py tests/test_monitoring/test_monitoring_backend.py -q --tb=short`
  - `128 passed`
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Repo-truth outcome:
- Build-13 gate families are now visible in:
  - runtime summary
  - protocol dashboard projection
  - monitoring payload
  - compact observability export

## 2026-04-21 Addendum 3 — Grafana Human Guide

The existing Local IA Lab Grafana dashboard now ends with a bounded human guide
panel explaining the current governed semantics of the promoted Build-13 /
Build-14 metrics.

Applied change:
- add a final Grafana `text` panel to the Local IA Lab dashboard
- document only metrics already emitted by the repo:
  - `v53_live_light_gate_group_status`
  - `v53_live_light_gate_group_reason_count`
  - `v53_build14_action`
  - `v53_build14_recommended_budget_factor`
  - `v53_build14_confidence_penalty_weight`
  - `v53_build14_requires_manual_review`
- keep Prometheus compact and machine-readable
- keep the explanation layer in Grafana, not in the metric export itself

Important boundary:
- no new thresholds were invented outside governed Build-14 semantics
- no runtime or gate behavior changed
- no new Build-14 bridge or dashboard API was introduced

Proof:
- `python -m pytest tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_observability.py tests/test_protocols/test_live_light_dashboard.py -q --tb=short`
  - `15 passed`
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Repo-truth outcome:
- the dashboard now has a human-readable guide layer for gate-group and
  Build-14 metrics
- Prometheus remains the compact telemetry surface
- Grafana is now explicitly the interpretation surface for this slice

## 2026-04-21 Addendum 4 — Shadow VPS Grafana Human Guide

The same bounded interpretation pattern is now applied to the local Shadow VPS
Grafana dashboard.

Applied change:
- add a final Grafana `text` panel to the Shadow VPS dashboard
- document the meaning of existing exported metrics only:
  - `v53_shadow_vps_service_status`
  - `v53_shadow_vps_service_promotion_gate_passed`
  - `v53_shadow_vps_execution_runtime_projection_ready`
  - `v53_shadow_vps_execution_runtime_projection_bridge_loaded`
  - `v53_shadow_vps_regime_lite_safing_status`
  - `v53_shadow_vps_regime_lite_entries_blocked`
  - `v53_shadow_vps_regime_lite_should_exit_all`
  - `v53_shadow_vps_telegram_alert_delivery_status`
- keep Prometheus compact and label-driven
- keep the long-form operator explanation in Grafana only

Important boundary:
- no runtime or exporter behavior changed
- no new thresholds were invented
- no second monitoring API was introduced

Proof:
- `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q --tb=short`
  - `5 passed`
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Repo-truth outcome:
- both local dashboards now follow the same split:
  - Prometheus = compact telemetry
  - Grafana = human interpretation layer

## 2026-04-21 Addendum 5 — Shared Terminology Dictionary

The Local IA Lab and Shadow VPS Grafana guides now read from one small
canonical monitoring-side terminology dictionary.

Applied change:
- add `src/monitoring/dashboard_metric_guides.py`
- centralize the shared guide rendering model:
  - `MetricGuideEntry`
  - `MetricGuideSection`
  - `render_local_lab_metric_guide_markdown()`
  - `render_shadow_vps_metric_guide_markdown()`
- switch both dashboards to use the shared guide renderer instead of embedding
  their prose inline
- add a direct test layer for the shared guide output

Important boundary:
- this is a Grafana explanation-layer refactor only
- no Prometheus metrics changed
- no runtime or exporter behavior changed
- no new thresholds or governance rules were introduced

Proof:
- `python -m pytest tests/test_monitoring/test_dashboard_metric_guides.py tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_observability.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_live_light_dashboard.py -q --tb=short`
  - `22 passed`
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Repo-truth outcome:
- Grafana terminology is now centralized for the current local dashboards
- future wording changes can be made in one monitoring-local place
- the repo keeps the intended split:
  - Prometheus = compact signals
  - Grafana = governed human explanation

## 2026-04-21 Addendum 6 — Active Grafana Scope Frozen

Repo-truth inspection confirms that the active generated Grafana scope in this
repository is currently limited to two dashboards only:
- Local IA Lab
- Shadow VPS

Applied change:
- align the two launcher tests with the new guide panels and updated panel
  counts
- keep the shared terminology dictionary scoped to these two active dashboards
- avoid speculative expansion to non-existent Grafana surfaces

Proof:
- `python -m pytest tests/test_monitoring/test_local_lab_grafana_dashboard_launcher.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_dashboard_metric_guides.py tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard.py -q --tb=short`
  - `9 passed`
- `python scripts/run_dag_check.py`
  - `PASS`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Repo-truth outcome:
- the shared Grafana guide dictionary now covers the full active Grafana
  generation perimeter of the repo
- no further dashboard extension is justified until a new real Grafana surface
  appears in `src/monitoring`
