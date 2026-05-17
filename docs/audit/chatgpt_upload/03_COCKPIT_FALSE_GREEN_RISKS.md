# 03 COCKPIT FALSE-GREEN RISKS

## P0 risks

### 1. Zero-default metrics can look real
Evidence from `PAGE_FORMULA_SOURCE_LEDGER.md`:
- `ce_net = 0.0` in:
  - `src/local_replay_runtime/replay_metrics_collector.py`
  - `src/cockpit/state_economic_sterilization.py`
  - `src/cockpit/state_engine_why.py`
  - `src/cockpit/state_engines.py`
  - `src/cockpit/state_replay_metrics.py`
  - monitoring/protocol contract layers
- `exec_rate = 0.0` in `src/cockpit/state_economic_sterilization.py`
- `Field(default=0.0, ...)` rows for `conflict_rate`, `drop_rate_pct`, `economic_pass_rate`, `decision_diff_rate`

Risk:
- a displayed `0.0` can mean "true measured zero"
- or "placeholder/default/no data"
- the current raw ledger does not separate them

### 2. `NOT_YET_PERSISTED` sits too close to health/operability story
Evidence:
- backlog rows:
  - `model_risk`
  - `refusal_journal`
- formula ledger rows:
  - `src/cockpit/state_model_risk.py`
  - `src/cockpit/state_refusal_journal.py`

Risk:
- the operator can read a mostly green cockpit while two audit-critical surfaces are still placeholder-backed
- this is especially risky when surfaced near verdict or readiness zones

### 3. Service and queue proof are duplicated across too many pages
Evidence from `PAGE_DUPLICATION_AUDIT.md`:
- `operational_proof.queue_trace.*` duplicated across:
  - `overview`
  - `shadow`
  - `vps`
  - and several fields also in `lab`
- `operational_proof.service_liveness.*` duplicated across:
  - `overview`
  - `shadow`
  - `vps`

Risk:
- the same control proof can drift semantically
- the operator sees repeated copies and can mistake repetition for stronger proof

### 4. Calibration is displayed outside its owner page
Evidence from `PAGE_DUPLICATION_AUDIT.md`:
- `calibration.*` duplicated across:
  - `lab`
  - `overview`
  - `trading`

Risk:
- thresholds/signatures appear as if they are equally native to Overview/Trading
- that creates false confidence about calibration provenance

### 5. CE net placeholders are mixed with real CE formulas
Evidence:
- placeholder rows like `ce_net = 0.0`
- real aggregate formulas that sum CE across records in `replay_metrics_collector.py`

Risk:
- "CE net visible" does not necessarily mean "CE net honestly derived"
- the package must force explicit source labeling

## P1 risks

### 6. Model-risk and refusal-journal duplication between `lab` and `overview`
Evidence:
- `model_risk.*` duplicated between `lab` and `overview`
- `refusal_journal.*` duplicated between `lab` and `overview`

Risk:
- overview becomes a false audit surface
- IA Lab/Shadow ownership is blurred

### 7. Feature lineage warning duplicated between `overview` and `trading`
Evidence:
- `feature_bridge.lineage_lock_status`
- `feature_bridge.lineage_lock_reasons`

Risk:
- a lineage gap may look like a secondary warning instead of a primary Trading ownership issue

### 8. Kill proof is compressed into verdict story without strong owner separation
Evidence:
- no major duplication row found for `kill_proof`
- but kill state is folded into system operability scoring

Risk:
- kill proof can look "accounted for" at overview level before the operator visits the owner proof surface

## Required remediation principle
- no metric near a green verdict may stay unlabeled between:
  - `REAL_MEASURED_VALUE`
  - `REPORT_VALUE`
  - `PLACEHOLDER_DEFAULT`
  - `NOT_YET_PERSISTED`
  - `OPERATIONAL_DIAGNOSTIC`
