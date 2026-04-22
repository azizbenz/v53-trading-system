# Build 3 Repo-Truth Audit - Execution Backbone - 2026-04-21

## Scope

This note audits **Build 3** only:

- `execution_backbone`
- `protocols.execution_runtime_bootstrap`
- `protocols.execution_opportunity_bridge`
- the current monitoring surface for execution latency

It answers one question:

> Does current Build-3 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected execution backbone and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 3:

- Build 3 is the canonical execution backbone.
- It must own:
  - executable order submission
  - gatekeeping before submit
  - real cost tracking
  - fill lifecycle
  - reconciliation
- It must stay measurable and adapter-backed.
- It must remain governed by existing contracts and bootstrap surfaces.

The doctrinal picture does **not** justify inventing a local second execution
rail, bypassing protocols, or bypassing gatekeeper logic.

## Repo-Truth Surface

### 1. Canonical module surface

Observed module export in:
- `src/execution_backbone/__init__.py`

Current Build-3 public surface includes:
- `ExecutionRuntime`
- `ExecutionOpportunity`
- `ExecutionSubmission`
- `ExecutionVenueAdapter`
- gatekeeper contracts and audit logging
- rate-limit model
- spread-guard model
- slippage model
- venue-constraint provider

Interpretation:
- Build 3 is a real runtime module, not just a bag of helpers
- the public API is already governed and typed

### 2. Real execution runtime

Observed in:
- `src/execution_backbone/execution_runtime.py`

Current `submit_opportunity(...)` path is real:
1. `_apply_runtime_slippage_model(...)`
2. gatekeeper `authorize(...)`
3. `adapter.submit_order(intent, now)`
4. local order registration and audit logging

Interpretation:
- Build 3 is operationally real
- the order submit path exists and is not synthetic

### 3. Real bootstrap surface

Observed in:
- `src/protocols/execution_runtime_bootstrap.py`

Current bootstrap supports:
- injected adapter
- optional execution no-trade filter bridge
- optional execution runtime projection loading
- optional gatekeeper audit store
- optional reconciliation bootstrap
- bounded Binance bootstrap path

Interpretation:
- Build 3 is not floating unbound
- it already has a canonical protocol/bootstrap seam

### 4. Real measured latency surface

Observed in:
- `src/execution_backbone/fill_tracker/latency_meter.py`
- `src/execution_backbone/execution_runtime_models.py`
- `src/monitoring/metrics_collector.py`
- `src/monitoring/observability_support.py`

Current measured latencies are:
- `signal_to_submit`
- `signal_to_scoring`
- `scoring_to_risk`
- `risk_to_portfolio`
- `portfolio_to_submit`
- `submit_to_ack`
- `submit_to_first_fill`
- `submit_to_full_fill`
- `ack_to_first_fill`

Current pre-submit seam is:
- `ExecutionOpportunity.signal_arrival_monotonic_s`
- `ExecutionOpportunity.scoring_completed_monotonic_s`
- `ExecutionOpportunity.risk_completed_monotonic_s`
- `ExecutionOpportunity.portfolio_completed_monotonic_s`
- `ExecutionSubmission.signal_to_submit_s`
- `ExecutionSubmission.signal_to_scoring_s`
- `ExecutionSubmission.scoring_to_risk_s`
- `ExecutionSubmission.risk_to_portfolio_s`
- `ExecutionSubmission.portfolio_to_submit_s`
- `LatencyMeasurement.signal_to_submit_s`
- `LatencyMeasurement.signal_to_scoring_s`
- `LatencyMeasurement.scoring_to_risk_s`
- `LatencyMeasurement.risk_to_portfolio_s`
- `LatencyMeasurement.portfolio_to_submit_s`
- `LatencyStats.avg_signal_to_submit_s`
- `LatencyStats.avg_signal_to_scoring_s`
- `LatencyStats.avg_scoring_to_risk_s`
- `LatencyStats.avg_risk_to_portfolio_s`
- `LatencyStats.avg_portfolio_to_submit_s`
- `LatencyStats.p90_signal_to_submit_s`
- `LatencyStats.p90_signal_to_scoring_s`
- `LatencyStats.p90_scoring_to_risk_s`
- `LatencyStats.p90_risk_to_portfolio_s`
- `LatencyStats.p90_portfolio_to_submit_s`

Current monitoring surface exports:
- `v53_execution_fill_latency_ms_p95`
- `v53_execution_signal_to_submit_ms_p90`
- `v53_execution_signal_to_scoring_ms_p90`
- `v53_execution_scoring_to_risk_ms_p90`
- `v53_execution_risk_to_portfolio_ms_p90`
- `v53_execution_portfolio_to_submit_ms_p90`

Interpretation:
- Build 3 is measurable
- and now has a canonical runtime-level pre-submit metric
- and that pre-submit metric is now decomposed into current repo-truth stage slices
- and that pre-submit metric is now projected into the current monitoring surface

### 5. Canonical upstream stitch now exists

Observed in:
- `src/protocols/execution_opportunity_bridge.py`
- `src/portfolio/__init__.py`

Current typed stitch surface includes:
- `ExecutionOpportunityBridgeContext`
- `PortfolioExecutionSelection`
- `resolve_portfolio_execution_selection(...)`
- `build_execution_opportunity_from_portfolio_selection(...)`
- `build_execution_opportunity_from_orchestrator_result(...)`

