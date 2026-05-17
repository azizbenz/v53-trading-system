# Cost Recomposition After Cap Reduction Spec

Purpose:
- define the promotion-grade economics doctrine after size reduction by portfolio caps

## Desired recomputation fields

- `expected_fee_bps`
- `expected_slippage_bps`
- `expected_impact_bps`
- `expected_total_cost_bps`
- `expected_ce_after_allocation`

## Doctrine

Current compatibility path:
- proportional scaling of expected edge and expected cost after cap reduction remains allowed for compatibility

Promotion-grade path:
- explicit recomputation after size reduction is preferred
- if explicit recomputation is absent, status must stay `NOT_PROVEN`

## Rules

- no invented recomputed measured values
- missing recomputation must block green promotion readiness
- replay expected CE remains expected-only
- recomputation doctrine must stay separate from realized profitability rail

## Status doctrine

Allowed status examples:

- `EXPLICIT_RECOMPUTATION`
- `PROPORTIONAL_SCALING_COMPATIBILITY`
- `NOT_PROVEN`
- `NEEDS_MORE_DATA`
