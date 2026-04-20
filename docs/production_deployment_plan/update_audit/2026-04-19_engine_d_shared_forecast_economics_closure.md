# Engine D Shared Forecast Economics Closure

## Objective

Close the remaining Step 2 shared forecast/economics seam on Engine D by replacing the legacy local heuristic forecast math with the shared `forecast_normalizer` and `break_even_filter` rails, while keeping the migration additive, keeping the canonical `SignalCandidate` unchanged, and avoiding any expansion into coordination or historical-linkage work.

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` shared forecast/economics target for additive migration
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` Engine D doctrinal target, including bounded forecast semantics
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` proof and honesty requirements
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md` audit-pack structure
- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md` promotion discipline and deferred threshold governance
- session doctrine: Step 2 must be closed before returning to deeper Engine D doctrine work

## Current Code Seam

- Canonical file today: `src/engines/engine_d/engine_d_runtime_support.py`
- Why this seam is the right place: the additive forecast candidate for Engine D is assembled here, and the legacy forecast/economics heuristics were localized here rather than in the canonical decision contract.
- Forbidden shortcut for this slice: do not rewrite Engine D runtime, do not widen public contracts, do not touch coordination/history rails, and do not turn `break_even_filter` into a second hard gate.

## Placement

- Target file: `src/engines/engine_d/engine_d_runtime_support.py`
- Doc target path: shared seams under `src/scoring_backbone/forecast_normalizer.py` and `src/scoring_backbone/break_even_filter.py`
- Actual landing decision: keep Engine D runtime support as the adapter seam, add a local `_EngineDForecastEconomics` helper, and consume the shared normalizer/filter there so the migration stays additive and reviewable.

## Files Changed

- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
- `docs/production_deployment_plan/update_audit/2026-04-19_engine_d_shared_forecast_economics_closure.md`

## Claims Implemented

- Engine D forecast strength now comes from the shared normalizer rather than `penalized_score * 20.0` -> `src/engines/engine_d/engine_d_runtime_support.py`
- Engine D expected break-even now comes from the shared break-even filter rather than `expected_cost + delta_safe` -> `src/engines/engine_d/engine_d_runtime_support.py`
- Engine D forecast candidate now carries additive economics truth in conditioning state and reason codes, including volatility proxy provenance and break-even branch -> `src/engines/engine_d/engine_d_runtime_support.py`
- Engine D forecast clip now converges to the doctrinal `[0, 10]` bound with explicit clipping evidence -> `src/engines/engine_d/engine_d_runtime_support.py`, `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
- Canonical `SignalCandidate`, invalidation reference, and coordination/history behavior remain unchanged in this slice -> `src/engines/engine_d/engine_d_runtime_support.py`

## Tests and Proof

- `python -m py_compile src/engines/engine_d/engine_d_runtime_support.py tests/test_engines/test_engine_d/test_engine_d_runtime.py` -> pass
- `rtk pytest -q tests/test_engines/test_engine_d/test_engine_d_runtime.py` -> `30 passed`
- `rtk pytest -q tests/test_engines/test_engine_d` -> `90 passed`
- `rtk pytest -q tests/test_scoring_backbone/test_forecast_normalizer.py tests/test_scoring_backbone/test_break_even_filter.py` -> `13 passed`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`
- `python scripts/run_dag_check.py` -> fails on pre-existing repo-global DAG/import violations outside this slice (`execution_backbone <-> venue_adapters` cycle and existing engine import policy failures)
- Additional proof:
  - `src/engines/engine_d/engine_d_runtime_support.py` line count reduced/held to `700`
  - accepted-path forecast test proves `strategy_id` preservation, normalized bounded forecast strength, shared break-even output, economics reason codes, and non-regression of `invalidation_ref`
  - fallback-path forecast test proves `delta_safe` volatility proxy fallback and explicit forecast clipping evidence

## Deferred / Not Done

- No Step 4 historical-linkage helpers: `first_episode_resolver_d.py`, `historical_linkage_guard_d.py`, `consecutive_stop_counter_d.py`
- No threshold governance migration for `THR-X10`, `THR-X11`, or other Engine D signed calibration seams
- No redesign of Engine D score truth surfaces beyond the shared forecast/economics adapter
- No coordination/runtime policy changes in this slice

## Risks / Open Questions

- Repo-level DAG validation is still red on pre-existing cycles/import-policy issues; this blocks a full `COMPLETE` status even though the slice-local proofs are green.
- Engine D forecast now uses the doctrinal `[0, 10]` bound, but deeper D doctrinal work still remains on historical dependence and threshold governance.
- The volatility proxy is intentionally transitional and honest: `atr / entry_price` when available, `delta_safe` fallback otherwise. This is sufficient for the shared seam closure, but not the end-state of all Engine D doctrine.

## Completion Status

`PARTIAL`

Reason:

`The Engine D shared forecast/economics slice landed as planned and all targeted tests plus guardrails passed, but repo-level DAG validation still fails on pre-existing violations outside this slice, so the overall proof set is not fully green.`

## Next Safe Step

`Move to Step 3 and audit whether spread_dynamics and the remaining microstructure registry/consumer obligations are quant-proof-ready before adding any new engine-local doctrine.`
