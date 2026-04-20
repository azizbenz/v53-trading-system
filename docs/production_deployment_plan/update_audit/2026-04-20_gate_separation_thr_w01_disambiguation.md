# Gate Separation And THR-W01 Disambiguation Across A/B/C/D

## Objective

Remove the semantic collision between risk/runtime `THR-W01` and economics `EV^net` floor language, make `THR-W01` risk-only in code and active doctrine docs, introduce `THR-E05` as the shared economics `EV^net` floor seam, and harden A/B/C/D runner/runtime refusal provenance so Gate 0, Gate 1, Gate 2, and Gate 3 failures are explicitly distinguishable without changing engine math.

## Docs Governants

- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md` threshold and `break_even_filter` sections
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` cost / break-even / EV-net and threshold table
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` Stage 5 economics gate and continuation refusal semantics
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` Stage 4/5 gating semantics and threshold table
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` engine seam landing discipline
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` R-QUANT-FIRST and no-silent-semantic-drift doctrine

## Current Code Seam

- Canonical risk threshold seam today: `src/risk_backbone/risk_runtime_drawdown_calibration.py`
- Canonical economics threshold seam added in this slice: `src/scoring_backbone/ev_net_floor_thresholds.py`
- Canonical runner/runtime provenance seams: `src/engines/engine_a/engine_a_runner*.py`, `src/engines/engine_b/engine_b_runner*.py`, `src/engines/engine_c/engine_c_runner*.py`, `src/engines/engine_d/engine_d_runner*.py`
- Why this seam is the right place: the threshold collision and gate provenance problem lives at the point where threshold ownership meets refusal/reason-code emission; the runner/runtime support seams are the additive place to make the split explicit without rewriting engine math
- Forbidden shortcut for this slice: do not relabel `marginal_value_score` as `marginal_EV`, do not overload `THR-W01`, and do not create a parallel orchestration or scoring stack

## Placement

- Target files:
  - `src/scoring_backbone/ev_net_floor_thresholds.py`
  - `src/engines/engine_a/engine_a_runner_support.py`
  - `src/engines/engine_b/engine_b_runner_support.py`
  - `src/engines/engine_c/engine_c_runner_support.py`
  - `src/engines/engine_d/marginal_value_estimator_d.py`
  - `src/engines/engine_d/engine_d_runner_support.py`
- Doc target path: docs 19/20/21/22 for economics references, docs 11/13 for risk-runtime threshold ownership
- Actual landing decision: `THR-E05` was added as the shared economics threshold ID in `scoring_backbone`; docs 19/20/21/22 were updated to use it; docs 11/13 keep `THR-W01` risk-only; Engine D stayed Model A with a local setup-quality threshold ID `THR-D_MARGINAL_VALUE_SCORE_MIN`

## Files Changed

