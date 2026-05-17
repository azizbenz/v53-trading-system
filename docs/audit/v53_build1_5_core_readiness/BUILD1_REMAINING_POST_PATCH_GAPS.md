# Build-1 Remaining Post-Patch Gaps

Date: `2026-05-01`

## Build-1 blocker status

No Build-1 blocker from the prior core-readiness audit remains open after this correction patch.

## Remaining non-blocking governance debt

1. Accepted engineering-guardrail baseline debt remains high.
   - Current accepted baseline fingerprints: `3476`
   - Status: `NOT_BLOCKING`
   - Why it stays visible:
     - baseline-aware smoke is green
     - legacy debt is still real and should be reduced over time
     - green means `new_violations=0`, not `total_violations=0`

2. Build-1 cockpit visibility depends on the latest smoke artifact refresh.
   - Artifact path: `build/build9_core_smoke/build1_core_health.json`
   - Status: `RESOLVED_PATCHED` for projection logic, but operators still need a fresh artifact for current truth

## What remains outside Build-1

- Build-3 stays partial for cost proof and fill realism.
- Build-4 stays partial for true drawdown, capital readiness, and richer covariance work.
- Build-5 stays partial for promotion-grade economics and downstream explainability/completeness.
