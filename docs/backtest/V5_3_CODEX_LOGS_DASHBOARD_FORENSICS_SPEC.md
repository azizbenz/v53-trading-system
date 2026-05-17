# V5.3 — LOGS DASHBOARD PROD-SAFE / SOURCE-MAPPED SPEC

**Scope:** Cockpit page `Logs`  
**Target page:** `src/cockpit/templates/pages/logs.html`  
**Mode:** read-only event forensics and bounded log inspection surface  
**Critical rule:** the Logs page must display only durable events, parsed log rows, and metadata that already exist in log files or existing log reader adapters. If a source is missing, stale, malformed, or not persisted, display `MISSING`, `STALE`, `PARSE_ERROR`, `NOT_YET_PERSISTED`, or `UNKNOWN`. Do not invent events, error causes, severity, correlation IDs, or operator conclusions.

---

# 0. Executive Decision

The Logs page is the **forensics page**.

It must answer:

```text
What happened?
When did it happen?
Which subsystem emitted it?
Which run/session/job/command does it belong to?
Was it an error, warning, info, or audit event?
Is the log source durable and parseable?
Are logs stale, truncated, or incomplete?
Are queue/runtime/backtest/lab events traceable by correlation ID?
Did the same error repeat?
Which events require operator review?
```

## Golden Rule

```text
Existing durable log/event exists -> read and display it.
Existing log parser exists        -> reuse it.
Source missing                    -> show MISSING / NOT_YET_PERSISTED.
Operational diagnostic simple aggregation -> allowed only from existing events.
No log source                     -> do not invent events.
```

The Logs page is not a trading dashboard, not an observability metrics dashboard, and not a mutation surface.

---

# 1. Current Logs Page Audit

The current `logs.html` already displays:

```text
Returned events
Query form:
  event_type
  contains_text
  max_events
  error_only
Recent Events:
  events_path
  parse_error_count
  truncated
  latest_event_type
Event table:
  event_type
  message
  session_date
  error
```

This is a good first version. It is already bounded and read-only.

However, it still needs a stricter **forensics / prod-safe layer**:

```text
Logs Source Ledger
Log Freshness
Event Schema Health
Severity Breakdown
Subsystem Breakdown
Error Rate Windows
Correlation / Run / Job / Command Trace
Queue Command Event Timeline
Runtime Event Timeline
Backtest Job Event Timeline
IA Lab Event Timeline
Parse Error Detail
Truncation / Retention Status
Repeated Error Detection
Operator Review Queue
Export-safe copied event reference, not file mutation
```

---

# 2. Page Ownership

## 2.1 Logs page owns

The Logs page owns:

```text
durable event log discovery
bounded event search
event filtering
parse errors
schema health
event freshness
event severity
event type distribution
component/subsystem distribution
correlation/run/session/job/command trace
error rate windows
repeated error patterns
operator review markers if already present
stdout/stderr tails if already persisted
log retention/truncation status
```

## 2.2 Logs page does not own

Do not put full diagnostics for these domains on Logs:

```text
Trading metrics -> Trading page
Backtest formulas/results -> Backtest page
IA Lab ML/post-trade details -> IA Lab page
VPS CPU/RAM/disk/process health -> VPS page
Warmup blocker matrix -> Shadow page
Prometheus/Grafana status -> Observability page
```

The Logs page may link or summarize IDs:

```text
run_id
job_id
command_id
session_date
correlation_id
source_page_hint
```

but the full domain-specific interpretation remains on the owning page.

---

# 3. Non-Negotiable Safety Rules

## R1 — Read-only

Forbidden in Logs state adapters/templates:

```text
write_text
write_bytes
atomic_write
os.remove
unlink
rmtree
os.kill
signal
queue writes
log rotation mutation
event mutation
runtime mutation
artifact mutation
```

The Logs page must not clean, rewrite, rotate, or export logs by writing files unless a separate governed export spec exists.

## R2 — No fake severity

Do not infer severity from vague text unless the event explicitly contains a severity field or an existing parser already classifies it.

Allowed fallback:

```text
severity = unknown
```

## R3 — No fake root cause

Do not infer root cause from message text.

Allowed fields:

```text
message
error
exception_type if present
traceback_digest if present
source_file if present
```

If no root cause field exists:

```text
root_cause = UNKNOWN
```

## R4 — No secrets

Never display raw secrets inside logs.

