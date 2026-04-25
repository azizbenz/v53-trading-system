# Build 6 Repo-Truth Closure - Engine A - 2026-04-25

## Scope

This closure note resolves **Build 6** only:

- `src/engines/engine_a/`
- the current Engine-A runner + runtime hot path
- the repo-truth gap identified in
  [2026-04-22_build_6_engine_a_repo_truth_audit.md](./2026-04-22_build_6_engine_a_repo_truth_audit.md)

The purpose of this closure is narrow:

> confirm whether the remaining Build-6 gap is still documentary only, or whether
> new code drift was found on the current branch.

## Governing Inputs

Primary sources used for closure:

- `src/engines/engine_a/`
- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/update_audit/2026-04-22_build_6_engine_a_repo_truth_audit.md`

## Closure Reading

The 2026-04-22 audit conclusion remains correct on the current branch:

- Build 6 is a **real, typed, green** Engine-A rail
- the current surface is broader than the compressed markdown story
- the remaining mismatch is still **docs/repo-truth narration**, not a newly
  observed Build-6 logic defect

Current repo-truth Build 6 already includes:

- canonical `run_engine_a(...)`
- typed `EngineAInput`, `EngineAOutput`, `EngineADecision`
- canonical `EngineARuntime`
- typed `EngineARuntimeInput`, `EngineARuntimeResult`, `EngineARuntimeStatus`
- structure / context / cost / conviction / invalidation runner stages
- stable no-trade reason-code semantics
- pre-entry validation hook seam
- `ScoringRuntime.run_round(...)` integration
- ranking / portfolio rejection handling
- `RiskRuntime.evaluate_candidate(...)` integration
- refusal-record generation
- runtime forecast construction
- public additive `build_signal_candidate_a(...)` adapter

The current repo-truth Build-6 interpretation is therefore:

- Engine A is not merely a trend runner
- Engine A is not merely a standalone signal adapter
- Engine A is already a full runner + runtime rail
- the standalone adapter is real, but it remains additive rather than canonical

That additive adapter seam does **not** block closure of the current Build-6
implemented surface.

## Verification Evidence

### Full Engine-A closure bundle

Command:

```powershell
python -m pytest tests/test_engines/test_engine_a -q --tb=short --basetemp=tmp_pytest_build6_closure
```

Result:

- `51 passed`

Interpretation:

- current Engine A runner, runtime, downstream seams, and standalone adapter are
  green on the closure replay bundle
- no Build-6 doctrine/code regression was observed

## Decision

`Build 6 = COMPLETE`

## Why

Build 6 is no longer honestly `PARTIAL` on the current repo-truth reading.

The prior gap was:

- markdown underdescribing the current Build-6 breadth
- later runtime/scoring/risk doctrine already landed additively in code
- adapter-oriented readings being too narrow for the canonical runner+runtime
  rail

That gap is now closed by explicit repo-truth clarification.

No new code gap was found.
No Engine-A redesign is justified.
No missing baseline Engine-A runtime rail was found.

So the correct closure reading is:

- current Build 6 code is real and governed
- the proof bundle is green
- the remaining difference was documentary only

## Final Verdict

Safe closure classification:

- `Build 6 = COMPLETE (real typed Engine-A runner + runtime rail, scoring and risk integration, refusal-record generation, and additive forecast/signal-candidate seams are present and proven; the standalone adapter is real but remains additive rather than the canonical Build-6 path)`