Current repo-truth behavior:
1. pair/engine-compatible selected portfolio rows are resolved against viable allocations
2. that typed stitched record is projected into `ExecutionOpportunity`
3. the projection stays additive in `protocols`, not in `portfolio` or `execution_backbone`
4. the Build-9 core smoke now proves that portfolio output can project to canonical execution input

Interpretation:
- Build 3 no longer lacks a standard upstream typed seam into `ExecutionOpportunity`
- the current stitch is canonical and auditable
- it does not create a parallel execution rail or bypass gatekeeper logic

## Verification Evidence

### Execution runtime + bootstrap

Command:

```powershell
python -m pytest tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py -q --tb=short
```

Result:
- `45 passed`

### Pre-submit latency instrumentation slice

Command:

```powershell
python -m pytest tests/test_execution_backbone/test_fill_tracker.py tests/test_execution_backbone/test_execution_runtime.py -q --tb=short
```

Result:
- `70 passed`

### Full Build-3 execution bundle

Command:

```powershell
python -m pytest tests/test_execution_backbone -q --tb=short
```

Result:
- `184 passed`

Execution note:
- the sandbox-local run was blocked by pre-existing `PermissionError` writes under `build/...`
- the rerun outside sandbox passed completely

### Monitoring surface around execution observability

Command:

```powershell
python -m pytest tests/test_monitoring/test_metrics_collector.py tests/test_monitoring/test_observability.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_light_dashboard.py -q --tb=short
```

Result:
- `100 passed`

### Monitoring runtime + UI contract integration

Command:

```powershell
python -m pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_ui_contracts.py -q --tb=short
```

Result:
- `49 passed`

### Canonical upstream stitch + smoke proof

Command:

```powershell
python -m pytest tests/test_portfolio/test_canonical_portfolio.py tests/test_protocols/test_execution_opportunity_bridge.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q --tb=short
```

Result:
- `14 passed`

### Notes on warnings

Observed warning:
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-3 doctrine/code issue
- no audited Build-3 functional failure

## Observed Divergence

### Divergence 1 - some later execution features described in markdown are not present as first-class modules

Doc 19 names later execution-oriented items such as:
- `execution_backbone/order_decider/hybrid_router.py`
- `execution_backbone/twap_decomposer.py`

Observed current repo-truth order_decider surface:
- `intent_builder.py`
- `order_type_selector.py`
- `execution_guard.py`
- `timeout_policy_selector.py`
- `decision_reporter.py`

Interpretation:
- Build 3 core execution is present
- but not every later doctrinal execution enhancement named in markdown exists
  yet as a current repo-truth module

This does **not** invalidate Build 3.
It does mean the markdown execution expansion remains ahead of the current code
on some planned sub-surfaces.

## Decision

`PARTIAL`

## Why

Build 3 is **real, active, and green** on its audited core surfaces.

What is clearly present:
- executable runtime
- gatekeeper
- adapter-backed submit path
- cost/fill/reconciliation tracking
- bootstrap seam
- canonical upstream typed stitch into `ExecutionOpportunity`
- monitoring exposure
- canonical runtime-level pre-submit latency instrumentation

So Build 3 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for one concrete reason:

1. some later markdown-named execution expansion modules remain planned rather
   than current repo-truth

So the correct ruling is:
- Build 3 is implemented and healthy
- but some later markdown execution expansion remains ahead of current code

## Patch Target

`mixed`

### Code target

Small additive follow-up slice:
- keep the current upstream typed stitch into `ExecutionOpportunity`
- keep the existing runtime + monitoring latency seam intact
- only add later execution expansion modules if those specific phases are opened

### Docs target

Clarify that current repo-truth:
- already measures post-submit execution lifecycle latency
- now also measures full runtime-level signal-to-submit latency
- and now projects that pre-submit metric into current monitoring
- and now includes a canonical typed projection seam from viable portfolio output
  into `ExecutionOpportunity`

### No target

No Build-3 redesign is justified by this audit.

The runtime path, bootstrap path, and gatekeeper path should stay intact.

## Final Verdict

Build 3 is operationally strong but still partially projection-incomplete.

Safe operational classification:
- `Build 3 = PARTIAL (real execution backbone exists and is green; canonical pre-submit runtime latency now exists and is projected into monitoring, and a canonical upstream stitch into ExecutionOpportunity now exists, but some later markdown execution expansions remain ahead of current repo-truth)`

## 2026-04-22 Addendum — Indicative Latency Root-Cause Audit

An indicative Build-9 smoke readout produced a first one-shot value around
`809 ms` for:
- `signal_to_submit`
- `portfolio_to_submit`

That number must **not** be treated as production truth.

Targeted root-cause checks showed:
- `ExecutionRuntime.submit_opportunity(...)` with a pure fake adapter is
  effectively sub-millisecond wall time in steady state
- `ExecutionRuntime.submit_opportunity(...)` on the bounded Binance bootstrap
  rail with mocked REST is roughly low-single-digit milliseconds wall time in
  steady state
- the large one-shot smoke number is dominated by **cold-start process cost**
  and first-run smoke harness setup, not by the canonical steady-state Build-3
  submit path itself

Operational interpretation:
- the smoke one-shot is useful as a coarse sanity read
- it is **not** a valid basis for an immediate performance rewrite
- no performance campaign should be opened from that one number alone

Repo-truth decision:
- keep the Build-3 latency seams
- keep the Build-3 monitoring projection
- if performance work is opened later, measure on a persistent runtime rail
  across consecutive submissions rather than on a one-shot smoke process
