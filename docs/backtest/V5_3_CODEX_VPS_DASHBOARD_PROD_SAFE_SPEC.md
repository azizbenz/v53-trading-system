# V5.3 — VPS DASHBOARD PROD-SAFE / SOURCE-MAPPED SPEC

**Scope:** Cockpit page `VPS`  
**Target page:** `src/cockpit/templates/pages/vps.html`  
**Mode:** read-only operational health dashboard  
**Critical rule:** the VPS page must display only data that already exists in runtime files, monitoring payloads, state adapters, or source code seams. If a metric source is missing, display `MISSING`, `NOT_YET_PERSISTED`, `STALE`, `UNKNOWN`, or `FORMULA_SOURCE_MISSING`. Do not invent backend facts.

---

# 0. Executive Decision

The VPS page is not a trading-performance page.

It is the **machine/runtime survivability page**.

It must answer:

```text
Is the VPS machine healthy?
Is the Shadow/VPS process alive?
Is the heartbeat fresh?
Is the queue consumed by the real service?
Is disk/log growth safe?
Is the network/exchange feed healthy?
Is time sync safe?
Are credentials/account-state valid without exposing secrets?
Is the kill/halt proof present?
Are config/profile/artifact hashes coherent?
Are operator alerts increasing?
```

## Golden Rule

```text
Existing runtime/monitoring value exists -> read and display it.
Existing state adapter exists            -> reuse it.
Source missing                           -> show MISSING / NOT_YET_PERSISTED.
Operational diagnostic simple formula    -> allowed only if inputs exist.
Trading/quant formula                    -> forbidden on VPS page.
```

The VPS page is an **operational truth surface**, not a quant page and not a hidden action controller.

---

# 1. Current VPS Page Audit

The current `vps.html` already displays:

```text
Build-17 status
CPU
RAM
Disk
Queue consumption status
PID
Threads
Raw service status
Control ready
Loop count
Heartbeat age
Build-17 verdict
Build-17 run state
Operator recommendation
Disk Growth partial
Service Liveness partial
Queue Trace partial
Operator Alerts
```

This is a strong base. However, it still lacks:

```text
VPS readiness verdict
Resource headroom
Disk days-to-full
Loop health / loop rate
PID safety / process identity verification
Kill/halt proof
Network/exchange connectivity
Time sync status
Data feed summary
Error/alert rate
Config/profile integrity
Credential/account-state summary
Operational source ledger
```

---

# 2. Page Ownership

## 2.1 VPS page owns

The VPS page owns:

```text
host resources
process identity
process liveness
heartbeat freshness
loop health
dashboard command queue health
disk/log/artifact growth
network and exchange connectivity summary
websocket freshness
time sync status
rate-limit pressure
kill/halt proof status
config/profile integrity
credentials/account-state summary without secrets
operator alerts and error rate
Build-17 runtime host status
```

## 2.2 VPS page does not own

Do not put full diagnostics for these domains on the VPS page:

```text
Trading performance -> Trading page
Engine/pair CE net matrix -> Trading page
Backtest formulas -> Backtest page
IA Lab artifacts/model risk/HLZ -> IA Lab page
Log search table -> Logs page
Grafana/Prometheus import details -> Observability page
Warmup deep blockers -> Shadow page
```

The VPS page may show compact badges:

```text
warmup_passed
queue_consumed
service_online
kill_proof_status
```

but full details remain on the owning pages.

---

# 3. Non-Negotiable Safety Rules

## R1 — Read-only

Forbidden in VPS state adapters/templates:

```text
write_text
write_bytes
atomic_write
os.kill
signal
queue writes
engine activation
runtime mode mutation
artifact activation
live/micro-live promotion
credential mutation
account mutation
```

## R2 — No secrets

Never display:

```text
API key
API secret
token
password
private key
raw credential bundle
```

Allowed:

```text
credential_inventory_count
active_profile_id
validation_status
environment
last_validation_at
```

## R3 — No trading formulas

The VPS page must not implement or display detailed formulas for:

```text
CE net
PSR
DSR
HLZ
Sharpe
Sortino
POT-GPD
Energy distance
VPIN
Kyle lambda
Amihud
OFI
score anatomy
engine edge
pair performance
```

