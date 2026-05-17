# V5.3 — IA LAB DASHBOARD ML + POST-TRADE REVIEW / SOURCE-MAPPED SPEC

**Scope:** Cockpit page `IA Lab`  
**Target page:** `src/cockpit/templates/pages/lab.html`  
**Mode:** Local IA Lab truth surface + governed artifact transfer visibility  
**Critical rule:** the IA Lab page must first scan existing code, reports, bundles, and artifacts to discover what can be observed. If a metric, ML detail, post-trade analysis field, or artifact proof is missing, the dashboard must show `MISSING`, `NOT_YET_PERSISTED`, `STALE`, `UNKNOWN`, or `FORMULA_SOURCE_MISSING`. Do not invent ML metrics, model scores, training reports, post-trade conclusions, or governance proofs in cockpit display code.

---

# 0. Executive Decision

The IA Lab page is the **research / calibration / ML / post-trade review / artifact governance page**.

It must answer:

```text
What did the Local IA Lab produce?
Which post-trade review conclusions exist?
Which mistakes/classes were found?
Which candidates were proposed, accepted, rejected, or archived?
Which ML/regime artifacts exist?
Which model risk entries exist?
Which feature families were used?
Which merge gates passed or failed?
Which statistical/multiple-testing controls exist?
Which artifacts are visible/imported on the VPS side?
Are transfer hashes and provenance consistent?
Are we allowed to trust this artifact for Shadow only, or is it not proven?
```

## Golden Rule

```text
Existing IA Lab report/bundle exists -> read and display it.
Existing ML/model-risk artifact exists -> read metadata only and display it.
Existing post-trade review exists -> display its structured findings.
Source missing -> show NOT_YET_PERSISTED / MISSING.
Dashboard wants a scientific conclusion -> do NOT infer it unless it exists in the report.
```

The IA Lab page is a truth surface, not a training engine, not a model evaluator, and not an artifact promotion bypass.

---

# 1. Current IA Lab Page Audit

The current `lab.html` already displays:

```text
Queue status
PHASE 2.5 Operational Proof Metrics
Run Comparison
Lab → VPS Transfer
Import Artifacts to VPS
Export from VPS
Feature Families Used
Artifact Families Visible on VPS
Transfer Queue Proof
Artifact Family Metrics
Lab Review
Refusal Journal
Model Risk
HLZ Guard
Calibration Thresholds
```

This is a good base. The page already owns the right domain: IA Lab outputs, artifact transfer, feature families, model risk, refusal journal, HLZ/multiple testing, and calibration.

However, it still needs a stricter **source-mapped ML/post-trade review layer**:

```text
IA Lab Source Ledger
Post-Trade Review Detail
Mistake Class Breakdown
Hypothesis / Candidate Lifecycle
Merge Gate Matrix
ML Artifact Inventory
Model Training / Evaluation Report Visibility
Regime Model Artifact Details
Feature Family Coverage
Label / Target Semantics Ledger
Model Risk Register Detail
Refusal Journal Detail
Multiple Testing / HLZ Detail
Calibration Provenance
Artifact Transfer Provenance
Artifact Import/Export Safety Proof
Local Lab → VPS Hash Match
IA Lab Scientific Readiness Verdict
```

---

# 2. Page Ownership

## 2.1 IA Lab page owns

The IA Lab page owns:

```text
Local IA Lab analysis bundles
post-trade review
mistake classes
hypotheses
candidate lifecycle
merge gates
artifact review and archive eligibility
capacity guard snapshot
model risk registry
ML artifact metadata
regime artifact metadata
feature family coverage
feature bridge family visibility
label / target semantics if present
training/evaluation report visibility
validation metrics if already produced
multiple-testing / HLZ guard output
calibration thresholds and provenance
refusal journal post-trade summary
artifact transfer to VPS
hash/provenance match between Local IA Lab and VPS
governed import/export queue proof
```

## 2.2 IA Lab page does not own

Do not put full diagnostics for these domains on IA Lab:

