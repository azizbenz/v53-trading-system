## 1. Objective

Remove ATR as a central engine primitive from the targeted V5.3 migration slice and replace it with the governed realized-vol / realized-vol-at-break path for Engines C, A, and D.

## 2. Docs Governants

- `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## 3. Current Code Seam

Before this slice, central ATR usage was present in:

- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
  - `CENTRAL_ENGINE_PRIMITIVE`
  - runtime forecast volatility proxy
- `src/engines/engine_c/invalidation_mapper_c.py`
  - `TRANSITIONAL_ENGINE_SEAM`
  - invalidation explicitly marked `TRANSITIONAL_ATR_PROXY`
- `src/engines/engine_c/structure_resolver_c.py`
  - `CENTRAL_ENGINE_PRIMITIVE`
  - structure fallback width logic
- `src/engines/engine_a/engine_a_runtime_support.py`
  - `CENTRAL_ENGINE_PRIMITIVE`
  - runtime forecast volatility proxy
- `src/engines/engine_a/invalidation_mapper_a.py`
  - `CENTRAL_ENGINE_PRIMITIVE`
  - invalidation price rule anchor
- `src/engines/engine_d/engine_d_runtime_support.py`
  - `CENTRAL_ENGINE_PRIMITIVE`
  - runtime forecast volatility proxy
- `src/engines/engine_d/invalidation_mapper_d.py`
  - `CENTRAL_ENGINE_PRIMITIVE`
  - invalidation stop/target anchor

Residual ATR matches after migration are now limited to:

- `src/engines/engine_a/engine_a_runner.py`
  - `LEGACY_CONTEXT_OVERLAY`
  - retained input field and negative-input rejection only
- `src/engines/engine_c/engine_c_runner.py`
  - `LEGACY_CONTEXT_OVERLAY`
  - retained input field only
- `src/engines/engine_c/engine_c_runner_support.py`
  - `LEGACY_CONTEXT_OVERLAY`
  - retained negative-input rejection only
- `src/engines/engine_d/engine_d_models.py`
  - `LEGACY_CONTEXT_OVERLAY`
  - retained input field only
- `src/engines/engine_d/engine_d_runner.py`
  - `LEGACY_CONTEXT_OVERLAY`
  - retained negative-input rejection only
- `src/engines/engine_a/signal_reporter_a.py`
  - `NON_ENGINE_DIAGNOSTIC`
  - enum label only

Follow-up Step 6 / 7 re-inventory confirmed no additional central ATR usage remains under `src/engines/engine_d/`. Residual code-level `atr` tokens under `src/engines/engine_a/`, `src/engines/engine_c/`, and `src/engines/engine_d/` are restricted to:

- `src/engines/engine_a/engine_a_runner.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_d/engine_d_models.py`
- `src/engines/engine_d/engine_d_runner.py`

No central A/C/D forecast, invalidation, or structure file contains `atr` after this slice.

## 4. Placement

The shared canonical realized-vol source remains `src/data_backbone/microstructure/realized_kernel_vol.py`. This slice extends the existing shared engine-facing provenance seam in `src/data_backbone/microstructure/engine_input_provenance.py` rather than burying realized-vol assembly in engine-local helpers.

Central migration order applied:

1. shared realized-vol seam confirmation and extension
2. Engine C migration
3. Engine A migration
4. Engine D migration
5. doctrine CI hardening

## 5. Files Changed

Shared:

- `src/data_backbone/microstructure/engine_input_provenance.py`
- `src/data_backbone/microstructure/feature_registry.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_engine_input_provenance.py`
- `tests/test_data_backbone/microstructure/test_feature_provenance_seams.py`
- `tests/test_data_backbone/microstructure/test_no_central_atr_in_engine_paths.py`

Engine C:

- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_c/invalidation_mapper_c.py`
- `src/engines/engine_c/structure_resolver_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py`
- `tests/test_engines/test_engine_c/test_invalidation_mapper_c.py`
- `tests/test_engines/test_engine_c/test_structure_resolver_c.py`

Engine A:

- `src/engines/engine_a/engine_a_runner.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_a/invalidation_mapper_a.py`
- `tests/test_engines/test_engine_a/test_engine_a.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_a/test_engine_a_integration.py`
- `tests/test_engines/test_engine_a/test_invalidation_mapper_a.py`

Engine D:

- `src/engines/engine_d/engine_d_models.py`
- `src/engines/engine_d/engine_d_runner.py`
- `src/engines/engine_d/engine_d_runner_support.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `src/engines/engine_d/invalidation_mapper_d.py`
- `tests/test_engines/test_engine_d/test_context_resolver_d.py`
- `tests/test_engines/test_engine_d/test_coordination_input_assembler_d.py`
- `tests/test_engines/test_engine_d/test_engine_d.py`
- `tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime_bs_next_regression.py`
- `tests/test_engines/test_engine_d/test_invalidation_mapper_d.py`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`

## 6. Claims Implemented

- Shared realized-vol engine-facing provenance now carries:
  - `realized_vol_current`
  - `realized_vol_at_break`
  - `realized_vol_post_close`
