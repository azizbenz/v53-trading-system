# V5.3 — SHADOW DASHBOARD PROD-SAFE / SOURCE-MAPPED SPEC

**Scope:** Cockpit page `Shadow`  
**Target page:** `src/cockpit/templates/pages/shadow.html`  
**Mode:** read-only Shadow runtime readiness and blocker truth surface  
**Critical rule:** the Shadow page must display only data already present in warmup summaries, shadow service state, verdict bundles, artifact visibility/comparison files, queue/service liveness adapters, or existing source seams. If a source is missing, display `MISSING`, `STALE`, `NOT_YET_PERSISTED`, `UNKNOWN`, or `FORMULA_SOURCE_MISSING`. Do not invent backend facts.

---

# 0. Executive Decision

The Shadow page is the **runtime readiness and blocker page**.

It must answer:

```text
Is Shadow eligible to trade?
Which warmup checks passed or blocked?
Is the service actually running or only archive-readable?
Is control readiness proven?
Are blockers actionable?
Are challenger artifacts visible?
Are shadow comparisons meaningful?
Is queue state consistent with service control?
Are websocket/data captures fresh?
Is the shadow verdict bundle present and current?
Are alerts critical, stale, or missing?
```

## Golden Rule

```text
Existing warmup/service/verdict value exists -> read and display it.
Existing state adapter exists                -> reuse it.
Source missing                               -> show MISSING / NOT_YET_PERSISTED.
Operational diagnostic simple formula        -> allowed only if inputs exist.
Trading/quant formula                        -> forbidden on Shadow page.
```

The Shadow page is not the Trading page, not the Backtest page, and not the IA Lab page.

---

# 1. Current Shadow Page Audit

The current `shadow.html` already displays:

```text
Eligible to trade
Service status
Runtime mode
Shadow verdict
Readiness Truth
Verdict Bundle
Service Liveness
Queue Trace
Warmup Explainer
Data Quality
Artifact Visibility
Shadow Comparisons
Shadow Alerts
```

This is a strong base. The page already owns the right domain: readiness, blockers, verdict bundle, queue/service proof, and shadow artifact visibility.

However, it still needs a stricter **source-mapped, prod-safe interpretation layer**:

```text
Shadow Source Ledger
Shadow Readiness Verdict
Warmup Check Matrix
Warmup History / Trend
Blocker Action Plan
Eligibility Preconditions
Service vs Archive Reader Truth
Control Readiness Proof
Shadow Artifact Freshness
Shadow Comparison Quality
Challenger Readiness
Warmup-to-Service Consistency
Data Capture Freshness
Shadow Alert Severity Rate
```

---

# 2. Page Ownership

## 2.1 Shadow page owns

The Shadow page owns:

```text
shadow readiness
eligible_to_trade truth
warmup checks and blockers
bootstrap reconciliation status
remote account state status
credentials readiness summary without secrets
time sync warmup status
market data capture status
account user data status
service readiness vs archive-reader-only mode
control readiness proof
queue summary as it affects shadow control
artifact verdict bundle
shadow artifact visibility
champion/challenger comparisons
shadow comparison event counts and CE deltas
shadow alerts
shadow data capture freshness
```

## 2.2 Shadow page does not own

Do not put full diagnostics for these domains on Shadow:

```text
Trading decision details -> Trading page
Engine/pair matrix -> Trading page
Backtest formulas -> Backtest page
IA Lab artifact lifecycle/model risk/HLZ -> IA Lab page
Host CPU/RAM/disk full details -> VPS page
Logs search table -> Logs page
Grafana/Prometheus details -> Observability page
```

Shadow may display compact cross-page badges:

```text
service_status
queue_consumption_status
data_freshness
vps_resource_warning
```

but full details remain on the owning pages.

---

# 3. Non-Negotiable Safety Rules

## R1 — Read-only