If a log event contains sensitive-looking fields, the parser must redact display output.

Forbidden raw display:

```text
api_key
api_secret
password
token
private_key
secret
authorization
cookie
```

Allowed redaction:

```text
<REDACTED>
```

## R5 — Missing source is valid output

If no durable event log exists:

```text
Display: NO_DURABLE_LOG_FOUND / NOT_YET_PERSISTED
Do not synthesize.
```

---

# 4. Source Discovery Procedure

Before modifying UI, Codex must inspect existing code and log files.

## 4.1 Code check

Inspect:

```text
src/cockpit/templates/pages/logs.html
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/state_recent_logs.py
src/cockpit/routes_*.py
scripts/run_cockpit.py
tests/cockpit/
```

Search existing log surfaces:

```text
grep -R "recent_logs\|event_type\|events_path\|parse_error\|truncated\|durable.*log\|jsonl\|stderr\|stdout\|correlation_id\|run_id\|job_id\|command_id" -n src scripts tests
```

## 4.2 Runtime file check

Search for log/event files:

```text
build/**/events*.jsonl
build/**/event_log*.jsonl
build/**/shadow_service.log
build/**/runtime*.log
build/**/stdout*.log
build/**/stderr*.log
build/**/backtest_job*.json
build/**/backtest*.log
build/**/lab*.log
build/**/queue*.jsonl
build/**/dashboard_command_queue/**
logs/**/*.log
logs/**/*.jsonl
outputs/runs/**/tests/pytest_output.txt
outputs/runs/**/runtime/*.jsonl
outputs/runs/**/lab/*.jsonl
```

## 4.3 Required source ledger

Codex must output before coding:

```text
Logs Source Ledger
- source name
- source path found
- parser/adaptor already present or missing
- source_status
- freshness
- event count
- parse errors
- fields available
- fields missing
```

If no source exists, the page must still render with `NO_DURABLE_LOG_FOUND`.

---

# 5. Logs Source Ledger

Create or extend:

```text
src/cockpit/state_logs_source_ledger.py
```

## 5.1 Model

```text
LogsSourceLedgerEntry
```

Fields:

```text
source_id
source_name
source_path
source_status
last_modified_at
age_seconds
file_size_bytes
event_count
parse_error_count
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
missing_parser
parse_error
not_needed
```

## 5.2 Mandatory UI section

Add a compact collapsible section:

```text
Logs Source Ledger
```

Columns:

```text
Source
Status
Age
Events
Parse errors
Fields
Parser
Reason
```

---

# 6. Event Record Normalization

Create or extend:

```text
src/cockpit/state_logs_event_records.py
```

## 6.1 Normalized event model

```text
NormalizedLogEvent
```

Fields:

```text
timestamp
event_type
severity
component
subsystem
message
error
exception_type
session_date
run_id
job_id
command_id
correlation_id
pair
engine
source_file
raw_line_number
redaction_applied
reason_codes
```

## 6.2 Normalization rules

If fields are absent:

```text
severity = unknown
component = unknown
correlation_id = None
```

Do not infer component from arbitrary message text unless current code already has a mapping.

Do not crash on malformed rows.

Malformed rows must increment:

```text
parse_error_count
```

---

# 7. Secret Redaction

Create or extend:

```text
src/cockpit/state_logs_redaction.py
```

## 7.1 Redaction targets

Redact values for keys matching:

```text
api_key
api_secret
password
token
private_key
secret
authorization
cookie
signature
```

## 7.2 Rules

Display:

```text
<REDACTED>
```

Set:

```text
redaction_applied = true
```

Add reason code:

```text
logs.redaction.applied
```

Tests must ensure no raw secret value is rendered.

---

# 8. Logs Freshness

Create:

```text
src/cockpit/state_logs_freshness.py
```

## 8.1 Fields

```text
events_path
last_modified_at
age_seconds
latest_event_timestamp
latest_event_age_seconds
freshness_status
source_status
reason_codes
```

## 8.2 Status

```text
fresh if latest_event_age_seconds <= 60
stale if 60 < age <= 300
old if age > 300
missing if no file
parse_error if latest timestamp invalid
```

If timestamps unavailable, use file mtime and mark:

```text
logs.freshness.using_file_mtime
```

---

# 9. Event Schema Health

Create:

```text
src/cockpit/state_logs_schema_health.py
```

## 9.1 Fields

