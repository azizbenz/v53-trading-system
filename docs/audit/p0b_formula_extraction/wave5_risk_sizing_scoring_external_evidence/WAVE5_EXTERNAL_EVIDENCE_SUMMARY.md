# Wave 5 External Evidence Summary

Role boundary:
- Evidence extraction only.
- No scientific self-certification.
- No formula approval.
- No code, engine, runtime, or test mutation in this Wave 5 pack.

MemPalace:
- Check performed.
- Project memory was found only as partial historical context.
- Source of truth for Wave 5 is the current codebase, current tests, and the Wave 1-4 audit docs.

Scope covered:
- scoring formulas
- break-even / EV / CE gates
- risk candidates and runtime guards
- position sizing and portfolio allocation
- exposure, beta, cluster, drawdown, and daily loss control
- min-notional and small-capital feasibility seams
- pipeline order and refusal / no-trade persistence
- cockpit false-green protections
- side / halal / spot-only safety
- gap-register update recommendations
- Backtest Strategy Ladder dependencies

Key evidence findings:
- `ce_net` remains expected CE, not realized profitability; Wave 5 does not contradict Wave 2.
- Scoring is additive raw score, additive penalties, then capped penalty / phantom-risk handling.
- ML confidence is non-sovereign in the inspected rail. It can modulate score confidence or remain neutral, but direct override is explicitly forbidden.
- Engine C and Engine D remain partial-by-design for shared scoring physics; the carriage and reason-code seams remain explicit.
- Break-even / EV / CE gates exist in both shared and engine-local seams, but no governed scoring or risk runtime consumer for Wave 3 cost-completeness statuses was proven by source search.
- Runtime risk controls are real rails: gross cap, position cap, cluster cap, beta cap, drawdown guard, and daily PnL breaker.
- Active portfolio and sizing evidence lives in `src/portfolio_minimal`; `src/portfolio_backbone/` was not present in the inspected tree.
- Kelly / fractional Kelly sizing was not found in the inspected sizing rails.
- Venue min-notional normalization is fail-closed at execution time, but replay small-capital exclusion is still reported as `NOT_PROVEN`.
- Cockpit replay economics already carries partial-cost, stale, sample-size, and placeholder protections, but some portfolio / small-capital governance seams are still informational rather than measured.

High-signal unresolved questions:
- Can a candidate still clear runtime score / risk gates even though replay cost completeness is partial? Source search suggests yes, because runtime score/risk rails do not consume `cost_model_completeness_status`.
- Is current allocation logic scientifically sufficient for 400-500 EUR trading across a multi-pair universe? The code proves fail-closed min-notional normalization, but not a pair-level viability study.
- Is 12-pair multi-asset risk sufficiently controlled by the current gross / pair / cluster / beta caps alone, or is a richer correlation rail still needed?
- Does the current capital rail need an executed-only realized net-return seam before any future capital ladder can make promotion-grade claims?

Validation status:
- See [WAVE5_TEST_COVERAGE_EVIDENCE.md](./WAVE5_TEST_COVERAGE_EVIDENCE.md) for the exact commands, discovered paths, assertions, and any environment failures.

