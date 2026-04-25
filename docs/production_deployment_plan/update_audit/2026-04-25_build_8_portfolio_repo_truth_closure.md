# Build 8 Repo-Truth Closure - Portfolio Minimal - 2026-04-25

## Scope

This closure note resolves **Build 8** only:

- `src/portfolio/`
- `src/portfolio_minimal/`
- the canonical portfolio-to-execution projection seam
- the repo-truth gap identified in
  [2026-04-21_build_8_portfolio_repo_truth_audit.md](./2026-04-21_build_8_portfolio_repo_truth_audit.md)

The purpose of this closure is narrow:

> confirm whether the prior mixed Build-8 gap is now closed on the current
> branch, or whether meaningful doctrine/code drift still remains.

## Governing Inputs

Primary sources used for closure:

- `src/portfolio/`
- `src/portfolio_minimal/`
- `src/protocols/execution_opportunity_bridge.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/update_audit/2026-04-21_build_8_portfolio_repo_truth_audit.md`

## Closure Reading

The 2026-04-21 audit conclusion was accurate for the branch state at that time:

- Build 8 was already real, typed, green, and canonical on the `portfolio` facade
- the remaining gap was not a redesign issue
- but two additive doctrine/code seams were still absent:
  - Carver-style vol-target sizing
  - Narang-style `PortfolioArbitrationRecord`

Those two seams are now present on the current branch.

Current repo-truth Build 8 now includes:

- canonical `portfolio` facade
- typed `OpportunityCandidate` seam
- real candidate pooling / conflict arbitration / ranking / structural selection
- real allocation / cap / phantom sterilization pipeline
- canonical projection toward `ExecutionOpportunity`
- bounded relative-rank hook seam
- additive Carver-style `vol_target_sizer.py`
- additive Narang-style `arbitration_record.py`
- orchestrator-level attachment of arbitration records to promoted or rejected
  portfolio intents

The current repo-truth Build-8 interpretation is therefore:

- Build 8 is not merely a minimal selector/allocation helper
- Build 8 already owns the canonical portfolio rail
- Carver-style sizing is now present as an additive governed seam
- Narang-style promoted/rejected arbitration grammar is now present as an
  additive governed seam
- no parallel portfolio rail was introduced

## Verification Evidence

### Portfolio selector / allocation / orchestrator / strong Build-8 slice

Command:

```powershell
python -m pytest tests/test_portfolio_minimal/test_opportunity_selector_minimal.py tests/test_portfolio_minimal/test_allocation_router_minimal.py tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py tests/test_portfolio_minimal/test_vol_target_sizing.py tests/test_portfolio_minimal/test_arbitration_record.py tests/test_portfolio/test_canonical_portfolio.py -q --tb=short --basetemp=tmp_pytest_build8_strong
```

Result:

- `97 passed`

### Canonical downstream projection seam

Command:

```powershell
python -m pytest tests/test_portfolio/test_canonical_portfolio.py tests/test_protocols/test_execution_opportunity_bridge.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q --tb=short --basetemp=tmp_pytest_build8_strong_bridge_escalated
```

Result:

- `14 passed`

### Environment note

The downstream bundle reproduced the already-known local sandbox artifact before
rerun:

- several smoke tests attempted to create directories under `build/...`
- sandbox run failed with local `PermissionError`
- rerun outside the sandbox passed cleanly

Interpretation:

- this is an environment proof issue only
- no Build-8 doctrine/code regression was observed

## Decision

`Build 8 = COMPLETE`

## Why

Build 8 is no longer honestly `PARTIAL` on the current repo-truth reading.

The prior gap was:

- later Carver/Narang portfolio enrichments were still absent as first-class
  repo surfaces
- the current sizing chain remained purely pre-Carver minimal

That gap is now closed by explicit additive implementation:

- `src/portfolio_minimal/allocation_router/vol_target_sizer.py`
- `src/portfolio_minimal/arbitration_record.py`
- orchestrator wiring that keeps the canonical rail intact

No Build-8 redesign was required.
No second canon was introduced.
No execution ownership was moved into the portfolio package.

So the correct closure reading is:

- current Build 8 code is real and governed
- the missing additive Carver/Narang seams are now present
- the proof bundles are green

## Final Verdict

Safe closure classification:

- `Build 8 = COMPLETE (real canonical portfolio rail, typed portfolio-to-execution projection, additive Carver-style vol-target sizing, and additive Narang-style PortfolioArbitrationRecord are present and proven on the current branch)`