```text
total_lines
parsed_events
parse_error_count
parse_error_ratio
missing_timestamp_count
missing_event_type_count
missing_message_count
schema_status
source_status
```

## 9.2 Formula

```text
parse_error_ratio =
    parse_error_count / max(total_lines, 1)
```

## 9.3 Status

```text
ok if parse_error_ratio == 0
watch if 0 < parse_error_ratio <= 0.05
critical if parse_error_ratio > 0.05
missing if no log source
```

---

# 10. Severity Breakdown

Create:

```text
src/cockpit/state_logs_severity.py
```

## 10.1 Fields

```text
total_events
debug_count
info_count
warning_count
error_count
critical_count
unknown_count
severity_status
source_status
```

## 10.2 Status

```text
ok if error_count == 0 and critical_count == 0
watch if error_count > 0
critical if critical_count > 0
unknown if severities missing
```

---

# 11. Subsystem Breakdown

Create:

```text
src/cockpit/state_logs_subsystems.py
```

## 11.1 Fields

For each subsystem/component:

```text
subsystem
event_count
warning_count
error_count
critical_count
latest_event_at
latest_error
status
```

Subsystem examples if present:

```text
shadow
vps
trading
backtest
lab
queue
cockpit
observability
runtime
unknown
```

Do not invent subsystem if not present or mapped by existing code. Use `unknown`.

---

# 12. Error Rate Windows

Create:

```text
src/cockpit/state_logs_error_rate.py
```

## 12.1 Fields

```text
error_count_last_5m
error_count_last_15m
error_count_last_1h
critical_count_last_1h
warning_count_last_1h
error_rate_per_min_5m
error_rate_per_min_1h
error_rate_status
source_status
```

## 12.2 Formulas

```text
error_rate_per_min_5m =
    error_count_last_5m / 5

error_rate_per_min_1h =
    error_count_last_1h / 60
```

## 12.3 Status

```text
ok if error_count_last_5m == 0 and critical_count_last_1h == 0
watch if error_count_last_5m > 0
critical if critical_count_last_1h > 0
```

If no timestamps, status:

```text
UNKNOWN_TIMESTAMP_WINDOW
```

---

# 13. Correlation / Run / Job / Command Trace

Create:

```text
src/cockpit/state_logs_trace_index.py
```

## 13.1 Fields

```text
run_ids
job_ids
command_ids
correlation_ids
session_dates
latest_run_id
latest_job_id
latest_command_id
latest_correlation_id
trace_status
source_status
```

## 13.2 Rules

Extract only if fields exist.

If no IDs:

```text
trace_status = NOT_YET_PERSISTED
```

Do not infer IDs from message text unless current code explicitly encodes them.

---

# 14. Command Event Timeline

Create:

```text
src/cockpit/state_logs_command_timeline.py
```

## 14.1 Fields

For each recent command_id:

```text
command_id
created_at
picked_at
completed_at
failed_at
status
latency_ms
event_count
latest_message
source_status
```

## 14.2 Formula

```text
latency_ms = completed_at_ms - created_at_ms
```

Only if both timestamps exist.

If not:

```text
latency_ms = NOT_YET_PERSISTED
```

---

# 15. Runtime Event Timeline

Create:

```text
src/cockpit/state_logs_runtime_timeline.py
```

## 15.1 Fields

```text
latest_service_start
latest_service_stop
latest_heartbeat
latest_loop_event
latest_error
loop_events_count
runtime_timeline_status
source_status
```

Do not infer service start/stop unless event types exist.

---

# 16. Backtest Job Event Timeline

Create:

```text
src/cockpit/state_logs_backtest_timeline.py
```

## 16.1 Fields

```text
job_id
requested_at
started_at
completed_at
failed_at
status
exit_code
latest_message
stdout_log_path
stderr_log_path
source_status
```

Source priority:

```text
backtest job records
durable event logs
stdout/stderr logs
```

If absent:

```text
NOT_YET_PERSISTED
```

---

# 17. IA Lab Event Timeline

Create:

```text
src/cockpit/state_logs_lab_timeline.py
```

## 17.1 Fields

```text
latest_review_event_at
latest_transfer_event_at
latest_import_event_at
latest_export_event_at
latest_model_risk_event_at
latest_hlz_event_at
event_count
source_status
```

If absent:

```text
NOT_YET_PERSISTED
```

---

# 18. Parse Error Detail

Create:

```text
src/cockpit/state_logs_parse_errors.py
```

