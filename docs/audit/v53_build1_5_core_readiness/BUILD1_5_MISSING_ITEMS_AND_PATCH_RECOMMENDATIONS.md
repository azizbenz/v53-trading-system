# Build-1 to Build-5 Missing Items and Patch Recommendations

Date: `2026-05-01`

## Missing Items

### Immediate core-governance gaps

- Build-stage registry does not include `cockpit` even though inventory does.
- Dependency registry does not allow the observed `cockpit -> data_backbone` import.
- Build-1 smoke is not green because engineering guardrails still report `107` new violations beyond baseline.

### Execution-readiness gaps

- replay fee provenance remains partial
- replay impact provenance remains partial
- measured fill realism remains partial
- replay/live cost parity remains partial

### Risk/scoring readiness gaps

- true executed-only net return is still missing
- true net-equity max drawdown is still missing
- small-capital viability remains blocked by backtest evidence
- richer covariance control remains future work

### Cockpit gaps

- Build-1 red-state health is not operator-visible
- Build-3 build-level execution-health status is weaker than the runtime/test surface

## Recommended Patches

### Patch now

1. Align `module_inventory.py`, `build_order_registry.py`, and `dependency_registry.py` on the canonical status of `cockpit`.
2. Resolve the unauthorized `cockpit -> data_backbone` edge either by registry declaration or by code-path refactor.
3. Clear or explicitly re-scope the `107` new engineering guardrail violations that block Build-1 smoke.
4. Add an operator-facing Build-1 core-health surface if foundational readiness needs to be visible in cockpit.

### Patch soon, but not in the same critical slice

1. Add explicit build-level execution-health projection to cockpit if operators need it.
2. Add true executed-only profitability and true drawdown rails to close the remaining promotion-grade economics gap.
3. Add measured fill/cost parity evidence and small-capital viability artifacts.

### Can wait

1. Broader cockpit expansion on downstream analytics pages.
2. Richer covariance controls beyond baseline caps.
3. Later capital-ladder, ML, and regime promotion work already tracked by Wave 5 and Wave 6.

## Non-Recommendations

- Do not rewrite the canonical build architecture.
- Do not create a second contract rail.
- Do not hide the Build-1 failures behind later-build green tests.
- Do not call later build surfaces cockpit-ready just because runtime code exists.
