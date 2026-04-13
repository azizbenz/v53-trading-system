# VPS -> Local Observability Architecture

> Status: planning and execution anchor, based on the real repo as of 2026-04-11.
>
> Rule of truth: current code wins over planning docs.

---

## 1. Objective

Define the correct observability split for V5.3:

- the VPS runs trading and lightweight collection
- the local PC hosts heavy monitoring, analysis, and long-retention tooling
- the VPS must not be saturated by raw-stream export, heavy dashboards, or uncontrolled log shipping

This file does not authorize a new runtime architecture. It only defines the observability rail that fits the already chosen `Local IA Lab / VPS` separation.

---

## 2. Short answer

Yes, the VPS should expose enough metrics and logs for the local PC to monitor and analyze everything important.

But the transport must stay bounded:

- continuous: compact summaries and typed metrics
- on demand: detailed logs and deep diagnostics
- never: full raw event streams in continuous export if they can burden the VPS

Recommended posture:

- VPS = runtime + lightweight exporters + short retention
- local PC = Prometheus + Grafana + detailed drill-down + long retention

---

## 3. Target topology

```text
[VPS]
  trading runtime
  monitoring snapshot builder
  app observability export (.prom)
  node_exporter
  structured logs + rotation
  optional alert-forward path
        |
        | scrape / pull / targeted fetch
        v
[Local PC]
  Prometheus
  Grafana
  Local IA Lab detailed monitoring
  optional Loki / log archive
  deep drill-down and replay analysis
```

### 3.1 Hard rule

The VPS must export:

- health
- runtime stage
- compact execution/risk/infra aggregates
- typed import/proof/promotion state

The VPS must not continuously stream:

- full raw runtime logs
- raw market snapshots
- every event tick-by-tick
- full replay artifacts

---

## 4. Continuous export vs on-demand detail

### 4.1 Continuous export from VPS

Send continuously:

- `runtime_mode`
- deployment stage
- heartbeat age
- queue backlog
- stale pair count
- reconnect count
- kill switch state
- alert counts
- expected cost vs realized cost
- partial fill count
- fill latency P95
- CPU / RAM / disk summary
- import artifact id / lineage / review state

### 4.2 On-demand retrieval from VPS

Fetch only when needed:

- detailed structured logs
- run-specific JSON sidecars
- reconciliation incident bundles
- deep order / fill traces
- long operator event history

### 4.3 Why this split

- keeps the VPS light
- keeps local analysis rich
- avoids turning the VPS into a logging warehouse
- preserves auditability without permanent heavy transport

---

## 5. Current code anchors already present

### 5.1 VPS monitoring contracts and payloads

Already present:

- `src/monitoring/contracts.py`
- `src/monitoring/metrics_collector.py`
- `src/monitoring/monitoring_runtime.py`
- `src/monitoring/health_dashboard_backend.py`
- `src/monitoring/technical_dashboard_backend.py`
- `src/monitoring/observability.py`
- `src/monitoring/observability_io.py`

Important current truth:

- `TechnicalDashboardPayload` already exists as a rich typed VPS/backend payload
- `ObservabilityExport` already exists as the app-metrics export contract
- the code can already emit Prometheus-style text payloads

### 5.2 Local IA Lab monitoring contracts and payloads

Already present:

- `src/local_replay_runtime/local_lab_monitoring_projection.py`
- `src/local_replay_runtime/local_lab_monitoring_backend.py`
- `src/local_replay_runtime/local_lab_observability.py`
- `src/monitoring/local_lab_monitoring_bundle_manifest.py`
- `src/monitoring/local_lab_bundle_loader.py`
- `src/monitoring/local_lab_bundle_discovery.py`
- `src/monitoring/local_lab_monitoring_feed.py`

Important current truth:

- Local IA Lab already emits a compact backend payload
- Local IA Lab already emits a Prometheus-style `.prom` text export
- Local IA Lab monitoring is already much closer to Grafana-ready than VPS process observability is

