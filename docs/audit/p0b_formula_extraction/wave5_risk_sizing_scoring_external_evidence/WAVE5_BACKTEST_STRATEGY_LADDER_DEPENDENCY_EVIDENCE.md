# Wave 5 Backtest Strategy Ladder Dependency Evidence

Role boundary:
- This document maps Wave 5 dependencies for the planning spec.
- It does not implement the Backtest Strategy Ladder.

Primary planning source:
- `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md`

## Planning evidence excerpts

Relevant planning statements:
- the ladder asks whether edge survives fees, spread, slippage, and partial fills
- the ladder explicitly asks whether the system works with `400 EUR`, `500 EUR`, `1000 EUR`, `2000 EUR`, and `4000 EUR`
- the ladder requires blocked / refusal / no-trade accounting
- the ladder requires capital levels, min-notional / step size / tick size, fee model, slippage model, and walk-forward / OOS evidence

Relevant planning excerpt summary:
- capital ladder depends on candidate outputs, replay outputs, cost realism, fill realism, and signed calibration artifacts
- hard fail if non-trades are omitted, walk-forward overlaps, timestamps leak, or slippage uses optimistic constants without provenance

## Wave 5 fields needed before future capital ladder coding

Required already-existing or partially-existing fields:
- `expected_ce`
- `expected_cost`
- `expected_total_cost_mean`
- `fee_source_status`
- `impact_source_status`
- `cost_model_completeness_status`
- `fill_ratio_source`
- `fill_realism_status`
- `realized_slippage_status`
- `small_capital_exclusion_rate`
- explicit refusal / no-trade reason codes
- venue `min_notional`, `step_size`, and `tick_size`
- cluster, beta, loss, and gross-cap outcomes

Still missing or partial for future ladder:
- true executed-only net return
- true net-equity max drawdown
- measured small-capital exclusion rate
- replay-vs-live expected/realized cost parity mapping
- measured-vs-synthetic fill provenance
- per-pair fee/impact/slippage calibration or doctrine closure

## Small-capital requirements from planning vs current code

Planning asks:
- 400 EUR case handles min-notional
- 500 EUR case handles fees
- 1000/2000/4000 EUR cases recompute slippage
- blocked trade counted as blocked, not omitted

Current code proves:
- fail-closed min-notional normalization exists
- blocked/no-trade reason codes are preserved through execution and portfolio rails
- replay/cockpit small-capital status fields exist

Current code does not yet prove:
- pair-level 400-500 EUR viability artifact
- fee-aware and slippage-aware exclusion report by capital bucket
- capital-fragmentation study across multi-pair universes

## Walk-forward / OOS dependencies

Planning dependencies:
- no lookahead
- embargo / fold separation
- OOS net edge and OOS drawdown
- stable refusal accounting

Wave 5 relevance:
- score/risk/cost semantics must be explicit before a future ladder can claim OOS promotion readiness
- replay expected CE cannot substitute for executed-only net return in future capital-ladder summaries

## Contradictions or tension points

1. Planning spec expects fee-model and slippage-aware capital evaluation.
   Current replay evidence still allows `cost_model_completeness_status = PARTIAL_NO_FEE_NO_IMPACT`.

2. Planning spec expects capital-feasibility claims at 400/500 EUR.
   Current small-capital exclusion rail is still `NOT_PROVEN`.

3. Planning spec expects drawdown-aware promotion.
   Current replay economics still has only `drawdown_proxy` as a diagnostic replay rail.

4. Planning spec expects blocked trades to remain counted.
   Current code is aligned here; portfolio, scoring, risk, and execution all preserve explicit rejection/no-trade accounting.

## Recommended prerequisites before coding ladder Batch 1+

- freeze the semantics of expected CE vs realized profitability
- settle replay cost completeness doctrine or explicit fee/impact provenance
- produce a measured small-capital exclusion artifact
- produce executed-only realized net-return and net-equity drawdown rails
- keep refusal / no-trade accounting explicit across discovery, replay, and ladder outputs

