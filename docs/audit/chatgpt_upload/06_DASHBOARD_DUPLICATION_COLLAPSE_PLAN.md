# 06 DASHBOARD DUPLICATION COLLAPSE PLAN

## Collapse rule
- owner page keeps the full table / diagnostics
- non-owner pages may keep at most:
  - one compact badge
  - or one sentence with a link/route to the owner page

## Collapse map

| Metric family | Current duplication | Keep full on | Collapse elsewhere to |
|---|---|---|---|
| `calibration.*` | `lab`, `overview`, `trading` | `IA Lab` | signature/version/status badge only |
| `lab_review.*` | `lab`, `overview` | `IA Lab` | candidate count / gate status badge only |
| `model_risk.*` | `lab`, `overview` | `IA Lab` | source-status badge only |
| `multiple_testing.*` | `lab`, `overview` | `IA Lab` | HLZ/DSR summary badge only |
| `refusal_journal.*` | `lab`, `overview` and Shadow-adjacent semantics | `Shadow` for detailed motifs, `IA Lab` for source-status only | one badge outside owner |
| `feature_bridge.*` | `overview`, `trading`, some `lab` reminders | `Trading` | lineage/source-status badge only |
| `engines.*` | `overview`, `trading` | `Trading` | active count badge only |
| `replay.*` and `economic_sterilization.*` | `overview`, `trading`, implicit Backtest overlap | `Trading` for live interpretation, `Backtest` for source map and replay proof | badge only |
| `operational_proof.warmup_explainer.*` | `overview`, `shadow` | `Shadow` | `Warmup: PASSED/BLOCKED` badge |
| `operational_proof.service_liveness.*` | `overview`, `shadow`, `vps` | `VPS` | `Service: ONLINE/OFFLINE` badge |
| `operational_proof.queue_trace.*` | `lab`, `overview`, `shadow`, `vps` | `VPS` | `Queue: CONSUMED/QUEUE_ONLY` badge |
| `operational_proof.disk_growth.*` | `overview`, `vps` | `VPS` | disk warning badge |
| `operational_proof.data_quality.*` | `shadow`, `trading` | `VPS` | stale/ok badge |
| `grafana_url` / observability refs | `overview`, `observability` | `Observability` | outbound link only |

## Immediate collapse priorities

### P0 collapse
1. move full `service_liveness` to `VPS`
2. move full `queue_trace` to `VPS`
3. move full `warmup_explainer` to `Shadow`
4. move full calibration tables to `IA Lab`
5. keep feature lineage deep detail on `Trading`

### P1 collapse
1. remove deep `model_risk` from `Overview`
2. remove deep `lab_review` from `Overview`
3. remove calibration tables from `Trading`
4. keep Backtest page as the source-mapped owner for replay/calibration proof

## Expected outcome
- fewer false-green repeats
- clearer ownership
- easier human audit
- easier future patching because each metric family has one home