```text
Trading runtime decision trace -> Trading page
Engine/pair live economics -> Trading page
Host CPU/RAM/disk full details -> VPS page
Warmup blockers -> Shadow page
Backtest formula ledger -> Backtest page
Event log search -> Logs page
Prometheus/Grafana bootstrap -> Observability page
```

The IA Lab page may display compact badges:

```text
queue_consumption_status
artifact_visible_on_vps
hash_match
latest_review_status
```

but full details remain in their page domains.

---

# 3. Non-Negotiable Safety Rules

## R1 — Dashboard is not a trainer

Forbidden in IA Lab cockpit adapters/templates:

```text
model.fit
train()
partial_fit()
torch training loop
sklearn training call
xgboost training call
hyperparameter search
dataset mutation
label generation mutation
artifact signing
artifact activation
promotion gate mutation
queue writes outside existing governed forms
```

If the current page already has POST forms for import/export, they must remain strictly governed by the existing permission gate + command queue seam.

## R2 — No fake ML metrics

Do not invent:

```text
AUC
accuracy
precision
recall
F1
Brier score
calibration error
expected return
directional hit rate
Sharpe uplift
regime accuracy
feature importance
SHAP
drift score
```

If not present in report/artifact metadata, show:

```text
NOT_YET_PERSISTED
```

## R3 — Directional labels must be explicit and contained

If a Local IA Lab artifact contains directional labels, the page may display **metadata only** if present:

```text
target_name
horizon
label_type
training_split
artifact_scope
allowed_runtime_usage
```

But the IA Lab page must not imply that VPS RegimeDetector consumes directional side.  
If directional target appears in a VPS-bound regime artifact, show warning:

```text
DIRECTIONAL_TARGET_RUNTIME_BOUNDARY_WARNING
```

## R4 — No secrets

Never display:

```text
API key
API secret
token
password
private key
raw credential bundle
```

## R5 — Missing source is valid output

If source does not exist:

```text
Display: MISSING / NOT_YET_PERSISTED / UNKNOWN
Add reason code.
Do not synthesize from unrelated files.
```

---

# 4. Source Discovery Procedure

Before modifying UI, Codex must inspect existing code and runtime files.

## 4.1 Code check

Inspect:

```text
src/cockpit/templates/pages/lab.html
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/state_lab_review.py
src/cockpit/state_lab_vps_transfer.py
src/cockpit/state_run_comparison.py
src/cockpit/state_refusal_journal.py
src/cockpit/state_model_risk.py
src/cockpit/state_hlz_guard.py
src/cockpit/state_feature_bridge.py
src/cockpit/state_calibration_thresholds.py
src/cockpit/state_queue_trace.py
src/cockpit/routes_*.py
scripts/run_cockpit.py
tests/cockpit/
```

Search existing IA Lab surfaces:

```text
grep -R "meta_learning_review\|post_trade_review\|mistake_class\|hypothesis\|candidate\|merge_gate\|model_risk\|HLZ\|multiple_testing\|artifact_family\|lab_vps_transfer\|refusal_journal" -n src scripts tests
```

Search existing ML/regime surfaces:

```text
grep -R "model_artifact\|regime_artifact\|training_report\|evaluation_report\|feature_importance\|drift\|calibration_error\|brier\|auc\|precision\|recall\|f1\|label\|target\|horizon" -n src scripts tests
```

## 4.2 Runtime file check

Inspect or search latest IA Lab files:

```text
build/local_lab_analysis_*/post_trade_review/meta_learning_review.bundle.json
build/local_lab_analysis_*/post_trade_review/*.json
build/local_lab_analysis_*/post_trade_review/*.md
build/**/meta_learning_review.bundle.json
build/**/model_risk*.json
build/**/refusal_journal*.json
build/**/multiple_testing_review*.json
build/**/hlz*.json
build/**/calibration_report*.json
build/**/training_report*.json
build/**/evaluation_report*.json
build/**/feature_importance*.json
build/**/drift_report*.json
build/**/artifact_manifest*.json
build/**/artifact_family*.json
build/**/shadow_verdict*.json
build/**/artifact_verdict_bundle*.json
build/**/feature_bridge.json
build/**/dashboard_command_queue/**
config/calibration/v1/thresholds.yml
```