Forbidden in Shadow state adapters/templates:

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
credential mutation
warmup mutation
live/micro-live promotion
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
credential_check_status
```

## R3 — No trading formulas

Shadow page must not implement or display detailed formulas for:

```text
CE net by engine/pair
score anatomy
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
trade sizing formulas
```

Shadow may display comparison fields if already present in verdict/comparison files:

```text
expected_ce_delta_mean
expected_gain_delta_mean
event_count
comparison_status
```

Do not recompute those in cockpit.

## R4 — Operational formulas only

Only simple operational/readiness diagnostics are allowed. They must be marked:

```text
DISPLAY_OPERATIONAL_DIAGNOSTIC
```

## R5 — Missing data is a valid output

If a source does not exist:

```text
Display: MISSING / NOT_YET_PERSISTED / UNKNOWN
Do not synthesize from unrelated files.
Do not create fake pass/fail state.
```

---

# 4. Source Discovery Procedure

Before modifying UI, Codex must inspect existing code and runtime files.

## 4.1 Code check

Inspect:

```text
src/cockpit/templates/pages/shadow.html
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/state_warmup_explainer.py
src/cockpit/state_service_liveness.py
src/cockpit/state_queue_trace.py
src/cockpit/state_data_quality.py
src/cockpit/state_source_freshness.py
src/cockpit/routes_*.py
scripts/run_cockpit.py
tests/cockpit/
```

Search for existing Shadow adapters:

```text
grep -R "warmup_explainer\|eligible_to_trade\|artifact_verdict_bundle\|artifact_runtime_visibility\|artifact_comparisons\|shadow alert\|readiness_status\|archive_reader_only" -n src/cockpit tests/cockpit
```

## 4.2 Runtime file check

Inspect or search latest runtime files:

```text
build/**/vps_warmup_run.summary.json
build/**/shadow_vps_service.state.json
build/**/shadow_vps_service_observability_export.json
build/**/artifact_verdict_bundle*.json
build/**/artifact_runtime_visibility*.json
build/**/artifact_comparisons*.json
build/**/shadow_comparisons*.json
build/**/dashboard_command_queue/**
build/**/live_websocket_snapshot_batch.json
build/**/time_sync*.json
build/**/binance_credential_inventory.json
build/**/events*.jsonl
build/**/shadow_service.log
```

## 4.3 Required source ledger

Codex must output before coding:

```text
Shadow Source Ledger
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

# 5. Shadow Source Ledger

Create or extend:

```text
src/cockpit/state_shadow_source_ledger.py
```

## 5.1 Model

Create typed model:

```text
ShadowSourceLedgerEntry
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
Shadow Source Ledger
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

# 6. Shadow Readiness Verdict

Create:

```text
src/cockpit/state_shadow_readiness.py
```

## 6.1 Model

```text
ShadowReadinessSnapshot
```

Fields:

```text
eligible_to_trade
final_state
readiness_status
warmup_status
service_status
control_ready
archive_reader_only
queue_consumption_status
data_capture_status
credential_status
time_sync_status
account_state_status
shadow_verdict
reason_codes
```

Allowed verdicts:

```text
SHADOW_BLOCKED
SHADOW_ARCHIVE_ONLY
SHADOW_OBSERVABLE
SHADOW_CONTROL_READY
SHADOW_READY
UNKNOWN
```

## 6.2 Verdict rules

```text
SHADOW_BLOCKED if eligible_to_trade is false or final_state == blocked
SHADOW_ARCHIVE_ONLY if service is offline and archive_reader_only is true
SHADOW_OBSERVABLE if warmup passed but service control_ready is false
SHADOW_CONTROL_READY if warmup passed and control_ready true but queue not consumed by service
SHADOW_READY only if:
    eligible_to_trade true
    warmup checks passed
    service running
    control_ready true
    archive_reader_only false
    queue consumption is consumed_by_service or healthy
    data capture fresh
```

Never output `MICRO_LIVE_READY` from this page.

---

# 7. Warmup Check Matrix

Create or extend:

```text
src/cockpit/state_shadow_warmup_matrix.py
```

## 7.1 Fields

For each warmup check:

```text
check_id
status
reason
source_file
current_value
required_value
required_action
suggested_command
severity
owner_page
```

Known checks:

```text
bootstrap_reconciliation
remote_account_state
time_sync
binance_credentials
market_data_capture
account_user_data
regime_lite_dependency
info_stress_dependency
```

## 7.2 Required action mapping

```text
bootstrap_reconciliation:
  action: run bootstrap reconciliation
  suggested_command: python scripts/run_shadow_bootstrap.py ...

remote_account_state:
  action: capture account snapshot / run reconciliation bootstrap

time_sync:
  action: enable time-sync probe / run with -EnableTimeSyncProbe

binance_credentials:
  action: verify credential inventory / run credential bootstrap

market_data_capture:
  action: verify websocket/depth/trade capture

account_user_data:
  action: authenticate user-data stream or accept review-only mode

regime_lite_dependency:
  action: verify regime lite dependency