## 18.1 Fields

For recent parse errors:

```text
source_path
line_number
error_summary
raw_line_preview
redacted
reason_codes
```

Rules:

```text
raw_line_preview must be truncated to max 300 chars
apply secret redaction before display
```

---

# 19. Truncation / Retention Status

Create:

```text
src/cockpit/state_logs_retention.py
```

## 19.1 Fields

```text
returned_event_count
max_events
truncated
events_path
file_size_mb
oldest_event_at
latest_event_at
retention_policy_present
retention_status
source_status
```

## 19.2 Status

```text
ok if not truncated and file_size acceptable
watch if truncated
critical if file_size too large and no retention policy
missing if no log
```

---

# 20. Repeated Error Detection

Create:

```text
src/cockpit/state_logs_repeated_errors.py
```

## 20.1 Fields

For repeated error groups:

```text
error_fingerprint
message_digest
exception_type
count
first_seen
last_seen
affected_components
status
```

## 20.2 Allowed formula

```text
error_fingerprint = sha256(exception_type + normalized_error_message)
```

Rules:

```text
Use redacted/normalized message.
Do not include secrets.
Do not infer root cause.
```

Status:

```text
repeated if count >= 2
frequent if count >= 5
```

---

# 21. Operator Review Queue

Create:

```text
src/cockpit/state_logs_operator_review.py
```

## 21.1 Fields

```text
review_event_count
critical_review_count
latest_review_event
categories
review_status
source_status
```

Rules:

```text
Only include events explicitly marked for operator review or severity critical/error.
Do not create workflow actions.
```

---

# 22. UI Layout for Logs Page

Update `logs.html` order:

```text
1. Logs Freshness Summary
2. Existing Query Form
3. Severity Breakdown
4. Error Rate Windows
5. Event Schema Health
6. Recent Events Table
7. Correlation / Run / Job / Command Trace
8. Command Event Timeline
9. Runtime Event Timeline
10. Backtest Job Event Timeline
11. IA Lab Event Timeline
12. Subsystem Breakdown
13. Parse Error Detail
14. Repeated Error Detection
15. Truncation / Retention Status
16. Operator Review Queue
17. Logs Source Ledger
```

Keep the existing query form and bounded recent-events table.

---

# 23. Files to Create / Modify

## 23.1 New state adapters

Create if missing:

```text
src/cockpit/state_logs_source_ledger.py
src/cockpit/state_logs_event_records.py
src/cockpit/state_logs_redaction.py
src/cockpit/state_logs_freshness.py
src/cockpit/state_logs_schema_health.py
src/cockpit/state_logs_severity.py
src/cockpit/state_logs_subsystems.py
src/cockpit/state_logs_error_rate.py
src/cockpit/state_logs_trace_index.py
src/cockpit/state_logs_command_timeline.py
src/cockpit/state_logs_runtime_timeline.py
src/cockpit/state_logs_backtest_timeline.py
src/cockpit/state_logs_lab_timeline.py
src/cockpit/state_logs_parse_errors.py
src/cockpit/state_logs_retention.py
src/cockpit/state_logs_repeated_errors.py
src/cockpit/state_logs_operator_review.py
```

If equivalent adapters already exist, extend them instead of duplicating.

## 23.2 New templates

Create if missing:

```text
src/cockpit/templates/partials/_logs_source_ledger.html
src/cockpit/templates/partials/_logs_freshness.html
src/cockpit/templates/partials/_logs_schema_health.html
src/cockpit/templates/partials/_logs_severity.html
src/cockpit/templates/partials/_logs_subsystems.html
src/cockpit/templates/partials/_logs_error_rate.html
src/cockpit/templates/partials/_logs_trace_index.html
src/cockpit/templates/partials/_logs_command_timeline.html
src/cockpit/templates/partials/_logs_runtime_timeline.html
src/cockpit/templates/partials/_logs_backtest_timeline.html
src/cockpit/templates/partials/_logs_lab_timeline.html
src/cockpit/templates/partials/_logs_parse_errors.html
src/cockpit/templates/partials/_logs_retention.html
src/cockpit/templates/partials/_logs_repeated_errors.html
src/cockpit/templates/partials/_logs_operator_review.html
```