If a compact trading status is required, use a badge only, sourced from existing Trading/Shadow snapshots.

## R4 — Operational formulas only

Only simple operational diagnostics are allowed. They must be marked:

```text
DISPLAY_OPERATIONAL_DIAGNOSTIC
```

These are not quant formulas and not promotion rules.

## R5 — Missing data is a valid output

If the source does not exist:

```text
Display: MISSING / NOT_YET_PERSISTED / UNKNOWN
Do not synthesize from unrelated files.
Do not create a fake metric.
```

---

# 4. Source Discovery Procedure

Before modifying the UI, Codex must inspect existing code and runtime files.

## 4.1 Code check

Inspect:

```text
src/cockpit/templates/pages/vps.html
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/state_service_liveness.py
src/cockpit/state_queue_trace.py
src/cockpit/state_disk_growth.py
src/cockpit/state_warmup_explainer.py
src/cockpit/state_data_quality.py
src/cockpit/routes_*.py
scripts/run_cockpit.py
tests/cockpit/
```

Search for existing VPS/monitoring adapters:

```text
grep -R "monitoring_payload\|service_liveness\|queue_trace\|disk_growth\|heartbeat\|pid\|Build-17\|live_complete" -n src/cockpit tests/cockpit
```

## 4.2 Runtime file check

Inspect or search latest runtime files:

```text
build/**/shadow_vps_service.state.json
build/**/vps_warmup_run.summary.json
build/**/shadow_vps_service_observability_export.json
build/**/dashboard_command_queue/**
build/**/live_websocket_snapshot_batch.json
build/**/time_sync*.json
build/**/binance_credential_inventory.json
build/**/events*.jsonl
build/**/shadow_service.log
build/**/kill_proof*.json
build/**/HALT.flag
build/**/monitoring_payload*.json
build/**/local_grafana_bootstrap.summary.json
```

## 4.3 Required source ledger

Codex must output before coding:

```text
VPS Source Ledger
- source name
- source path found
- parser/adaptor already present or missing
- source_status
- freshness
- fields available
- fields missing
```

If the source does not exist, do not invent it.

---

# 5. VPS Operational Source Ledger

Create or extend:

```text
src/cockpit/state_vps_source_ledger.py
```

## 5.1 Model

Create typed model:

```text
VpsSourceLedgerEntry
```

Fields:

```text
source_id
source_name
source_path
source_status
last_modified_at
age_seconds
fields_available
fields_missing
parser_status
reason_codes
```

Allowed `source_status`:

```text
ok
missing
stale
parse_error
not_yet_persisted
unknown
```

Allowed `parser_status`:

```text
existing_adapter
new_adapter
not_needed
missing_parser
parse_error
```

## 5.2 Mandatory UI section

Add a compact collapsible section:

```text
VPS Source Ledger
```

Columns:

```text
Source
Status
Age
Fields available
Parser
Reason
```

---

# 6. VPS Readiness Verdict

Create:

```text
src/cockpit/state_vps_readiness.py
```

## 6.1 Model

```text
VpsReadinessSnapshot
```

Fields:

```text
host_resources_status
process_status
heartbeat_status
queue_status
disk_status
network_status
time_sync_status
kill_proof_status
config_integrity_status
credential_status
vps_verdict
reason_codes
```

Allowed verdicts:

```text
VPS_NOT_OPERABLE
VPS_SHADOW_READY
VPS_RUNTIME_READY
VPS_RISK_WARNING
UNKNOWN
```

## 6.2 Verdict rules

```text
VPS_NOT_OPERABLE if process_status in [offline, dead, missing]
VPS_NOT_OPERABLE if heartbeat_status in [dead, missing]
VPS_RISK_WARNING if disk_status == critical
VPS_RISK_WARNING if queue_status in [not_configured, stalled, failed]
VPS_RISK_WARNING if network_status == degraded
VPS_RISK_WARNING if time_sync_status == drift
VPS_SHADOW_READY if process alive and heartbeat fresh but kill_proof_status == NOT_PROVEN
VPS_RUNTIME_READY only if:
    process alive
    heartbeat fresh
    disk ok/watch
    queue consumed_by_service or healthy
    network ok or unknown_not_required
    time_sync ok or unknown_not_required
    config integrity ok
```