info_stress_dependency:
  action: verify info stress dependency
```

Do not execute commands. Display only.

---

# 8. Warmup History / Trend

Create:

```text
src/cockpit/state_shadow_warmup_history.py
```

## 8.1 Fields

```text
current_run_id
previous_run_id
eligible_transition
blocked_count_current
blocked_count_previous
passed_count_current
passed_count_previous
new_blockers
resolved_blockers
stable_blockers
trend_status
source_status
```

## 8.2 Operational formulas

```text
blocked_count = count(check.status == blocked)

passed_count = count(check.status == passed)

resolved_blockers =
    previous_blocked_checks - current_blocked_checks

new_blockers =
    current_blocked_checks - previous_blocked_checks
```

If only one run exists:

```text
trend_status = INSUFFICIENT_HISTORY
```

---

# 9. Eligibility Preconditions

Create:

```text
src/cockpit/state_shadow_eligibility.py
```

## 9.1 Fields

```text
eligible_to_trade
all_hard_checks_passed
review_only_checks
blocking_reasons
preconditions_met_count
preconditions_total
missing_preconditions
eligibility_status
source_status
```

## 9.2 Rules

```text
all_hard_checks_passed true only if hard checks are passed
review_only checks do not count as hard pass unless doctrine says so
eligibility_status:
  eligible
  blocked
  review_only
  unknown
```

Hard checks default:

```text
bootstrap_reconciliation
remote_account_state
time_sync
binance_credentials
market_data_capture
```

If doctrine/code marks a different hard-check list, use code truth and report it.

---

# 10. Service vs Archive Reader Truth

Extend `state_service_liveness.py` or create:

```text
src/cockpit/state_shadow_service_truth.py
```

## 10.1 Fields

```text
service_status
control_ready
archive_reader_only
pid_file_present
pid_is_alive
heartbeat_age_seconds
main_loop_count
runtime_mode
service_truth_status
reason_codes
```

## 10.2 Status

```text
running_control_ready if service running and control_ready true
archive_only if archive_reader_only true
offline if service offline
stale if heartbeat stale
unknown if source missing
```

This section must clearly state whether the Shadow page is reading live state or archive files.

---

# 11. Control Readiness Proof

Create:

```text
src/cockpit/state_shadow_control_readiness.py
```

## 11.1 Fields

```text
control_ready
queue_configured
queue_consumed_by_service
pid_proof_present
halt_flag_watcher_enabled
last_command_processed
last_command_result
control_readiness_status
reason_codes
```

## 11.2 Rules

```text
not_control_ready if control_ready false
queue_only if queue exists but consumption by service not proven
control_ready if queue consumed + pid proof + service running
not_proven if required proof missing
```

Do not implement actions here.

---

# 12. Data Capture Freshness

Create or extend:

```text
src/cockpit/state_shadow_capture_freshness.py
```

## 12.1 Fields

```text
market_data_capture_status
last_capture_at
capture_age_seconds
pairs_seen
pairs_fresh
pairs_stale
websocket_status
time_sync_status
capture_freshness_status
source_status
```

## 12.2 Operational formulas

```text
capture_age_seconds = now_ts - last_capture_ts

stale_pair_ratio =
    pairs_stale / max(pairs_seen, 1)