- `docs/production_deployment_plan/11_DYNAMIC_THRESHOLDS_CATALOG.md`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `src/scoring_backbone/ev_net_floor_thresholds.py`
- `src/scoring_backbone/__init__.py`
- `src/engines/engine_a/engine_a_runner_support.py`
- `src/engines/engine_a/engine_a_runner.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runner_support.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_forecast_support.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_d/marginal_value_estimator_d.py`
- `src/engines/engine_d/__init__.py`
- `src/engines/engine_d/engine_d_runner_support.py`
- `src/engines/engine_d/engine_d_runner.py`
- `src/engines/engine_d/engine_d_runtime_support_refusal.py`
- `tests/test_scoring_backbone/test_ev_net_floor_thresholds.py`
- `tests/test_scoring_backbone/test_threshold_semantic_disambiguation.py`
- `tests/test_engines/test_engine_a/test_engine_a.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py`
- `tests/test_engines/test_engine_b/test_engine_b.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`
- `tests/test_engines/test_engine_d/test_engine_d.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
- `tests/test_engines/test_engine_d/test_marginal_value_estimator_d.py`

## Claims Implemented

- `THR-W01` remains reserved for risk/runtime drawdown-warning semantics and is no longer used as the economics `EV^net` floor ID -> `src/risk_backbone/risk_runtime_drawdown_calibration.py`, `src/scoring_backbone/ev_net_floor_thresholds.py`, `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`, `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`, `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`, `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- Shared economics threshold ownership now uses `THR-E05` with a signed-threshold resolver and `break_even_filter`-compatible updates -> `src/scoring_backbone/ev_net_floor_thresholds.py`
- Engine gate provenance is explicit in runner/runtime reason-code families:
  - A Gate 0 hard blocks, Gate 1 structure/context, Gate 2 economics, Gate 3 scoring/portfolio/runtime -> `src/engines/engine_a/engine_a_runner_support.py`, `src/engines/engine_a/engine_a_runner.py`, `src/engines/engine_a/engine_a_runtime_support.py`
  - B Gate 1 excess/fade/anti-breakout stays separate from Gate 2 economics -> `src/engines/engine_b/engine_b_runner_support.py`, `src/engines/engine_b/engine_b_runner.py`, `src/engines/engine_b/engine_b_runtime.py`, `src/engines/engine_b/engine_b_runtime_forecast_support.py`
  - C Gate 0 coordination, Gate 1 continuation validity, Gate 2 economics, Gate 3 scoring/portfolio/runtime are now emitted through distinct reason families -> `src/engines/engine_c/engine_c_runner_support.py`, `src/engines/engine_c/engine_c_runner.py`, `src/engines/engine_c/engine_c_runtime_support.py`, `src/engines/engine_c/engine_c_runtime_forecast_support.py`
  - D stays Model A: Gate 1 local history/reformation/marginal-value setup quality, Gate 2 economics; `marginal_value_score` is not relabeled as `marginal_EV` -> `src/engines/engine_d/marginal_value_estimator_d.py`, `src/engines/engine_d/engine_d_runner_support.py`, `src/engines/engine_d/engine_d_runner.py`, `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- Threshold-collision regression tests now prove `THR-W01` risk-only, `THR-E05` economics-only, and D Model A local threshold ownership -> `tests/test_scoring_backbone/test_threshold_semantic_disambiguation.py`

## Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile src/scoring_backbone/ev_net_floor_thresholds.py src/scoring_backbone/__init__.py src/engines/engine_a/engine_a_runner_support.py src/engines/engine_a/engine_a_runner.py src/engines/engine_a/engine_a_runtime_support.py src/engines/engine_b/engine_b_runner_support.py src/engines/engine_b/engine_b_runner.py src/engines/engine_b/engine_b_runtime.py src/engines/engine_b/engine_b_runtime_forecast_support.py src/engines/engine_c/engine_c_runner_support.py src/engines/engine_c/engine_c_runner.py src/engines/engine_c/engine_c_runtime_support.py src/engines/engine_c/engine_c_runtime_forecast_support.py src/engines/engine_d/marginal_value_estimator_d.py src/engines/engine_d/__init__.py src/engines/engine_d/engine_d_runner_support.py src/engines/engine_d/engine_d_runner.py src/engines/engine_d/engine_d_runtime_support_refusal.py tests/test_scoring_backbone/test_ev_net_floor_thresholds.py tests/test_scoring_backbone/test_threshold_semantic_disambiguation.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_marginal_value_estimator_d.py` -> `pass`
- `python -m pytest -q tests/test_scoring_backbone/test_ev_net_floor_thresholds.py tests/test_scoring_backbone/test_threshold_semantic_disambiguation.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_b/test_engine_b.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_d/test_engine_d.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_marginal_value_estimator_d.py --basetemp=.test_tmp/pytest` -> `226 passed`
- `python -m pytest -q tests/test_engines/test_engine_b tests/test_engines/test_engine_c tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest` -> `367 passed`
- `python -m pytest -q tests/test_interface_contracts --basetemp=.test_tmp/pytest` -> `184 passed`
- `python -m pytest -q tests/test_engines/test_engine_a tests/test_engines/test_engine_b tests/test_engines/test_engine_c tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest` -> `blocked by pre-existing ImportError from tests/test_engines/test_engine_a/test_engine_a_runtime.py (the file is truncated to one line in the current worktree)`
- `python -m pytest -q tests/test_protocols tests/test_interface_contracts --basetemp=.test_tmp/pytest` -> `114 failed, 512 passed, 6 errors`; failures are dominated by pre-existing `PermissionError` writes into `build/` and `.test_tmp/pytest`, outside the files touched by this slice
- `python scripts/run_engineering_guardrails.py` -> `new_violations=4`; remaining new violations are outside this slice in the dirty worktree, first at `src/engines/engine_a/engine_a_runtime.py`
- `python -m dag_validator` -> `No module named dag_validator`
- `python scripts/run_dag_check.py` -> unchanged repo-global baseline fail with `9` violations (cycle `execution_backbone -> venue_adapters -> execution_backbone` and pre-existing unauthorized imports)
- `rg -n "THR-W01|THR-E05" docs src tests` -> verified `THR-W01` live code usage is risk-runtime only and `THR-E05` is the economics threshold seam; remaining `THR-W01` references in docs 19/20/21/22 are explanatory “risk-only / not reused” text, not economics ownership

## Deferred / Not Done

- No engine math migration to a new economics object was performed; this slice only clarified threshold ownership and gate provenance
- Engine D remains Model A; a true `marginal_EV` gate and threshold are explicitly deferred
- The broad Engine A test directory cannot be declared green until the pre-existing truncated `tests/test_engines/test_engine_a/test_engine_a_runtime.py` file is repaired
- The broad protocols suite remains blocked by existing `PermissionError` writes into repo-local `build/` and `.test_tmp/pytest`

## Risks / Open Questions

- `src/engines/engine_a/engine_a_runtime.py` is already modified in the dirty worktree and still trips guardrails (`FILE_TOO_LONG`); this slice did not change that file
- Historical update-audit docs still mention the old `THR-W01` ambiguity; they were not rewritten as part of this active-doctrine slice
- Because some engine/runtime tests outside the touched slice are already broken in the working tree, the repo-wide proof surface is not fully clean even though the slice-local proof is green

## Completion Status

`PARTIAL`

Reason:

`The THR-W01/THR-E05 collision and gate-family provenance are resolved in active code/docs and slice-local tests, but broader repo proof remains blocked by pre-existing A-test truncation, protocol permission failures, and unrelated dirty-tree guardrail violations.`

## Next Safe Step

`Repair the pre-existing tests/test_engines/test_engine_a/test_engine_a_runtime.py truncation and the build-directory permission failures in protocol tests, then re-run the full engine/protocol proof set to close this governance slice cleanly.`
