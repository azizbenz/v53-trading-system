# Microstructure Spread Dynamics Path Alignment

## Objective

Close the remaining doc23 path drift in the canonical microstructure package by landing the missing `spread_dynamics.py` module as the doctrinal entry point for live quoted/effective/realized spread diagnostics, while reusing the already implemented `realized_effective_spread` calculator and avoiding any second calculator stack or formula rewrite.

## Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md` Phase 2 canonical microstructure package rollout
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md` §1 directory layout and §3.11 realized/effective spread formulas
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` microstructure package as `NEW_WORK_VALID`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` proof discipline
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md` audit-pack structure
- session doctrine: Step 3 must stay canonical, quant-first, and additive

## Current Code Seam

- Canonical file today: `src/data_backbone/microstructure/realized_effective_spread.py`
- Why this seam is the right place: the live spread formulas already existed and were tested, but doc23 still required a canonical `spread_dynamics.py` landing module.
- Forbidden shortcut for this slice: do not invent new spread formulas, do not rename the existing calculator away, and do not create a duplicate registry feature or second contract surface.

## Placement

- Target file: `src/data_backbone/microstructure/spread_dynamics.py`
- Doc target path: `src/data_backbone/microstructure/spread_dynamics.py`
- Actual landing decision: add a thin canonical wrapper over `realized_effective_spread.py`, export it from the package, and prove parity so the package reaches the doctrinal path without behavior drift.

## Files Changed

- `src/data_backbone/microstructure/spread_dynamics.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_spread_dynamics.py`
- `docs/production_deployment_plan/update_audit/2026-04-19_microstructure_spread_dynamics_path_alignment.md`

## Claims Implemented

- Doc23 canonical module path `src/data_backbone/microstructure/spread_dynamics.py` now exists -> `src/data_backbone/microstructure/spread_dynamics.py`
- The new module is a strict wrapper over the existing live spread implementation, not a second calculator stack -> `src/data_backbone/microstructure/spread_dynamics.py`
- The canonical microstructure package now exports spread-dynamics names directly -> `src/data_backbone/microstructure/__init__.py`
- The top-level `data_backbone` package now re-exports the spread-dynamics aliases for public-surface consistency -> `src/data_backbone/__init__.py`
- Parity between the doctrinal wrapper and the pre-existing implementation is explicitly tested -> `tests/test_data_backbone/microstructure/test_spread_dynamics.py`

## Tests and Proof

- `python -m py_compile src/data_backbone/microstructure/spread_dynamics.py src/data_backbone/microstructure/__init__.py tests/test_data_backbone/microstructure/test_spread_dynamics.py` -> pass
- `python -m py_compile src/data_backbone/microstructure/spread_dynamics.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_spread_dynamics.py` -> pass
- `rtk pytest -q tests/test_data_backbone/microstructure/test_spread_dynamics.py tests/test_data_backbone/microstructure/test_realized_effective_spread.py tests/test_data_backbone/microstructure/test_feature_registry.py` -> `12 passed`
- `rtk pytest -q tests/test_data_backbone/microstructure` -> `67 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`
- `python scripts/run_dag_check.py` -> fails on pre-existing repo-global DAG/import-policy violations outside this slice

## Deferred / Not Done

- No feature-registry id rename from `realized_effective_spread.live`; this slice only closes the canonical module-path drift
- No broader consumer audit to prove every downstream import uses the new doctrinal path
- No work on Step 4 historical linkage or any engine-deepening step

## Risks / Open Questions

- Repo-global DAG validation remains red on pre-existing cycles/import-policy issues unrelated to this patch, so the full proof set is not globally green
- The registry still uses the stable feature id `realized_effective_spread.live`; that preserves compatibility, but the naming split between feature id and doctrinal module path should stay documented to avoid confusion
- A future consumer audit may decide whether top-level `data_backbone` should also re-export the spread-dynamics aliases

## Completion Status

`PARTIAL`

Reason:

`The canonical spread_dynamics module path is now present and parity-proven with the existing live spread calculator, but repo-global DAG validation still fails outside this slice, so the overall proof set is not fully green.`

## Next Safe Step

`Continue Step 3 by auditing the remaining microstructure registry/consumer map and deciding whether any downstream consumer still needs path-alignment or provenance cleanup before moving to Step 4.`