Never output `LIVE_READY` from this page.

---

# 7. Resource Headroom

Create:

```text
src/cockpit/state_vps_resource_headroom.py
```

## 7.1 Fields

```text
cpu_pct
cpu_headroom_pct
cpu_status
ram_pct
ram_headroom_pct
ram_status
rss_mb
disk_used_pct
disk_headroom_pct
disk_free_gb
disk_status
source_status
```

## 7.2 Allowed formulas

```text
cpu_headroom_pct = 100 - cpu_pct
ram_headroom_pct = 100 - ram_pct
disk_headroom_pct = 100 - disk_used_pct
```

## 7.3 Thresholds

```text
CPU:
ok if cpu_pct < 60
watch if 60 <= cpu_pct < 80
critical if cpu_pct >= 80

RAM:
ok if ram_pct < 70
watch if 70 <= ram_pct < 85
critical if ram_pct >= 85

DISK:
ok if disk_used_pct < 75
watch if 75 <= disk_used_pct < 85
critical if disk_used_pct >= 85
```

---

# 8. Disk / Log Growth and Days To Full

Extend or create:

```text
src/cockpit/state_vps_disk_growth.py
```

## 8.1 Fields

```text
logs_size_mb
auto_exports_size_mb
artifacts_size_mb
service_dir_size_mb
daily_growth_mb
free_space_mb
estimated_days_to_full
oldest_log_date
retention_policy_present
cleanup_needed
source_status
```

## 8.2 Formula

```text
daily_growth_mb = size_today_mb - size_yesterday_mb

estimated_days_to_full =
    free_space_mb / max(daily_growth_mb, eps)
```

If no historical size sample:

```text
estimated_days_to_full = NOT_ENOUGH_HISTORY
```

If daily_growth_mb <= 0:

```text
estimated_days_to_full = STABLE_OR_SHRINKING
```

---

# 9. Service Loop Health

Create:

```text
src/cockpit/state_vps_loop_health.py
```

## 9.1 Fields

```text
main_loop_count
last_loop_started_at
last_loop_completed_at
last_cycle_duration_ms
cycle_duration_p50_ms
cycle_duration_p95_ms
missed_cycle_count
loop_rate_per_min
loop_status
source_status
```

## 9.2 Formulas

```text
last_cycle_duration_ms =
    completed_at_ms - started_at_ms

loop_rate_per_min =
    loop_count_delta / max(time_delta_minutes, eps)
```

If history not available:

```text
cycle_duration_p50_ms = NOT_YET_PERSISTED
cycle_duration_p95_ms = NOT_YET_PERSISTED
loop_rate_per_min = NOT_ENOUGH_HISTORY
```

---

# 10. Heartbeat Freshness

Extend `state_service_liveness.py` or create:

```text
src/cockpit/state_vps_heartbeat.py
```

## 10.1 Fields

```text
last_heartbeat_at
heartbeat_age_seconds
heartbeat_status
heartbeat_source_file
source_status
```

## 10.2 Formula

```text
heartbeat_age_seconds = now_ts - last_heartbeat_ts
```

## 10.3 Status

```text
fresh if age <= 60 seconds
stale if 60 < age <= 300 seconds
dead if age > 300 seconds
missing if no heartbeat
parse_error if invalid timestamp
```

---

# 11. Queue Consumption Health

Extend:

```text
src/cockpit/state_queue_trace.py
```

or create:

```text
src/cockpit/state_vps_queue_health.py
```

## 11.1 Fields

```text
queue_status
pending_count
completed_count
failed_count
last_command_id
last_kind
created_at
picked_at
completed_at
latency_ms
consumer_service_pid
command_queue_snapshot_present
queue_backlog_stalled
oldest_pending_age_seconds
failure_rate
consumption_status
source_status
```

## 11.2 Formulas

