# Microstructure Engine Input Provenance Seams

## Objective

Advance Step 3 without forcing engine rewrites by making the current Engine A and Engine C microstructure input seams explicit and test-audited: the engines must expose the additive canonical feature fields they currently consume, and the runner/consumer surfaces must not hide direct imports of canonical microstructure calculators.

## Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md` Phase 2 canonical microstructure rollout
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md` consumer-map doctrine for OFI / VPIN / Kyle / realized-kernel / queue pressure
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` additive migration order and no-greenfield rule
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` proof discipline
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md` audit-pack structure

## Current Code Seam

- Canonical files today: `src/engines/engine_a/engine_a_runner.py` and `src/engines/engine_c/engine_c_runner.py`
- Why this seam is the right place: these input contracts are the current landing seams through which canonical microstructure evidence would flow into Engine A and Engine C, even though the full upstream assembler is not wired yet.
- Forbidden shortcut for this slice: do not wire calculators directly into engines, do not widen the public contracts, and do not claim the engines are already upstream-canonical when they still consume scalar additive seams.

## Placement

- Target files:
  - `src/engines/engine_a/engine_a_runner.py`
  - `src/engines/engine_c/engine_c_runner.py`
  - `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`
- Actual landing decision: add concise provenance comments on the existing input seam fields and add a test that verifies the expected fields exist while the engine runner surfaces remain free of direct microstructure-calculator imports.

## Files Changed

- `src/engines/engine_a/engine_a_runner.py`
- `src/engines/engine_c/engine_c_runner.py`
- `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`
- `docs/production_deployment_plan/update_audit/2026-04-19_microstructure_engine_input_provenance_seams.md`

## Claims Implemented

- Engine A now explicitly marks `ofi_flow_score`, `realized_kernel_vol_scale`, and `kyle_lambda_cost_uplift` as the canonical upstream microstructure provenance seam -> `src/engines/engine_a/engine_a_runner.py`
- Engine C now explicitly marks `cumulative_ofi`, `queue_pressure`, `vpin`, and `kyle_lambda` as the canonical upstream microstructure provenance seam -> `src/engines/engine_c/engine_c_runner.py`
- A targeted audit test now proves those seam fields exist on the current engine input contracts -> `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`
- A targeted audit test now proves the current Engine A/C runner-consumer surfaces do not import canonical microstructure calculators directly -> `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`

## Tests and Proof

- `python -m py_compile src/engines/engine_a/engine_a_runner.py src/engines/engine_c/engine_c_runner.py tests/test_data_backbone/microstructure/test_feature_provenance_seams.py` -> pass
- `rtk pytest -q tests/test_data_backbone/microstructure/test_feature_provenance_seams.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_c/test_engine_c.py` -> `26 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`
- `python scripts/run_dag_check.py` -> fails on pre-existing repo-global DAG/import-policy violations outside this slice

## Deferred / Not Done

- No upstream assembler yet from canonical microstructure calculators into Engine A or Engine C inputs
- No direct provenance objects or signed feature payload contracts yet
- No Engine B or Engine D provenance-seam audit in this slice
- No runtime proof yet that the scalar seam values originate from canonical calculator outputs

## Risks / Open Questions

- The engines remain on scalar additive seams; this patch improves auditability but does not by itself guarantee canonical-source provenance at runtime
- Repo-global DAG validation remains red outside this slice, so repository-wide proof closure is still blocked
- The next provenance slice will need to decide whether to add a shared assembler/helper contract or keep provenance closure at the test/audit level until Step 5 and Step 7

## Completion Status

`PARTIAL`

Reason:

`The current Engine A/C microstructure input seams are now explicit and test-audited, but the canonical upstream assembler is still deferred and repo-global DAG validation remains red outside this slice.`

## Next Safe Step

`Continue Step 3 by defining and auditing the upstream provenance path for Engine A OFI/Kyle/realized-kernel and Engine C OFI/queue/VPIN/Kyle inputs before moving into Engine A governance promotion or Engine C doctrinal deepening.`
