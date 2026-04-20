# Microstructure Registry Consumer Surface Truth

## Objective

Make the canonical microstructure registry more truthful and audit-ready by normalizing `consumed_by` entries to real source surfaces that exist in the current repo, and by adding a test that prevents future drift back toward non-resolvable fantasy consumer paths.

## Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md` Phase 2 canonical microstructure package discipline
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md` §4 feature registry contract and consumer-map doctrine
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` canonical microstructure registry as a governed landing seam
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` proof discipline
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md` audit-pack structure

## Current Code Seam

- Canonical file today: `src/data_backbone/microstructure/feature_registry.py`
- Why this seam is the right place: `consumed_by` is the only central consumer-map field for canonical microstructure features, so stale or non-resolvable entries here directly degrade audit truth.
- Forbidden shortcut for this slice: do not claim runtime-import proof for every consumer, do not invent new engine wiring, and do not rename features or formulas.

## Placement

- Target file: `src/data_backbone/microstructure/feature_registry.py`
- Doc target path: `src/data_backbone/microstructure/feature_registry.py`
- Actual landing decision: keep the registry contract unchanged, but replace stale conceptual consumer labels with dotted paths that resolve to real modules or packages under `src/`, then enforce that rule in tests.

## Files Changed

- `src/data_backbone/microstructure/feature_registry.py`
- `tests/test_data_backbone/microstructure/test_feature_registry.py`
- `docs/production_deployment_plan/update_audit/2026-04-19_microstructure_registry_consumer_surface_truth.md`

## Claims Implemented

- `consumed_by` entries now resolve to real source surfaces under `src/` rather than stale non-existent dotted paths -> `src/data_backbone/microstructure/feature_registry.py`
- Engine-facing consumer labels now use the real `engines.*` namespace rather than the stale pre-namespace shorthand -> `src/data_backbone/microstructure/feature_registry.py`
- Registry drift is now guarded by an explicit test that every `consumed_by` entry resolves to a real module or package path -> `tests/test_data_backbone/microstructure/test_feature_registry.py`

## Tests and Proof

- `python -m py_compile src/data_backbone/microstructure/feature_registry.py tests/test_data_backbone/microstructure/test_feature_registry.py` -> pass
- `rtk pytest -q tests/test_data_backbone/microstructure/test_feature_registry.py tests/test_data_backbone/microstructure/test_spread_dynamics.py tests/test_data_backbone/microstructure/test_no_1990s_ta_in_engine_inputs.py` -> `12 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`
- `python scripts/run_dag_check.py` -> fails on pre-existing repo-global DAG/import-policy violations outside this slice

## Deferred / Not Done

- No proof yet that every registry consumer imports or executes the canonical calculator directly at runtime
- No broader engine rewiring from scalar input seams toward canonical microstructure assemblers
- No feature-id or registry-contract redesign to distinguish `current_consumed_by` from doctrinal future targets

## Risks / Open Questions

- Some features still resolve only to broad package surfaces rather than narrow runtime modules because the finer downstream wiring does not exist yet in current code
- Repo-global DAG validation remains red outside this slice, so full proof closure is still blocked at repository scope
- A future Step 3 slice may need an explicit provenance audit that traces canonical-calculator outputs into engine inputs, not just registry surface truth

## Completion Status

`PARTIAL`

Reason:

`The registry consumer map is now truthful at the source-surface level and protected by tests, but this slice does not yet prove direct runtime usage of every canonical microstructure feature by every declared consumer, and repo-global DAG validation remains red outside scope.`

## Next Safe Step

`Continue Step 3 with a provenance audit that traces canonical microstructure outputs into current engine input seams, starting with Engine A OFI/Kyle/realized-kernel and Engine C OFI/queue/VPIN/Kyle fields.`
