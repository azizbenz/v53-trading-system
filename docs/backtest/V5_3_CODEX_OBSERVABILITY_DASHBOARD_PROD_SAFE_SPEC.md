# V5.3 — OBSERVABILITY DASHBOARD PROD-SAFE / SOURCE-MAPPED SPEC

**Scope:** Cockpit page `Observability`  
**Target page:** `src/cockpit/templates/pages/observability.html`  
**Mode:** read-only monitoring plumbing, Prometheus/Grafana/metrics-bridge truth surface  
**Critical rule:** the Observability page must display only monitoring data, bridge data, Prometheus/Grafana state, scrape status, exported metrics metadata, dashboard import state, and bootstrap summaries that already exist in files, endpoints, or existing state adapters. If a source is missing, display `MISSING`, `STALE`, `NOT_YET_PERSISTED`, `UNREACHABLE`, `PARSE_ERROR`, or `UNKNOWN`. Do not invent monitoring health.

---

# 0. Executive Decision

The Observability page is the **monitoring infrastructure page**.

It must answer:

```text
Is Prometheus reachable?
Is Grafana reachable?
Is the metrics bridge reachable?
Is the Prometheus textfile export present and fresh?
Are expected metrics emitted?
Are dashboards imported?
Are dashboard UIDs stable?
Are scrape targets healthy?
Are metric names consistent with cockpit/runtime expectations?
Are there missing Prometheus refs?
Is the observability stack reading live data or stale files?
Are alerting rules present, absent, or not configured?
```

## Golden Rule

```text
Existing monitoring value exists -> read and display it.
Existing state adapter exists    -> reuse it.
Endpoint reachable               -> display result.
Source missing                   -> display MISSING / NOT_YET_PERSISTED / UNREACHABLE.
Operational diagnostic formula   -> allowed only if inputs exist.
Trading/quant formula            -> forbidden on Observability page.
```

The Observability page is not the VPS page, not the Trading page, and not Grafana itself. It verifies that the monitoring plumbing works.

---

# 1. Current Observability Page Audit

The current `observability.html` already displays:

```text
Source status
Grafana status
Prometheus status
Bridge status
Prom text ready/missing
Output dir
Bootstrap summary path
Dashboard summary path
Bridge URL
Grafana URL
Prometheus URL
Imported dashboards:
  Shadow VPS dashboard status code / UID
  IA Lab dashboard status code / UID
  Build-17 dashboard status code / UID
```

This is a good base. It already targets the correct domain: Grafana, Prometheus, bridge readiness, prom text path, bootstrap summaries, and imported dashboard visibility.

However, it still needs a stricter **monitoring proof layer**:

```text
Observability Source Ledger
Observability Readiness Verdict
Prometheus Reachability
Grafana Reachability
Metrics Bridge Health
Prometheus Textfile Freshness
Metric Inventory / Expected Metric Coverage
Scrape Target Health
Dashboard Import Integrity
Dashboard UID Stability
Missing Metric References
Alert Rule Visibility
Exporter / Collector Health
Cross-Page Metric Contract Check
Observability Freshness and Staleness
```

---

# 2. Page Ownership

## 2.1 Observability page owns

The Observability page owns:

```text
Prometheus availability
Grafana availability
metrics bridge availability
Prometheus textfile path/freshness
metrics endpoint health
scrape target health
dashboard import status
dashboard UID visibility
observability bootstrap summary
dashboard bootstrap summary
missing metric references
metric name inventory
expected metric coverage
alert rule existence/status
exporter health
Prometheus scrape age
Grafana datasource status if available
```

## 2.2 Observability page does not own

Do not put full diagnostics for these domains on Observability:

```text
Trading performance -> Trading page
Backtest statistics/formulas -> Backtest page
IA Lab ML/post-trade details -> IA Lab page
VPS CPU/RAM/disk/process details -> VPS page
Shadow warmup blockers -> Shadow page
Log event forensics -> Logs page
```

Observability may show compact badges:

```text
service_metrics_exporting
prometheus_scraping
grafana_dashboards_imported
bridge_online
```