- Engine C forecast now uses governed realized-vol proxies instead of `atr / entry_price`.
- Engine C invalidation no longer uses ATR as the central stop anchor primitive; it now prefers `realized_vol_at_break`, then `realized_vol_current`, then an explicit floor fallback.
- Engine C structure fallback width no longer uses ATR centrally; it now uses governed realized-vol input.
- Engine A forecast now uses `realized_vol_current` first, then existing realized-kernel scale, then explicit `delta_safe` fallback.
- Engine A invalidation no longer uses ATR. When realized-vol is missing, the fallback is explicit: time-only invalidation with no price rule.
- Engine D forecast now uses `realized_vol_post_close`, then `realized_vol_current`, then explicit `delta_safe` fallback.
- Engine D invalidation no longer uses ATR centrally; it now prefers post-close/current realized-vol with explicit floor fallback.
- CI now fails if ATR is reintroduced into the central migrated A/C/D runtime forecast, invalidation, or structure files.
- Step 7 doctrine CI is hardened further: code-level `atr` tokens anywhere under `src/engines/engine_a`, `src/engines/engine_c`, or `src/engines/engine_d` are now restricted to one explicit overlay allowlist, while comments and strings remain ignored to avoid noisy false positives.

## 7. Tests and Proof

Syntax/import sanity:

- `python -m py_compile ...` on all touched shared, A, C, D files and tests: pass
- post-guardrail fix:
  - `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/engines/engine_d/engine_d_runtime_support.py`: pass

Shared tests:

- `rtk pytest -q tests/test_data_backbone/microstructure/test_engine_input_provenance.py tests/test_data_backbone/microstructure/test_feature_provenance_seams.py tests/test_data_backbone/microstructure/test_no_central_atr_in_engine_paths.py --basetemp=.test_tmp/pytest`
  - pass
- `rtk pytest -q tests/test_data_backbone/microstructure tests/test_interface_contracts --basetemp=.test_tmp/pytest`
  - `273 passed`
- `rtk pytest -q tests/test_scoring_backbone -k "not fee_aware_edge_gate" --basetemp=.test_tmp/pytest`
  - `164 passed`

Engine tests:

- focused migrated slice:
  - `rtk pytest -q ...`
  - `190 passed`
- package suites:
  - `rtk pytest -q tests/test_engines/test_engine_c tests/test_engines/test_engine_a tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
  - `259 passed`
- post-file-length fix sanity:
  - `rtk pytest -q tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_data_backbone/microstructure/test_no_central_atr_in_engine_paths.py --basetemp=.test_tmp/pytest`
  - `35 passed`

Doctrine CI:

- `rtk pytest -q tests/test_data_backbone/microstructure/test_no_1990s_ta_in_engine_inputs.py tests/test_data_backbone/microstructure/test_no_central_atr_in_engine_paths.py --basetemp=.test_tmp/pytest`
  - `6 passed`
- follow-up Step 6 / 7 hardening:
  - `rtk pytest -q tests/test_data_backbone/microstructure/test_no_central_atr_in_engine_paths.py --basetemp=.test_tmp/pytest`
  - pass

Guardrails:

- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

DAG:

- `python -m dag_validator`
  - blocked: module not installed in this environment
- `python scripts/run_dag_check.py`
  - fails on pre-existing repo-global baseline:
    - `execution_backbone -> venue_adapters -> execution_backbone` cycle
    - pre-existing unauthorized imports in `engine_a`, `engine_b`, `engine_c`, `engine_d`, `execution_backbone`

## 8. Deferred / Not Done

- No broader production caller outside current engine seams is yet shown to assemble and persist the new realized-vol inputs end-to-end.
- Engine D now has one truthful adopted caller seam for realized-vol input assembly.
- Engine C still has no truthful `src/` caller beyond local declarations and shared compose helpers.
- Engine A still has no truthful `src/` caller beyond local declarations and shared provenance helpers.
- Engine C and D still retain explicit transitional floor fallbacks when realized-vol inputs are absent.
- Engine A still retains ATR as a legacy input field and negative-input validation seam, not as a central primitive.
- Engine C and D still retain ATR as legacy input fields / validation seams, not as central primitives.
- Full `tests/test_scoring_backbone/` could not be claimed fully green because `tests/test_scoring_backbone/test_fee_aware_edge_gate.py` hits a pre-existing Windows ACL failure under `build/pytest-fee-aware-edge-gate/`.

## 9. Risks / Open Questions

- Upstream realized-vol population remains the real operational dependency. This slice removes central ATR usage from targeted engine files, but shadow/live completeness still depends on real callers providing governed realized-vol fields.
- Engine A / Engine C cannot be pushed further on upstream adoption without creating new orchestration, which would violate the current no-synthetic-caller constraint.
- The explicit floor fallbacks in Engine C and Engine D are honest transitional seams, not doctrinal end-state closure.
- The repo-local DAG baseline is still red outside this slice, so architectural proof remains partial at repository scope.

## 10. Completion Status

PARTIAL

Central ATR usage has been removed from the targeted migrated A/C/D engine forecast, invalidation, and structure paths, and doctrine CI now guards against regression. Status remains partial because realized-vol upstream adoption is only truly adopted for D so far, A/C still lack a truthful caller surface, explicit transitional fallbacks remain in C/D, and repo-global proof remains blocked outside this slice.

## 11. Next Safe Step

Create or adopt the first truthful upstream caller surface that populates governed realized-vol fields for A/C/D end-to-end, then remove or tighten the remaining explicit floor fallbacks in Engine C and Engine D.