```text
queue_latency_ms =
    completed_at_ms - created_at_ms

failure_rate =
    failed_count / max(completed_count + failed_count, 1)

queue_backlog_stalled =
    pending_count > 0 and oldest_pending_age_seconds > backlog_stall_threshold_seconds
```

Default stall threshold:

```text
backlog_stall_threshold_seconds = 60
```

## 11.3 Consumption status

```text
consumed_by_service if consumer_service_pid exists or service_last_request_id matches queue request
queue_only if completed exists but no service consumer proof
not_configured if queue snapshot missing/null
stalled if backlog_stalled
failed if failure_rate > 0.20
unknown otherwise
```

---

# 12. Process Identity / PID Safety

Create:

```text
src/cockpit/state_vps_process_identity.py
```

## 12.1 Fields

```text
pid_file_present
pid
pid_is_alive
process_name
process_cmdline
process_start_time
process_uptime_seconds
pid_matches_expected_service
pid_status
source_status
```

## 12.2 Formula

```text
process_uptime_seconds =
    now_ts - process_start_ts
```

## 12.3 Status

```text
ok if pid alive and process matches expected service
pid_stale if pid file exists but process not alive
pid_missing if no pid file
pid_mismatch if pid alive but not expected service
unknown if source unavailable
```

Do not kill or signal the process from this adapter.

---

# 13. Kill / Halt Proof

Create:

```text
src/cockpit/state_vps_kill_proof.py
```

## 13.1 Fields

```text
kill_switch_status
pid_file_present
halt_flag_watcher_enabled
last_kill_test_at
last_kill_latency_ms
last_kill_result
halt_flag_path
evidence_file
source_status
```

## 13.2 Status

```text
NOT_PROVEN if no evidence file
PROVEN_SHADOW if last_kill_result == ok and latency_ms <= 1000 in shadow mode
PROVEN_PAPER if paper-mode proof exists
PROVEN_LIVE only if explicit live proof exists and project doctrine allows it
FAILED if evidence exists with failed result
parse_error if proof file corrupt
```

Do not implement kill here.  
Do not write `HALT.flag`.  
Do not call `os.kill`.

---

# 14. Network / Exchange Connectivity

Create:

```text
src/cockpit/state_vps_network_health.py
```

## 14.1 Fields

```text
ws_connected
ws_reconnect_count
last_ws_message_at
ws_gap_seconds
rest_api_latency_ms
binance_time_offset_ms
time_sync_abs_ms
time_sync_status
rate_limit_usage_pct
network_status
source_status
```

## 14.2 Formulas

```text
ws_gap_seconds =
    now_ts - last_ws_message_ts

time_sync_abs_ms =
    abs(binance_time_offset_ms)
```

## 14.3 Status

```text
ws_ok if ws_gap_seconds <= threshold
ws_stale if ws_gap_seconds > threshold
time_sync_ok if abs(offset_ms) <= threshold
time_sync_drift if abs(offset_ms) > threshold
rate_limit_watch if rate_limit_usage_pct >= 80
rate_limit_critical if rate_limit_usage_pct >= 95
```

Default thresholds:

```text
ws_gap_threshold_seconds = 30
time_sync_threshold_ms = 250
```

---

# 15. Data Feed Summary

Create:

```text
src/cockpit/state_vps_data_feed_summary.py
```

## 15.1 Fields

```text
pairs_tracked
pairs_fresh
pairs_stale
stale_pair_ratio
last_capture_at
capture_status
market_data_capture_status
source_status
```

## 15.2 Formula

```text
stale_pair_ratio =
    pairs_stale / max(pairs_tracked, 1)
```

## 15.3 Status

```text
ok if pairs_stale == 0 and pairs_tracked > 0
watch if 0 < stale_pair_ratio <= 0.25
critical if stale_pair_ratio > 0.25
missing if no pair data
```

---

# 16. Error / Alert Rate

Create:

```text
src/cockpit/state_vps_error_rate.py
```

## 16.1 Fields

```text
error_count_last_5m
error_count_last_1h
critical_count_last_1h
warning_count_last_1h
latest_error_type
latest_error_message
error_rate_per_min
alert_status
source_status
```

## 16.2 Formula