## 23.3 Existing files to update

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/templates/pages/logs.html
tests/cockpit/
```

Do not modify domain backends.

---

# 24. Tests

Create tests:

```text
tests/cockpit/test_state_logs_source_ledger.py
tests/cockpit/test_state_logs_event_records.py
tests/cockpit/test_state_logs_redaction.py
tests/cockpit/test_state_logs_freshness.py
tests/cockpit/test_state_logs_schema_health.py
tests/cockpit/test_state_logs_severity.py
tests/cockpit/test_state_logs_subsystems.py
tests/cockpit/test_state_logs_error_rate.py
tests/cockpit/test_state_logs_trace_index.py
tests/cockpit/test_state_logs_command_timeline.py
tests/cockpit/test_state_logs_runtime_timeline.py
tests/cockpit/test_state_logs_backtest_timeline.py
tests/cockpit/test_state_logs_lab_timeline.py
tests/cockpit/test_state_logs_parse_errors.py
tests/cockpit/test_state_logs_retention.py
tests/cockpit/test_state_logs_repeated_errors.py
tests/cockpit/test_state_logs_operator_review.py
tests/cockpit/test_routes_logs_page.py
```

## 24.1 Mandatory test cases

```text
test_logs_page_survives_no_log_source
test_malformed_jsonl_increments_parse_error
test_secret_values_are_redacted
test_freshness_uses_event_timestamp_if_available
test_freshness_falls_back_to_file_mtime
test_schema_health_parse_error_ratio
test_severity_breakdown_unknown_when_missing
test_error_rate_requires_timestamps
test_trace_index_extracts_only_existing_ids
test_command_timeline_latency_only_when_timestamps_exist
test_runtime_timeline_not_inferred_from_free_text
test_backtest_timeline_missing_not_yet_persisted
test_lab_timeline_missing_not_yet_persisted
test_parse_error_preview_truncated_and_redacted
test_retention_truncated_status
test_repeated_error_fingerprint_redacted
test_operator_review_only_explicit_or_error_events
test_logs_route_renders_all_sections
test_no_writes_or_deletes_in_logs_state_adapters
```

---

# 25. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run read-only/destructive check:

```bash
grep -E "write_text|write_bytes|atomic_write|os.remove|unlink|rmtree|os.kill|signal\." src/cockpit/state_logs*.py
```

Expected:

```text
0 matches
```

Run secret exposure check:

```bash
grep -iE "api_secret|api_key|password|token|private_key|authorization|cookie" src/cockpit/templates/pages/logs.html src/cockpit/templates/partials/_logs*.html
```

Expected:

```text
0 raw secret values
```

Labels are allowed only if not rendering raw values.

Run backend protection check:

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal src/execution_backbone src/model_risk_registry
```

Expected:

```text
empty
```

---

# 26. Acceptance Criteria

Return `COMPLETE` only if:

```text
Logs Source Ledger exists
Logs Freshness visible
Event Schema Health visible
Severity Breakdown visible
Error Rate Windows visible
Recent Events still works
Trace Index visible
Command Event Timeline visible or NOT_YET_PERSISTED
Runtime Event Timeline visible or NOT_YET_PERSISTED
Backtest Timeline visible or NOT_YET_PERSISTED
IA Lab Timeline visible or NOT_YET_PERSISTED
Subsystem Breakdown visible
Parse Error Detail visible
Repeated Error Detection visible
Truncation / Retention Status visible
Operator Review Queue visible
All missing sources explicit
Secrets redacted
All tests pass
Read-only/destructive invariant proven
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

# 27. Codex Output Format

Codex must return exactly:

```text
1. Source Ledger
2. Current Logs Page Audit
3. Files Created / Modified
4. Sections Added
5. Event Metrics Added
6. Operational Diagnostics Used
7. Existing Values Preferred
8. Missing Sources Not Invented
9. Secret Redaction Proof
10. Tests Added
11. Test Results
12. Read-only / No-Destructive Guardrail Proof
13. Remaining Gaps
14. Completion Status
```

---

# 28. Final Reminder

The Logs page must not pretend to know what happened if no durable event exists.

Correct behavior:

```text
no log file                     -> NO_DURABLE_LOG_FOUND
malformed rows                  -> PARSE_ERROR with count
secret-like value               -> <REDACTED>
no timestamps                   -> UNKNOWN_TIMESTAMP_WINDOW
no command_id                   -> TRACE_NOT_YET_PERSISTED
event repeated                  -> repeated_error group
critical event                  -> operator_review
truncated result                -> retention warning
```

The Logs page must let the operator investigate safely without mutating the system.