## 4.3 Required source ledger

Codex must output before coding:

```text
IA Lab Source Ledger
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

# 5. IA Lab Source Ledger

Create or extend:

```text
src/cockpit/state_lab_source_ledger.py
```

## 5.1 Model

```text
LabSourceLedgerEntry
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
IA Lab Source Ledger
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

# 6. IA Lab Scientific Readiness Verdict

Create:

```text
src/cockpit/state_lab_readiness.py
```

## 6.1 Model

```text
LabReadinessSnapshot
```

Fields:

```text
latest_review_status
post_trade_review_status
merge_gates_status
model_risk_status
refusal_journal_status
hlz_status
calibration_status
artifact_transfer_status
feature_family_status
ml_artifact_status
lab_verdict
reason_codes
```

Allowed verdicts:

```text
LAB_NOT_READY
LAB_REVIEW_ONLY
LAB_ARTIFACTS_VISIBLE
LAB_TRANSFER_PROVEN
LAB_SHADOW_READY
UNKNOWN
```

## 6.2 Verdict rules

```text
LAB_NOT_READY if latest review bundle missing
LAB_REVIEW_ONLY if review exists but no artifact transfer/hash proof
LAB_ARTIFACTS_VISIBLE if artifacts visible but queue/transfer proof missing
LAB_TRANSFER_PROVEN if Local→VPS hash match exists and queue transfer proof exists
LAB_SHADOW_READY only if:
    review exists
    merge gates pass
    model risk status ok or explicitly not_applicable
    HLZ/multiple testing status ok or not_required_for_current_slice
    artifact transfer hash match true
    artifacts marked shadow-only or validated for shadow use
```

Never output `LIVE_READY` from IA Lab page.

---

# 7. Post-Trade Review Detail

Create or extend:

```text
src/cockpit/state_lab_post_trade_review.py
```

## 7.1 Fields

```text
review_id
review_created_at
review_source_file
session_date
summary_status
mistake_classes
hypotheses_count
candidates_count
merge_gate_count
merge_gate_pass_count
merge_gate_fail_count
archive_eligibility
review_decisions
capacity_guard_snapshot
source_status
reason_codes
```

## 7.2 Rules

Use structured fields from `meta_learning_review.bundle.json` if present.

Do not infer conclusions from text blobs unless the report has explicit fields.

If only Markdown exists:

```text
source_status = partial_text_only
```

---

# 8. Mistake Class Breakdown

Create:

```text
src/cockpit/state_lab_mistake_classes.py
```

## 8.1 Fields

For each mistake class:

```text
mistake_class_id
label
severity
count
first_seen
last_seen
linked_hypotheses
linked_candidates
status
source_status
```

Known example:

```text
economic_sterilization
```

Rules:

```text
Display only classes present in review bundle.
If absent -> NOT_YET_PERSISTED.
Do not create new mistake class from dashboard.
```

---

# 9. Hypothesis / Candidate Lifecycle

Create:

```text
src/cockpit/state_lab_candidate_lifecycle.py
```

## 9.1 Fields

For each hypothesis/candidate:

```text
candidate_id
hypothesis_id
title
status
created_at
last_updated_at
linked_mistake_class
expected_effect
evidence_refs
tests_pending
merge_gate_status
archive_eligibility
decision
reason_codes
```

Status examples:

```text
proposed
under_review
tests_pending
accepted_shadow
rejected
archived
blocked
```

Rules:

```text
Only display fields present in bundle.
Do not infer expected_effect if not present.
```

---

# 10. Merge Gate Matrix

Create:

```text
src/cockpit/state_lab_merge_gates.py
```

## 10.1 Fields

For each gate:

```text
gate_id
gate_name
status
required
evidence_file
failure_reason
owner
last_checked_at
source_status
```

Allowed statuses:

```text
pass
fail
warning
not_applicable
not_yet_persisted
unknown
```

Rules:

```text
All pass -> merge_gate_status = all_pass
Any fail -> merge_gate_status = blocked
Missing required gate -> partial
```

---

# 11. ML Artifact Inventory

Create:

```text
src/cockpit/state_lab_ml_artifact_inventory.py
```

## 11.1 Fields

For each artifact:

```text
artifact_id
artifact_kind
family_id
model_type
created_at
feature_set_version
label_name
target_type
horizon
training_window
validation_status
shadow_only
allowed_runtime_usage
source_file
hash
source_status
reason_codes
```

Artifact kinds:

```text
ml_model
regime_model
shadow_ml_challenger
shadow_regime_challenger
calibration_artifact
feature_artifact
unknown
```

Rules:

```text
Read metadata only.
Do not load pickle/model binary into cockpit.
Do not execute model.
Do not compute predictions.
If binary exists but metadata absent -> metadata_missing.
```

---

# 12. Model Training / Evaluation Report Visibility

Create:

```text
src/cockpit/state_lab_model_evaluation.py
```

## 12.1 Fields

```text
artifact_id
training_report_status
evaluation_report_status
dataset_id
train_start
train_end
validation_start
validation_end
test_start
test_end
n_train
n_validation
n_test
metric_names_available
metrics
sample_warning
source_status
reason_codes
```

## 12.2 Rules

Display metrics only if present in `training_report.json`, `evaluation_report.json`, or artifact metadata.

Do not invent:

```text
AUC
accuracy
precision
recall
F1
Brier
ECE
calibration slope
drift score
```

If missing:

```text
NOT_YET_PERSISTED
```

## 12.3 Sample warnings

```text
SAMPLE_TOO_SMALL if n_train, n_validation, or n_test < report-defined threshold
UNKNOWN_SAMPLE if counts missing
```

---

# 13. Regime Model Artifact Details

Create:

```text
src/cockpit/state_lab_regime_artifacts.py
```

## 13.1 Fields

```text
artifact_id
regime_outputs
allowed_outputs
forbidden_outputs_detected
market_toxicity_score_available
regime_transition_risk_available
regime_stability_score_available
expected_duration_bucket_available
directional_label_detected
runtime_boundary_status
source_status
reason_codes
```

Allowed VPS regime semantics:

```text
regime_transition_risk
regime_stability_score
market_toxicity_score
expected_duration_bucket
```

Forbidden for VPS regime artifact:

```text
direction_up
direction_down
long
short
buy_signal
sell_signal
expected_return_direction
```

If forbidden output detected:

```text
runtime_boundary_status = violation
reason_code = lab.regime.directional_output_detected
```

---

# 14. Feature Family Coverage

Create or extend:

```text
src/cockpit/state_lab_feature_family_coverage.py
```

## 14.1 Fields

```text
feature_set_version
feature_families
recognized_feature_families
unrecognized_feature_families
feature_count
rows_with_features
missing_feature_rows
coverage_ratio
lineage_lock_status
source_status
```

## 14.2 Formula

Allowed display diagnostic:

```text
coverage_ratio =
    rows_with_features / max(rows_with_features + missing_feature_rows, 1)
```

Mark:

```text
DISPLAY_OPERATIONAL_DIAGNOSTIC
```

---

# 15. Label / Target Semantics Ledger

Create:

```text
src/cockpit/state_lab_label_semantics.py
```

## 15.1 Fields

For each artifact/report:

```text
artifact_id
target_name
target_type
horizon
label_generation_source
allowed_runtime_scope
is_directional
is_regime_only
is_cost_or_risk_only
boundary_status
reason_codes
```

Allowed `target_type` examples:

```text
regime
toxicity
duration_bucket
cost
risk
directional
unknown
```

Rules:

```text
Directional labels may exist in Local IA Lab reports but must be clearly marked.
If directional label is bound to VPS RegimeDetector artifact -> violation.
If label source missing -> unknown.
```

---