but full domain interpretation remains on the owner pages.

---

# 3. Non-Negotiable Safety Rules

## R1 — Read-only

Forbidden in Observability state adapters/templates:

```text
write_text
write_bytes
atomic_write
requests.post
requests.put
requests.delete
dashboard import mutation
Grafana API mutation
Prometheus config mutation
service restart
queue writes
runtime mutation
artifact mutation
```

The Observability page must not create/import dashboards, rewrite configs, restart services, or mutate Grafana/Prometheus.

## R2 — No secrets

Never display:

```text
Grafana admin password
Prometheus credentials
API key
API secret
token
authorization header
cookie
private key
```

Allowed:

```text
URL
status code
dashboard UID
datasource UID
source_status
```

## R3 — No trading/quant formulas

The Observability page must not compute:

```text
CE net
Sharpe
PSR
DSR
HLZ
POT-GPD
Energy
VPIN
OFI
trading edge
cost realism
```

It can display metric names and whether they are present, but not interpret trading performance.

## R4 — Operational formulas only

Only simple monitoring diagnostics are allowed. They must be marked:

```text
DISPLAY_OPERATIONAL_DIAGNOSTIC
```

## R5 — Missing data is a valid output

If source does not exist:

```text
Display: MISSING / NOT_YET_PERSISTED / UNKNOWN
Do not synthesize from unrelated files.
Do not claim Prometheus/Grafana is OK from a stale summary.
```

---

# 4. Source Discovery Procedure

Before modifying UI, Codex must inspect existing code and runtime files.

## 4.1 Code check

Inspect:

```text
src/cockpit/templates/pages/observability.html
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/state_observability.py
src/cockpit/routes_*.py
scripts/run_cockpit.py
scripts/run_v53_local_solution.py
scripts/Run-V53LocalSolution.ps1
src/monitoring/local_observability_stack.py
src/monitoring/local_lab_grafana_dashboard.py
tests/cockpit/
tests/monitoring/
```

Search existing observability surfaces:

```text
grep -R "observability\|prometheus\|grafana\|bridge_url\|prom_text\|dashboard_uid\|dashboard_status\|bootstrap_summary\|scrape\|metrics" -n src scripts tests
```

## 4.2 Runtime file check

Search for observability files:

```text
build/**/observability*.json
build/**/local_observability*.json
build/**/local_grafana_bootstrap.summary.json
build/**/dashboard_summary*.json
build/**/prometheus*.yml
build/**/grafana*.json
build/**/prom_text*.prom
build/**/*.prom
outputs/**/observability*.json
logs/**/observability*.log
```

Check configured URLs if present:

```text
prometheus_url
grafana_url
bridge_url
metrics bridge endpoint
```

## 4.3 Required source ledger

Codex must output before coding:

```text
Observability Source Ledger
- source name
- source path / URL found
- parser/adaptor already present or missing
- source_status
- freshness
- fields available
- fields missing
- endpoint reachability if applicable
```

If the source does not exist, do not invent it.

---

# 5. Observability Source Ledger

Create or extend:

```text
src/cockpit/state_observability_source_ledger.py
```

## 5.1 Model

```text
ObservabilitySourceLedgerEntry
```

Fields:

```text
source_id
source_name
source_kind
source_path_or_url
source_status
last_modified_at
age_seconds
http_status_code
fields_available
fields_missing
parser_status
reason_codes
```

Allowed `source_kind`:

```text
file
url
endpoint
config
summary
unknown
```

Allowed `source_status`:

```text
ok
missing
stale
parse_error
not_yet_persisted
unreachable
unknown
```

Allowed `parser_status`:

```text
existing_adapter
new_adapter
missing_parser
parse_error
not_needed
```

## 5.2 Mandatory UI section

Add a compact collapsible section:

```text
Observability Source Ledger
```

Columns:

```text
Source
Kind
Status
Age / HTTP
Fields
Parser
Reason
```

---

# 6. Observability Readiness Verdict

Create:

```text
src/cockpit/state_observability_readiness.py
```

