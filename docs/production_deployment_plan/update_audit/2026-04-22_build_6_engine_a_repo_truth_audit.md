# Build 6 Repo-Truth Audit - Engine A - 2026-04-22

## Scope

This note audits **Build 6** only:

- `engines.engine_a.engine_a_runner`
- `engines.engine_a.engine_a_runtime`
- current Engine A runtime-support and scoring-candidate seams
- current Engine A standalone signal-candidate adapter surface

It answers one question:

> Does current Build-6 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Engine A and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 6:

- Build 6 is canonical **Engine A**.
- Build-order identity is:
  - `Premium Trend / Expansion`
- It must remain one of the four canonical engines.
- It must produce a governed directional signal on its own doctrine.
- Later doctrine layers also expect Engine A to participate in:
  - scoring/ranking
  - risk-runtime gating
  - forecast candidate projection

## Repo-Truth Surface

### 1. Build 6 is not only a runner; it already has a full runner + runtime rail

Observed in:
- `src/engines/engine_a/engine_a_runner.py`
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/__init__.py`

Current repo-truth Build-6 surface includes:
- canonical `run_engine_a(...)`
- typed `EngineAInput`, `EngineAOutput`, `EngineADecision`
- canonical `EngineARuntime`
- typed `EngineARuntimeInput`, `EngineARuntimeResult`, `EngineARuntimeStatus`
- typed pre-entry validation hook seam

Interpretation:
- Engine A is not just a pure signal runner anymore
- it already has a real runtime rail that closes Build 6 against Build 5 and Build 4

### 2. The runner is real, typed, and materially broader than a simple trend score

Observed in:
- `src/engines/engine_a/engine_a_runner.py`
- `src/engines/engine_a/context_validator_a.py`
- `src/engines/engine_a/conviction_builder_a.py`
- `src/engines/engine_a/cost_feasibility_a.py`
- `src/engines/engine_a/invalidation_mapper_a.py`
- `src/engines/engine_a/structure_detector_a.py`

Current repo-truth runner includes:
- structure stage
- context stage
- cost stage
- conviction stage
- invalidation stage
- structured no-trade exits with stable reason codes
- canonical realized-vol and delta-confirmation seams from shared data/physics inputs

Interpretation:
- current Engine A is materially richer than a minimal premium-trend runner story
- Build 6 already consumes governed upstream seams rather than recomputing them ad hoc

### 3. The runtime closes the canonical Build-6 hot path through scoring and risk

Observed in:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_a/engine_a_scoring_candidate_builder.py`

Current repo-truth runtime includes:
- circuit-breaker gating before scoring
- `ScoringRuntime.run_round(...)`
- typed `scoring_audit` resolution
- ranking and portfolio rejection handling
- `RiskRuntime.evaluate_candidate(...)`
- risk-rejected / reduced / observe-only runtime statuses
- refusal-record generation

Interpretation:
- Build 6 is already a true runner+runtime engine rail
- it does not bypass Build 5 or Build 4
- it also does not bypass Build 3, which remains intentionally outside Engine A

### 4. Forecast and signal-candidate projection now exist on two seams

Observed in:
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_a/signal_candidate_adapter.py`

Current repo-truth includes:
- private runtime forecast construction used inside the runtime rail
- public standalone `build_signal_candidate_a(...)` adapter module

Interpretation:
- the standalone adapter is real and green
- but it is additive
- the canonical runtime rail still flows through `EngineARuntime` and its support helpers

## Verification Evidence

### Full Engine-A audit bundle

Command:

```powershell
python -m pytest tests/test_engines/test_engine_a -q --tb=short
```

Result:
- `51 passed`

Interpretation:
- current Engine A runner, runtime, downstream seams, and standalone adapter are green on the audited bundle

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-6 code surface

The simplified doctrinal story often compresses Build 6 to:
- Engine A runner
- trend / expansion signal

Current repo-truth is broader:
- canonical runner
- canonical runtime
- scoring integration
- risk integration
- pre-entry validation hook
- refusal-record generation
- forecast / signal-candidate projection

Interpretation:
- this is not dangerous code drift
- it is a documentation compression drift

### Divergence 2 - later doctrinal layers have already landed additively inside Engine A

Observed in current code:
- scoring and risk are already first-class Engine-A runtime dependencies
- forecast candidate construction is already part of runtime behavior
- standalone adapter exists as a public additive surface

Interpretation:
- later doctrine is not merely planned for Engine A
- a meaningful part of it has already landed in current repo-truth

### Divergence 3 - the standalone adapter is real, but it is not the canonical runtime rail

Observed in:
- `src/engines/engine_a/signal_candidate_adapter.py`
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`

Current repo-truth:
- `EngineARuntime` remains the main Build-6 rail
- the standalone adapter is a public additive projection module

Interpretation:
- this is not a conflict
- but a markdown or backlog that talks only about adapters or only about the runner is incomplete for current Engine-A code-truth

## Decision

`PARTIAL`

## Why

Build 6 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- real `run_engine_a(...)`
- typed Engine A inputs / outputs / decisions
- real `EngineARuntime`
- scoring / ranking / portfolio integration
- risk-runtime integration
- forecast/signal-candidate projection seams
- standalone public adapter surface

So Build 6 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-6 surface now is
2. later doctrinal runtime/scoring/risk layers have already landed materially in code
3. the adapter surface is real but additive, while the canonical Build-6 rail remains the runner+runtime path

So the correct ruling is:
- Build 6 is operationally real and healthy
- but the doctrinal narrative is narrower than the current repo-truth implementation

## Patch Target

`docs only`
