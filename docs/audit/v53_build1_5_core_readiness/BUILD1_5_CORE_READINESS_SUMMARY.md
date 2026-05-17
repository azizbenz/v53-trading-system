# V5.3 Build-1 to Build-5 Core Readiness Summary

Date: `2026-05-01`
Scope: source-level audit of the canonical V5.3 core build foundation before further engine, portfolio, shadow/live, cockpit, and backtest-capital promotion work.

## Verdicts

- Build-1 verdict: `BLOCKED_BY_DAG`
- Build-2 verdict: `READY`
- Build-3 verdict: `PARTIAL`
- Build-4 verdict: `PARTIAL`
- Build-5 verdict: `PARTIAL`
- Build-1 -> Build-5 core foundation verdict: `BLOCKED_BY_BUILD1`

## Evidence Base

Canonical build mapping and dependency evidence:

- `src/manifest_registry/module_inventory.py`
- `src/manifest_registry/build_order_registry.py`
- `src/manifest_registry/dependency_registry.py`
- `src/dag_validator/*`
- `src/smoke_bootstrap_recovery/*`
- `scripts/run_build9_core_smoke.py`

Build runtime evidence:

- `src/data_backbone/*`
- `src/execution_backbone/*`
- `src/risk_backbone/*`
- `src/scoring_backbone/*`
- `src/cockpit/*`

Validation evidence:

- Build-1 band: `331 passed, 10 failed`
- Build-1 failing subset: `69 passed, 8 failed`
- Build-2..5 band: `912 passed`
- `run_build9_core_smoke.py`: Build-1 `FAIL`; Build-2..9 `PASS`

## What Is Solid

- Canonical module inventory, build-stage registry, dependency registry, DAG validator, contract test suite, bootstrap recovery rail, and calibration loader all exist in source and are typed.
- Build-2 data backbone is materially implemented and well-covered: websocket gateway, REST bootstrap, gap fill, freshness, consistency, pair health, normalized market events, and microstructure rails are present.
- Build-3 execution backbone is materially implemented and well-covered: gatekeeper, order decider, routing bridge, venue constraints, spread guard, rate limiter, slippage model, fill tracker, execution cost meter, reconciliation layer, and halal fail-close guards are present.
- Build-4 risk backbone is materially implemented and well-covered: runtime models, explainability, loss budgeting, exposure caps, BTC beta guard, cluster guard, breaker rails, and explicit missing-input semantics are present.
- Build-5 scoring backbone is materially implemented and well-covered: candidate input contract, raw-score pipeline, hard-block pipeline, ranking router, cost completeness carriage, non-positive ML modulation compatibility, and supplementary-ref neutralization are present.

## What Is Missing

- Build-1 is not green because the canonical governance rails disagree on `cockpit`.
- `cockpit` exists in module inventory and dependency registry, but it is missing from `BUILD_STAGES`, so manifest consistency fails.
- The real-code DAG still reports one unauthorized edge: `cockpit -> data_backbone`.
- Build-1 smoke is not clean because engineering guardrails report `107` new violations beyond baseline in the current repo state.
- Build-3 remains partial on measured fee/impact/fill realism and realized-cost parity.
- Build-4 remains partial on true drawdown, small-capital readiness, and richer covariance control.
- Build-5 remains partial on promotion-grade economics because expected CE is still expected-only and incomplete cost cannot go green.

## What Must Be Patched Now

- Align `manifest_registry/build_order_registry.py` with the current canonical inventory so every governed module has a declared stage, including a consistent decision on `cockpit`.
- Resolve the `cockpit -> data_backbone` dependency mismatch either in registry policy or in cockpit import structure.
- Clear or explicitly re-scope the `107` new engineering guardrail violations that currently fail Build-1 smoke.
- Add cockpit visibility for Build-1 core health if operator-facing foundational readiness is required.

## What Can Wait

- Broader cockpit projection of every downstream build-health artifact.
- Replay/live cost parity, measured fill realism, capital-ladder viability artifacts, and true executed-only profitability rails.
- Future covariance model promotion, richer portfolio readiness rails, and later ML/regime promotion items already tracked elsewhere.

## What Blocks Shadow

- Build-1 core governance is not clean yet.
- True executed-only net return is still missing.
- True net-equity max drawdown is still missing.
- Replay fee/impact completeness and fill realism are still partial.
- Engine C/D engine-specific promotion artifacts remain open.

## What Blocks Micro-live

- All Shadow blockers remain.
- Small-capital viability and capital-profile artifacts remain backtest-blocked.
- Build-3 measured fill realism and Build-4 capital readiness remain partial.
- ML live governed source, live drift source, and anti-leakage artifact implementation remain open if ML is ever promoted.

## What Blocks Live

- All Micro-live blockers remain.
- The Build-1 foundation must be coherent before stronger live-readiness claims.
- Live balance-driven sizing proof, replay/live economics parity, and governed live artifact freshness remain incomplete.

## Build-Level Notes

### Build-1

Implemented and tested, but not green. The failures are structural and explicit, not hidden:

- missing build-stage assignment for `cockpit`
- unauthorized `cockpit -> data_backbone` dependency
- engineering guardrail failure in the smoke rail

### Build-2

Core data acquisition and normalization are implemented, typed, and heavily tested. No major source-level hole was found in the canonical backbone itself.

### Build-3

Execution safety doctrine is strong, but measured execution-realism proof is still incomplete. This is a readiness gap, not a missing-runtime gap.

### Build-4

Risk semantics and fail-close posture are strong, but promotion-grade drawdown and capital-readiness proof remain incomplete.

### Build-5

Scoring semantics and neutrality rules are strong, but expected-only economics and partial cost completeness remain gating limitations.
