# 2026-04-20 - Shadow Gate Check CLI + Exit Code Alignment

## Docs Governants

- `docs/production_deployment_plan/18_CODE_VS_PLAN_AUDIT_AND_WORK_PLAN.md`
- `docs/production_deployment_plan/update_audit/2026-04-20_codex_critical_path_micro_live_verify_and_close.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`

## Objective

Close the remaining `shadow_gate_check` gap from the pre-MICRO_LIVE critical-path pilot without changing the gate math:

- align the launcher with the requested CLI seam
- make exit-code behavior explicit and testable
- preserve the existing schema/report payload

## Current Code Seam

- launcher: `scripts/shadow_gate_check.py`
- report builder: `scripts/shadow_gate_check_support.py`
- optional sections: `scripts/shadow_gate_check_sections_support.py`
- schema: `schemas/shadow_gate_report.schema.json`
- launcher proof: `tests/test_protocols/test_shadow_gate_check_launcher.py`

## Files Changed

- `scripts/shadow_gate_check.py`
- `tests/test_protocols/test_shadow_gate_check_launcher.py`
- `docs/production_deployment_plan/update_audit/2026-04-20_codex_critical_path_micro_live_verify_and_close.md`

## Claims Implemented

- `shadow_gate_check.py` now accepts `--run-id` and `--window-days`.
- `--input` is now an alias of `--inputs-json`.
- `--window-days` can resolve `gate_id` truthfully when `--gate-id` is omitted:
  - `< 40` -> `G2.1`
  - `< 60` -> `G2.2`
  - `>= 60` -> `G2.3`
- default output path can now be derived from `--run-id` when `--output` is not passed.
- exit codes are now explicit and tested:
  - `0` = pass
  - `1` = fail on PSR or any non-Hansen blocking metric
  - `2` = fail on required Hansen SPA metric
- no gate math, schema shape, or canonical contracts were widened.

## Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache_shadow_gate python -m py_compile scripts/shadow_gate_check.py tests/test_protocols/test_shadow_gate_check_launcher.py` -> pass
- `python -m pytest -q tests/test_protocols/test_shadow_gate_check_launcher.py` -> `5 passed`
- CLI/exit-code grep proof on `scripts/shadow_gate_check.py` confirms:
  - `--run-id`
  - `--window-days`
  - `--input`
  - `--output`
  - explicit `0/1/2` classifier

## Deferred / Not Done

- no change to `shadow_gate_check` schema structure
- no change to gate math thresholds
- no attempt to close `§2.1` quant-anchor verification
- no attempt to close `§2.3` rate limiter wording/alignment

## Guardrails

- `python scripts/run_engineering_guardrails.py` -> repo-global `new_violations=5`, unchanged and outside this slice

## Completion Status

`COMPLETE` for the narrowed `shadow_gate_check` CLI/exit-code alignment slice.

## Next Safe Step

Continue with the next remaining pilot gap:

- `§2.3` rate limiter alignment
- or repo-global guardrails / DAG baseline cleanup
