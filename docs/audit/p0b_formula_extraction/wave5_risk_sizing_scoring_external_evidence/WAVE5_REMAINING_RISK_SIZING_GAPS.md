# Wave 5 Remaining Risk / Sizing Gaps

This list stays open after the semantic-safety patch.

## Open gaps

1. Runtime cost completeness hard-gating is still partial by design.
Evidence:
- strict break-even mode can reject incomplete economics
- broader runtime score/risk acceptance still uses additive readiness semantics rather than universal hard rejection

2. Small-capital viability is not measured.
Evidence:
- fail-closed min-notional protection exists
- 400 / 500 / 1500 / 4000 scenario artifacts do not yet exist

3. Live/shadow balance adaptation is not proven.
Evidence:
- `portfolio_minimal` sizes from configured/profiled `available_capital`
- a governed runtime free-quote-balance source feeding that rail was not proven

4. Capital fragmentation guard is not proven.
Evidence:
- baseline caps exist
- pair-universe-too-wide-for-capital logic is not proven as a dedicated guard

5. Min-notional viability awareness at sizing stage is not proven.
Evidence:
- execution normalization blocks invalid orders fail-closed
- sizing-stage feasibility warning remains partial

6. Cost recomputation after size/cap reduction is only partially proven.
Evidence:
- phantom guard rescales expected edge and expected cost by size ratio
- full fee / impact / slippage recalculation across capital buckets is not proven

7. True executed-only net return is still missing.
Evidence:
- expected CE remains distinct from realized profitability

8. True net-equity max drawdown is still missing.
Evidence:
- replay `drawdown_proxy` remains non-promotion-grade

9. Kelly sizing is still intentionally absent.
Evidence:
- no Kelly route was added
- doctrine remains fixed-fraction + vol-target + caps

10. Full covariance model is still intentionally absent.
Evidence:
- portfolio rail remains pair/gross/cluster/beta caps only

## Promotion consequence

These remaining gaps mean:
- green semantics are harder to fake
- but scientific readiness for capital-sensitive promotion still requires more evidence

## Next dependencies

- Backtest Strategy Ladder capital scenarios
- measured capital-exclusion artifacts
- governed runtime balance source proof
- executed-only realized return rail
- true net-equity drawdown rail
- richer multi-asset OOS evidence if covariance control is later proposed