## 6.1 Model

```text
ObservabilityReadinessSnapshot
```

Fields:

```text
prometheus_status
grafana_status
bridge_status
prom_text_status
scrape_status
dashboard_import_status
metric_coverage_status
alert_rule_status
observability_verdict
reason_codes
```

Allowed verdicts:

```text
OBS_NOT_READY
OBS_PARTIAL
OBS_READY
OBS_STALE
UNKNOWN
```

## 6.2 Verdict rules

```text
OBS_NOT_READY if Prometheus unreachable and no prom_text export exists
OBS_NOT_READY if metrics bridge unreachable and no file export exists
OBS_STALE if all sources exist but freshness thresholds exceeded
OBS_PARTIAL if some sources work and some are missing/unreachable
OBS_READY only if:
    Prometheus reachable or prom_text fresh
    Grafana reachable or dashboard import summary present
    metrics bridge reachable or prom_text fresh
    required dashboards imported or explicitly not_required
    expected metric coverage is ok/watch
```

Never output `PROD_READY` from this page.

---

# 7. Prometheus Reachability

Create or extend:

```text
src/cockpit/state_observability_prometheus.py
```

## 7.1 Fields

```text
prometheus_url
reachable
http_status_code
response_time_ms
version
target_count
healthy_target_count
unhealthy_target_count
last_query_at
prometheus_status
source_status
reason_codes
```

## 7.2 Operational diagnostics

Allowed:

```text
target_health_ratio =
    healthy_target_count / max(target_count, 1)
```

Status:

```text
ok if reachable and unhealthy_target_count == 0
watch if reachable and unhealthy_target_count > 0
unreachable if not reachable
unknown if no URL
```

Do not mutate Prometheus.

---

# 8. Grafana Reachability

Create or extend:

```text
src/cockpit/state_observability_grafana.py
```

## 8.1 Fields

```text
grafana_url
reachable
http_status_code
response_time_ms
grafana_status
dashboard_count_visible
datasource_status
grafana_version
source_status
reason_codes
```

Status:

```text
ok if reachable and status code 2xx/3xx
unreachable if request fails
unknown if no URL
```

Do not use admin APIs that mutate state.  
Do not display credentials.

---

# 9. Metrics Bridge Health

Create or extend:

```text
src/cockpit/state_observability_bridge.py
```

## 9.1 Fields

```text
bridge_url
reachable
http_status_code
response_time_ms
bridge_status
metric_family_count
sample_count
last_bridge_update_at
bridge_age_seconds
source_status
reason_codes
```

## 9.2 Status

```text
ok if reachable and sample_count > 0
empty if reachable but sample_count == 0
stale if bridge_age_seconds > threshold
unreachable if request fails
unknown if no URL
```

Default threshold:

```text
bridge_stale_seconds = 60
```

---

# 10. Prometheus Textfile Freshness

Create:

```text
src/cockpit/state_observability_prom_text.py
```

## 10.1 Fields

```text
prom_text_path
exists
last_modified_at
age_seconds
file_size_bytes
metric_line_count
parse_error_count
prom_text_status
source_status
reason_codes
```

## 10.2 Status

```text
ok if exists and age_seconds <= 60 and metric_line_count > 0
stale if age_seconds > 60
empty if file exists but metric_line_count == 0
missing if file absent
parse_error if cannot parse
```

---

# 11. Metric Inventory / Expected Metric Coverage

Create:

```text
src/cockpit/state_observability_metric_inventory.py
```

## 11.1 Fields

```text
metric_names_present
expected_metric_names
missing_metric_names
unexpected_metric_names
metric_family_count
coverage_ratio
coverage_status
source_status
```

## 11.2 Expected metric examples

Codex must discover expected metrics from existing docs/code first. If no canonical list exists, create a minimal dashboard-level expectation based on existing cockpit references, but mark:

```text
expected_metric_source = cockpit_references
```

Potential metric families:

```text
v53_shadow_vps_service_status
v53_shadow_vps_queue_pending
v53_shadow_vps_queue_completed
v53_shadow_vps_queue_failed
v53_shadow_vps_heartbeat_age_seconds
v53_shadow_vps_cpu_pct
v53_shadow_vps_ram_pct
v53_shadow_vps_disk_used_pct
v53_shadow_vps_loop_count
v53_shadow_vps_stale_pair_count
v53_shadow_vps_reconnect_count
v53_shadow_vps_kill_switch_state
v53_ia_lab_review_status
v53_ia_lab_artifact_transfer_status
```

## 11.3 Formula

```text
coverage_ratio =
    present_expected_count / max(len(expected_metric_names), 1)
```

Status:

```text
ok if coverage_ratio >= 0.90
watch if 0.50 <= coverage_ratio < 0.90
critical if coverage_ratio < 0.50
unknown if no expected list
```

---

# 12. Scrape Target Health

Create:

```text
src/cockpit/state_observability_scrape_targets.py
```

## 12.1 Fields

For each target:

```text
job
instance
health
last_scrape
last_scrape_age_seconds
last_error
scrape_duration_seconds
labels
target_status
```

Status:

```text
ok if health == up
down if health == down
stale if last_scrape_age_seconds > threshold
unknown if not available
```

Do not fail page if Prometheus target API unavailable.

---

# 13. Dashboard Import Integrity

Create or extend:

```text
src/cockpit/state_observability_dashboards.py
```

## 13.1 Fields

For each dashboard surface:

```text
surface
status_code
uid
title
imported
embedded_in
last_import_at
source_file
dashboard_status
reason_codes
```

Surfaces:

```text
Shadow VPS
IA Lab
Build-17
Trading
Backtest
VPS
Logs
Observability
```

Only include surfaces that exist or are expected by current code/docs.

Status:

```text
imported if uid present and status code 2xx/3xx
failed if status code >= 400
missing if no UID/status
embedded if explicitly embedded in another dashboard
unknown otherwise
```

---

# 14. Dashboard UID Stability

Create:

```text
src/cockpit/state_observability_uid_stability.py
```

## 14.1 Fields

```text
surface
current_uid
previous_uid
uid_changed
uid_stability_status
source_status
```

If no previous summary exists:

```text
uid_stability_status = INSUFFICIENT_HISTORY
```

If UID changed:

```text
uid_stability_status = CHANGED
```

This helps avoid broken Grafana links.

---

# 15. Missing Metric References

Create:

```text
src/cockpit/state_observability_missing_refs.py
```

## 15.1 Fields

```text
reference_id
metric_name
referenced_by
present_in_inventory
severity
reason_codes
```

Sources:

```text
dashboard JSONs
cockpit templates
monitoring builders
Prometheus metric inventory
```

Status:

```text
ok if referenced metric exists
missing if referenced metric not emitted
unknown if inventory unavailable
```

---

# 16. Alert Rule Visibility

Create:

```text
src/cockpit/state_observability_alert_rules.py
```

## 16.1 Fields

```text
rule_group_count
alert_rule_count
active_alert_count
firing_alert_count
pending_alert_count
missing_rule_files
alert_rule_status
source_status
reason_codes
```

Status:

```text
ok if rules visible and no firing alerts
watch if pending alerts exist
critical if firing alerts exist
not_configured if no rules found
unknown if source unavailable
```

Do not create or update alert rules.

---

# 17. Exporter / Collector Health

Create:

```text
src/cockpit/state_observability_exporter_health.py
```

## 17.1 Fields

```text
exporter_name
exporter_status
last_export_at
export_age_seconds
export_file
sample_count
error_count
reason_codes
```

Exporter examples:

```text
shadow_vps_exporter
ia_lab_exporter
build17_exporter
metrics_bridge
prom_text_exporter
unknown
```

Status:

```text
ok
stale
missing
parse_error
unreachable
```

---

# 18. Cross-Page Metric Contract Check

Create:

```text
src/cockpit/state_observability_contract_check.py
```

## 18.1 Purpose

Verify that metrics needed by pages exist in the monitoring inventory.

Fields:

```text
page_name
required_metric
present
source
status
reason_codes
```

Pages:

```text
Shadow
Trading
Backtest
IA Lab
VPS
Logs
Observability
```

This is not a trading formula. It is a monitoring contract check.

If no required metric map exists:

```text
status = NOT_YET_PERSISTED
```

---

# 19. Observability Freshness and Staleness

Create:

```text
src/cockpit/state_observability_freshness.py
```

## 19.1 Fields

```text
source_name
source_kind
last_updated_at
age_seconds
freshness_status
reason_codes
```

Status:

```text
fresh if age <= threshold
stale if age > threshold
missing if no source
unknown if no timestamp
```

Default thresholds:

```text
metrics bridge: 60s
prom text: 60s
bootstrap summary: 1 day
dashboard summary: 1 day
Prometheus target scrape: 60s
```

---

# 20. UI Layout for Observability Page

Update `observability.html` order:

```text
1. Observability Readiness Verdict
2. Existing Grafana / Prometheus / Bridge / Prom Text cards
3. Prometheus Reachability
4. Grafana Reachability
5. Metrics Bridge Health
6. Prometheus Textfile Freshness
7. Metric Inventory / Expected Metric Coverage
8. Scrape Target Health
9. Dashboard Import Integrity
10. Dashboard UID Stability
11. Missing Metric References
12. Alert Rule Visibility
13. Exporter / Collector Health
14. Cross-Page Metric Contract Check
15. Observability Freshness
16. Observability Source Ledger
17. Existing Stack Summary / Imported Dashboards
```

Do not remove current cards unless replaced by richer equivalents.

---

# 21. Files to Create / Modify

## 21.1 New state adapters

Create if missing:

```text
src/cockpit/state_observability_source_ledger.py
src/cockpit/state_observability_readiness.py
src/cockpit/state_observability_prometheus.py
src/cockpit/state_observability_grafana.py
src/cockpit/state_observability_bridge.py
src/cockpit/state_observability_prom_text.py
src/cockpit/state_observability_metric_inventory.py
src/cockpit/state_observability_scrape_targets.py
src/cockpit/state_observability_dashboards.py
src/cockpit/state_observability_uid_stability.py
src/cockpit/state_observability_missing_refs.py
src/cockpit/state_observability_alert_rules.py
src/cockpit/state_observability_exporter_health.py
src/cockpit/state_observability_contract_check.py
src/cockpit/state_observability_freshness.py
```

If equivalent adapters already exist, extend them instead of duplicating.

## 21.2 New templates

Create if missing:

```text
src/cockpit/templates/partials/_observability_source_ledger.html
src/cockpit/templates/partials/_observability_readiness.html
src/cockpit/templates/partials/_observability_prometheus.html
src/cockpit/templates/partials/_observability_grafana.html
src/cockpit/templates/partials/_observability_bridge.html
src/cockpit/templates/partials/_observability_prom_text.html
src/cockpit/templates/partials/_observability_metric_inventory.html
src/cockpit/templates/partials/_observability_scrape_targets.html
src/cockpit/templates/partials/_observability_dashboards.html
src/cockpit/templates/partials/_observability_uid_stability.html
src/cockpit/templates/partials/_observability_missing_refs.html
src/cockpit/templates/partials/_observability_alert_rules.html
src/cockpit/templates/partials/_observability_exporter_health.html
src/cockpit/templates/partials/_observability_contract_check.html
src/cockpit/templates/partials/_observability_freshness.html
```