```

Status:

```text
fresh if capture_age_seconds <= 60 and stale_pair_ratio == 0
watch if capture_age_seconds <= 300
stale if capture_age_seconds > 300
missing if no capture source
```

---

# 13. Shadow Artifact Freshness

Create:

```text
src/cockpit/state_shadow_artifact_freshness.py
```

## 13.1 Fields

For each visible artifact:

```text
slot
artifact_id
artifact_kind
forecast_target_class
forecast_horizon_class
influence_detail
shadow_only
source_file
last_modified_at
age_seconds
artifact_freshness_status
validation_status
reason_codes
```

Rules:

```text
fresh if artifact visibility file is fresh
stale if file older than threshold
missing if no artifact visibility
invalid if validation_status invalid
```

Do not activate artifacts.

---

# 14. Shadow Comparison Quality

Create:

```text
src/cockpit/state_shadow_comparison_quality.py
```

## 14.1 Fields

For each comparison:

```text
family_id
champion_artifact_id
challenger_artifact_id
comparison_status
event_count
expected_ce_delta_mean
expected_gain_delta_mean
sample_status
comparison_quality_status
reason_codes
```

## 14.2 Rules

Use report values only. Do not recompute CE deltas.

Sample status:

```text
TOO_SMALL if event_count < 30
WATCH if event_count < 100
OK otherwise
```

Comparison quality:

```text
inconclusive if sample too small
candidate_positive if expected_ce_delta_mean > 0 and sample OK
candidate_negative if expected_ce_delta_mean < 0 and sample OK
missing if source missing
```

---

# 15. Challenger Readiness

Create:

```text
src/cockpit/state_shadow_challenger_readiness.py
```

## 15.1 Fields

```text
ready_family_count
invalid_family_count
sharia_blocked_family_count
runtime_inputs_missing_family_count
shadow_only_count
active_count
operator_recommendation
challenger_readiness_status
reason_codes
```

Source priority:

```text
artifact_verdict_bundle
artifact_family_visibility
artifact_comparisons
```

Rules:

```text
ready if ready_family_count > 0 and invalid_family_count == 0
blocked_by_sharia if sharia_blocked_family_count > 0
blocked_by_missing_inputs if runtime_inputs_missing_family_count > 0
not_available if verdict bundle missing
```

---

# 16. Shadow Alert Severity Rate

Create:

```text
src/cockpit/state_shadow_alerts.py
```

or extend existing alerts adapter.

## 16.1 Fields

```text
alert_count
critical_count
warning_count
info_count
latest_alert_category
latest_alert_message
alert_rate_status
source_status
```

Status:

```text
ok if critical_count == 0 and warning_count == 0
watch if warning_count > 0
critical if critical_count > 0
```

---

# 17. Warmup-to-Service Consistency

Create:

```text
src/cockpit/state_shadow_consistency.py
```

## 17.1 Fields

```text
eligible_to_trade
service_status
control_ready
queue_consumption_status
artifact_visibility_count
consistency_status
inconsistencies
reason_codes
```

## 17.2 Rules

Flag inconsistencies:

```text
eligible true but service offline
control_ready true but queue not configured
artifact verdict ready but runtime inputs missing
market_data_capture passed but capture freshness stale
binance_credentials passed but credential inventory missing
```

Allowed statuses:

```text
consistent
watch
inconsistent
unknown
```

---

# 18. UI Layout for Shadow Page

Update `shadow.html` order:

```text
1. Shadow Readiness Verdict
2. Existing Eligible / Service / Runtime / Verdict cards
3. Readiness Truth
4. Warmup Check Matrix
5. Blocker Action Plan
6. Service vs Archive Reader Truth
7. Control Readiness Proof
8. Queue Trace compact
9. Data Capture Freshness
10. Warmup History / Trend
11. Artifact Verdict Bundle
12. Shadow Artifact Freshness
13. Shadow Comparisons
14. Shadow Comparison Quality
15. Challenger Readiness
16. Shadow Alerts + Severity
17. Warmup-to-Service Consistency
18. Shadow Source Ledger
```

Do not remove current sections unless replaced by richer equivalents.

---

# 19. Files to Create / Modify

## 19.1 New state adapters

Create if missing:

```text
src/cockpit/state_shadow_source_ledger.py
src/cockpit/state_shadow_readiness.py
src/cockpit/state_shadow_warmup_matrix.py
src/cockpit/state_shadow_warmup_history.py
src/cockpit/state_shadow_eligibility.py
src/cockpit/state_shadow_service_truth.py
src/cockpit/state_shadow_control_readiness.py
src/cockpit/state_shadow_capture_freshness.py
src/cockpit/state_shadow_artifact_freshness.py
src/cockpit/state_shadow_comparison_quality.py
src/cockpit/state_shadow_challenger_readiness.py
src/cockpit/state_shadow_alerts.py
src/cockpit/state_shadow_consistency.py
```

If equivalent adapters already exist, extend them instead of duplicating.

## 19.2 New templates

Create if missing:

```text
src/cockpit/templates/partials/_shadow_source_ledger.html
src/cockpit/templates/partials/_shadow_readiness.html
src/cockpit/templates/partials/_shadow_warmup_matrix.html
src/cockpit/templates/partials/_shadow_blocker_action_plan.html
src/cockpit/templates/partials/_shadow_warmup_history.html
src/cockpit/templates/partials/_shadow_eligibility.html
src/cockpit/templates/partials/_shadow_service_truth.html
src/cockpit/templates/partials/_shadow_control_readiness.html
src/cockpit/templates/partials/_shadow_capture_freshness.html
src/cockpit/templates/partials/_shadow_artifact_freshness.html
src/cockpit/templates/partials/_shadow_comparison_quality.html
src/cockpit/templates/partials/_shadow_challenger_readiness.html
src/cockpit/templates/partials/_shadow_alerts.html
src/cockpit/templates/partials/_shadow_consistency.html
```

## 19.3 Existing files to update

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/templates/pages/shadow.html
tests/cockpit/
```

