# Build-1 to Build-5 Test Coverage Evidence

Date: `2026-05-01`

## Requested Validation Commands

### Build-1 band

Command:

```text
python -m pytest -q tests/test_manifest_registry tests/test_dag_validator tests/test_contract_test_suite tests/test_smoke_bootstrap_recovery --tb=short --disable-warnings
```

Observed execution:

- sandboxed RTK equivalent run completed
- result: `331 passed, 10 failed`

### Build-1 failing subset

Command:

```text
python -m pytest -q tests/test_manifest_registry/test_build_order.py tests/test_dag_validator/test_report_and_pipeline.py tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py --tb=short --disable-warnings
```

Observed execution:

- result: `69 passed, 8 failed`

### Build-1 DAG detail

Command:

```text
python -m pytest tests/test_dag_validator/test_report_and_pipeline.py::TestFullPipeline::test_v53_codebase_passes_validation -vv --tb=short --disable-warnings
```

Observed execution:

- result: `1 failed`
- critical detail: one unauthorized import, `cockpit -> data_backbone`

### Build-2..5 band

Command:

```text
python -m pytest -q tests/test_data_backbone tests/test_execution_backbone tests/test_risk_backbone tests/test_scoring_backbone --tb=short --disable-warnings
```

Observed execution:

- sandboxed RTK attempt hit temp-dir permission noise
- unrestricted rerun passed
- result: `912 passed`

### Core smoke launcher

Command:

```text
python scripts/run_build9_core_smoke.py
```

Observed execution:

- exit status: non-zero
- Build-1: `FAIL`
- Build-2..9: `PASS`

## Logic Test Status

### Build-1

Status: `FAIL`

Proven failure reasons:

- `cockpit` missing from build stages
- one DAG violation
- engineering guardrails report `107` new violations beyond baseline

### Build-2

Status: `PASS`

### Build-3

Status: `PASS`

### Build-4

Status: `PASS`

### Build-5

Status: `PASS`

## Environment Failures

- RTK wrapper did not behave cleanly for every read/pytest pattern in this shell setup.
- One sandboxed Build-2..5 pytest run reported `PermissionError [WinError 5]` on the `.test_tmp` cleanup path.
- The Build-2..5 logic status was recovered by an unrestricted rerun, which passed cleanly.

These environment failures do not explain the Build-1 logic failures.

## Coverage Assessment

- Build-1 has strong direct coverage across registry, DAG, contract-suite, and smoke rails.
- Build-2 has broad direct coverage across ingestion, freshness, consistency, pair health, event normalization, and microstructure.
- Build-3 has broad direct coverage across execution runtime, gatekeeper, rate limits, venue constraints, fill tracking, reconciliation, and smoke import/API checks.
- Build-4 has broad direct coverage across risk runtime, guards, breakers, budgeters, and explainability.
- Build-5 has broad direct coverage across runtime, integration, raw-score, penalty, hard-block, ranking, thresholds, and fee-aware edge gates.

## Test Coverage Verdict

Test coverage status: `STRONG_BUT_NOT_UNIFORMLY_GREEN`

Reason:

- Build-2..5 are green in the requested band
- Build-1 has real failing governance checks, not just missing coverage
