# Build 1 Repo-Truth Audit — Dependency Architecture — 2026-04-21

## Scope

This note audits **Build 1** only:

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`
- `calibration_loader`

It answers one question:

> Does current Build-1 code still match the doctrinal expectation, or has it
> drifted from the markdown narrative?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 1:

- Build 1 is the dependency architecture and shared contract foundation.
- It must remain the root of the system.
- It must carry:
  - contracts
  - manifest/dependency truth
  - DAG validation
  - contract/build smoke/bootstrap recovery
  - shared calibration loading
- Later doctrinal enrichments from doc 20 must land **additively** on top of
  Build-1 contracts, not via replacement or bypass.

## Repo-Truth Surface

### 1. Manifest and build ordering

Build 1 is explicitly defined in:
- `src/manifest_registry/build_order_registry.py`
- `src/manifest_registry/module_inventory.py`
- `src/manifest_registry/dependency_registry.py`

Observed Build-1 module set:
- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `contract_test_suite`
- `smoke_bootstrap_recovery`
- `calibration_loader`

This is coherent across:
- module inventory
- dependency registry
- build order registry

### 2. `interface_contracts`

Current surface is broader than an early minimal contract layer.

Observed exports include:
- classical decision/risk/execution contracts
- additive forecast contracts
- strategy identity
- refusal records
- Build-14 contracts
- engine validation contracts
- shadow VPS service contracts
- pair catalog

Evidence:
- `src/interface_contracts/__init__.py`

Interpretation:
- Build 1 remained the canonical contract root
- but it absorbed several later additive doctrinal seams after the initial core

### 3. `dag_validator`

Current code confirms a real, active Build-1 DAG enforcement surface.

Observed:
- import scanning
- dependency matching
- manifest cycle detection
- observed cycle detection
- layer validation
- unified report formatting

Evidence:
- `src/dag_validator/__init__.py`
- `scripts/run_dag_check.py`

Interpretation:
- this is not stale scaffolding
- Build 1 still actively enforces architecture

### 4. `smoke_bootstrap_recovery`

Current code shows that this module is no longer just a tiny bootstrap stub.

Observed:
- bootstrap runner
- config validation
- recovery runner
- state sanity checks
- Build-1 smoke reporting
- shadow readiness helpers
- engineering guardrails integration

Evidence:
- `src/smoke_bootstrap_recovery/__init__.py`
- `scripts/run_smoke_tests.py`
- `scripts/run_engineering_guardrails.py`

Interpretation:
- the module has grown into the real Build-1 operational sanity surface
- the original markdown narrative underdescribes its current role

### 5. `calibration_loader`

Current code confirms that `calibration_loader` is a shared root module, not a
late utility.

Observed:
- typed artifact contracts
- typed loader
- validation errors
- shared import surface reused by:
  - scoring thresholds
  - regime classifier
  - execution reconciliation scheduler
  - venue adapters
  - sharia compliance
  - replay/runtime utilities

Evidence:
- `src/calibration_loader/__init__.py`
- imports across `src/`

Interpretation:
- Build 1 doctrine is correct to keep `calibration_loader` in the shared root
- but older plan narratives often understate how central it has become

## Verification Evidence

### Manifest / build registry tests

Command:

```powershell
python -m pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_dependencies.py tests/test_manifest_registry/test_build_order.py -q --tb=short
```

Result:
- `85 passed`

### Build-1 smoke / guardrails / calibration contracts

Command:

```powershell
python -m pytest tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py tests/test_smoke_bootstrap_recovery/test_engineering_guardrails.py tests/test_calibration_loader/test_contracts.py -q --tb=short
```

Result:
- `31 passed`

### Notes on warnings

Observed warning:
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-1 doctrine/code issue
- no functional failure on the audited surfaces

## Observed Divergence

### Divergence 1 — Build 1 is broader than the early markdown story

The markdown story often describes Build 1 as:
- contracts
- manifest
- DAG
- smoke/bootstrap

Current code shows Build 1 also acts as the landing zone for later additive
doctrinal seams:
- forecast contracts
- refusal records
- strategy identity
- Build-14 contract surfaces
- engine validation contracts

This is not a break.
It is an **evolution of the contract root**.

### Divergence 2 — `smoke_bootstrap_recovery` is more operational than the original narrative

The current module now owns:
- smoke orchestration
- sanity checks
- engineering guardrails participation

So the markdown phrasing "bootstrap / recovery" is no longer complete enough to
describe the module truthfully.

### Divergence 3 — `calibration_loader` is now a stronger root dependency than many plan notes imply

In current repo-truth, `calibration_loader` is not an edge utility.
It is a real Build-1 shared-core primitive used across multiple later builds.

## Decision

`PARTIAL`

## Why

Build 1 is **not broken**.

The core doctrine is still correct:
- Build 1 is the shared dependency architecture root
- the module set is coherent
- the DAG is governed
- smoke/bootstrap/guardrails exist
- calibration loading is rooted correctly

But Build 1 is **not a clean `MATCH`** either, because the markdown narrative
is now narrower than the current code surface.

So the right ruling is:
- not `STALE_CODE`
- not `STALE_MD` in the sense of total invalidity
- but `PARTIAL`, because the doctrine still points in the right direction while
  underdescribing the actual current Build-1 surface

## Patch Target

`docs only`

No Build-1 code rewrite is justified by this audit.

What should be updated over time is the doctrinal wording:
- Build 1 should be described as the shared root for
  - contracts
  - manifest/DAG enforcement
  - smoke/bootstrap recovery
  - engineering guardrails
  - shared calibration artifact loading

## Final Verdict

Build 1 is operationally healthy and structurally coherent.

The repo does **not** show a dangerous Build-1 implementation drift.

What exists is a **documentation compression drift**:
- the code is richer than the simplified doctrinal story
- but still aligned with the role Build 1 is supposed to play

Safe operational classification:
- `Build 1 = PARTIAL (docs underdescribe current code truth; no code fix required)`
