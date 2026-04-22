# Build 7 Repo-Truth Audit - Engine B - 2026-04-22

## Scope

This note audits **Build 7** only:

- `engines.engine_b.engine_b_runner`
- `engines.engine_b.engine_b_runtime`
- current Engine B runtime-support and forecast-support seams
- current Engine B standalone signal-candidate adapter surface
- the already-proven Build-9 smoke alignment around Engine B

It answers one question:

> Does current Build-7 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Engine B and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 7:

- Build 7 is canonical **Engine B**.
- Build-order identity is:
  - `Mean Reversion Intraday`
- It must remain one of the four canonical engines.
- It must produce a governed intraday mean-reversion signal on its own doctrine.
- Later doctrine layers also expect Engine B to participate in:
  - scoring/ranking
  - risk-runtime gating
  - forecast candidate projection

## Repo-Truth Surface

### 1. Build 7 is not only a runner; it already has a full runner + runtime rail

Observed in:
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/__init__.py`

Current repo-truth Build-7 surface includes:
- canonical `run_engine_b(...)`
- typed `EngineBInput`, `EngineBOutput`, `EngineBDecision`
- canonical `EngineBRuntime`
- typed `EngineBRuntimeInput`, `EngineBRuntimeResult`, `EngineBRuntimeStatus`
- typed sweep-validation hook seam

Interpretation:
- Engine B is not just a pure signal runner anymore
- it already has a real runtime rail that closes Build 7 against Build 5 and Build 4

### 2. The runner is real, typed, and materially broader than a simple z-score mean-reversion check

Observed in:
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_b/local_mean_estimator_b.py`
- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/anti_breakout_filter_b.py`
- `src/engines/engine_b/cost_feasibility_b.py`
- `src/engines/engine_b/conviction_builder_b.py`
- `src/engines/engine_b/invalidation_mapper_b.py`

Current repo-truth runner includes:
- local-mean / z-score stage
- excess stage
- anti-breakout stage
- cost stage
- conviction stage
- invalidation stage
- structured no-trade exits with stable reason codes
- upstream microstructure / market-physics / toxic-flow seams already represented in the input contract

Interpretation:
- current Engine B is materially richer than a minimal `price below mean -> emit` story
- Build 7 already consumes governed upstream seams rather than recomputing them ad hoc

### 3. The runtime closes the canonical Build-7 hot path through scoring and risk

Observed in:
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`

Current repo-truth runtime includes:
- circuit-breaker gating before scoring
- optional sweep-validation hook before scoring
- `ScoringRuntime.run_round(...)`
- typed `scoring_audit` resolution
- ranking and portfolio rejection handling
- `RiskRuntime.evaluate_candidate(...)`
- risk-rejected / reduced / observe-only runtime statuses
- refusal-record generation

Interpretation:
- Build 7 is already a true runner+runtime engine rail
- it does not bypass Build 5 or Build 4
- it also does not bypass Build 3, which remains intentionally outside Engine B

### 4. Forecast and signal-candidate projection now exist on two seams

Observed in:
- `src/engines/engine_b/engine_b_runtime_forecast_support.py`
- `src/engines/engine_b/signal_candidate_adapter.py`

Current repo-truth includes:
- private runtime forecast construction and downstream annotation
- public standalone `build_signal_candidate_b(...)` adapter module

Interpretation:
- the standalone adapter is real and green
- but it is additive
- the canonical runtime rail still flows through `EngineBRuntime` and its runtime forecast support helpers

## Verification Evidence

### Full Engine-B audit bundle

Command:

```powershell
python -m pytest tests/test_engines/test_engine_b -q --tb=short
```

Result:
- `153 passed`

Interpretation:
- current Engine B runner, runtime, downstream seams, refusal handling, and standalone adapter are green on the audited bundle

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-7 code surface

The simplified doctrinal story often compresses Build 7 to:
- mean reversion runner
- local mean and z-score

Current repo-truth is broader:
- canonical runner
- canonical runtime
- scoring integration
- risk integration
- sweep-validation hook
- refusal-record generation
- forecast / signal-candidate projection

Interpretation:
- this is not dangerous code drift
- it is a documentation compression drift

### Divergence 2 - later doctrinal layers have already landed additively inside Engine B

Observed in current code:
- scoring and risk are already first-class Engine-B runtime dependencies
- forecast candidate construction and downstream annotation are already part of runtime behavior
- standalone adapter exists as a public additive surface

Interpretation:
- later doctrine is not merely planned for Engine B
- a meaningful part of it has already landed in current repo-truth

### Divergence 3 - the standalone adapter is real, but it is not the canonical runtime rail

Observed in:
- `src/engines/engine_b/signal_candidate_adapter.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_forecast_support.py`

Current repo-truth:
- `EngineBRuntime` remains the main Build-7 rail
- the standalone adapter is a public additive projection module

Interpretation:
- this is not a conflict
- but a markdown or backlog that talks only about adapters or only about the runner is incomplete for current Engine-B code-truth

### Divergence 4 - the historical smoke scenario drift was real and has already been resolved in favor of the engine

Observed in:
- `tests/test_execution_backbone/test_build9_core_smoke_script.py`
- `scripts/run_build9_core_smoke.py`

Repo-truth:
- the old smoke expectation around Engine B favorable inputs had drifted
- the engine behavior was the correct source of truth
- the smoke scenario was later realigned by adding the needed `flow_coherence=0.8` input in the canonical Build-9 smoke script

Interpretation:
- the meaningful drift around Build 7 was not a broken current engine
- it was a stale smoke/test narrative that had to be brought back in line with the live doctrinal engine seam

## Decision

`PARTIAL`

## Why

Build 7 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- real `run_engine_b(...)`
- typed Engine B inputs / outputs / decisions
- real `EngineBRuntime`
- scoring / ranking / portfolio integration
- risk-runtime integration
- forecast/signal-candidate projection seams
- standalone public adapter surface
- already-resolved smoke drift in favor of engine code-truth

So Build 7 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for four concrete reasons:

1. the markdown story underdescribes how broad the current Build-7 surface now is
2. later doctrinal runtime/scoring/risk layers have already landed materially in code
3. the adapter surface is real but additive, while the canonical Build-7 rail remains the runner+runtime path
4. the main proven historical drift around Engine B was a stale smoke scenario, not a code defect in the engine

So the correct ruling is:
- Build 7 is operationally real and healthy
- but the doctrinal/test narrative has been narrower and sometimes stale relative to the current repo-truth implementation

## Patch Target

`docs only`