```text
error_rate_per_min =
    error_count_window / window_minutes
```

## 16.3 Status

```text
ok if error_count_last_5m == 0
watch if error_count_last_5m > 0
critical if critical_count_last_1h > 0
```

---

# 17. Config / Profile Integrity

Create:

```text
src/cockpit/state_vps_config_integrity.py
```

## 17.1 Fields

```text
runtime_profile
runtime_mode
config_file
config_hash
kill_switch_config_hash
thresholds_hash
artifact_hash_loaded
profile_complete
live_trading_allowed
config_status
source_status
```

## 17.2 Rules

```text
live_trading_allowed must be false/0 in shadow/paper
profile_complete must be true for COMPLETE runtime profile
config_hash missing -> partial
thresholds_hash missing -> partial
kill_switch_config_hash missing -> watch
```

Never expose secrets.

---

# 18. Credentials / Account State Summary

Create:

```text
src/cockpit/state_vps_account_summary.py
```

## 18.1 Fields

```text
credential_profile_active
credential_validation_status
credential_inventory_count
remote_account_snapshot_age_seconds
remote_account_state_status
open_orders_count
balances_snapshot_age_seconds
account_summary_status
source_status
```

## 18.2 Rules

```text
validated if inventory_count > 0 and active profile validation_status valid/validated
missing if inventory_count == 0
stale if remote account snapshot age > threshold
unknown if source not available
```

Default threshold:

```text
remote_account_snapshot_stale_seconds = 300
```

Never display:

```text
api_key
api_secret
token
password
```

---

# 19. UI Layout for VPS Page

Update `vps.html` order:

```text
1. VPS Readiness Verdict
2. Existing CPU/RAM/Disk/Queue cards
3. Resource Headroom
4. Process Identity / PID Safety
5. Heartbeat Freshness
6. Service Loop Health
7. Queue Consumption Health
8. Network / Exchange Connectivity
9. Data Feed Summary
10. Disk / Log Growth + Days To Full
11. Kill / Halt Proof
12. Config / Profile Integrity
13. Credentials / Account State Summary
14. Operator Alerts + Error Rate
15. VPS Source Ledger
16. Existing Build-17 Process State
```

Do not remove existing sections unless they are replaced by richer equivalents.

---

# 20. Files to Create / Modify

## 20.1 New state adapters

Create if missing:

```text
src/cockpit/state_vps_source_ledger.py
src/cockpit/state_vps_readiness.py
src/cockpit/state_vps_resource_headroom.py
src/cockpit/state_vps_disk_growth.py
src/cockpit/state_vps_loop_health.py
src/cockpit/state_vps_heartbeat.py
src/cockpit/state_vps_queue_health.py
src/cockpit/state_vps_process_identity.py
src/cockpit/state_vps_kill_proof.py
src/cockpit/state_vps_network_health.py
src/cockpit/state_vps_data_feed_summary.py
src/cockpit/state_vps_error_rate.py
src/cockpit/state_vps_config_integrity.py
src/cockpit/state_vps_account_summary.py
```

If equivalent adapters already exist, extend them instead of duplicating.

## 20.2 New templates

Create if missing:

```text
src/cockpit/templates/partials/_vps_source_ledger.html
src/cockpit/templates/partials/_vps_readiness.html
src/cockpit/templates/partials/_vps_resource_headroom.html
src/cockpit/templates/partials/_vps_loop_health.html
src/cockpit/templates/partials/_vps_heartbeat.html
src/cockpit/templates/partials/_vps_queue_health.html
src/cockpit/templates/partials/_vps_process_identity.html
src/cockpit/templates/partials/_vps_kill_proof.html
src/cockpit/templates/partials/_vps_network_health.html
src/cockpit/templates/partials/_vps_data_feed_summary.html
src/cockpit/templates/partials/_vps_error_rate.html
src/cockpit/templates/partials/_vps_config_integrity.html
src/cockpit/templates/partials/_vps_account_summary.html
```

