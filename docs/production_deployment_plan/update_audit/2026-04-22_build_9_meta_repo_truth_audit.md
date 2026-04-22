# Build 9 Repo-Truth Audit - Meta Minimal - 2026-04-22

## Scope

This note audits **Build 9** only:

- `src/meta/__init__.py`
- `src/meta_minimal/__init__.py`
- `src/meta_minimal/meta_runtime.py`
- current `break_even_dashboard`, `cra_monitor`, `dtr_core`, and prudent-edge seams
- current additive `cost_drift_monitor` and `refusal_journal` seams

It answers one question:

> Does current Build-9 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Meta layer and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 9:

- Build 9 is canonical **Meta Minimal**.
- Build-order identity is:
  - `Meta Minimal`
- Build-order description is:
  - `DTR, CRA, break-even, edge tracker`
- It is an audit/economic-observability build, not the order-departure hot path.

## Repo-Truth Surface

### 1. Build 9 already has a canonical facade plus a richer implementation package

Observed in:
- `src/meta/__init__.py`
- `src/meta_minimal/__init__.py`

Current repo-truth Build-9 surface includes:
- canonical package name `meta`
- stable re-export of:
  - `build_dtr_summary`
  - `build_cra_report`
  - `build_break_even_report`
  - `build_edge_report`
- additive runtime exports:
  - `MetaInputSource`
  - `MetaRuntime`
  - `MetaRuntimeConfig`
  - `MetaRuntimeInput`
  - `MetaRuntimeResult`
  - `MetaRuntimeStatus`
- implementation package `meta_minimal` that also exposes:
  - `cost_drift_monitor`
  - `refusal_journal`

Interpretation:
- current Build 9 is not a single flat module
- it is a governed dual surface:
  - a canonical facade under `meta`
  - a richer implementation/runtime package under `meta_minimal`

### 2. Build 9 is no longer only four reporters; it already has a real runtime rail

Observed in:
- `src/meta_minimal/meta_runtime.py`

Current repo-truth runtime includes:
- typed `MetaRuntimeInput`
- typed `MetaRuntimeConfig`
- typed `MetaRuntimeResult`
- typed `MetaInputSource`
- typed `MetaRuntimeStatus`
- canonical `MetaRuntime.evaluate(...)`
- canonical `build_meta_runtime_result_from_records(...)`

Current Build-9 runtime path is:
- DTR persistence
- DTR summary
- CRA classification/report
- break-even aggregation/report
- prudent edge classification/report

Interpretation:
- Build 9 is already a real runtime/audit rail
- it is broader than a simple collection of independent reporters

### 3. Input-source and path-quality semantics are already governed in current code

Observed in:
- `src/meta_minimal/meta_runtime.py`

Current repo-truth includes explicit input-source handling for:
- `REAL_MARKET`
- `SHADOW_REAL`
- `LOCAL_REPLAY`
- `SYNTHETIC`

Current repo-truth also includes explicit runtime outcomes:
- `EMPTY`
- `READY`
- `HAS_PATH_WARNINGS`
- `HAS_SYNTHETIC_INPUTS`

Current runtime warnings already govern:
- synthetic inputs excluded from edge validation
- local replay inputs marked indicative only
- incomplete decision paths explicitly carried into DTR warnings

Interpretation:
- Build 9 already encodes important epistemic status, not only economic summaries
- this is materially broader than the short registry description

### 4. The actual Build-9 implementation already includes additive seams not named in the stage description

Observed in:
- `src/meta_minimal/cost_drift_monitor/monitor.py`
- `src/meta_minimal/refusal_journal/refusal_journal.py`
- `src/meta_minimal/__init__.py`

Current repo-truth Build-9 implementation already includes:
- `CostDriftMonitor`
- `CostDriftMonitorConfig`
- `CostDriftResult`
- `RefusalJournal`
- `RefusalJournalManifest`
- `RefusalJournalSink`

Interpretation:
- the short stage description `DTR, CRA, break-even, edge tracker` is now too narrow
- current Build 9 also carries additive execution-cost-drift and refusal-evidence seams

### 5. Build 9 remains outside the order-departure hot path

Observed in:
- `src/meta_minimal/meta_runtime.py`
- current Build-3 / Build-8 repo-truth audits

Interpretation:
- Build 9 is operationally real
- but it is not the canonical layer that sends the order
- it remains an audit/evidence/economic-observability layer around significant decisions and realized outcomes

## Verification Evidence

### Full Build-9 audit bundle

Command:

```powershell
python -m pytest tests/test_meta tests/test_meta_minimal -q --tb=short
```

Result:
- `106 passed`
- `1 warning`

Warning detail:
- pytest cache creation warning under `.pytest_cache`

Interpretation:
- current Build-9 facade, runtime, reporters, cost-drift monitor, and refusal journal are green on the audited bundle
- the warning is cache-related only, not a Build-9 functional failure

## Observed Divergence

### Divergence 1 - the build-order story is materially narrower than the current Build-9 implementation

The simplified doctrinal story compresses Build 9 to:
- DTR
- CRA
- break-even
- edge tracker

Current repo-truth is broader:
- canonical facade
- typed runtime rail
- input-source governance
- path-quality governance
- additive cost-drift monitoring
- additive refusal journaling

Interpretation:
- this is not dangerous code drift
- it is documentation compression drift

### Divergence 2 - current Build 9 has a deliberate facade/implementation split that old markdown summaries usually ignore

Observed in:
- `src/meta/__init__.py`
- `src/meta_minimal/__init__.py`

Current repo-truth:
- `meta` preserves the canonical package surface
- `meta_minimal` carries the richer implementation/runtime surface

Interpretation:
- any markdown or backlog item that treats Build 9 as a single flat package is incomplete against current code truth

### Divergence 3 - additive Build-9 seams already exist beyond the old sprint expectation

Observed in:
- `src/meta_minimal/cost_drift_monitor/monitor.py`
- `src/meta_minimal/refusal_journal/refusal_journal.py`

Interpretation:
- old expectations that Build 9 stops at the four named economic reporters are stale
- current repo-truth already carries governed additive audit seams inside Build 9

## Decision

`PARTIAL`

## Why

Build 9 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- canonical `meta` facade
- real `meta_minimal` implementation package
- typed `MetaRuntime`
- governed input-source/path-warning semantics
- DTR -> CRA -> break-even -> edge runtime path
- additive `cost_drift_monitor`
- additive `refusal_journal`

So Build 9 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the registry/doc summary underdescribes how broad the current Build-9 surface now is
2. the current facade/implementation split is real but underdocumented
3. additive Build-9 seams such as cost-drift and refusal journaling already exist beyond the narrower doctrinal story

So the correct ruling is:
- Build 9 is operationally real and healthy
- but the doctrinal narrative has remained narrower than the current repo-truth implementation

## Patch Target

`docs only`