# 16. Model Risk Register Detail

Create or extend:

```text
src/cockpit/state_lab_model_risk_detail.py
```

## 16.1 Fields

```text
risk_id
artifact_id
risk_category
severity
status
detected_at
mitigation
owner
evidence_file
source_status
```

Risk categories:

```text
overfit
data_leakage
feature_drift
label_drift
sample_too_small
runtime_boundary_violation
calibration_stale
artifact_hash_mismatch
unknown
```

If model risk file absent:

```text
NOT_YET_PERSISTED
```

---

# 17. Refusal Journal Detail

Create or extend:

```text
src/cockpit/state_lab_refusal_journal_detail.py
```

## 17.1 Fields

```text
journal_status
total_refusals
top_refusal_reasons
hard_veto_count
soft_veto_count
economic_blocked_count
slippage_blocked_count
min_notional_blocked_count
data_stale_blocked_count
feature_missing_blocked_count
tail_risk_refusal_count
source_status
```

Rules:

```text
Read from refusal journal dump if present.
Do not reconstruct from unrelated files unless DTR explicitly maps refusals.
```

---

# 18. Multiple Testing / HLZ Detail

Create or extend:

```text
src/cockpit/state_lab_multiple_testing_detail.py
```

## 18.1 Fields

```text
hlz_status
dsr_floor
trial_count
candidate_count
family_count
multiple_testing_review_status
evidence_file
source_status
reason_codes
```

Rules:

```text
Display report values only.
Do not implement HLZ/DSR formulas in dashboard.
If missing -> NOT_YET_PERSISTED.
```

---

# 19. Calibration Provenance

Create or extend:

```text
src/cockpit/state_lab_calibration_provenance.py
```

## 19.1 Fields

For each threshold/calibration item:

```text
threshold_id
value
unit
used_by
source_file
signed_by
signed_at
hash
staleness_status
calibration_status
reason_codes
```

Rules:

```text
Read thresholds/calibration reports.
Do not change thresholds.
Do not compute new thresholds.
```

---

# 20. Artifact Transfer Provenance

Create or extend:

```text
src/cockpit/state_lab_transfer_provenance.py
```

## 20.1 Fields

```text
local_artifact_id
local_path
local_hash
vps_artifact_id
vps_path
vps_hash
hash_match
transfer_command_id
transfer_status
queue_consumption_status
last_transfer_at
source_status
reason_codes
```

Rules:

```text
If local exists and VPS missing -> missing_on_vps
If VPS exists and local missing -> missing_on_local
If hash differs -> hash_mismatch
If hashes match -> hash_match
Do not copy or move files.
```

---

# 21. Artifact Import/Export Safety Proof

Create:

```text
src/cockpit/state_lab_artifact_io_safety.py
```

## 21.1 Fields

```text
import_endpoints_present
export_endpoints_present
permission_gate_present
queue_route_present
max_upload_size_enforced
allowed_extensions
sha256_manifest_required
direct_activation_forbidden
last_import_result
last_export_result
io_safety_status
reason_codes
```

Rules:

```text
Unsafe if upload/import directly activates artifact.
Unsafe if permission gate missing.
Unsafe if no sha256 manifest.
Unsafe if no size cap.
Safe only if routed through governed queue.
```

---

# 22. UI Layout for IA Lab Page

Update `lab.html` order:

```text
1. IA Lab Scientific Readiness Verdict
2. Queue Status / Transfer Health compact cards
3. Run Comparison
4. Local Lab → VPS Transfer
5. Post-Trade Review Detail
6. Mistake Class Breakdown
7. Hypothesis / Candidate Lifecycle
8. Merge Gate Matrix
9. ML Artifact Inventory
10. Model Training / Evaluation Visibility
11. Regime Model Artifact Details
12. Feature Family Coverage
13. Label / Target Semantics Ledger
14. Model Risk Register Detail
15. Refusal Journal Detail
16. Multiple Testing / HLZ Detail
17. Calibration Provenance
18. Artifact Transfer Provenance
19. Artifact Import/Export Safety Proof
20. Existing Import/Export Forms
21. IA Lab Source Ledger
```