## 20.3 Existing files to update

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/templates/pages/vps.html
tests/cockpit/
```

Do not modify trading/backend protected modules.

---

# 21. Tests

Create tests:

```text
tests/cockpit/test_state_vps_source_ledger.py
tests/cockpit/test_state_vps_readiness.py
tests/cockpit/test_state_vps_resource_headroom.py
tests/cockpit/test_state_vps_disk_growth.py
tests/cockpit/test_state_vps_loop_health.py
tests/cockpit/test_state_vps_heartbeat.py
tests/cockpit/test_state_vps_queue_health.py
tests/cockpit/test_state_vps_process_identity.py
tests/cockpit/test_state_vps_kill_proof.py
tests/cockpit/test_state_vps_network_health.py
tests/cockpit/test_state_vps_data_feed_summary.py
tests/cockpit/test_state_vps_error_rate.py
tests/cockpit/test_state_vps_config_integrity.py
tests/cockpit/test_state_vps_account_summary.py
tests/cockpit/test_routes_vps_page.py
```

## 21.1 Mandatory test cases

```text
test_vps_page_survives_all_sources_missing
test_vps_readiness_not_operable_without_process
test_resource_headroom_formulas
test_disk_days_to_full_not_enough_history
test_disk_days_to_full_stable_or_shrinking
test_heartbeat_fresh_stale_dead_missing
test_queue_latency_and_failure_rate
test_queue_consumption_not_configured_when_snapshot_missing
test_process_pid_stale_when_pid_file_dead
test_process_pid_mismatch_detected
test_kill_proof_missing_not_proven
test_network_ws_gap_and_time_sync_drift
test_data_feed_stale_pair_ratio
test_error_rate_status
test_config_integrity_live_trading_not_allowed_in_shadow
test_account_summary_hides_secrets
test_vps_source_ledger_records_missing_sources
test_vps_route_renders_all_sections
test_no_writes_or_signals_in_vps_state_adapters
```

---

# 22. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run grep checks:

```bash
grep -E "write_text|write_bytes|atomic_write|os.kill|signal\." src/cockpit/state_vps*.py
```

Expected:

```text
0 matches
```

Run secret exposure check:

```bash
grep -iE "api_secret|api_key|password|token|private_key" src/cockpit/templates/pages/vps.html src/cockpit/templates/partials/_vps*.html
```

Expected:

```text
0 displayed secret values
```

Labels like `credential_profile_active` are OK. Raw keys/secrets are not.

Run backend protection check:

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal src/execution_backbone
```

Expected:

```text
empty
```

---

# 23. Acceptance Criteria

Return `COMPLETE` only if:

```text
VPS Source Ledger exists
VPS Readiness Verdict visible
Resource headroom visible
Disk days-to-full visible or NOT_ENOUGH_HISTORY
Service loop health visible
Heartbeat freshness visible
Queue consumption health visible
PID safety visible
Kill proof visible and NOT_PROVEN if no evidence
Network/exchange connectivity visible or NOT_YET_PERSISTED
Data feed summary visible
Error/alert rate visible
Config/profile integrity visible
Credentials/account summary visible without secrets
All missing sources are explicit, not hidden
All operational formulas marked DISPLAY_OPERATIONAL_DIAGNOSTIC
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

# 24. Codex Output Format

Codex must return exactly:

```text
1. Source Ledger
2. Current VPS Page Audit
3. Files Created / Modified
4. Sections Added
5. Operational Metrics Added
6. Operational Formulas Used
7. Existing Values Preferred
8. Missing Sources Not Invented
9. Secret Exposure Check
10. Tests Added
11. Test Results
12. Read-only Guardrail Proof
13. Remaining Gaps
14. Completion Status
```

---

# 25. Final Reminder

The VPS page must not pretend the system is safe.

Correct behavior:

```text
Process missing              -> VPS_NOT_OPERABLE
Heartbeat stale/dead         -> VPS_NOT_OPERABLE
Queue not consumed           -> VPS_RISK_WARNING
Disk critical                -> VPS_RISK_WARNING
Kill proof absent            -> NOT_PROVEN
Credentials missing          -> MISSING
Network source missing       -> NOT_YET_PERSISTED
Secrets present in output    -> FAIL
```

The VPS page must protect the operator from false confidence.
