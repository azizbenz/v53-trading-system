# 2026-04-17 Promotion Calibration Register

## Docs Governants

- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/13_CALIBRATION_METHODS.md`
- `docs/production_deployment_plan/14_SHADOW_GATE_MATH.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`

## Current Code Seam

- Promotion blockers were already present, but spread across:
  - engine audit packs
  - docs `12`, `13`, `14`
  - repo alignment notes
- No durable doc in `production_deployment_plan/` said in one place:
  - what still needs calibration before Shadow sign-off
  - what still needs proof before `G2.3 -> MICRO_LIVE`
  - what remains required before Live scaling

## Files Changed

- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md`
- `docs/production_deployment_plan/00_README.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_promotion_calibration_register.md`

## Claims Implemented

- Added a durable promotion-calibration register at `30_PROMOTION_CALIBRATION_REGISTER.md`.
- The register distinguishes:
  - `READY_FOR_SHADOW`
  - `NEEDS_MORE_CALIBRATION`
  - `RESEARCH_ONLY`
  - `DO_NOT_PROMOTE`
- The register is stage-specific:
  - before Shadow sign-off
  - before Micro-live
  - before Live scaling
- The register explicitly separates:
  - statistical calibration
  - deterministic governance proof
  - signed-artifact requirements
- Engine A, B, C, D, canonical microstructure, and shared promotion rails are all covered in one place.
- `00_README.md` now points to the new register and acknowledges the current extended doc set.

## Tests and Proof

- `rtk grep -n "Shadow/Micro-live|Micro-live|promotion|calibration|READY_FOR_SHADOW|NEEDS_MORE_CALIBRATION|DO_NOT_PROMOTE|RESEARCH_ONLY|before promotion" docs/production_deployment_plan docs/production_deployment_plan/update_audit`
- `rtk read docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `rtk read docs/production_deployment_plan/13_CALIBRATION_METHODS.md`
- `rtk read docs/production_deployment_plan/14_SHADOW_GATE_MATH.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`
- `python scripts/run_engineering_guardrails.py`

Proof target:

- new register exists in the durable plan folder, not only in `update_audit/`
- the register covers A/B/C/D plus shared rails
- the register names stage-specific blockers instead of vague "to calibrate later"
- guardrails remain clean

## Completion Status

`COMPLETE`

## Next Safe Step

Use `30_PROMOTION_CALIBRATION_REGISTER.md` as the durable checkpoint every time an engine slice changes:

- verdict
- Shadow blockers
- Micro-live blockers
- Live-scaling blockers
