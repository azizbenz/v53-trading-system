# Build-1 Governance / DAG / Smoke Correction Patch Report

Date: `2026-05-01`

## Scope

This patch corrected the Build-1 blockers found in the Build-1 to Build-5 core readiness audit without changing trading logic, engines, or execution/risk/scoring formulas.

## Resolved items

1. `cockpit` build-stage governance is now coherent.
   - `cockpit` remains in canonical inventory with `build_stage=17`.
   - `BUILD_STAGES` now declares `cockpit` in Build-17.
   - `BUILD_STAGES` no longer duplicates `protocols` across Build-11/12/13 or `ui` across Build-10/17.
   - Build-stage validation now enforces exactly one declared stage per inventory module.

2. The `cockpit -> data_backbone` DAG mismatch is now explicit and governed.
   - `cockpit` is now allowed to read `data_backbone` as a read-only operator projection dependency.
   - The dependency validator now passes with `0` unauthorized imports and `0` cycles.

3. Build-1 smoke is green again.
   - `run_build9_core_smoke.py` now writes `build/build9_core_smoke/build1_core_health.json`.
   - Build-1 smoke passed with all 5 Build-1 modules green.

4. Build-1 cockpit visibility is now present.
   - The cockpit reads the governed Build-1 core-health artifact.
   - `system_flow` now surfaces:
     - `build1_manifest_status`
     - `build1_dag_status`
     - `build1_guardrail_status`
     - `build1_smoke_status`
     - `build1_core_health_status`
   - Missing or failing Build-1 proof remains non-green.

5. Engineering guardrails are now baseline-clean again.
   - Pre-refresh governance scan in this patch slice:
     - `total_violations=3476`
     - `baseline_violations=3365`
     - `new_violations=111`
   - Explicit baseline refresh was performed through the existing governed baseline-aware rail.
   - Post-refresh governance scan:
     - `total_violations=3476`
     - `baseline_violations=3476`
     - `new_violations=0`

## Validation

- `python -m pytest -q tests/test_manifest_registry tests/test_dag_validator tests/test_contract_test_suite tests/test_smoke_bootstrap_recovery --tb=short --disable-warnings`
  - `346 passed`
- `python -m pytest -q tests/cockpit --tb=short --disable-warnings`
  - `73 passed`
- `python scripts/run_build9_core_smoke.py`
  - `PASS`
- `python -m pytest -q tests/test_data_backbone tests/test_execution_backbone tests/test_risk_backbone tests/test_scoring_backbone --tb=short --disable-warnings`
  - `912 passed`

## Outcome

- Build-1 corrected verdict: `READY`
- Build-1 no longer blocks the Build-1 to Build-5 core foundation.
- Build-1 to Build-5 foundation can now be treated as `PARTIAL_READY`, with Build-3/4/5 still partial for their normal downstream reasons.