Keep current forms only if their backend endpoints are governed. Add warning near forms:

```text
Governed queue only. Upload/import does not activate live artifact.
```

---

# 23. Files to Create / Modify

## 23.1 New state adapters

Create if missing:

```text
src/cockpit/state_lab_source_ledger.py
src/cockpit/state_lab_readiness.py
src/cockpit/state_lab_post_trade_review.py
src/cockpit/state_lab_mistake_classes.py
src/cockpit/state_lab_candidate_lifecycle.py
src/cockpit/state_lab_merge_gates.py
src/cockpit/state_lab_ml_artifact_inventory.py
src/cockpit/state_lab_model_evaluation.py
src/cockpit/state_lab_regime_artifacts.py
src/cockpit/state_lab_feature_family_coverage.py
src/cockpit/state_lab_label_semantics.py
src/cockpit/state_lab_model_risk_detail.py
src/cockpit/state_lab_refusal_journal_detail.py
src/cockpit/state_lab_multiple_testing_detail.py
src/cockpit/state_lab_calibration_provenance.py
src/cockpit/state_lab_transfer_provenance.py
src/cockpit/state_lab_artifact_io_safety.py
```

If equivalent adapters already exist, extend them instead of duplicating.

## 23.2 New templates

Create if missing:

```text
src/cockpit/templates/partials/_lab_source_ledger.html
src/cockpit/templates/partials/_lab_readiness.html
src/cockpit/templates/partials/_lab_post_trade_review.html
src/cockpit/templates/partials/_lab_mistake_classes.html
src/cockpit/templates/partials/_lab_candidate_lifecycle.html
src/cockpit/templates/partials/_lab_merge_gates.html
src/cockpit/templates/partials/_lab_ml_artifact_inventory.html
src/cockpit/templates/partials/_lab_model_evaluation.html
src/cockpit/templates/partials/_lab_regime_artifacts.html
src/cockpit/templates/partials/_lab_feature_family_coverage.html
src/cockpit/templates/partials/_lab_label_semantics.html
src/cockpit/templates/partials/_lab_model_risk_detail.html
src/cockpit/templates/partials/_lab_refusal_journal_detail.html
src/cockpit/templates/partials/_lab_multiple_testing_detail.html
src/cockpit/templates/partials/_lab_calibration_provenance.html
src/cockpit/templates/partials/_lab_transfer_provenance.html
src/cockpit/templates/partials/_lab_artifact_io_safety.html
```

## 23.3 Existing files to update

```text
src/cockpit/state.py
src/cockpit/server.py
src/cockpit/templates/pages/lab.html
tests/cockpit/
```

Do not modify model training, runtime, engine, protocol, or calibration backends.

---

# 24. Tests

Create tests:

```text
tests/cockpit/test_state_lab_source_ledger.py
tests/cockpit/test_state_lab_readiness.py
tests/cockpit/test_state_lab_post_trade_review.py
tests/cockpit/test_state_lab_mistake_classes.py
tests/cockpit/test_state_lab_candidate_lifecycle.py
tests/cockpit/test_state_lab_merge_gates.py
tests/cockpit/test_state_lab_ml_artifact_inventory.py
tests/cockpit/test_state_lab_model_evaluation.py
tests/cockpit/test_state_lab_regime_artifacts.py
tests/cockpit/test_state_lab_feature_family_coverage.py
tests/cockpit/test_state_lab_label_semantics.py
tests/cockpit/test_state_lab_model_risk_detail.py
tests/cockpit/test_state_lab_refusal_journal_detail.py
tests/cockpit/test_state_lab_multiple_testing_detail.py
tests/cockpit/test_state_lab_calibration_provenance.py
tests/cockpit/test_state_lab_transfer_provenance.py
tests/cockpit/test_state_lab_artifact_io_safety.py
tests/cockpit/test_routes_lab_page.py
```

## 24.1 Mandatory test cases