---

## 6. What is still missing in code

### 6.1 Missing or incomplete on the VPS side

#### A. Process/system metric producers

Current reality:

- contracts already have `cpu_pct` and `ram_pct`
- some scripts still inject demo/static values
- there is no verified process/system sampler wired on the real VPS runtime path

Missing bounded code:

- process sampler for:
  - process up
  - heartbeat age
  - `cpu_pct`
  - RSS / memory
  - thread count
  - optional FD count
- disk/free-space sampler
- stable periodic write of VPS `.prom` text export

#### B. Ops alerting pieces

Still missing in repo:

- `src/alerting/telegram_alerter.py`

#### C. Runtime/risk slices still missing

Still missing in repo:

- `src/regime_classifier/`
- `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py`
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `src/risk_backbone/info_stress_monitor.py`
- `src/execution_backbone/spread_guard.py`
- `src/execution_backbone/slippage_model.py`

#### D. Venue/runtime proof still missing

Still incomplete:

- real Binance Testnet/live proof
- long-run soak proof on websocket/execution surfaces
- final execution telemetry producer for Local IA Lab `13-C`

### 6.2 Missing or incomplete on the local side

#### A. Monitoring stack integration

Not yet implemented in repo:

- Grafana dashboards consuming the current payloads
- optional Loki/log archive integration

Partially implemented in repo:

- typed per-VPS scrape handoff artifacts
- local aggregation into Prometheus `file_sd` JSON
- checked local Prometheus config generator

#### B. Log retrieval strategy

Partially implemented in repo:

- bounded durable JSONL retrieval now exists for the Shadow VPS service rail
- bounded recent-tail summary now exists for cheap continuous export

Still missing in repo:

- richer bounded log-pull tooling for:
  - time-window fetch
  - run-id fetch
  - severity-filtered fetch
- explicit compressed handoff bundles for incident drill-down

---

## 7. Recommended implementation plan

### O1. VPS process metrics producer

Goal:

- make real `cpu_pct`, `ram_pct`, process heartbeat, and runtime liveness observable from the live VPS path

Likely code targets:

- `src/monitoring/metrics_collector.py`
- `src/monitoring/monitoring_runtime.py`
- `src/protocols/shadow_vps_service.py`

Deliverables:

- typed process metrics gathered on the real service path
- no demo-only injected values on the live path

### O2. VPS application Prometheus text export

Goal:

- materialize one stable `.prom` export on the VPS from the existing `ObservabilityExport`

Likely code targets:

- `src/monitoring/observability.py`
- `src/monitoring/observability_io.py`
- bounded launcher/service write path

Recommended pattern:

- write a textfile collector file periodically
- avoid opening a custom heavy HTTP metrics server first

Current code truth:

- the Shadow VPS service already writes its own compact `.prom`
- the service can now also mirror that payload into a node_exporter textfile collector directory when configured
- deployment of node_exporter itself remains outside the repo

### O3. VPS host/system observability

Goal:

- add host metrics without bloating app code

Out-of-repo runtime component:

- `node_exporter` on the VPS

What it covers:

- CPU host
- RAM host
- filesystem
- disk IO
- network
- load

### O4. Local Prometheus + Grafana

Goal:

- keep heavy monitoring on the local PC

Recommended local stack:

- Prometheus on the local PC
- Grafana on the local PC
- optional Loki later for logs

Scrape targets:

- VPS `node_exporter`
- VPS app `.prom` exporter path or bounded scrape endpoint
- Local IA Lab `.prom` exports / ingestion feed

Current code truth:

- per-VPS scrape handoff can now be emitted from the real Shadow VPS service rail
- local-PC aggregation into Prometheus `file_sd` JSON now exists
- checked local Prometheus config generation now exists
- Grafana dashboards still remain to be added

### O5. VPS log transport strategy

Goal:

- get the important logs locally without saturating the VPS

Recommended rule:

- immediate:
  - `CRITICAL`
  - `ERROR`
  - selected `WARNING`
- batched or on-demand:
  - `INFO`
  - `DEBUG`
  - large structured traces

Recommended bounded capabilities:

- fetch by time range
- fetch by `correlation_id`
- fetch by `run_id`
- fetch by severity

### O6. UI hookup

Goal:

- keep the VPS UI minimal and the local UI rich

VPS minimal UI should consume:

- `HealthDashboardPayload`
- `TechnicalDashboardPayload`
- `ObservabilityExport`

Local IA Lab detailed UI should consume:

- `LocalLabMonitoringBackendPayload`
- `LocalLabMonitoringIngestionSummary`
- `local_lab_monitoring_feed`
- Local IA Lab sidecars/manifests for drill-down

---

## 8. Process UI for the VPS

The VPS process UI should remain minimal and operator-oriented.

It should show:

- service up/down
- runtime mode
- last heartbeat
- websocket health
- user-data health
- queue backlog
- stale pair count
- reconnect count
- kill switch state
- import artifact id / lineage
- promotion stage
- CPU / RAM / disk
- latest alerts

It should not try to become the heavy diagnostics UI.

The detailed diagnostics should stay on the local PC.

---

## 9. Recommended frequencies and load discipline

### 9.1 VPS export frequencies

- heartbeat / liveness: every 5s to 15s
- execution/risk/app gauges: every 10s to 30s
- CPU / RAM / disk: every 30s to 60s
- log batch shipping: coarse interval or on demand

### 9.2 Cardinality discipline

Never use high-cardinality labels for Prometheus such as:

- `order_id`
- `trade_id`
- dynamic free-text reasons
- unbounded file names

Prefer labels such as:

- `runtime_mode`
- `engine_id`
- `pair`
- `status`
- `deployment_stage`

### 9.3 Retention discipline

- short retention on the VPS
- long retention on the local PC
- compressed bundles for incidents

---

## 10. What should start now

Yes, observability plumbing should start now.

But in this order:

1. `node_exporter` deployment and scrape hookup
2. Grafana dashboards on stable payloads
3. compressed incident-bundle retrieval
4. only then richer UI wiring

This means:

- start backend observability now
- do not start by polishing dashboards

---

## 11. Estimated progress of the whole solution

This is an estimate, not a measured KPI.

### 11.1 Estimated progress by pillar

| Pillar | Estimate |
|---|---:|
| Governed replay/import rail | 85% |
| Local IA Lab core (diagnostic/proof/release dry-run) | 78% |
| Local IA Lab math/calibration stack | 62% |
| VPS runtime + venue + execution backbone | 55% |
| VPS ops/risk missing slices | 30% |
| Monitoring/UI/observability integration end-to-end | 42% |

### 11.2 Estimated overall progress

Estimated total solution progress:

- **~62%**

Interpretation:

- the foundations and Lab core are strong
- the governed handoff rail is strong
- the VPS runtime exists
- the missing work is no longer “everything”; it is concentrated in:
  - live/Testnet proof
  - missing VPS ops/risk modules
  - observability plumbing end-to-end
  - final UI integration

---

## 12. Immediate next coding order

1. VPS process metrics producer on the real service path
2. VPS app `.prom` writer
3. `13-C EXECUTION` continuation with real execution telemetry producer
4. `T9/T10/T11/T12/T13` missing VPS code slices
5. local Prometheus/Grafana hookup
6. UI hookup on already-stable payloads

---

## 13. Acceptance criteria for this architecture direction

- [x] Local IA Lab remains the heavy analysis side
- [x] VPS remains the light execution + collection side
- [x] no continuous raw-stream burden is imposed on the VPS
- [x] existing typed monitoring contracts are reused
- [x] Prometheus/Grafana start at backend/export level, not at UI level
- [x] missing code areas are explicitly identified
- [x] an explicit overall progress estimate is recorded
