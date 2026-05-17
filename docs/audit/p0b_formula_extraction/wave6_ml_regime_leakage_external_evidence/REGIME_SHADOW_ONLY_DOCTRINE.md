# Regime Shadow-Only Doctrine

Date: 2026-04-30

## Canonical doctrine

- Regime runtime outputs are non-directional only.
- Regime runtime signal is `shadow_only`.
- No scoring consumer is currently proven.
- No risk consumer is currently proven.
- No execution consumer is currently proven.
- Future scoring/risk/execution use requires an external consumer audit first.

## Allowed runtime outputs

- `regime_transition_risk`
- `regime_stability_score`
- `market_toxicity_score`
- `expected_duration_bucket`

## Forbidden runtime outputs

- `side`
- `buy_probability`
- `sell_probability`
- `direction_up_300s_fee_safe`
- `direct_trade_decision`
- any directional label or future-return target

## Safety consequences

- regime cannot create side
- regime cannot create trades
- regime cannot become a hidden directional engine

## Promotion doctrine

- any future attempt to inject regime into scoring/risk/execution is `FUTURE_RESERVED`
- promotion requires direct consumer proof and external audit

