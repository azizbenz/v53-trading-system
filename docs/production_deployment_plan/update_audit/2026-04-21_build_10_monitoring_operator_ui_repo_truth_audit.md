# Build 10 Repo-Truth Audit - Monitoring + Operator UI - 2026-04-21

## Scope

This note audits **Build 10** only:

- `monitoring`
- `ui`
- the current local Prometheus / Grafana operator surfaces
- the current technical dashboard HTML / local UI surface

It answers one question:

> Does current Build-10 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected operator observability layer
> and the real implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 10:

- Build 10 is the monitoring and operator observability layer.
- It must expose a real operator-facing supervision surface.
- The VPS must stay minimal.
- The local PC is the place for:
  - Prometheus
  - Grafana
  - detailed drill-down
  - longer retention and operator interpretation
- Local and VPS views may coexist, but they must not become two competing
  runtime-control systems.

## Repo-Truth Surface

### 1. Real Prometheus / Grafana local observability surface exists

Observed in:
- `src/monitoring/local_prometheus_config.py`
- `src/monitoring/local_prometheus_metrics_bridge.py`
- `src/monitoring/local_grafana_dashboard.py`
- `src/monitoring/local_lab_grafana_dashboard.py`
- `src/monitoring/local_grafana_api.py`

Current repo-truth Build-10 monitoring surface includes:
- local-PC Prometheus config generation
- local Prometheus text payload bridging
- typed Grafana dashboard generation for:
  - Shadow VPS
  - Local IA Lab
- typed Grafana bootstrap/import API

Interpretation:
- Prometheus / Grafana are not hypothetical backlog items anymore
- they are already part of current repo-truth operator observability

### 2. Metric semantics and operator guidance are now part of the Grafana surface

Observed in:
- `src/monitoring/dashboard_metric_guides.py`
- `src/monitoring/local_grafana_dashboard.py`
- `src/monitoring/local_lab_grafana_dashboard.py`

Current repo-truth already includes:
- shared metric-guide wording
- explicit text panels at the end of generated dashboards
- metric/status semantics attached to the real Grafana output

Interpretation:
- operator-facing explanation is no longer only implicit in raw metrics
- Build 10 has a governed human-readable observability layer on top of
  Prometheus metrics

### 3. The technical HTML dashboard still exists and is real

Observed in:
- `src/ui/technical_dashboard_view.py`
- `src/ui/technical_dashboard_html.py`
- `src/ui/complete_dashboard_view.py`
- `src/ui/light_ui_runtime.py`

Current repo-truth still includes:
- typed technical dashboard view assembly
- local HTML rendering
- light / complete UI launcher surfaces

Interpretation:
- the HTML/technical UI is not dead code
- it remains a supported local operator surface
- but it is not the only Build-10 truth anymore

### 4. Build 10 is now a coexistence build, not a single-dashboard build

Observed current repo-truth shows two valid but non-competing surfaces:

1. local Prometheus / Grafana observability for deployed supervision
2. local typed technical UI / HTML dashboard for static or payload-oriented
   inspection

Interpretation:
- the earlier doctrine warning against “two competing dashboard engines” is
  still relevant
- but current code does **not** violate it, because the two surfaces are views,
  not two independent control planes

## Verification Evidence

### Local Prometheus / Grafana + technical dashboard UI

Command:

```powershell
python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_grafana_api.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_light_dashboard.py tests/test_ui/test_complete_dashboard_launcher.py -q --tb=short
```

Result:
- `55 passed`

### Notes on warnings

Observed warning:
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-10 doctrine/code issue
- no audited Build-10 functional failure

## Observed Divergence

### Divergence 1 - doc 16 still underdescribes the current Grafana reality

Doc 16 contains statements such as:
- local Prometheus config generation exists
- Grafana dashboards still remain to be added

Current repo-truth contradicts that backlog framing.

Observed current repo-truth:
- Grafana dashboards already exist
- Grafana bootstrap already exists
- metric guide text has already been integrated

Interpretation:
- this is a real documentation drift
- Build 10 code is ahead of the older observability markdown on Grafana

### Divergence 2 - “HTML dashboard = operator truth” is no longer accurate

Current code still has:
- `technical_dashboard_view.py`
- `technical_dashboard_html.py`

But current deployment/operator observability truth also includes:
- local Prometheus
- local Grafana
- scrape handoff
- Grafana bootstrap/import

Interpretation:
- HTML is still real and tested
- but it is no longer the sole or primary operator observability story for the
  deployed system

### Divergence 3 - Build 10 is broader than a single UI narrative

Current Build 10 spans:
- metric emission and observability support
- Prometheus-oriented export / bridge / config
- Grafana dashboards
- typed technical UI rendering

Interpretation:
- the codebase has evolved from “one technical dashboard” into a broader
  operator observability stack
- markdown summaries that compress Build 10 down to only one surface are now
  too narrow

## Decision

`PARTIAL`

## Why

Build 10 is clearly **implemented and green** on both audited operator surfaces:

- Prometheus / Grafana local observability
- local typed technical dashboard / HTML rendering

So Build 10 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for two concrete reasons:

1. some doctrinal markdown still describes Grafana as pending, while current
   repo-truth already has generated and bootstrapped Grafana dashboards
2. the simplified doctrinal story often over-compresses Build 10 into one UI
   surface, whereas the real repo now has a broader monitoring + dashboard
   coexistence model

So the correct ruling is:
- Build 10 is operationally real and healthy
- but the markdown/operator narrative is partially stale and too narrow

## Patch Target

`docs only`

### Docs target

Clarify that current repo-truth Build 10 already includes:
- local Prometheus config generation
- local Prometheus text bridge
- Shadow VPS Grafana dashboard generation
- Local IA Lab Grafana dashboard generation
- Grafana bootstrap/import
- shared metric-guide text panels
- local typed HTML dashboard view

And clarify the role split:
- Prometheus / Grafana = deployment-facing local observability truth
- technical HTML dashboard = supported local typed inspection view

### No target

No Build-10 code redesign is justified by this audit.

There is no evidence that the current coexistence model is broken.

## Final Verdict

Build 10 is operationally healthy but doctrinally compressed.

Safe operational classification:
- `Build 10 = PARTIAL (Prometheus/Grafana observability and technical HTML UI both exist and are green; older markdown underdescribes the current Grafana/operator surface and over-compresses Build 10 into a simpler single-dashboard story)`