```text
test_lab_page_survives_all_sources_missing
test_lab_readiness_not_ready_without_review_bundle
test_post_trade_review_reads_meta_learning_bundle
test_mistake_classes_display_only_existing_classes
test_candidate_lifecycle_no_inferred_expected_effect
test_merge_gate_matrix_blocks_on_failed_required_gate
test_ml_artifact_inventory_reads_metadata_only
test_model_evaluation_missing_metrics_not_invented
test_regime_artifacts_detect_directional_runtime_violation
test_feature_family_coverage_ratio
test_label_semantics_unknown_when_source_missing
test_model_risk_not_yet_persisted
test_refusal_journal_not_reconstructed_without_source
test_hlz_dsr_no_dashboard_formula_implementation
test_calibration_provenance_no_threshold_mutation
test_transfer_provenance_hash_match_and_mismatch
test_artifact_io_safety_requires_permission_gate_and_queue
test_lab_route_renders_all_sections
test_no_training_calls_in_lab_state_adapters
test_no_writes_or_activation_in_lab_state_adapters
test_no_secrets_displayed_on_lab_page
```

---

# 25. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run read-only/training check:

```bash
grep -E "fit\(|partial_fit\(|train\(|torch\.optim|xgboost|os.kill|signal\.|write_text|write_bytes|atomic_write" src/cockpit/state_lab*.py
```

Expected:

```text
0 matches
```

Run secret exposure check:

```bash
grep -iE "api_secret|api_key|password|token|private_key" src/cockpit/templates/pages/lab.html src/cockpit/templates/partials/_lab*.html
```

Expected:

```text
0 displayed secret values
```

Run backend protection check:

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal src/execution_backbone src/model_risk_registry
```

Expected:

```text
empty
```

If existing import/export routes require small template changes, they must remain governed and must not activate artifacts directly.

---

# 26. Acceptance Criteria

Return `COMPLETE` only if:

```text
IA Lab Source Ledger exists
IA Lab Scientific Readiness Verdict visible
Post-Trade Review Detail visible
Mistake Class Breakdown visible
Hypothesis/Candidate Lifecycle visible
Merge Gate Matrix visible
ML Artifact Inventory visible
Model Training/Evaluation Visibility visible or NOT_YET_PERSISTED
Regime Artifact Details visible with runtime-boundary warning
Feature Family Coverage visible
Label/Target Semantics Ledger visible
Model Risk Detail visible or NOT_YET_PERSISTED
Refusal Journal Detail visible or NOT_YET_PERSISTED
HLZ/Multiple Testing Detail visible or NOT_YET_PERSISTED
Calibration Provenance visible
Artifact Transfer Provenance visible
Artifact Import/Export Safety Proof visible
All missing sources explicit
No ML metrics invented
No model training in cockpit
No artifacts activated directly
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

# 27. Codex Output Format

Codex must return exactly:

```text
1. Source Ledger
2. Current IA Lab Page Audit
3. Files Created / Modified
4. Sections Added
5. ML/Post-Trade Metrics Displayed
6. Existing Values Preferred
7. Missing Sources Not Invented
8. ML Metrics Not Invented
9. Artifact IO Safety Proof
10. Secret Exposure Check
11. Tests Added
12. Test Results
13. Read-only / No-Training Guardrail Proof
14. Remaining Gaps
15. Completion Status
```

---

# 28. Final Reminder

The IA Lab page must not pretend that research proof exists.

Correct behavior:

```text
review bundle missing              -> LAB_NOT_READY
training report missing            -> NOT_YET_PERSISTED
model risk file missing            -> NOT_YET_PERSISTED
HLZ report missing                 -> NOT_YET_PERSISTED
directional target in VPS regime   -> RUNTIME_BOUNDARY_WARNING
artifact metadata missing          -> METADATA_MISSING
hash mismatch Local→VPS            -> TRANSFER_MISMATCH
import directly activates artifact -> FAIL
```

The IA Lab page must let the operator see exactly what the lab proved, what it did not prove, and what cannot yet be trusted.
