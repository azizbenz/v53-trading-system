# Build 8 Repo-Truth Audit - Portfolio Minimal - 2026-04-21

## Scope

This note audits **Build 8** only:

- `portfolio`
- `portfolio_minimal`
- the current typed input/output seam of the portfolio pipeline
- the current downstream relationship between portfolio output and Build 3 execution

It answers one question:

> Does current Build-8 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected portfolio layer and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 8:

- Build 8 is the canonical portfolio layer.
- It must own:
  - candidate pooling from surviving engine outputs
  - comparison / ranking / conflict arbitration
  - structural selection
  - capital allocation under portfolio caps
  - phantom-trade sterilization
- It must stay typed and auditable.
- Later Carver / Narang enrichments are expected to land additively:
  - Carver-style vol-target sizing
  - Narang-style portfolio arbitration record
- It should connect coherently to downstream execution, without inventing a
  parallel portfolio rail.

## Repo-Truth Surface

### 1. Canonical facade exists and is stable

Observed in:
- `src/portfolio/__init__.py`

Current public facade exports:
- `allocation_router`
- `opportunity_selector`
- `OrchestratorConfig`
- `OrchestratorResult`
- `run_portfolio_pipeline`

Interpretation:
- Build 8 has a governed canonical import surface
- the real implementation lives in `portfolio_minimal`, but the public build
  identity remains `portfolio`

### 2. Typed upstream input is real

Observed in:
- `src/portfolio_minimal/opportunity_selector/candidate_pool_builder.py`

Current typed upstream candidate seam is:
- `OpportunityCandidate`

It already carries the core portfolio inputs:
- pair / engine
- direction
- emitted time
- penalized score / raw score
- CE / expected cost / EV net
- candidate size
- tier suggestion
- cluster id
- loss / beta impact
- holding horizon
- scoring version

Interpretation:
- Build 8 is not operating on anonymous dictionaries
- the upstream portfolio input seam is already explicit and typed

### 3. Real orchestration pipeline exists end-to-end

Observed in:
- `src/portfolio_minimal/portfolio_orchestrator.py`

Current `run_portfolio_pipeline(...)` path is real:
1. `build_candidate_pool(...)`
2. `check_conflicts(...)`
3. `rank_candidates(...)`
4. `resolve_selection(...)`
5. `compute_base_size(...)`
6. `compute_modulated_size(...)`
7. `apply_caps(...)`
8. `check_phantom(...)`
9. `build_report(...)`

Interpretation:
- Build 8 is operationally real
- selection and allocation are already separated cleanly
- the current pipeline is typed, deterministic, and auditable

### 4. Typed downstream output is real and now has a canonical execution projection seam

Observed in:
- `src/portfolio_minimal/portfolio_orchestrator.py`
- `src/portfolio_minimal/allocation_router/allocation_reporter.py`
- `src/protocols/execution_opportunity_bridge.py`
- `src/portfolio/__init__.py`

Current downstream portfolio outputs are:
- `OrchestratorResult`
- `SelectionResult`
- `AllocationReport`
- `AllocationEntry`
- `SelectionEntry`
- protocol bridge helpers toward `ExecutionOpportunity`

These outputs expose:
- selected vs rejected candidates
- viable allocations vs phantoms
- remaining gross / loss / beta / cluster capacities

Interpretation:
- Build 8 does return a real promoted-allocation surface
- and current repo-truth now includes a canonical typed bridge in `protocols`
  that projects viable portfolio output into `ExecutionOpportunity`
- while keeping Build 8 itself free of direct execution ownership

### 5. Relative-rank extension seam already exists

Observed in:
- `src/portfolio_minimal/portfolio_orchestrator.py`

Current bounded hook surface:
- `PortfolioRelativeRankAdjustmentInput`
- `PortfolioRelativeRankAdjustmentOutcome`
- `PortfolioRelativeRankAdjustmentHook`

Interpretation:
- Build 8 is already designed for bounded additive portfolio influence
- this is consistent with V5.3 governance discipline

## Verification Evidence

### Portfolio selector / allocation / orchestrator / canonical facade

Command:

```powershell
python -m pytest tests/test_portfolio_minimal/test_opportunity_selector_minimal.py tests/test_portfolio_minimal/test_allocation_router_minimal.py tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py tests/test_portfolio/test_canonical_portfolio.py -q --tb=short
```

Result:
- `90 passed`

### Canonical downstream projection seam

Command:

```powershell
python -m pytest tests/test_portfolio/test_canonical_portfolio.py tests/test_protocols/test_execution_opportunity_bridge.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q --tb=short
```

Result:
- `14 passed`

### Notes on warnings

Observed warning:
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-8 doctrine/code issue
- no audited Build-8 functional failure

## Observed Divergence

### Divergence 1 - doc 19 / doc 20 portfolio enrichments are still ahead of current repo-truth

Doc 19 / 20 explicitly name additive Build-8 sub-surfaces such as:
- `src/portfolio_minimal/allocation_router/vol_target_sizer.py`
- `src/portfolio_minimal/arbitration_record.py`
- `PortfolioArbitrationRecord`

Observed current repo-truth:
- `vol_target_sizer.py` is absent
- `arbitration_record.py` is absent
- no `PortfolioArbitrationRecord` is currently exported or tested

Interpretation:
- current Build 8 is real and green
- but later Carver / Narang portfolio enrichments remain backlog, not current
  repo truth

### Divergence 2 - current sizing is still the pre-Carver minimal chain

Observed current sizing stack:
- `compute_base_size(...)`
- `compute_modulated_size(...)`
- `apply_caps(...)`

Current sizing is based on:
- available capital
- base fraction
- tier
- ranking score
- gross / cluster / loss / beta caps

It is **not yet** the later doctrinal sizing chain described in doc 19 / 20:
- forecast-normalized sizing
- instrument value vol
- full Carver vol-scalar path

Interpretation:
- Build 8 current sizing is coherent
- but the later doctrine is still ahead of the implementation on this point

## Decision

`PARTIAL`

## Why

Build 8 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- canonical `portfolio` facade
- typed candidate input seam
- real ranking / conflict / selection pipeline
- real allocation / cap / phantom pipeline
- bounded hook seam
- broad non-regression test coverage

So Build 8 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. later doctrinal Build-8 enrichments from doc 19 / 20 remain unimplemented
   as first-class repo surfaces
2. current sizing remains the minimal chain, not the later Carver-canonical
   vol-target sizing chain

So the correct ruling is:
- Build 8 is operationally real and healthy
- but the doctrinal story is ahead of the current implementation on some
  additive sub-surfaces

## Patch Target

`mixed`

### Code target

Only additive future slices are justified:
- Carver-style vol-target sizing if that specific phase is opened
- Narang-style `PortfolioArbitrationRecord` if that specific phase is opened

### Docs target

Clarify that current repo-truth Build 8 already provides:
- candidate pooling
- ranking / conflict arbitration
- selection
- allocation
- phantom sterilization

But does **not yet** provide:
- Carver vol-target sizing
- Narang arbitration record

### No target

No Build-8 redesign is justified by this audit.

The current portfolio facade and orchestrator rail should stay intact.

## Final Verdict

Build 8 is operationally solid but doctrinally incomplete.

Safe operational classification:
- `Build 8 = PARTIAL (real portfolio selection/allocation layer exists and is green; a canonical portfolio-to-execution projection seam now exists, but Carver/Narang additive enrichments remain incomplete)`
