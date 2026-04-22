# Build 5 Repo-Truth Audit - Scoring Backbone - 2026-04-22

## Scope

This note audits **Build 5** only:

- `scoring_backbone.scoring_runtime*`
- current raw-score, penalty, hard-block, and ranking-router surfaces
- current forecast-normalization, break-even, fee-aware-edge, and threshold seams
- the engine-runtime scoring seams currently calling Build 5

It answers one question:

> Does current Build-5 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Scoring Backbone and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 5:

- Build 5 is the governed **Scoring Backbone** stage.
- It must own the hard/soft/rank scoring rail before later engine/runtime
  layers rely on it.
- It must remain typed, auditable, and fail-closed.
- Later docs 19/20 also describe additive scoring surfaces such as:
  - `forecast_normalizer.py`
  - `break_even_filter.py`
  - `ml_fusion.py`

## Repo-Truth Surface

### 1. Build 5 is a real stateful runtime, not just score helpers

Observed in:
- `src/scoring_backbone/scoring_runtime.py`
- `src/scoring_backbone/scoring_runtime_support.py`

Current repo-truth Build-5 runtime includes:
- `ScoringRuntime`
- typed `ScoringCandidateInput`, `ScoringCandidateAudit`, `ScoringRoundResult`
- explicit `now` requirement via `require_runtime_timestamp(...)`
- structured explainability and economics projections
- physics projection from `data_backbone.market_physics_math`
- bounded soft-penalty hook seams

Interpretation:
- Build 5 is not a loose collection of math helpers
- it is already a governed runtime rail with explicit audit surfaces

### 2. The primary scoring chain is real and broader than the build-order summary

Observed in:
- `src/scoring_backbone/scoring_runtime.py`

Current repo-truth scoring chain includes:
- feature selection
- raw score calculation
- score reporting
- score penalty aggregation
- size penalty aggregation
- penalty-cap / phantom-risk evaluation
- hard-block evaluation and reason encoding
- ranking candidate construction
- portfolio compatibility checking
- ranking-score computation
- selection resolution
- full round-audit reconciliation

Interpretation:
- current Build 5 is broader than a short `hard/soft/rank` label
- it already includes portfolio-aware routing and typed round reconciliation

### 3. Build 5 already exposes additive economics / calibration seams

Observed in:
- `src/scoring_backbone/__init__.py`
- `src/scoring_backbone/forecast_normalizer.py`
- `src/scoring_backbone/break_even_filter.py`
- `src/scoring_backbone/fee_aware_edge_gate.py`
- `src/scoring_backbone/ev_net_floor_thresholds.py`
- engine-specific threshold resolvers under `src/scoring_backbone/`

Current repo-truth also includes:
- forecast normalization
- break-even filtering
- fee-aware edge gating
- shared EV-net floors
- engine-specific cost / breakout / excess / invalidation / continuation /
  coordination / first-episode threshold resolvers

Interpretation:
- later scoring doctrine has already landed partly in code
- Build 5 is not limited to the original raw-score rail anymore

### 4. Engines already depend on Build 5 on the hot path

Observed in:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_d/engine_d_runtime.py`

Current repo-truth:
- engine runtimes construct `ScoringCandidateInput`
- engine runtimes call `ScoringRuntime.run_round(...)`
- engine runtimes resolve `scoring_audit`
- scoring outcomes map into runtime statuses such as:
  - hard blocked
  - rejected ranking
  - rejected portfolio
  - accepted
- forecast/runtime support layers consume `scoring_audit` for reason codes,
  conditioning, and post-run annotations

Interpretation:
- Build 5 is not theoretical
- it is already part of the real per-signal engine hot path

## Verification Evidence

### Build-5 runtime, additive seams, and forecast-contract integration

Command:

```powershell
python -m pytest tests/test_scoring_backbone/test_scoring_runtime.py tests/test_scoring_backbone/test_scoring_integration.py tests/test_scoring_backbone/test_raw_score_builder.py tests/test_scoring_backbone/test_ranking_router.py tests/test_scoring_backbone/test_penalty_aggregator.py tests/test_scoring_backbone/test_hard_block_gate.py tests/test_scoring_backbone/test_forecast_normalizer.py tests/test_scoring_backbone/test_break_even_filter.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py tests/test_scoring_backbone/test_ev_net_floor_thresholds.py tests/test_interface_contracts/test_forecast_contracts.py -q --tb=short
```

Result:
- `175 passed`

### Notes on local sandbox behavior

Observed once during the first run:
- four tests in `test_fee_aware_edge_gate.py` failed under sandbox because
  their fixtures could not create `build/...` temporary directories

Rerun outside the sandbox:
- full command passed with `175 passed`

Interpretation:
- not a Build-5 doctrine/code issue
- no audited Build-5 functional failure

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-5 code surface

The simplified doctrinal story often compresses Build 5 to:
- hard scoring
- soft scoring
- ranking

Current repo-truth is broader:
- stateful `ScoringRuntime`
- explicit timestamp discipline
- typed explainability and economics projections
- bounded soft-penalty hook seam
- physics projection seam
- portfolio compatibility checking
- round-level audit reconciliation
- engine-facing additive forecast / threshold utilities

Interpretation:
- this is not dangerous code drift
- it is a documentation compression drift

### Divergence 2 - later docs 19/20 are mixed: some scoring add-ons are real, one remains planned

Observed in current code:
- `forecast_normalizer.py` exists
- `break_even_filter.py` exists

Observed in current codebase:
- `src/scoring_backbone/ml_fusion.py` does not exist

Interpretation:
- later markdown is neither fully ahead of code nor fully behind it
- part of the later scoring doctrine has already landed
- `ml_fusion.py` remains planned rather than current repo-truth

### Divergence 3 - the build-order description is directionally right but too compressed

Observed in:
- `src/manifest_registry/build_order_registry.py`

Current build-order description:
- `Hard/soft/rank scoring pipeline`

Current repo-truth is broader:
- governed round runtime
- typed scoring audit and economics projection
- portfolio compatibility and selection resolution
- forecast / break-even / fee-aware-edge seams
- engine hot-path integration

Interpretation:
- the registry description is directionally correct
- but operationally underdescribes the real Build-5 seam

## Decision

`PARTIAL`

## Why

Build 5 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- real `ScoringRuntime`
- typed scoring candidate / audit / round contracts
- raw-score, penalty, hard-block, and ranking runtime chain
- forecast normalization and break-even seams
- fee-aware-edge and EV-net floor surfaces
- engine-specific threshold resolvers
- engine-runtime hot-path integration

So Build 5 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-5 surface now is
2. later docs 19/20 are mixed, with some planned scoring seams already landed and `ml_fusion.py` still absent
3. the build-order description is directionally correct but operationally too compressed for the current implementation

So the correct ruling is:
- Build 5 is operationally real and healthy
- but the doctrinal narrative is narrower in some places and ahead of code in others

## Patch Target

`docs only`
