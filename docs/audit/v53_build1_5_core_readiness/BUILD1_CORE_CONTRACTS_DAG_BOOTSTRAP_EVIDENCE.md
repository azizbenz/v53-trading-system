# Build-1 Core Contracts / DAG / Bootstrap Evidence

Date: `2026-05-01`

## Scope

Build-1 covers the canonical core governance rails:

- `src/interface_contracts/`
- `src/manifest_registry/`
- `src/dag_validator/`
- `src/contract_test_suite/`
- `src/smoke_bootstrap_recovery/`
- `src/calibration_loader/`

## Source-Level Evidence

### 1. Interface contracts exist

Representative files:

- `src/interface_contracts/decision_contracts.py`
- `src/interface_contracts/forecast_contracts.py`
- `src/interface_contracts/market_event_contracts.py`
- `src/interface_contracts/refusal_records.py`
- `src/interface_contracts/strategy_identity.py`
- `src/interface_contracts/artifact_contracts*.py`

Evidence:

- One canonical `interface_contracts` package exists.
- No second top-level canonical contract package was found in the Build-1 scope.

### 2. Canonical module inventory exists

Primary file:

- `src/manifest_registry/module_inventory.py`

Evidence:

- typed `ModuleEntry`
- explicit `build_stage` on inventory rows
- canonical module table covering Build-1 through later builds

Relevant Build-1 module entries are present for:

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`
- `calibration_loader`

### 3. Build-stage mapping exists but is not coherent

Primary file:

- `src/manifest_registry/build_order_registry.py`

Evidence:

- typed `BuildStage`
- `BUILD_STAGES`
- `validate_build_order_coherent()`
- `validate_modules_have_stages()`

Observed issue:

- `cockpit` is present in inventory but absent from `BUILD_STAGES`
- `check_manifest_consistency()` reports `modules without stage: ['cockpit']`

### 4. Dependency registry exists

Primary file:

- `src/manifest_registry/dependency_registry.py`

Evidence:

- `ALLOWED_DEPENDENCIES`
- `get_allowed_dependencies(...)`
- `is_dependency_allowed(...)`
- validation helpers for unknown targets and self-dependencies

Observed issue:

- `cockpit` is declared with allowed deps `interface_contracts` and `monitoring`
- real DAG validation still detects `cockpit -> data_backbone` as unauthorized

### 5. DAG validator exists

Primary files:

- `src/dag_validator/import_scanner.py`
- `src/dag_validator/dependency_matcher.py`
- `src/dag_validator/cycle_detector.py`
- `src/dag_validator/layer_validator.py`
- `src/dag_validator/report_builder.py`

Evidence:

- real codebase scan is implemented
- cycle detection is implemented
- authorized vs unauthorized imports are classified
- dynamic imports are tracked

Observed validation result:

- cycles: `0`
- unauthorized import violations: `1`
- failing edge: `cockpit -> data_backbone`

### 6. Contract test suite exists

Primary files:

- `src/contract_test_suite/schema_assertions.py`
- `src/contract_test_suite/compatibility_checker.py`
- `src/contract_test_suite/negative_case_runner.py`
- `src/contract_test_suite/contract_test_runner.py`
- `src/contract_test_suite/contract_reporter.py`

Evidence:

- positive schema assertions
- compatibility checks
- negative-case runner
- reporting surface

### 7. Bootstrap recovery exists

Primary files:

- `src/smoke_bootstrap_recovery/bootstrap_runner.py`
- `src/smoke_bootstrap_recovery/recovery_runner.py`
- `src/smoke_bootstrap_recovery/state_sanity_checker.py`
- `src/smoke_bootstrap_recovery/engineering_guardrails.py`
- `src/smoke_bootstrap_recovery/smoke_reporter.py`

Evidence:

- import bootstrap
- full bootstrap with export checks
- state sanity checks
- guardrail integration
- smoke reporting

### 8. Calibration loader is shared Build-1 core

Primary files:

- `src/calibration_loader/loader.py`
- `src/calibration_loader/contracts.py`

Evidence:

- typed calibration artifact loader
- explicit missing-path failure
- explicit signature validation
- explicit unsupported-format failure

## Test Evidence

Relevant suites found:

- `tests/test_manifest_registry/*`
- `tests/test_dag_validator/*`
- `tests/test_contract_test_suite/*`
- `tests/test_smoke_bootstrap_recovery/*`

Executed:

- Build-1 band: `331 passed, 10 failed`
- failing subset: `69 passed, 8 failed`

## Smoke Evidence

`scripts/run_build9_core_smoke.py` result:

- Build-1: `FAIL`
- Build-2..9: `PASS`

Build-1 smoke failure causes:

- `manifest_registry`: `modules without stage: ['cockpit']`
- `dag_validator`: `DAG violations: 1 error(s)`
- `smoke_bootstrap_recovery`: engineering guardrails not clean

Guardrail evidence from smoke:

- `total_violations=3472`
- `baseline_violations=3365`
- `new_violations=107`

## Audit Checks

### No second canonical contract

Status: `PROVEN`

Reason:

- one canonical `src/interface_contracts/` package exists in the Build-1 scope

### No unauthorized dependency cycles

Status: `PROVEN`

Reason:

- cycle detector reported `0` cycles

### No fake Build-1 green

Status: `PROVEN`

Reason:

- tests and smoke both fail explicitly
- the repo is not silently presenting Build-1 as green

### No manifest drift

Status: `NOT_PROVEN`

Reason:

- build-stage mapping drift exists because `cockpit` is not staged

### Duplicate module inventory

Status: `NOT_FOUND`

Reason:

- no second inventory file was required to explain current behavior

### Calibration artifacts typed and signed/neutral

Status: `PROVEN`

Reason:

- `calibration_loader` is typed and performs explicit signature/validation checks

## Verdict

Build-1 verdict: `BLOCKED_BY_DAG`

Why:

- the build has real implementation and strong test surface
- but canonical registry coherence is broken
- smoke and DAG checks both prove the breakage explicitly