Do not modify trading/backend protected modules.

---

# 20. Tests

Create tests:

```text
tests/cockpit/test_state_shadow_source_ledger.py
tests/cockpit/test_state_shadow_readiness.py
tests/cockpit/test_state_shadow_warmup_matrix.py
tests/cockpit/test_state_shadow_warmup_history.py
tests/cockpit/test_state_shadow_eligibility.py
tests/cockpit/test_state_shadow_service_truth.py
tests/cockpit/test_state_shadow_control_readiness.py
tests/cockpit/test_state_shadow_capture_freshness.py
tests/cockpit/test_state_shadow_artifact_freshness.py
tests/cockpit/test_state_shadow_comparison_quality.py
tests/cockpit/test_state_shadow_challenger_readiness.py
tests/cockpit/test_state_shadow_alerts.py
tests/cockpit/test_state_shadow_consistency.py
tests/cockpit/test_routes_shadow_page.py
```

## 20.1 Mandatory test cases

```text
test_shadow_page_survives_all_sources_missing
test_shadow_readiness_blocked_when_eligible_false
test_shadow_readiness_archive_only_when_service_offline_archive_true
test_shadow_ready_requires_queue_and_service_control
test_warmup_matrix_maps_known_blockers_to_actions
test_warmup_history_insufficient_history_single_run
test_eligibility_hard_checks_required
test_service_truth_archive_reader_only_visible
test_control_readiness_queue_only_not_control_ready
test_capture_freshness_stale_when_old
test_artifact_freshness_missing_visibility
test_comparison_quality_sample_too_small
test_challenger_readiness_sharia_blocked
test_alert_rate_critical
test_consistency_flags_eligible_true_service_offline
test_no_writes_or_signals_in_shadow_state_adapters
test_shadow_route_renders_all_sections
test_no_secrets_displayed_on_shadow_page
```

---

# 21. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run read-only check:

```bash
grep -E "write_text|write_bytes|atomic_write|os.kill|signal\." src/cockpit/state_shadow*.py
```

Expected:

```text
0 matches
```

Run secret exposure check:

```bash
grep -iE "api_secret|api_key|password|token|private_key" src/cockpit/templates/pages/shadow.html src/cockpit/templates/partials/_shadow*.html
```

Expected:

```text
0 displayed secret values
```

Labels like `credential_status` are OK. Raw keys/secrets are not.

Run backend protection check:

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal src/execution_backbone
```

Expected:

```text
empty
```

---

# 22. Acceptance Criteria

Return `COMPLETE` only if:

```text
Shadow Source Ledger exists
Shadow Readiness Verdict visible
Warmup Check Matrix visible
Blocker Action Plan visible
Warmup History visible or INSUFFICIENT_HISTORY
Eligibility Preconditions visible
Service vs Archive Reader Truth visible
Control Readiness Proof visible
Data Capture Freshness visible
Shadow Artifact Freshness visible
Shadow Comparison Quality visible
Challenger Readiness visible
Shadow Alert Severity visible
Warmup-to-Service Consistency visible
All missing sources are explicit, not hidden
All operational formulas marked DISPLAY_OPERATIONAL_DIAGNOSTIC
All tests pass
Read-only invariant proven
No secrets exposed
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

# 23. Codex Output Format

Codex must return exactly:

```text
1. Source Ledger
2. Current Shadow Page Audit
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

# 24. Final Reminder

The Shadow page must not pretend that the system is ready.

Correct behavior:

```text
eligible_to_trade false       -> SHADOW_BLOCKED
service offline + archive     -> SHADOW_ARCHIVE_ONLY
warmup passed but no control  -> SHADOW_OBSERVABLE
queue not consumed            -> CONTROL_NOT_PROVEN
artifact comparison < 30 evts -> SAMPLE_TOO_SMALL
verdict bundle missing        -> NOT_YET_PERSISTED
credential source missing     -> MISSING
secrets displayed             -> FAIL
```

The Shadow page must protect the operator from false confidence.