## 21.3 Existing files to update

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/templates/pages/observability.html
tests/cockpit/
```

Do not modify monitoring builders unless explicitly required by a separate implementation task.

---

# 22. Tests

Create tests:

```text
tests/cockpit/test_state_observability_source_ledger.py
tests/cockpit/test_state_observability_readiness.py
tests/cockpit/test_state_observability_prometheus.py
tests/cockpit/test_state_observability_grafana.py
tests/cockpit/test_state_observability_bridge.py
tests/cockpit/test_state_observability_prom_text.py
tests/cockpit/test_state_observability_metric_inventory.py
tests/cockpit/test_state_observability_scrape_targets.py
tests/cockpit/test_state_observability_dashboards.py
tests/cockpit/test_state_observability_uid_stability.py
tests/cockpit/test_state_observability_missing_refs.py
tests/cockpit/test_state_observability_alert_rules.py
tests/cockpit/test_state_observability_exporter_health.py
tests/cockpit/test_state_observability_contract_check.py
tests/cockpit/test_state_observability_freshness.py
tests/cockpit/test_routes_observability_page.py
```

## 22.1 Mandatory test cases

```text
test_observability_page_survives_all_sources_missing
test_readiness_not_ready_when_prometheus_and_bridge_missing
test_prometheus_unreachable_status
test_grafana_unreachable_status
test_bridge_empty_status
test_prom_text_missing_stale_empty_ok
test_metric_inventory_coverage_ratio
test_scrape_targets_down_status
test_dashboard_import_missing_uid
test_uid_stability_insufficient_history
test_missing_metric_refs_detected
test_alert_rules_not_configured
test_exporter_stale_status
test_contract_check_not_yet_persisted_without_map
test_freshness_uses_thresholds
test_observability_route_renders_all_sections
test_no_mutating_http_methods_in_observability_state_adapters
test_no_secrets_displayed_on_observability_page
```

---

# 23. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run read-only/mutation check:

```bash
grep -E "write_text|write_bytes|atomic_write|requests\.post|requests\.put|requests\.delete|os.kill|signal\." src/cockpit/state_observability*.py
```

Expected:

```text
0 matches
```

Run secret exposure check:

```bash
grep -iE "password|token|api_key|api_secret|authorization|cookie|private_key" src/cockpit/templates/pages/observability.html src/cockpit/templates/partials/_observability*.html
```

Expected:

```text
0 displayed secret values
```

Run backend protection check:

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal src/execution_backbone
```

Expected:

```text
empty
```

---

# 24. Acceptance Criteria

Return `COMPLETE` only if:

```text
Observability Source Ledger exists
Observability Readiness Verdict visible
Prometheus Reachability visible
Grafana Reachability visible
Metrics Bridge Health visible
Prometheus Textfile Freshness visible
Metric Inventory/Coverage visible
Scrape Target Health visible or NOT_YET_PERSISTED
Dashboard Import Integrity visible
Dashboard UID Stability visible or INSUFFICIENT_HISTORY
Missing Metric References visible or UNKNOWN
Alert Rule Visibility visible or NOT_CONFIGURED
Exporter/Collector Health visible
Cross-Page Metric Contract Check visible or NOT_YET_PERSISTED
Observability Freshness visible
All missing/unreachable sources explicit
No mutating HTTP calls
No secrets exposed
All tests pass
Read-only invariant proven
No backend protected modules modified
```

Otherwise return:

```text
PARTIAL
```

or:

```text
BLOCKED
```

with exact missing sources.

---

# 25. Codex Output Format

Codex must return exactly:

```text
1. Source Ledger
2. Current Observability Page Audit
3. Files Created / Modified
4. Sections Added
5. Monitoring Metrics Added
6. Operational Diagnostics Used
7. Existing Values Preferred
8. Missing Sources Not Invented
9. Endpoint Reachability Results
10. Secret Exposure Check
11. Tests Added
12. Test Results
13. Read-only / No-Mutation Guardrail Proof
14. Remaining Gaps
15. Completion Status
```

---

# 26. Final Reminder

The Observability page must not pretend the monitoring stack works if it cannot prove it.

Correct behavior:

```text
Prometheus unreachable       -> UNREACHABLE
Grafana unreachable          -> UNREACHABLE
Bridge reachable but empty   -> EMPTY
Prom text missing            -> MISSING
Prom text stale              -> STALE
Dashboard UID missing        -> NOT_IMPORTED / MISSING
Metric reference absent      -> MISSING_REF
Alert rules absent           -> NOT_CONFIGURED
No source ledger             -> PARTIAL
```

The Observability page must protect the operator from false observability.
